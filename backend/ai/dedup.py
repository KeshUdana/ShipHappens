"""
Feature #2 — Embedding-based duplicate guard.

Catches the demo-killer case where a generated question accidentally reproduces
text from the uploaded source PDFs.

Public API:
    from ai.dedup import check_duplicates

    warnings: list[DuplicateWarning] = check_duplicates(paper, source_pdf_paths)

Approach:
  1. Extract text from each source PDF using pymupdf, chunk by paragraph.
  2. Embed every chunk with Gemini's embedding model.
  3. Embed every generated question's prompt + context_passage.
  4. For each generated text, find the nearest source chunk by cosine similarity.
  5. Flag any pair >= 0.80 as a warning.

pgvector NOTE:
  This module currently keeps embeddings in memory (per-request). To grow a
  cross-session question bank, persist `_embed_texts()` outputs to the
  question_embedding table via SQLModel — see backend/app/models/question_embedding.py.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fitz  # pymupdf
from google.genai import types

from ai.client import client
from ai.schemas import DuplicateWarning, PaperSchema

logger = logging.getLogger(__name__)


# ── Config ───────────────────────────────────────────────────────────────────

EMBED_MODEL = "gemini-embedding-001"  # text-embedding-004 was retired (404s on v1beta)
HIGH_THRESHOLD = 0.90
MEDIUM_THRESHOLD = 0.80
MIN_CHUNK_CHARS = 60   # ignore very short fragments (headers, page numbers)
MAX_CHUNK_CHARS = 800  # split very long paragraphs


# ── Source text extraction ──────────────────────────────────────────────────


_WHITESPACE = re.compile(r"\s+")


def _extract_chunks(pdf_path: Path) -> list[str]:
    """Pull paragraph-sized text chunks from a PDF."""
    doc = fitz.open(str(pdf_path))
    try:
        raw = "\n\n".join(page.get_text() for page in doc)  # type: ignore[attr-defined]
    finally:
        doc.close()

    # Split on blank lines and normalise whitespace
    chunks: list[str] = []
    for para in raw.split("\n\n"):
        text = _WHITESPACE.sub(" ", para).strip()
        if len(text) < MIN_CHUNK_CHARS:
            continue
        # Further split long paragraphs at sentence boundaries
        if len(text) > MAX_CHUNK_CHARS:
            for sub in re.split(r"(?<=[.!?])\s+", text):
                sub = sub.strip()
                if len(sub) >= MIN_CHUNK_CHARS:
                    chunks.append(sub[:MAX_CHUNK_CHARS])
        else:
            chunks.append(text)
    return chunks


# ── Embedding helpers ───────────────────────────────────────────────────────


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the Gemini embedding model."""
    if not texts:
        return []
    logger.info("[dedup] Embedding %d text(s) with %s...", len(texts), EMBED_MODEL)
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,  # type: ignore[arg-type]
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    return [e.values for e in response.embeddings]


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Vectors from text-embedding-004 are already L2-normalised."""
    return sum(x * y for x, y in zip(a, b))


def _severity(sim: float) -> str:
    if sim >= HIGH_THRESHOLD:
        return "high"
    if sim >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


# ── Public API ───────────────────────────────────────────────────────────────


def check_duplicates(
    paper: PaperSchema,
    source_pdf_paths: list[Path],
    *,
    threshold: float = MEDIUM_THRESHOLD,
) -> list[DuplicateWarning]:
    """
    Compare every generated question against text from the source PDFs.

    Args:
        paper:             The generated PaperSchema.
        source_pdf_paths:  Local paths to the source PDFs used as input.
        threshold:         Minimum similarity to flag as a warning (default 0.80).

    Returns:
        A list of DuplicateWarning entries, sorted by descending similarity.
        Empty list means the paper is original.
    """
    # 1. Extract source chunks
    source_chunks: list[str] = []
    for path in source_pdf_paths:
        if not path.exists():
            logger.warning("[dedup] Source PDF missing: %s", path)
            continue
        chunks = _extract_chunks(path)
        logger.info("[dedup] %s -> %d chunks", path.name, len(chunks))
        source_chunks.extend(chunks)

    if not source_chunks:
        logger.warning("[dedup] No source chunks extracted — skipping dedup check.")
        return []

    # 2. Collect generated question texts (one per question)
    q_records: list[tuple[str, str]] = []  # (question_id, text)
    for sec in paper.sections:
        for q in sec.questions:
            parts = [q.prompt]
            if q.context_passage:
                parts.append(q.context_passage)
            for sp in q.sub_parts:
                parts.append(sp.prompt)
            q_records.append((q.id, " ".join(parts)))

    if not q_records:
        return []

    # 3. Embed both sides
    source_embs = _embed_texts(source_chunks)
    q_embs = _embed_texts([t for _, t in q_records])

    # 4. Nearest-neighbour scan
    warnings: list[DuplicateWarning] = []
    for (qid, _), q_emb in zip(q_records, q_embs):
        best_sim = -1.0
        best_chunk = ""
        for chunk, c_emb in zip(source_chunks, source_embs):
            sim = _cosine(q_emb, c_emb)
            if sim > best_sim:
                best_sim = sim
                best_chunk = chunk
        if best_sim >= threshold:
            warnings.append(DuplicateWarning(
                question_id=qid,
                similarity=round(best_sim, 4),
                matched_source_snippet=best_chunk[:300],
                severity=_severity(best_sim),
            ))

    warnings.sort(key=lambda w: w.similarity, reverse=True)
    logger.info(
        "[dedup] Done. Flagged %d question(s) (high=%d, medium=%d)",
        len(warnings),
        sum(1 for w in warnings if w.severity == "high"),
        sum(1 for w in warnings if w.severity == "medium"),
    )
    return warnings
