import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer


MODEL_DIR = Path(
    os.getenv("MODEL_DIR", "./bge-m3-onnx")
)

MODEL_PATH = MODEL_DIR / "model.onnx"

MAX_PASSAGES = int(os.getenv("MAX_PASSAGES", "32"))
MAX_BATCH_TOKENS = int(os.getenv("MAX_BATCH_TOKENS", "16384"))
DEFAULT_MAX_LENGTH = int(os.getenv("DEFAULT_MAX_LENGTH", "512"))


app = FastAPI(
    title="BGE-M3 ONNX Hybrid Server",
    version="1.0.0",
)


# ---------------------------------------------------------
# ONNX Runtime configuration
# ---------------------------------------------------------

if not MODEL_PATH.exists():
    raise RuntimeError(f"ONNX model not found: {MODEL_PATH}")

available_providers = ort.get_available_providers()

preferred_providers = [
    provider
    for provider in [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    if provider in available_providers
]

if not preferred_providers:
    raise RuntimeError(
        f"No supported ONNX providers. Available: {available_providers}"
    )

session_options = ort.SessionOptions()
session_options.graph_optimization_level = (
    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
)

session = ort.InferenceSession(
    str(MODEL_PATH),
    sess_options=session_options,
    providers=preferred_providers,
)

tokenizer = AutoTokenizer.from_pretrained(
    str(MODEL_DIR),
    local_files_only=True,
)


# Validate graph when application starts
input_names = {item.name for item in session.get_inputs()}
output_names = {item.name for item in session.get_outputs()}

required_inputs = {"input_ids", "attention_mask"}
required_outputs = {
    "dense_vecs",
    "sparse_vecs",
    "colbert_vecs",
}

missing_inputs = required_inputs - input_names
missing_outputs = required_outputs - output_names

if missing_inputs:
    raise RuntimeError(
        f"Missing ONNX inputs: {sorted(missing_inputs)}"
    )

if missing_outputs:
    raise RuntimeError(
        f"Missing ONNX outputs: {sorted(missing_outputs)}"
    )


# ---------------------------------------------------------
# API schemas
# ---------------------------------------------------------

class EmbeddingRequest(BaseModel):
    passages: List[str] = Field(min_length=1, max_length=MAX_PASSAGES)
    max_length: int = Field(
        default=DEFAULT_MAX_LENGTH,
        ge=8,
        le=8192,
    )


# ---------------------------------------------------------
# Sparse-vector processing
# ---------------------------------------------------------

SPECIAL_TOKEN_IDS = {
    token_id
    for token_id in [
        tokenizer.cls_token_id,
        tokenizer.eos_token_id,
        tokenizer.pad_token_id,
        tokenizer.unk_token_id,
    ]
    if token_id is not None
}


def postprocess_sparse(
    sparse_output: np.ndarray,
    input_ids: np.ndarray,
    attention_mask: np.ndarray,
) -> List[Dict[str, float]]:
    """
    Convert [batch, sequence, 1] token weights into:

        {token_id: maximum_weight}

    This matches FlagEmbedding behavior:
    - ignore padding
    - remove special tokens
    - keep the maximum weight for repeated tokens
    """

    if sparse_output.ndim != 3 or sparse_output.shape[-1] != 1:
        raise ValueError(
            "Unexpected sparse output shape: "
            f"{sparse_output.shape}; expected [B, S, 1]"
        )

    token_weights = sparse_output.squeeze(-1)
    results: List[Dict[str, float]] = []

    for ids, weights, mask in zip(
        input_ids,
        token_weights,
        attention_mask,
    ):
        lexical_weights = defaultdict(float)

        for token_id, weight, is_valid in zip(ids, weights, mask):
            if not is_valid:
                continue

            token_id = int(token_id)

            if token_id in SPECIAL_TOKEN_IDS:
                continue

            weight = float(weight)

            if weight > lexical_weights[str(token_id)]:
                lexical_weights[str(token_id)] = weight

        results.append(dict(lexical_weights))

    return results


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "aapot/bge-m3-onnx",
        "providers": session.get_providers(),
    }


@app.post("/v1/hybrid-embeddings")
def get_hybrid_embeddings(request: EmbeddingRequest):
    passages = [passage.strip() for passage in request.passages]

    if any(not passage for passage in passages):
        raise HTTPException(
            status_code=400,
            detail="Passages cannot contain empty strings",
        )

    encoded = tokenizer(
        passages,
        padding=True,
        truncation=True,
        max_length=request.max_length,
        return_tensors="np",
        return_token_type_ids=False,
    )

    input_ids = encoded["input_ids"].astype(np.int64)
    attention_mask = encoded["attention_mask"].astype(np.int64)

    # ONNX computes the padded tensor, so check batch × padded length.
    padded_token_count = int(input_ids.size)

    if padded_token_count > MAX_BATCH_TOKENS:
        raise HTTPException(
            status_code=413,
            detail={
                "message": "Batch token limit exceeded",
                "batch_tokens": padded_token_count,
                "max_batch_tokens": MAX_BATCH_TOKENS,
            },
        )

    onnx_inputs = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
    }

    try:
        dense_out, sparse_out, colbert_out = session.run(
            [
                "dense_vecs",
                "sparse_vecs",
                "colbert_vecs",
            ],
            onnx_inputs,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"ONNX inference failed: {exc}",
        ) from exc

    sparse_processed = postprocess_sparse(
        sparse_output=sparse_out,
        input_ids=input_ids,
        attention_mask=attention_mask,
    )

    response_data = []

    for index in range(len(passages)):
        actual_length = int(attention_mask[index].sum())

        # ColBERT graph removes CLS:
        # last_hidden_state[:, 1:]
        colbert_length = max(actual_length - 1, 0)

        response_data.append(
            {
                "dense": dense_out[index].tolist(),
                "sparse": sparse_processed[index],
                "colbert": (
                    colbert_out[index, :colbert_length].tolist()
                ),
                "token_count": actual_length,
                "truncated": actual_length >= request.max_length,
            }
        )

    return {
        "model": "aapot/bge-m3-onnx",
        "dimension": int(dense_out.shape[-1]),
        "data": response_data,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )