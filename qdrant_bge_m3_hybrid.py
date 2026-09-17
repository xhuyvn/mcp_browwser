from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

import httpx
from qdrant_client import QdrantClient, models


EMBEDDING_SERVER_URL = os.getenv(
    "EMBEDDING_SERVER_URL",
    "http://localhost:8000/v1/hybrid-embeddings",
)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_HTTP_PORT = int(os.getenv("QDRANT_HTTP_PORT", "6333"))
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "bge_m3_hybrid_v1",
)

EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "4"))
PASSAGE_MAX_LENGTH = int(os.getenv("PASSAGE_MAX_LENGTH", "512"))
QUERY_MAX_LENGTH = int(os.getenv("QUERY_MAX_LENGTH", "256"))


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


embedding_client = httpx.Client(
    timeout=httpx.Timeout(connect=10.0, read=300.0, write=300.0, pool=10.0),
    limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
    # Both services are local; do not route large ColBERT payloads through
    # HTTP_PROXY/HTTPS_PROXY inherited from the host environment.
    trust_env=False,
)

qdrant = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_HTTP_PORT,
    grpc_port=QDRANT_GRPC_PORT,
    prefer_grpc=True,
    api_key=QDRANT_API_KEY,
    timeout=120,
    trust_env=False,
)


def batched(items: Sequence[Any], size: int) -> Iterator[Sequence[Any]]:
    if size < 1:
        raise ValueError("Batch size must be positive")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def get_hybrid_embeddings(
    texts: Sequence[str],
    *,
    max_length: int,
) -> list[dict[str, Any]]:
    if not texts:
        return []

    response = embedding_client.post(
        EMBEDDING_SERVER_URL,
        json={"passages": list(texts), "max_length": max_length},
    )
    response.raise_for_status()
    payload = response.json()

    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise RuntimeError("Embedding server returned an invalid batch")
    return data


def sparse_vector(values: Mapping[str, float]) -> models.SparseVector:
    # Stable ordering makes requests reproducible and guarantees unique indices.
    pairs = sorted((int(index), float(value)) for index, value in values.items())
    return models.SparseVector(
        indices=[index for index, _ in pairs],
        values=[value for _, value in pairs],
    )


def setup_collection(*, recreate: bool = False) -> None:
    exists = qdrant.collection_exists(COLLECTION_NAME)
    if exists and not recreate:
        return
    if exists:
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            # Candidate retrieval: retain high recall, halve storage vs float32.
            "dense": models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE,
                datatype=models.Datatype.FLOAT16,
                memory=models.Memory.CACHED,
            ),
            # Rerank only: 4-bit storage, SSD-backed, no HNSW graph.
            "colbert": models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE,
                datatype=models.Datatype.TURBO4,
                memory=models.Memory.COLD,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                ),
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    datatype=models.Datatype.FLOAT16,
                    memory=models.Memory.COLD,
                )
            )
        },
    )


def _point_id(document_id: str) -> str:
    # Deterministic UUID makes repeated ingestion idempotent.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"bge-m3:{document_id}"))


def upsert_documents(documents: Sequence[Document]) -> int:
    if not documents:
        return 0

    inserted = 0
    for document_batch in batched(documents, EMBEDDING_BATCH_SIZE):
        texts = [document.text for document in document_batch]
        embeddings = get_hybrid_embeddings(
            texts,
            max_length=PASSAGE_MAX_LENGTH,
        )

        points: list[models.PointStruct] = []
        for document, embedding in zip(document_batch, embeddings, strict=True):
            payload = dict(document.metadata)
            payload.update(
                {
                    "document_id": document.id,
                    "text": document.text,
                    "embedding_model": "BAAI/bge-m3",
                    "embedding_format": "dense+sparse+colbert",
                }
            )

            points.append(
                models.PointStruct(
                    id=_point_id(document.id),
                    payload=payload,
                    vector={
                        "dense": embedding["dense"],
                        "sparse": sparse_vector(embedding["sparse"]),
                        "colbert": embedding["colbert"],
                    },
                )
            )

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )
        inserted += len(points)

    return inserted


def query_hybrid(
    query_text: str,
    *,
    top_k: int = 10,
    candidate_limit: int | None = None,
) -> list[models.ScoredPoint]:
    if not query_text.strip():
        raise ValueError("Query must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be positive")

    # Give ColBERT enough candidates to improve ranking.
    candidates = candidate_limit or max(50, top_k * 10)
    candidates = max(candidates, top_k)

    embedding = get_hybrid_embeddings(
        [query_text],
        max_length=QUERY_MAX_LENGTH,
    )[0]

    # Stage 1: dense and sparse retrieve candidates independently.
    # Stage 2: RRF combines their ranks.
    # Stage 3: ColBERT MaxSim reranks only the fused candidate set.
    result = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=models.Prefetch(
            prefetch=[
                models.Prefetch(
                    query=embedding["dense"],
                    using="dense",
                    limit=candidates,
                ),
                models.Prefetch(
                    query=sparse_vector(embedding["sparse"]),
                    using="sparse",
                    limit=candidates,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=candidates,
        ),
        query=embedding["colbert"],
        using="colbert",
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )
    return result.points


def close_clients() -> None:
    embedding_client.close()
    qdrant.close()


if __name__ == "__main__":
    # Windows consoles default to a legacy codepage that can't encode
    # non-ASCII text (e.g. Vietnamese); force UTF-8 so printing never crashes.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    sample_documents = [
        Document(
            id="ubuntu-24-install",
            text="Hướng dẫn cài đặt hệ điều hành Ubuntu 24.04 trên máy tính cá nhân.",
            metadata={"source": "demo"},
        ),
        Document(
            id="timeout-definition",
            text="Mã lỗi ERR_CONNECTION_TIMED_OUT xuất hiện khi trình duyệt không thể kết nối tới server.",
            metadata={"source": "demo"},
        ),
        Document(
            id="ai-ml",
            text="Trí tuệ nhân tạo và học máy đang thay đổi thế giới công nghệ.",
            metadata={"source": "demo"},
        ),
        Document(
            id="timeout-fix",
            text="Cách khắc phục ERR_CONNECTION_TIMED_OUT bằng cách đổi DNS sang 8.8.8.8.",
            metadata={"source": "demo"},
        ),
    ]

    try:
        setup_collection()
        print(f"Upserted: {upsert_documents(sample_documents)}")
        for hit in query_hybrid(
            "Làm sao sửa lỗi ERR_CONNECTION_TIMED_OUT?",
            top_k=2,
        ):
            print(f"{hit.score:.4f} | {hit.payload['text']}")
    finally:
        close_clients()
