"""
PBI-07 — Blueprint extraction.

Public API:
    from ai.blueprint import extract_blueprint
    from ai.schemas import BlueprintSchema

    blueprint: BlueprintSchema = extract_blueprint(file_uris)

The function takes a list of Gemini Files API URIs (already uploaded by the
storage adapter / FS2).  It does NOT handle local PDF uploads — that is the
storage adapter's responsibility.

For local testing / the spike, use _upload_and_extract() at the bottom of
this file, which handles the upload step too.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from google.genai import types
from pydantic import ValidationError

from ai.client import client, fast_model
from ai.schemas import BlueprintSchema

logger = logging.getLogger(__name__)

# ── Prompt ──────────────────────────────────────────────────────────────────

_PROMPT = """\
You are an expert exam-paper analyst specialising in A-Level and O-Level English examinations.

You have been given {n} past-paper PDF(s). Your task is to extract the SHARED STRUCTURAL BLUEPRINT \
that captures everything needed to generate a brand-new paper of the same type.

Instructions:
- Identify EVERY section that appears across the papers.
- For each section list ALL recurring question_types (e.g. fill-in-the-blank, MCQ, \
short-answer, essay, reading-comprehension, paragraph-writing).
- For marks: use the modal (most common) value across papers if they differ.
- For typical_prompt_style: reproduce the canonical instruction wording with specific \
content replaced by [BLANK].
- For tone_notes: describe register (formal/informal), vocabulary level, passage type \
(prose/news/literature), and any stylistic patterns the generator must match.
- For instructions_pattern: list only the cover-page instructions that appear on every paper.
- Output ONLY valid JSON matching the schema — do NOT include markdown fences, \
do NOT add any explanation text outside the JSON object.
- Preserve the marks distribution exactly as observed; do not invent sections or \
inflate mark totals.
"""


# ── Retry wrapper ────────────────────────────────────────────────────────────

_MAX_RETRIES = 2


def _call_with_retry(
    file_parts: list[types.Part],
    prompt: str,
) -> BlueprintSchema:
    """
    Call Gemini and parse the result. Retries up to _MAX_RETRIES times on
    ValidationError or JSON decode errors, logging the raw text each time.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 2):  # attempts: 1, 2, 3
        logger.info("[blueprint] Attempt %d / %d — calling %s…", attempt, _MAX_RETRIES + 1, fast_model)

        response = client.models.generate_content(
            model=fast_model,
            contents=[*file_parts, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BlueprintSchema,
            ),
        )

        raw = response.text
        logger.debug("[blueprint] Raw response (%d chars):\n%s", len(raw), raw)

        try:
            blueprint = BlueprintSchema.model_validate_json(raw)
            if attempt > 1:
                logger.info("[blueprint] Succeeded on attempt %d after earlier parse failure.", attempt)
            return blueprint

        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "[blueprint] Parse failure on attempt %d: %s\nRaw text was:\n%s",
                attempt,
                exc,
                raw,
            )

    # All retries exhausted
    raise RuntimeError(
        f"Blueprint extraction failed after {_MAX_RETRIES + 1} attempts. "
        f"Last error: {last_exc}"
    ) from last_exc


# ── Public API ───────────────────────────────────────────────────────────────


def extract_blueprint(file_uris: list[str]) -> BlueprintSchema:
    """
    Extract a BlueprintSchema from pre-uploaded Gemini Files API URIs.

    Args:
        file_uris:  One or more URIs returned by the Gemini Files API
                    (e.g. "https://generativelanguage.googleapis.com/v1beta/files/abc123").
                    These must already exist in Gemini's file store.

    Returns:
        A validated BlueprintSchema instance (see ai/schemas.py §4.2).

    Raises:
        ValueError:   If file_uris is empty.
        RuntimeError: If all retry attempts fail to produce valid JSON.
    """
    if not file_uris:
        raise ValueError("At least one Gemini file URI is required.")

    file_parts = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in file_uris
    ]

    prompt = _PROMPT.format(n=len(file_uris))
    logger.info("[blueprint] Extracting blueprint from %d file(s)…", len(file_uris))

    blueprint = _call_with_retry(file_parts, prompt)

    logger.info(
        "[blueprint] Done: subject=%r  board=%r  sections=%d  total_marks=%d",
        blueprint.subject,
        blueprint.board,
        len(blueprint.sections),
        blueprint.total_marks,
    )
    return blueprint


# ── Local test helper (not called by the server) ────────────────────────────


def _upload_pdf(path: Path) -> str:
    """Upload a local PDF and return its Gemini URI.  Used only for local testing."""
    print(f"[blueprint] Uploading {path.name}…")
    uploaded = client.files.upload(
        file=str(path),
        config=types.UploadFileConfig(mime_type="application/pdf"),
    )
    print(f"[blueprint]   -> {uploaded.uri}")
    return uploaded.uri


def _upload_and_extract(pdf_paths: list[Path]) -> BlueprintSchema:
    """
    Upload local PDFs then extract a blueprint.
    Convenience wrapper for local testing — the server uses extract_blueprint()
    directly with URIs already cached on SourceFile rows.
    """
    uris = [_upload_pdf(p) for p in pdf_paths]
    return extract_blueprint(uris)
