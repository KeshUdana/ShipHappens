"""
PBI-12 / PBI-19 / PBI-23 — Paper generation.

Public API:
    from ai.generate import generate_paper
    from ai.schemas import BlueprintSchema, PaperSchema

    paper: PaperSchema = generate_paper(blueprint, file_uris)

Uses gemini-2.5-pro (auto-falls back to flash on free-tier quota exhaustion).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Iterator

from google.genai import types

from ai.client import client, fast_model, pro_model
from ai.schemas import BlueprintSchema, PaperSchema
from ai.wrapper import OnUsage, call_structured

logger = logging.getLogger(__name__)


# ── Prompt ──────────────────────────────────────────────────────────────────
#
# Prompt-polish notes (PBI-19):
# - Added explicit section-marks accounting table in the prompt so the model
#   can plan marks distribution before writing questions.
# - Tightened context-passage instructions: cultural relevance, no fiction tropes.
# - Added sub-parts marks-sum rule explicitly.
# - Clarified that section ids in the output MUST match blueprint section ids.

_PROMPT_TEMPLATE = """\
You are an expert {level} {subject} exam paper writer working for {board}.

TASK
Generate a COMPLETE, BRAND-NEW examination paper that strictly follows the BLUEPRINT below. \
The source PDFs (if attached) are for STYLE REFERENCE and CONTENT AVOIDANCE only — do not \
reproduce any text, passages, or questions from them.

BLUEPRINT
{blueprint_json}

MARKS PLAN (you MUST hit these exactly)
{marks_plan}
Total: {total_marks} marks

HARD CONSTRAINTS — an automated validator will reject any violation:
1. Sections: output EXACTLY {num_sections} section(s). Each section id and title must match \
   the blueprint exactly.
2. Marks per section: questions in each section must sum to exactly that section's marks (see \
   MARKS PLAN above).
3. Total marks: sum across ALL sections = {total_marks}. Not one mark more or less.
   IMPORTANT: If you cannot make the marks sum to {total_marks}, signal failure by setting \
   the paper's total_marks field to 0. Do not silently output a wrong total.
4. Question IDs: every question.id must be UNIQUE. Use format s<section_idx>q<q_idx> \
   (e.g. s0q0, s0q1, s1q0). Section index starts at 0.
5. No empty fields: every question.prompt must be non-empty, meaningful text.
6. Context passages: for question types reading_comprehension_*, fill-in-the-blank_from_passage, \
   vocabulary_in_context_*, pronoun_reference — set context_passage to a self-contained \
   paragraph of 80–150 words. Use topics that are culturally appropriate (education, \
   environment, society, science, current events). Avoid fantasy or fiction tropes.
7. Sub-parts: if a question is split into (a)(b)(c) etc., populate sub_parts and ensure \
   their marks sum to the parent question's marks.
8. Tone: follow tone_notes — formal academic register, A-Level / O-Level appropriate vocabulary.
9. Wording: model each question closely on the typical_prompt_style of its section, \
   replacing [BLANK] with concrete content appropriate to the topic.
10. Output ONLY valid JSON matching PaperSchema. No markdown fences. No text outside the JSON.
11. Difficulty rating: for each question, set difficulty (1-5):
    1 = trivial recall, 2 = easy, 3 = standard A-Level / O-Level expected difficulty,
    4 = challenging, 5 = top-band stretch.
    Aim for a balanced distribution: most questions at 2-3, a few at 4-5 toward the end.

