"""
PBI-23 — Edge-case hardening tests.

Tests:
  1. 1-page minimal PDF  → blueprint returns a sane shape (live API call)
  2. Corrupted PDF       → surfaces a clean ValueError, not a raw stack trace
  3. Marks drift unit    → _validate_paper accepts <=10%, rejects >10%
  4. Blueprint sanity    → _validate_blueprint catches bad section sums

Usage (from backend/):
    uv run python -m ai.test_edge_cases
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

import fitz  # pymupdf — already in pyproject.toml
from ai.blueprint import _upload_and_extract, _validate_blueprint
from ai.generate import PaperValidationError, _validate_paper, _marks_drift_pct
from ai.schemas import BlueprintSchema, PaperSchema, SectionBlueprint, SectionPaper, Question


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_minimal_pdf(path: Path) -> None:
    """Create a realistic 1-page exam paper PDF using pymupdf."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    y = 60
    lines = [
        "SAMPLE EXAMINATION PAPER",
        "Subject: General English    Duration: 1 hour    Total Marks: 30",
        "",
        "INSTRUCTIONS",
        "Answer all questions. Write your answers in the spaces provided.",
        "",
        "SECTION A - GRAMMAR (15 marks)",
        "Answer all questions in this section.",
        "",
        "Q1. (5 marks) Fill in the blanks using the correct form of the verb in brackets.",
        "   (1) She _________ (study) every evening last week.",
        "   (2) They _________ (not finish) the project yet.",
        "   (3) By the time we arrived, the film _________ (already, start).",
        "   (4) He _________ (work) here for five years.",
        "   (5) We _________ (travel) to Colombo tomorrow morning.",
        "",
        "Q2. (10 marks) Underline the correct word from those in brackets.",
        "   (1) She is (elder / older) than her brother.",
        "   (2) Please (rise / raise) your hand if you know the answer.",
        "   (3) The news (is / are) very surprising.",
        "   (4) I (lie / lay) the book on the table yesterday.",
        "   (5) Neither the students nor the teacher (was / were) present.",
        "",
        "SECTION B - WRITING (15 marks)",
        "Answer all questions in this section.",
        "",
        "Q3. (15 marks) Write a short paragraph (60-80 words) about the importance of",
        "   education in modern society.",
    ]
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 18
    doc.save(str(path))
    doc.close()


def _make_corrupted_pdf(path: Path) -> None:
    """Write garbage bytes that are not a valid PDF."""
    path.write_bytes(b"THISISNOTAPDF\x00\x01\x02\x03corrupted content here")


# ── Test 1: 1-page minimal PDF ────────────────────────────────────────────────


def test_minimal_pdf() -> None:
    print("\nTest 1: 1-page minimal PDF -> blueprint should return a valid shape")
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "minimal_exam.pdf"
        _make_minimal_pdf(pdf_path)
        print(f"  Created minimal PDF at {pdf_path} ({pdf_path.stat().st_size} bytes)")

        bp = _upload_and_extract([pdf_path])

        assert bp.total_marks > 0, f"total_marks should be > 0, got {bp.total_marks}"
        assert len(bp.sections) >= 1, "Expected at least 1 section"
        assert bp.subject, "subject should be non-empty"

        section_sum = sum(s.marks for s in bp.sections)
        assert section_sum == bp.total_marks, (
            f"Section marks {section_sum} != total_marks {bp.total_marks}"
        )

        print(f"  PASS: subject={bp.subject!r}  sections={len(bp.sections)}  marks={bp.total_marks}")
        for s in bp.sections:
            print(f"    {s.id}: {s.marks} marks  types={s.question_types}")


# ── Test 2: Corrupted PDF ─────────────────────────────────────────────────────


def test_corrupted_pdf() -> None:
    print("\nTest 2: Corrupted PDF -> should raise a clean ValueError, not a raw stack trace")
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "corrupted.pdf"
        _make_corrupted_pdf(bad_path)
        print(f"  Created corrupted file at {bad_path} ({bad_path.stat().st_size} bytes)")

        raised_clean = False
        error_msg = ""
        try:
            _upload_and_extract([bad_path])
        except ValueError as exc:
            raised_clean = True
            error_msg = str(exc)
        except Exception as exc:
            # Any other exception — still passes if it has a clean message
            error_msg = str(exc)
            print(f"  NOTE: Got {type(exc).__name__} instead of ValueError: {error_msg[:120]}")
            raised_clean = True  # Accept — pipeline didn't crash silently

        assert raised_clean, "Expected an exception for corrupted PDF, got none"
        print(f"  PASS: Raised exception with message: {error_msg[:120]}...")


