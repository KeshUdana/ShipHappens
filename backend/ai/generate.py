"""
PBI-12 — Paper generation.

Public API:
    from ai.generate import generate_paper
    from ai.schemas import BlueprintSchema, PaperSchema

    paper: PaperSchema = generate_paper(blueprint, file_uris)

The function takes:
  - blueprint:   A validated BlueprintSchema (output of PBI-07).
  - file_uris:   Gemini Files API URIs of the source PDFs (for style context
                 and content avoidance — already uploaded by the storage adapter).

Uses gemini-2.5-pro for maximum quality.
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from google.genai import types
from pydantic import ValidationError

from ai.client import client, pro_model, fast_model
from ai.schemas import BlueprintSchema, PaperSchema

logger = logging.getLogger(__name__)

# ── Prompt ──────────────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """\
You are an expert {level} {subject} exam paper writer working for {board}.

TASK
Generate a COMPLETE, BRAND-NEW examination paper that strictly follows the
BLUEPRINT provided below.  The source PDFs attached are for STYLE REFERENCE
and CONTENT AVOIDANCE only — do not reproduce any text, passages, or questions
from them.

BLUEPRINT
{blueprint_json}

HARD CONSTRAINTS — violating any of these will cause an automated rejection:
1. Section structure: produce EXACTLY {num_sections} section(s), with the same id and title as the blueprint.
2. Marks per section: questions within each section must sum to exactly that section's marks value.
3. Total marks: the sum across all sections must equal exactly {total_marks}.
4. Question IDs: every question.id must be UNIQUE across the whole paper.
         Use the format  s<section_index>q<question_index>  (e.g. s0q0, s0q1, s1q0).
5. No empty fields: every question must have a non-empty prompt.
6. Context passages: for any question of type reading_comprehension_*, fill-in-the-blank_from_passage,
   vocabulary_in_context_*, or pronoun_reference, set context_passage to a self-contained
   paragraph of 80-150 words appropriate for the level.
7. Tone: follow tone_notes exactly — register, vocabulary level, passage topics.
8. Question wording: model each question's wording closely on the typical_prompt_style
   of its section, replacing [BLANK] with concrete content.
9. Sub-parts: if a question is naturally split (e.g. (a), (b), (c)), populate sub_parts
   and set the parent question's marks to the sum of sub-part marks.
10. Output ONLY valid JSON matching the PaperSchema — no markdown fences, no commentary.

