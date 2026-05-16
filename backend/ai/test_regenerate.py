"""
Manual test for PBI-13: regenerates 3 questions from paper_setA.

Usage (from backend/):
    uv run python -m ai.test_regenerate

Checks:
  - Returned id matches the requested id
  - Returned marks match the original
  - Prompt is non-empty
  - Content differs from the original (visual check)
"""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from ai.regenerate import regenerate_question      # noqa: E402
from ai.schemas import BlueprintSchema, PaperSchema  # noqa: E402

SAMPLES = Path(__file__).parent / "samples"


def check(label: str, new_q, original_q) -> None:
    assert new_q.id == original_q.id, f"ID mismatch: {new_q.id!r} != {original_q.id!r}"
    assert new_q.marks == original_q.marks, f"Marks mismatch: {new_q.marks} != {original_q.marks}"
    assert new_q.prompt.strip(), "Empty prompt"

    # For questions with sub_parts (MCQ etc.) the top-level prompt is a
    # generic instruction that legitimately stays the same; compare sub_parts.
    if original_q.sub_parts:
        orig_content = json.dumps([sp.model_dump() for sp in original_q.sub_parts])
        new_content  = json.dumps([sp.model_dump() for sp in new_q.sub_parts])
        assert new_content != orig_content or new_q.context_passage != original_q.context_passage, \
            "sub_parts and context_passage are identical to original"
    else:
        assert new_q.prompt != original_q.prompt, \
            "Prompt is identical to original (expected new content)"

    print(f"  [{label}] PASS  id={new_q.id}  marks={new_q.marks}  type={new_q.type!r}")
    snippet = (new_q.sub_parts[0].prompt if new_q.sub_parts else new_q.prompt)
    print(f"     New content: {snippet[:100]}...")


def main() -> None:
    paper = PaperSchema.model_validate_json(
        (SAMPLES / "paper_setA.json").read_text(encoding="utf-8")
    )
    blueprint = BlueprintSchema.model_validate_json(
        (SAMPLES / "blueprint_setA.json").read_text(encoding="utf-8")
    )

    # Build a quick lookup of questions by id
    q_by_id = {q.id: q for s in paper.sections for q in s.questions}

    # Test 1: fill-in-the-blank (s0q0, Grammar section)
    print("\nTest 1: fill-in-the-blank (no nudge)")
    new1 = regenerate_question(paper, blueprint, "s0q0")
    check("test1", new1, q_by_id["s0q0"])

    # Test 2: MCQ_word_choice (s0q2, Grammar section)
    print("\nTest 2: MCQ word choice (no nudge)")
    new2 = regenerate_question(paper, blueprint, "s0q2")
    check("test2", new2, q_by_id["s0q2"])

    # Test 3: reading comprehension with nudge (s2q0, Reading Skills section)
    print("\nTest 3: reading comprehension with nudge='focus on environmental topics'")
    new3 = regenerate_question(
        paper, blueprint, "s2q0", nudge="focus on environmental topics"
    )
    check("test3", new3, q_by_id["s2q0"])
    # Check nudge was roughly honoured (heuristic — environmental words in passage or prompt)
    combined = (new3.prompt + (new3.context_passage or "")).lower()
    nudge_words = {"environment", "climate", "nature", "pollution", "ecology", "green", "carbon"}
    if nudge_words & set(combined.split()):
        print(f"     Nudge honoured: found environmental vocabulary in output.")
    else:
        print(f"     NOTE: nudge words not detected — inspect output manually.")

    print("\nAll 3 regeneration tests passed.")


if __name__ == "__main__":
    main()
