"""
Feature #1 — Answer key + marking scheme generation.

Public API:
    from ai.answer_key import generate_answer_key
    from ai.schemas import PaperSchema, AnswerKeySchema

    key: AnswerKeySchema = generate_answer_key(paper)

Takes a generated PaperSchema and produces a 1:1 mapped AnswerKeySchema
containing model answers, marking criteria, and common mistakes.

Uses gemini-2.5-flash — answer keys are easier than the paper itself.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from ai.client import fast_model
from ai.schemas import AnswerKeySchema, PaperSchema
from ai.wrapper import OnUsage, call_structured

logger = logging.getLogger(__name__)


# ── Prompt ───────────────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """\
You are an experienced examiner who has marked thousands of {level} {subject} papers.

TASK
Produce a complete ANSWER KEY and MARKING SCHEME for the paper below.

PAPER (JSON)
{paper_json}

REQUIREMENTS
1. For every question (including every sub-part), produce one QuestionAnswer entry.
2. question_id must match the paper's question.id exactly.
3. model_answer:
   - For fill-in-the-blank / MCQ / single-word: the EXACT correct answer.
   - For short-answer / paragraph: a HIGH-BAND exemplar (the answer a top student would write).
   - For essay / long-form: 3-5 sentence outline of the expected answer structure.
4. marking_criteria: 2-5 specific bullet points describing what earns marks.
   Total marks across criteria must equal the question's marks.
5. sub_part_answers: one entry per SubPart on the source question. Leave empty
   if the question has no sub_parts.
6. common_mistakes: 1-3 typical errors candidates make.
7. paper_title and total_marks must match the source paper exactly.
8. Output ONLY valid JSON matching AnswerKeySchema. No markdown fences.
"""


def _build_prompt(paper: PaperSchema) -> str:
    return _PROMPT_TEMPLATE.format(
        level="A-Level / O-Level",
        subject="English",
        paper_json=json.dumps(paper.model_dump(), indent=2, ensure_ascii=False),
    )


# ── Post-validation ──────────────────────────────────────────────────────────


def _validate_answer_key(key: AnswerKeySchema, paper: PaperSchema) -> None:
    """Cross-check that every question has an answer."""
    paper_qids = {q.id for s in paper.sections for q in s.questions}
    key_qids = {qa.question_id for s in key.sections for qa in s.answers}

    missing = paper_qids - key_qids
    extra = key_qids - paper_qids

    errors: list[str] = []
    if missing:
        errors.append(f"Missing answers for: {sorted(missing)}")
    if extra:
        errors.append(f"Extra answers not in paper: {sorted(extra)}")
    if key.total_marks != paper.total_marks:
        errors.append(
            f"total_marks mismatch: paper={paper.total_marks}, key={key.total_marks}"
        )

    if errors:
        raise ValueError(
            f"Answer key failed {len(errors)} check(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ── Public API ───────────────────────────────────────────────────────────────


def generate_answer_key(
    paper: PaperSchema,
    *,
    on_usage: Optional[OnUsage] = None,
) -> AnswerKeySchema:
    """
    Generate an answer key + marking scheme for an existing paper.

    Args:
        paper:     The generated PaperSchema to answer.
        on_usage:  Optional usage-tracking callback (see wrapper.UsageRecord).

    Returns:
        A validated AnswerKeySchema with 1:1 mapping to paper questions.
    """
    logger.info(
        "[answer_key] Generating answer key for %r (%d questions)",
        paper.title,
        sum(len(s.questions) for s in paper.sections),
    )

    prompt = _build_prompt(paper)

    key = call_structured(
        model=fast_model,
        contents=[prompt],
        schema=AnswerKeySchema,
        retries=1,
        label="answer_key",
        post_validate=lambda k: _validate_answer_key(k, paper),
        on_usage=on_usage,
    )

    logger.info(
        "[answer_key] Done: %d sections, %d answers",
        len(key.sections),
        sum(len(s.answers) for s in key.sections),
    )
    return key
