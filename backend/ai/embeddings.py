"""
S2-05 — Shared embedding service.

One place that turns text into vectors for the whole pipeline:
  - ingestion (app/services/ingestion.py) embeds each extracted question
  - retrieval (app/services/retrieval.py) embeds slot queries
  - dedup (ai/dedup.py) embeds source chunks + generated questions

Model: gemini-embedding-001 (3072-dim native). We truncate to EMBED_DIM via the
Matryoshka property (leading dims carry the most signal) and re-normalise, so the
pgvector column and HNSW index stay compact while keeping retrieval quality.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from google.genai import types

from ai.client import client
from ai.wrapper import UsageRecord, _emit_usage

logger = logging.getLogger(__name__)

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 1536  # Matryoshka truncation of the 3072-dim native vector
_BATCH = 100


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _truncate(vec: list[float]) -> list[float]:
    """Take leading EMBED_DIM dims, then re-normalise so cosine == dot product."""
    return _l2_normalize(vec[:EMBED_DIM])


def embed_texts(
    texts: list[str],
    *,
    task_type: str = "SEMANTIC_SIMILARITY",
    label: str = "embed",
) -> list[list[float]]:
    """Embed a batch of texts → EMBED_DIM-length L2-normalised vectors.

    Emits a UsageRecord per API call via the global usage hooks (eval cost tracking).
    """
    if not texts:
        return []

    out: list[list[float]] = []
    for start in range(0, len(texts), _BATCH):
        chunk = texts[start : start + _BATCH]
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=chunk,  # type: ignore[arg-type]
            config=types.EmbedContentConfig(task_type=task_type),
        )
        out.extend(_truncate(e.values) for e in response.embeddings)

        # Embeddings are billed on input tokens; record best-effort usage.
        meta = getattr(response, "usage_metadata", None)
        tokens = getattr(meta, "total_token_count", 0) if meta else 0
        _emit_usage(
            UsageRecord(
                label=label, model=EMBED_MODEL,
                input_tokens=tokens or 0, output_tokens=0, total_tokens=tokens or 0,
                cost_usd=(tokens or 0) / 1_000_000 * 0.15,
                status="success",
            ),
            None,
        )

    return out


def embed_query(text: str) -> list[float]:
    """Embed a single retrieval query (RETRIEVAL_QUERY task type)."""
    vecs = embed_texts([text], task_type="RETRIEVAL_QUERY", label="embed_query")
    return vecs[0] if vecs else []


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Vectors from embed_* are already L2-normalised → dot product."""
    return sum(x * y for x, y in zip(a, b))
