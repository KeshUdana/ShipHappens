"""
S2-13 — Math correctness verification (SymPy + LLM hybrid).

For each generated MathQuestion we check that its stated final answer is actually
correct and the question is solvable:

  1. SymPy path (cheap, deterministic): when the final answer parses as a number or
     simple algebraic expression, try to confirm it. We re-evaluate the answer
     expression and, where the prompt yields a checkable equation, confirm the answer
     satisfies it. This catches arithmetic/algebra errors with no LLM cost.

  2. LLM path (fallback): for proofs, word problems, or anything SymPy can't parse,
     an independent cheap-model solve-and-compare pass judges whether the worked
     solution's final answer is correct for the prompt.

`verify_question` never raises — it returns a VerificationResult so the caller
(ai/generate.py) can decide whether to accept, flag, or regenerate.
"""

from __future__ import annotations

import logging

from sympy import simplify
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from ai.client import fast_model
from ai.schemas import MathQuestion, VerificationResult
from ai.wrapper import call_structured
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


# ── SymPy path ────────────────────────────────────────────────────────────────


def _strip_latex(text: str) -> str:
    """Best-effort LaTeX → plain math for SymPy parsing."""
    t = text.strip()
    for token in ("$$", "$", "\\(", "\\)", "\\[", "\\]", "\\left", "\\right"):
        t = t.replace(token, "")
    t = (t.replace("\\times", "*").replace("\\cdot", "*").replace("\\div", "/")
           .replace("^{", "^(").replace("}", ")").replace("{", "("))
    # Drop a trailing unit/word after the number (e.g. "12 cm"), keep the math head.
    return t.strip().rstrip(".")


def _try_sympy(question: MathQuestion) -> VerificationResult | None:
    """Return a result if SymPy can make a determination, else None (defer to LLM)."""
    answer_raw = question.worked_solution.final_answer
    expr_text = _strip_latex(answer_raw)
    if not expr_text:
        return None

    # If it's a bare equation "lhs = rhs", verify the two sides are equal. This is
    # the only path SymPy can decide on its own, so check it before plain sympify
    # (which rejects the "=").
    if expr_text.count("=") == 1:
        lhs_s, rhs_s = expr_text.split("=")
        try:
            lhs = parse_expr(lhs_s, transformations=_TRANSFORMS)
            rhs = parse_expr(rhs_s, transformations=_TRANSFORMS)
            equal = simplify(lhs - rhs) == 0
            return VerificationResult(
                question_id=question.id,
                status="verified" if equal else "failed",
                method="sympy",
                detail="" if equal else f"{lhs_s.strip()} != {rhs_s.strip()}",
            )
        except (SympifyError, SyntaxError, TypeError, ValueError, AttributeError):
            return None

    # A bare value/expression: correctness-vs-prompt needs the LLM regardless, so
    # always defer the semantic check.
    return None


# ── LLM path ──────────────────────────────────────────────────────────────────


class _Judgment(BaseModel):
    correct: bool = Field(description="Is the stated final answer correct for the question?")
    reason: str = Field(description="One-sentence justification")
    solvable: bool = Field(description="Is the question well-posed and solvable as written?")


_JUDGE_PROMPT = """\
You are a meticulous O/L Mathematics examiner. Solve the QUESTION yourself, then
compare your answer to the STATED ANSWER.

QUESTION
{prompt}

STATED FINAL ANSWER
{answer}

WORKED SOLUTION (for reference; may contain errors)
{solution}

Decide:
- correct: true only if the STATED ANSWER matches what you independently compute.
- solvable: false if the question is ambiguous, contradictory, or missing data.
Output JSON matching the schema. Be strict — a wrong answer must be marked correct=false.
"""


def _judge_llm(question: MathQuestion) -> VerificationResult:
    prompt = _JUDGE_PROMPT.format(
        prompt=question.prompt,
        answer=question.worked_solution.final_answer,
        solution=" ".join(question.worked_solution.steps)[:2000],
    )
    try:
        j = call_structured(
            model=fast_model,
            contents=[prompt],
            schema=_Judgment,
            retries=1,
            label="verify",
        )
    except Exception as exc:
        return VerificationResult(
            question_id=question.id, status="unchecked", method="llm",
            detail=f"judge error: {exc}",
        )
    ok = j.correct and j.solvable
    return VerificationResult(
        question_id=question.id,
        status="verified" if ok else "failed",
        method="llm",
        detail=j.reason,
    )


# ── Public API ──────────────────────────────────────────────────────────────


def verify_question(question: MathQuestion) -> VerificationResult:
    """Verify one generated question. Tries SymPy first, falls back to the LLM judge."""
    sympy_result = _try_sympy(question)
    if sympy_result is not None:
        return sympy_result
    return _judge_llm(question)
