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
    difficulty: int = Field(
        default=3,
        ge=1,
        le=5,
        description=(
            "Estimated difficulty 1-5 (1=easy recall, 3=standard, 5=challenging). "
            "Used by the FE to display a balanced-paper indicator."
        ),
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


# ── §4.4  Answer Key (AI → teacher) ─────────────────────────────────────────


class SubPartAnswer(BaseModel):
    label: str = Field(description="Matches SubPart.label, e.g. '(a)'")
    model_answer: str
    marks: int


class QuestionAnswer(BaseModel):
    """Model answer + marking criteria for one Question."""

    question_id: str = Field(description="Matches Question.id exactly")
    model_answer: str = Field(
        description=(
            "The expected best answer. For open-ended questions, a high-band exemplar; "
            "for fill-in-the-blank / MCQ, the exact correct option(s)."
        )
    )
    marking_criteria: list[str] = Field(
        description=(
            "Bullet points describing how to award marks. "
            "E.g. ['1 mark for correct verb form', '1 mark for subject-verb agreement']."
        )
    )
    sub_part_answers: list[SubPartAnswer] = Field(
        default_factory=list,
        description="One entry per SubPart on the source Question (empty if no sub-parts).",
    )
    common_mistakes: list[str] = Field(
        default_factory=list,
        description="Typical errors candidates make for this question type.",
    )


class SectionAnswerKey(BaseModel):
    section_id: str
    section_title: str
    answers: list[QuestionAnswer]


class AnswerKeySchema(BaseModel):
    """
    §4.4 — Answer key + marking scheme for a generated paper.
    Maps 1:1 against PaperSchema by ids.
    """

    paper_title: str
    total_marks: int
    sections: list[SectionAnswerKey]


# ── Dedup warning shape (FE display) ────────────────────────────────────────


class DuplicateWarning(BaseModel):
    """One potential overlap between a generated question and the source PDFs."""

    question_id: str
    similarity: float = Field(ge=0.0, le=1.0)
    matched_source_snippet: str = Field(description="The source text fragment that closely matches")
    severity: str = Field(description="'high' (>=0.9), 'medium' (0.8-0.9), 'low' (<0.8)")


# ════════════════════════════════════════════════════════════════════════════
# Sprint 2 — Math-oriented schemas (O/L Mathematics, RAG pipeline)
#
# These coexist with the sprint-1 English schemas above during the cutover.
# Topic strings are canonical `Topic.value` from ai/taxonomy.py.
# ════════════════════════════════════════════════════════════════════════════

Difficulty = str  # "easy" | "medium" | "hard"
QType = str       # "mcq" | "structured" | "calculation" | "proof" | "word_problem"


# ── Extraction output: one question pulled from a teacher's past paper ────────


class ExtractedQuestion(BaseModel):
    """One question decomposed from an uploaded paper → persisted as a Question row."""

    question_number: str = Field(description="As printed, e.g. '1', '2(a)', '3(ii)'")
    question_text: str = Field(description="Full question text, math in LaTeX (inline $...$ or $$...$$)")
    topic: str = Field(description="Canonical topic from the taxonomy (see taxonomy_for_prompt)")
    subtopics: list[str] = Field(default_factory=list)
    question_type: QType = Field(description="mcq | structured | calculation | proof | word_problem")
    difficulty: Difficulty = Field(description="easy | medium | hard")
    marks: int = Field(ge=0)
    solution: Optional[str] = Field(default=None, description="Worked solution if present in the source, LaTeX")
    mark_scheme: Optional[str] = Field(default=None, description="Mark breakdown if present in the source")
    has_diagram: bool = Field(default=False, description="True if the question depends on a figure/diagram")
    source_page: Optional[int] = None


class ExtractionResult(BaseModel):
    """Full extraction of one source PDF."""

    questions: list[ExtractedQuestion]


# ── Blueprint: a paper spec made of typed slots ───────────────────────────────


class Slot(BaseModel):
    """One question slot in the blueprint — the spec a generated question must fill."""

    topic: str = Field(description="Canonical topic from the taxonomy")
    subtopic: Optional[str] = None
    question_type: QType = Field(description="mcq | structured | calculation | proof | word_problem")
    difficulty: Difficulty = Field(description="easy | medium | hard")
    marks: int = Field(ge=0)


class MathSection(BaseModel):
    id: str = Field(description="Stable section id, e.g. 'secA'")
    title: str
    instructions: str = ""
    slots: list[Slot]

    @property
    def marks(self) -> int:
        return sum(s.marks for s in self.slots)


class MathBlueprint(BaseModel):
    """Paper specification derived from the teacher's StyleProfile + paper structure."""

    subject: str = "Mathematics"
    level: str = "GCE O/L"
    paper_label: str = Field(default="Paper I", description="e.g. 'Paper I', 'Paper II'")
    duration_minutes: int
    total_marks: int
    instructions: list[str] = Field(default_factory=list)
    sections: list[MathSection]


# ── Generated math question + worked solution + mark scheme ───────────────────


class MarkSchemeItem(BaseModel):
    """One awardable mark with the criterion that earns it (method/accuracy marks)."""

    marks: int = Field(ge=0)
    criterion: str = Field(description="What earns these mark(s), e.g. 'M1: correct substitution'")


class WorkedSolution(BaseModel):
    """Step-by-step worked solution for the answer paper."""

    steps: list[str] = Field(description="Ordered solution steps, math in LaTeX")
    final_answer: str = Field(description="The final answer, LaTeX; the value SymPy verification checks")


class MathQuestion(BaseModel):
    """A generated math question. Stable `id` across edits/regeneration."""

    id: str
    number: str
    topic: str
    subtopic: Optional[str] = None
    question_type: QType
    difficulty: Difficulty
    marks: int = Field(ge=0)
    prompt: str = Field(description="Full question text as printed, math in LaTeX")
    worked_solution: WorkedSolution
    mark_scheme: list[MarkSchemeItem] = Field(default_factory=list)
    needs_diagram: bool = Field(default=False, description="Flagged for manual diagram addition (S2-22)")
    exemplar_ids: list[str] = Field(
        default_factory=list,
        description="IDs of the teacher's bank questions used as RAG exemplars (provenance/audit)",
    )


class MathSectionPaper(BaseModel):
    id: str
    title: str
    instructions: str = ""
    questions: list[MathQuestion]

    @property
    def marks(self) -> int:
        return sum(q.marks for q in self.questions)


class MathPaper(BaseModel):
    """A generated O/L math paper."""

    title: str
    subject: str = "Mathematics"
    level: str = "GCE O/L"
    duration_minutes: int
    total_marks: int
    instructions: list[str] = Field(default_factory=list)
    sections: list[MathSectionPaper]


# ── Verification result (S2-13) ───────────────────────────────────────────────


class VerificationResult(BaseModel):
    """Outcome of SymPy + LLM verification for one generated question."""

    question_id: str
    status: str = Field(description="'verified' | 'failed' | 'unchecked'")
    method: str = Field(description="'sympy' | 'llm' | 'none'")
    detail: str = Field(default="", description="Why it passed/failed; mismatch info for debugging")
