# BGE-M3 hybrid retrieval with local Qdrant

This setup stores three BGE-M3 representations in one Qdrant collection:

- `dense`: float16 with HNSW for candidate retrieval.
- `sparse`: float16 lexical index for candidate retrieval.
- `colbert`: Turbo4 multivectors on SSD, with HNSW disabled, for reranking only.

It requires Qdrant 1.19 or later because Turbo4 multivectors were introduced in
Qdrant 1.19.

## Start Qdrant

```bash
docker compose -f docker-compose.qdrant.yml up -d
```

Dashboard: <http://localhost:6333/dashboard>

## Install the client

```bash
python -m pip install -r requirements-qdrant.txt
```

Start the BGE-M3 ONNX API on port 8000, then run:

```bash
python qdrant_bge_m3_hybrid.py
```

http://localhost:6333/dashboard
## Query pipeline

dense retrieval ─┐
                 ├─ RRF fusion ── ColBERT MaxSim rerank ── top_k
sparse retrieval ┘

1. Dense and sparse searches each produce a candidate set.
2. Reciprocal Rank Fusion combines those candidates.
3. ColBERT MaxSim reranks only the fused candidates.

The default candidate limit is `max(50, top_k * 10)`. Tune it with a retrieval
evaluation set rather than assuming a fixed value is optimal.

## Important operational notes

- `setup_collection()` is non-destructive by default. Use
  `setup_collection(recreate=True)` only when deleting the existing collection
  is intentional.
- Stable document IDs make repeated ingestion idempotent.
- Keep document ColBERT lengths near 512 tokens unless evaluation proves that
  longer vectors are worth their storage and latency cost.
- Turbo4 reduces ColBERT vector bytes by 87.5% relative to float32; total
  collection storage falls by less because payload, sparse index, metadata and
  segment overhead remain.
- The Docker ports bind to localhost only. Add authentication and TLS before
  exposing Qdrant beyond the local machine.
