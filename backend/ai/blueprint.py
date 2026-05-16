"""
PBI-07 / PBI-19 / PBI-23 — Blueprint extraction.

Public API:
    from ai.blueprint import extract_blueprint
    from ai.schemas import BlueprintSchema

    blueprint: BlueprintSchema = extract_blueprint(file_uris)
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.genai import types

from ai.client import client, fast_model
from ai.schemas import BlueprintSchema
from ai.wrapper import call_structured

logger = logging.getLogger(__name__)


# ── Blueprint post-validation (PBI-23) ───────────────────────────────────────


def _validate_blueprint(bp: BlueprintSchema) -> None:
    """
    Sanity-check the extracted blueprint.
    Raises ValueError to trigger a wrapper retry on obviously bad output.
    """
    errors: list[str] = []

    if bp.total_marks <= 0:
        errors.append(f"total_marks must be > 0, got {bp.total_marks}")

    if not bp.sections:
        errors.append("Blueprint has no sections.")

    section_total = sum(s.marks for s in bp.sections)
    if section_total != bp.total_marks:
        errors.append(
            f"Section marks sum {section_total} != total_marks {bp.total_marks}. "
            "Model may have combined marks from multiple papers."
        )

    for sec in bp.sections:
        if not sec.id.strip():
            errors.append(f"Section has empty id: {sec.title!r}")
        if sec.marks <= 0:
            errors.append(f"Section '{sec.id}' has marks <= 0: {sec.marks}")
        if not sec.question_types:
            errors.append(f"Section '{sec.id}' has no question_types.")

    if errors:
        raise ValueError(
            f"Blueprint failed {len(errors)} sanity check(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

# ── Prompt ──────────────────────────────────────────────────────────────────
#
# Prompt-polish notes (PBI-19):
# - Added explicit "ONE paper's marks only" rule to stop the model from summing
#   marks across multiple uploaded PDFs (observed in setB testing).
# - Clarified "most common" section structure when papers differ.
# - Sharpened tone_notes and typical_prompt_style guidance.

_PROMPT = """\
You are an expert exam-paper analyst specialising in A-Level and O-Level English examinations.

You have been given {n} past-paper PDF(s). Your task is to extract a STRUCTURAL BLUEPRINT \
that describes the shape of ONE paper of this type — not the sum of all papers combined.

RULES
1. If multiple PDFs show different structures, identify the sections that appear MOST OFTEN \
   and use those as the blueprint. Do not list sections that appear in only one outlier paper.
2. total_marks must reflect the marks for ONE complete paper, not the sum across all PDFs. \
   If papers differ, use the modal (most common) total.
3. For each section, marks must be the marks for THAT section in ONE paper.
4. The sum of all section marks must equal total_marks exactly.
5. For question_types: list only recurring types that appear across multiple papers.
6. For typical_prompt_style: copy the canonical instruction wording with specific content \
   replaced by [BLANK]. Use a semicolon to separate multiple instruction patterns.
7. For tone_notes: describe register (formal/academic), vocabulary level (A-Level/O-Level), \
   passage topics (news/narrative/data/poetry), and any formatting conventions.
8. For instructions_pattern: list only the cover-page instructions that appear verbatim \
   (or near-verbatim) on EVERY paper.
9. Output ONLY valid JSON — no markdown fences, no commentary outside the JSON object.
"""


# ── Public API ───────────────────────────────────────────────────────────────


def extract_blueprint(file_uris: list[str]) -> BlueprintSchema:
    """
    Extract a BlueprintSchema from pre-uploaded Gemini Files API URIs.

    Args:
        file_uris:  One or more Gemini Files API URIs (already uploaded).

    Returns:
        A validated BlueprintSchema (see ai/schemas.py §4.2).
    """
    if not file_uris:
        raise ValueError("At least one Gemini file URI is required.")

    contents: list = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in file_uris
    ]
    contents.append(_PROMPT.format(n=len(file_uris)))

    logger.info("[blueprint] Extracting blueprint from %d file(s)...", len(file_uris))

    try:
        blueprint = call_structured(
            model=fast_model,
            contents=contents,
            schema=BlueprintSchema,
            retries=1,
            label="blueprint",
            post_validate=_validate_blueprint,
        )
    except Exception as exc:
        err = str(exc)
        # Surface API errors (e.g. corrupted / unsupported PDF) with a clean message
        if "INVALID_ARGUMENT" in err or "400" in err:
            raise ValueError(
                "One or more uploaded files could not be processed by Gemini. "
                "Ensure all files are valid, readable PDF documents. "
                f"Original error: {exc}"
            ) from exc
        raise

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
    """Upload a local PDF and return its Gemini URI. Used only for local testing."""
    print(f"[blueprint] Uploading {path.name}...")
    uploaded = client.files.upload(
        file=str(path),
        config=types.UploadFileConfig(mime_type="application/pdf"),
    )
    print(f"[blueprint]   -> {uploaded.uri}")
    return uploaded.uri


def _upload_and_extract(pdf_paths: list[Path]) -> BlueprintSchema:
    """Upload local PDFs then extract a blueprint. Convenience for local testing."""
    uris = [_upload_pdf(p) for p in pdf_paths]
    return extract_blueprint(uris)
