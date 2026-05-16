"""
Shared Pydantic schemas for all AI module outputs.

These are the CONTRACTS between the AI module and the rest of the system.
Frontend, backend routes, and the AI engineer must all use the same field names.

Section references:
  §4.2  BlueprintSchema  — output of blueprint.extract_blueprint()
  §4.3  PaperSchema      — output of generate.generate_paper()   (defined here for FE mocking)
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── §4.2  Blueprint (AI → FE for review; AI → generate prompt) ─────────────


class SectionBlueprint(BaseModel):
    """One labelled section inside a BlueprintSchema."""

    id: str = Field(description="Short slug, e.g. 'secA', 'secB'")
    title: str = Field(description="Full display title, e.g. 'Section A — Grammar and Vocabulary'")
    marks: int = Field(description="Total marks allocated to this section")
    instructions: str = Field(description="Section-level instruction text shown above the questions")
    question_types: list[str] = Field(
        description="Recurring question type labels, e.g. ['fill-in-the-blank', 'MCQ', 'short-answer']"
    )
    typical_prompt_style: str = Field(
        description=(
            "Representative wording pattern for questions in this section, "
            "with specific content replaced by [BLANK], "
            "e.g. 'Fill in the blank with the correct form of the verb: [BLANK]'"
        )
    )


class BlueprintSchema(BaseModel):
    """
    §4.2 — Structural blueprint extracted from uploaded past papers.

    Field names here are the canonical contract shared with the FE.
    Do NOT rename fields without updating front/lib/store.ts.
    """

    subject: str = Field(description="e.g. 'General English', 'A-Level English Language'")
    board: str = Field(description="e.g. 'Cambridge', 'Department of Examinations Sri Lanka'")
    level: str = Field(description="e.g. 'A Level', 'O Level', 'GCE Advanced Level'")
    duration_minutes: int
    total_marks: int
    tone_notes: str = Field(
        description=(
            "Free-text description of register, vocabulary level, passage style, "
            "and any recurring stylistic features the generator should match"
        )
    )
    instructions_pattern: list[str] = Field(
        description="Standard cover-page instructions that appear on every paper, in order"
    )
    sections: list[SectionBlueprint]


# ── §4.3  Paper (AI → FE for editing) ─────────────────────────────────────
# Defined here so FE can mock from the same file before generate.py is ready.


class SubPart(BaseModel):
    label: str = Field(description="e.g. '(a)', '(b)'")
    prompt: str
    marks: int


class Question(BaseModel):
    """One question inside a PaperSchema section."""

    id: str = Field(description="Stable identifier for the life of the paper, e.g. 'q1', 'q2a'")
    number: str = Field(description="Display number, e.g. '1', '2(a)'")
    marks: int
    type: str = Field(description="Same vocabulary as SectionBlueprint.question_types")
    prompt: str = Field(description="Full question text as it will appear on the printed paper")
    sub_parts: list[SubPart] = Field(default_factory=list)
    context_passage: Optional[str] = Field(
        default=None,
        description="Optional reading passage shown above the question",
    )


class SectionPaper(BaseModel):
    id: str
    title: str
    marks: int
    instructions: str
    questions: list[Question]


class PaperSchema(BaseModel):
    """
    §4.3 — Generated paper.  Also the shape after FE edits.

    Every question.id is stable for the life of the paper.
    Regeneration replaces the question object's content but keeps its id.
    """

    title: str
    duration_minutes: int
    total_marks: int
    instructions: list[str] = Field(description="Cover-page instructions, in order")
    sections: list[SectionPaper]
