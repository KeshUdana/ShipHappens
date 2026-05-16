"""
PBI-13 / PBI-19 — Per-question regeneration.

Public API:
    from ai.regenerate import regenerate_question
    from ai.schemas import BlueprintSchema, PaperSchema, Question

    new_q: Question = regenerate_question(paper, blueprint, question_id, nudge)

Uses gemini-2.5-flash for snappy UX.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from ai.client import fast_model
from ai.schemas import BlueprintSchema, PaperSchema, Question, SectionBlueprint
from ai.wrapper import call_structured

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _find_question(paper: PaperSchema, question_id: str) -> tuple[Question, str]:
    for section in paper.sections:
        for q in section.questions:
            if q.id == question_id:
                return q, section.id
    valid = [q.id for s in paper.sections for q in s.questions]
    raise ValueError(f"Question '{question_id}' not found. Valid IDs: {valid}")


def _find_section_blueprint(
    blueprint: BlueprintSchema, section_id: str
) -> Optional[SectionBlueprint]:
    for sec in blueprint.sections:
        if sec.id == section_id:
            return sec
    return None


# ── Prompt ────────────────────────────────────────────────────────────────────
#
# Prompt-polish notes (PBI-19):
# - Added explicit "sub_parts marks must sum to parent marks" constraint.
# - Added "number and type must remain the same" to prevent drift.
# - Separated nudge into its own clearly marked block.
# - Added "do not copy phrasing from original" reminder.

_PROMPT_TEMPLATE = """\
You are an expert {level} {subject} exam paper writer.

TASK
Replace the question below with a BRAND-NEW question of the same type and difficulty. \
The replacement must be clearly different from the original — new topic, new vocabulary, \
new passage (if applicable). Do not copy any phrasing from the original.

ORIGINAL QUESTION
{original_json}

SECTION CONTEXT
Section title:      {section_title}
Question types:     {question_types}
Wording style:      {typical_prompt_style}

PAPER TONE
{tone_notes}
{nudge_block}
HARD CONSTRAINTS
- id must equal "{question_id}" exactly.
- marks must equal {marks} exactly.
- number must equal "{number}" exactly (keep the display number unchanged).
- type should remain "{q_type}" unless the nudge explicitly requests a change.
- prompt must be non-empty and complete — no placeholder text.
- If this question type uses a context_passage (reading comprehension, \
  fill-in-the-blank from passage, vocabulary in context, pronoun reference), \
  provide a self-contained paragraph of 80–150 words. Use culturally appropriate \
  topics (education, environment, science, society). Avoid fantasy/fiction clichés.
- If sub_parts are present, their marks must sum to exactly {marks}.
- Output ONLY the JSON object for the question — no markdown, no commentary.
"""


def _build_prompt(
    original: Question,
    section_bp: Optional[SectionBlueprint],
    blueprint: BlueprintSchema,
    nudge: Optional[str],
) -> str:
    nudge_block = (
        f"\nTEACHER NUDGE\n{nudge}\n(Honour this instruction in the new question.)\n"
        if nudge
        else ""
    )
    return _PROMPT_TEMPLATE.format(
        level=blueprint.level,
        subject=blueprint.subject,
        question_id=original.id,
        original_json=json.dumps(original.model_dump(), indent=2, ensure_ascii=False),
        section_title=section_bp.title if section_bp else "Unknown",
        question_types=", ".join(section_bp.question_types) if section_bp else "varies",
        typical_prompt_style=section_bp.typical_prompt_style if section_bp else "",
        tone_notes=blueprint.tone_notes,
        nudge_block=nudge_block,
        marks=original.marks,
        number=original.number,
        q_type=original.type,
    )


# ── Post-parse fixups ─────────────────────────────────────────────────────────


def _fixup(new_q: Question, original: Question, question_id: str) -> Question:
    """Silently enforce id and marks — model occasionally drifts on these."""
    updates: dict = {}
    if new_q.id != question_id:
        logger.warning(
            "[regenerate] Model returned id=%r, overwriting with %r.",
            new_q.id, question_id,
        )
        updates["id"] = question_id
    if new_q.marks != original.marks:
        logger.warning(
            "[regenerate] Model returned marks=%d, overwriting with %d.",
            new_q.marks, original.marks,
        )
        updates["marks"] = original.marks
    if not new_q.prompt.strip():
        raise ValueError("Regenerated question has empty prompt.")
    return new_q.model_copy(update=updates) if updates else new_q


# ── Public API ────────────────────────────────────────────────────────────────


def regenerate_question(
    paper: PaperSchema,
    blueprint: BlueprintSchema,
    question_id: str,
    nudge: Optional[str] = None,
) -> Question:
    """
    Regenerate a single question and return the replacement object.

    Args:
        paper:        Current paper (used to locate the original question).
        blueprint:    Session's BlueprintSchema (provides section constraints).
        question_id:  Stable id of the question to replace (e.g. 's0q2').
        nudge:        Optional teacher instruction, e.g. "harder", "passive voice".

    Returns:
        A new Question with the same id, marks, and number as the original.

    Raises:
        ValueError:   question_id not found in paper.
        RuntimeError: Model failed to return a valid Question after retries.
    """
    original, section_id = _find_question(paper, question_id)
    section_bp = _find_section_blueprint(blueprint, section_id)

    logger.info(
        "[regenerate] question=%r  type=%r  marks=%d  section=%r%s",
        question_id, original.type, original.marks, section_id,
        f"  nudge={nudge!r}" if nudge else "",
    )

    prompt = _build_prompt(original, section_bp, blueprint, nudge)

    raw_q = call_structured(
        model=fast_model,
        contents=[prompt],
        schema=Question,
        retries=1,
        label="regenerate",
    )

    new_q = _fixup(raw_q, original, question_id)
    logger.info("[regenerate] Done: id=%r  type=%r  marks=%d", new_q.id, new_q.type, new_q.marks)
    return new_q