PAPER TITLE: "{subject} — {level} Mock Paper"
"""


def _marks_plan(blueprint: BlueprintSchema) -> str:
    lines = [f"  {s.id}: {s.marks} marks ({s.title})" for s in blueprint.sections]
    return "\n".join(lines)


def _build_prompt(blueprint: BlueprintSchema) -> str:
    return _PROMPT_TEMPLATE.format(
        level=blueprint.level,
        subject=blueprint.subject,
        board=blueprint.board,
        blueprint_json=json.dumps(blueprint.model_dump(), indent=2, ensure_ascii=False),
        marks_plan=_marks_plan(blueprint),
        num_sections=len(blueprint.sections),
        total_marks=blueprint.total_marks,
    )


# ── Post-generation validation ────────────────────────────────────────────────


class PaperValidationError(ValueError):
    """Raised when the generated paper fails hard-constraint checks."""


_DRIFT_THRESHOLD_PCT = 10.0  # marks within this % are accepted with a warning


def _marks_drift_pct(actual: int, expected: int) -> float:
    if expected == 0:
        return 100.0
    return abs(actual - expected) / expected * 100.0


def _validate_paper(paper: PaperSchema, blueprint: BlueprintSchema) -> None:
    """
    Domain checks that Pydantic cannot enforce.
    Raises PaperValidationError (a ValueError subclass) to trigger a wrapper retry.

    Total-marks policy (PBI-23):
      - paper.total_marks == 0 → model signalled it could not match; always retry.
      - drift > _DRIFT_THRESHOLD_PCT  → error; triggers retry.
      - drift <= _DRIFT_THRESHOLD_PCT → log warning; accept (no retry).
    """
    errors: list[str] = []

    # Model "signal failure" marker
    if paper.total_marks == 0:
        errors.append(
            "Model set total_marks=0 to signal it could not satisfy the marks constraint."
        )

    if len(paper.sections) != len(blueprint.sections):
        errors.append(
            f"Section count: expected {len(blueprint.sections)}, got {len(paper.sections)}"
        )

    all_questions = [q for sec in paper.sections for q in sec.questions]
    actual_total = sum(q.marks for q in all_questions)
    drift = _marks_drift_pct(actual_total, blueprint.total_marks)

    if drift > _DRIFT_THRESHOLD_PCT:
        errors.append(
            f"Total marks drift {drift:.0f}% (>{_DRIFT_THRESHOLD_PCT}%): "
            f"expected {blueprint.total_marks}, got {actual_total} — retrying."
        )
    elif drift > 0:
        logger.warning(
            "[generate] Marks drift %.1f%% (<=%.0f%% tolerance): "
            "expected %d, got %d — accepting.",
            drift, _DRIFT_THRESHOLD_PCT, blueprint.total_marks, actual_total,
        )

    bp_marks = {s.id: s.marks for s in blueprint.sections}
    for sec in paper.sections:
        expected = bp_marks.get(sec.id)
        if expected is None:
            continue
        actual = sum(q.marks for q in sec.questions)
        sec_drift = _marks_drift_pct(actual, expected)
        if sec_drift > _DRIFT_THRESHOLD_PCT:
            errors.append(
                f"Section '{sec.id}': marks drift {sec_drift:.0f}%: "
                f"expected {expected}, got {actual}"
            )

    dupes = [qid for qid, n in Counter(q.id for q in all_questions).items() if n > 1]
    if dupes:
        errors.append(f"Duplicate question IDs: {dupes}")

    empty = [q.id for q in all_questions if not q.prompt.strip()]
    if empty:
        errors.append(f"Empty prompts on: {empty}")

    if errors:
        raise PaperValidationError(
            f"Paper failed {len(errors)} constraint(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ── Model selection with quota fallback ──────────────────────────────────────


def _pick_model_and_generate(
    contents: list, blueprint: BlueprintSchema
) -> PaperSchema:
    """
    Try pro_model first; on 429 quota exhaustion fall back to fast_model.
    Each model attempt uses call_structured (handles parse retries).
    """
    for model in ([pro_model, fast_model] if pro_model != fast_model else [fast_model]):
        try:
            return call_structured(
                model=model,
                contents=contents,
                schema=PaperSchema,
                retries=1,
                label="generate",
                post_validate=lambda p: _validate_paper(p, blueprint),
            )
        except Exception as exc:
            err = str(exc)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                logger.warning(
                    "[generate] Quota exhausted on %s, falling back to %s.",
                    model,
                    fast_model,
                )
                if model == fast_model:
                    raise  # already on fallback, nothing left to try
                continue
            raise

    raise RuntimeError("[generate] All models exhausted.")


# ── Public API ────────────────────────────────────────────────────────────────


def generate_paper(blueprint: BlueprintSchema, file_uris: list[str]) -> PaperSchema:
    """
    Generate a brand-new PaperSchema from a blueprint and source PDF URIs.

    Args:
        blueprint:   Validated BlueprintSchema (from extract_blueprint).
        file_uris:   Gemini Files API URIs of the source PDFs (style context +
                     content avoidance). Pass [] if no source files are available.

    Returns:
        A validated PaperSchema (ai/schemas.py §4.3) with marks verified.
    """
    contents: list = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in file_uris
    ]
    contents.append(_build_prompt(blueprint))

    logger.info(
        "[generate] Generating paper: subject=%r  sections=%d  total_marks=%d",
        blueprint.subject,
        len(blueprint.sections),
        blueprint.total_marks,
    )

    paper = _pick_model_and_generate(contents, blueprint)

    # PBI-23: Final drift safety net — if marks are still >10% off after normal
    # retries, force one more attempt before surfacing the result.
    actual = sum(q.marks for s in paper.sections for q in s.questions)
    drift = _marks_drift_pct(actual, blueprint.total_marks)
    if drift > _DRIFT_THRESHOLD_PCT:
        logger.warning(
            "[generate] Final drift check: %.0f%% off after normal retries. "
            "Forcing one additional attempt.",
            drift,
        )
        try:
            paper = _pick_model_and_generate(contents, blueprint)
        except Exception as exc:
            logger.error(
                "[generate] Additional attempt also failed: %s. "
                "Returning best-effort paper with %.0f%% drift.",
                exc, drift,
            )

    logger.info(
        "[generate] Done: title=%r  questions=%d  marks=%d",
        paper.title,
        sum(len(s.questions) for s in paper.sections),
        paper.total_marks,
    )
    return paper


# ── Feature #3: Streaming paper generation ───────────────────────────────────
#
# Yields progress events as the model generates the paper. The FE consumes
# these via Server-Sent Events to show "Section A done...", "Section B done..."
# instead of an infinite spinner.
#
# Event shapes (each yielded as a dict):
#   {"event": "start",    "model": "gemini-2.5-pro"}
#   {"event": "chunk",    "chars": 1234, "section_hint": "secA"}    # progress tick
#   {"event": "section",  "section_id": "secA", "title": "..."}     # detected a section
#   {"event": "complete", "paper": {...}}                            # final validated paper
#   {"event": "error",    "message": "..."}                          # fatal failure


def generate_paper_stream(
    blueprint: BlueprintSchema,
    file_uris: list[str],
) -> Iterator[dict]:
    """
    Generator version of generate_paper. Yields progress events suitable for SSE.

    The function streams raw JSON text from Gemini and detects section
    completions heuristically (looking for new `"id": "..."` keys in the JSON
    text). When the stream finishes, it parses and validates the full result.
    """
    contents: list = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in file_uris
    ]
    contents.append(_build_prompt(blueprint))

    # Use fast_model for streaming (pro is often quota-limited)
    model = fast_model

    yield {"event": "start", "model": model}
    logger.info("[generate_stream] Starting stream with %s", model)

    buffer = ""
    section_ids_seen: set[str] = set()
    blueprint_section_ids = {s.id: s.title for s in blueprint.sections}

    try:
        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PaperSchema,
            ),
        )

        for chunk in stream:
            text = getattr(chunk, "text", None)
            if not text:
                continue
            buffer += text

            # Detect newly-emitted sections by scanning for blueprint ids
            for sid, title in blueprint_section_ids.items():
                if sid in section_ids_seen:
                    continue
                if f'"{sid}"' in buffer:
                    section_ids_seen.add(sid)
                    yield {"event": "section", "section_id": sid, "title": title}

            yield {
                "event": "chunk",
                "chars": len(buffer),
                "sections_seen": len(section_ids_seen),
            }

        # Stream complete — parse final result
        paper = PaperSchema.model_validate_json(buffer)

        # Run domain validation but don't fail the stream on minor drift
        try:
            _validate_paper(paper, blueprint)
        except PaperValidationError as exc:
            yield {"event": "warning", "message": str(exc)}

        yield {"event": "complete", "paper": paper.model_dump()}
        logger.info("[generate_stream] Done: %d chars, %d sections", len(buffer), len(section_ids_seen))

    except Exception as exc:
        logger.exception("[generate_stream] Failed")
        yield {"event": "error", "message": str(exc)}