PAPER TITLE FORMAT: "{subject} — {level} Mock Paper"
"""


def _build_prompt(blueprint: BlueprintSchema) -> str:
    return _PROMPT_TEMPLATE.format(
        level=blueprint.level,
        subject=blueprint.subject,
        board=blueprint.board,
        blueprint_json=json.dumps(blueprint.model_dump(), indent=2, ensure_ascii=False),
        num_sections=len(blueprint.sections),
        total_marks=blueprint.total_marks,
    )


# ── Post-generation validation ───────────────────────────────────────────────

class PaperValidationError(ValueError):
    """Raised when the generated paper fails hard-constraint checks."""


def _validate_paper(paper: PaperSchema, blueprint: BlueprintSchema) -> None:
    """
    Check hard constraints that Gemini structured output cannot guarantee.
    Raises PaperValidationError with a descriptive message on first violation.
    """
    errors: list[str] = []

    # 1. Section count
    if len(paper.sections) != len(blueprint.sections):
        errors.append(
            f"Section count mismatch: expected {len(blueprint.sections)}, "
            f"got {len(paper.sections)}"
        )

    # 2. Total marks
    all_questions = [q for sec in paper.sections for q in sec.questions]
    actual_total = sum(q.marks for q in all_questions)
    if actual_total != blueprint.total_marks:
        errors.append(
            f"Total marks mismatch: expected {blueprint.total_marks}, "
            f"got {actual_total}"
        )

    # 3. Per-section marks
    bp_section_marks = {s.id: s.marks for s in blueprint.sections}
    for sec in paper.sections:
        expected = bp_section_marks.get(sec.id)
        actual = sum(q.marks for q in sec.questions)
        if expected is not None and actual != expected:
            errors.append(
                f"Section '{sec.id}' marks mismatch: expected {expected}, got {actual}"
            )

    # 4. Unique question IDs
    all_ids = [q.id for q in all_questions]
    dupes = [qid for qid, count in Counter(all_ids).items() if count > 1]
    if dupes:
        errors.append(f"Duplicate question IDs: {dupes}")

    # 5. No empty prompts
    empty = [q.id for q in all_questions if not q.prompt.strip()]
    if empty:
        errors.append(f"Questions with empty prompts: {empty}")

    if errors:
        raise PaperValidationError(
            f"Paper failed {len(errors)} constraint(s):\n" + "\n".join(f"  - {e}" for e in errors)
        )


# ── Retry wrapper ────────────────────────────────────────────────────────────

_MAX_RETRIES = 1  # 2 attempts total (initial + 1 retry)


def _call_with_retry(
    file_parts: list[types.Part],
    prompt: str,
    blueprint: BlueprintSchema,
) -> PaperSchema:
    last_exc: Exception | None = None

    # Try pro first; if quota-exhausted (429), fall back to fast model.
    models_to_try = [pro_model, fast_model] if pro_model != fast_model else [fast_model]

    for attempt in range(1, _MAX_RETRIES + 2):
        # On retry, we may have already switched to fast_model due to quota
        current_model = models_to_try[min(attempt - 1, len(models_to_try) - 1)]
        logger.info(
            "[generate] Attempt %d / %d — calling %s (this may take 30-90s)...",
            attempt,
            _MAX_RETRIES + 1,
            current_model,
        )

        raw = ""
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=[*file_parts, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PaperSchema,
                ),
            )
            raw = response.text
            logger.debug("[generate] Raw response (%d chars):\n%s", len(raw), raw)

            paper = PaperSchema.model_validate_json(raw)
            _validate_paper(paper, blueprint)

            if attempt > 1:
                logger.info("[generate] Succeeded on attempt %d.", attempt)
            return paper

        except (ValidationError, PaperValidationError, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "[generate] Validation failure on attempt %d: %s\nRaw text was:\n%s",
                attempt,
                exc,
                raw,
            )

        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning(
                    "[generate] Quota exhausted on %s (attempt %d). "
                    "Falling back to %s on next attempt.",
                    current_model,
                    attempt,
                    fast_model,
                )
                # Force fast_model for all remaining attempts
                models_to_try = [fast_model] * len(models_to_try)
                print(f"[generate] Quota hit on {current_model}, retrying with {fast_model}...")
            else:
                raise

    raise RuntimeError(
        f"Paper generation failed after {_MAX_RETRIES + 1} attempt(s). "
        f"Last error: {last_exc}"
    ) from last_exc


# ── Public API ───────────────────────────────────────────────────────────────


def generate_paper(blueprint: BlueprintSchema, file_uris: list[str]) -> PaperSchema:
    """
    Generate a brand-new PaperSchema from a blueprint and source PDF URIs.

    Args:
        blueprint:   Validated BlueprintSchema (from extract_blueprint).
        file_uris:   Gemini Files API URIs of the source PDFs.
                     Used as style context and for content avoidance.
                     Pass an empty list if no source files are available.

    Returns:
        A validated PaperSchema instance (see ai/schemas.py §4.3).

    Raises:
        RuntimeError: If all retry attempts fail post-validation.
    """
    file_parts = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in file_uris
    ]

    prompt = _build_prompt(blueprint)
    logger.info(
        "[generate] Generating paper: subject=%r  sections=%d  total_marks=%d",
        blueprint.subject,
        len(blueprint.sections),
        blueprint.total_marks,
    )

    paper = _call_with_retry(file_parts, prompt, blueprint)

    q_count = sum(len(s.questions) for s in paper.sections)
    logger.info(
        "[generate] Done: title=%r  sections=%d  questions=%d  marks=%d",
        paper.title,
        len(paper.sections),
        q_count,
        paper.total_marks,
    )
    return paper