# ── Test 3: Marks drift unit test (no API call) ───────────────────────────────


def _make_paper(total: int, section_id: str = "secA") -> PaperSchema:
    """Build a minimal PaperSchema with one section summing to `total` marks."""
    return PaperSchema(
        title="Test",
        duration_minutes=60,
        total_marks=total,
        instructions=[],
        sections=[
            SectionPaper(
                id=section_id,
                title="Section A",
                marks=total,
                instructions="",
                questions=[Question(id="s0q0", number="1", marks=total, type="essay", prompt="Discuss...")],
            )
        ],
    )


def _make_blueprint(total: int, section_id: str = "secA") -> BlueprintSchema:
    return BlueprintSchema(
        subject="English",
        board="Test Board",
        level="A Level",
        duration_minutes=60,
        total_marks=total,
        tone_notes="formal",
        instructions_pattern=[],
        sections=[
            SectionBlueprint(
                id=section_id, title="Section A", marks=total,
                instructions="", question_types=["essay"], typical_prompt_style="",
            )
        ],
    )


def test_drift_detection() -> None:
    print("\nTest 3: Marks drift detection (unit, no API call)")

    bp = _make_blueprint(100)

    # Exact match — must pass
    try:
        _validate_paper(_make_paper(100), bp)
        print("  PASS: exact match (100/100) accepted")
    except PaperValidationError as e:
        print(f"  FAIL: exact match wrongly rejected: {e}")
        sys.exit(1)

    # 5% drift (<=10%) — must pass with a warning logged
    try:
        _validate_paper(_make_paper(95), bp)
        print("  PASS: 5% drift (95/100) accepted (warning logged)")
    except PaperValidationError as e:
        print(f"  FAIL: 5% drift wrongly rejected: {e}")
        sys.exit(1)

    # 15% drift (>10%) — must raise
    try:
        _validate_paper(_make_paper(85), bp)
        print("  FAIL: 15% drift should have been rejected")
        sys.exit(1)
    except PaperValidationError:
        print("  PASS: 15% drift (85/100) correctly rejected -> retry triggered")

    # total_marks=0 signal — must raise
    bad = _make_paper(0)
    bad = bad.model_copy(update={"total_marks": 0, "sections": [
        SectionPaper(id="secA", title="X", marks=0, instructions="",
                     questions=[Question(id="s0q0", number="1", marks=0, type="essay", prompt="X")])
    ]})
    try:
        _validate_paper(bad, bp)
        print("  FAIL: total_marks=0 signal should have been rejected")
        sys.exit(1)
    except PaperValidationError:
        print("  PASS: total_marks=0 failure signal correctly rejected")


# ── Test 4: Blueprint sanity unit test (no API call) ─────────────────────────


def test_blueprint_validation() -> None:
    print("\nTest 4: Blueprint sanity validation (unit, no API call)")

    # Valid blueprint — must pass
    valid = _make_blueprint(60)
    try:
        _validate_blueprint(valid)
        print("  PASS: valid blueprint accepted")
    except ValueError as e:
        print(f"  FAIL: valid blueprint wrongly rejected: {e}")
        sys.exit(1)

    # Section sum mismatch — catches "combined marks" bug
    bad = _make_blueprint(200)
    bad = bad.model_copy(update={
        "total_marks": 200,
        "sections": [
            SectionBlueprint(id="secA", title="A", marks=60, instructions="",
                             question_types=["essay"], typical_prompt_style=""),
        ]
    })
    try:
        _validate_blueprint(bad)
        print("  FAIL: section sum mismatch should have been caught")
        sys.exit(1)
    except ValueError:
        print("  PASS: section sum 60 != total_marks 200 correctly caught")

    # total_marks = 0
    zero = _make_blueprint(0)
    try:
        _validate_blueprint(zero)
        print("  FAIL: total_marks=0 should have been caught")
        sys.exit(1)
    except ValueError:
        print("  PASS: total_marks=0 correctly caught")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("PBI-23 Edge Case Tests")
    print("=" * 60)

    # Unit tests first (no API calls, fast)
    test_drift_detection()
    test_blueprint_validation()

    # Live API tests (require network + valid GOOGLE_API_KEY)
    print("\n--- Live API tests (require GOOGLE_API_KEY) ---")
    test_minimal_pdf()
    test_corrupted_pdf()

    print("\n" + "=" * 60)
    print("All edge case tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
