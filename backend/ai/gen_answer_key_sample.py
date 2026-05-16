"""
Generates answer_key_setA.json for FE mocking.

Usage (from backend/):
    uv run python -m ai.gen_answer_key_sample
"""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from ai.answer_key import generate_answer_key  # noqa: E402
from ai.schemas import PaperSchema             # noqa: E402

SAMPLES = Path(__file__).parent / "samples"


def main() -> None:
    paper = PaperSchema.model_validate_json(
        (SAMPLES / "paper_setA.json").read_text(encoding="utf-8")
    )
    print(f"[gen_answer_key] Source: {paper.title!r}  questions={sum(len(s.questions) for s in paper.sections)}")

    key = generate_answer_key(paper)

    out = SAMPLES / "answer_key_setA.json"
    out.write_text(json.dumps(key.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    n_answers = sum(len(s.answers) for s in key.sections)
    print(f"[gen_answer_key] Saved -> {out}")
    print(f"             sections={len(key.sections)}  answers={n_answers}  total_marks={key.total_marks}")
    print("[gen_answer_key] DONE.")


if __name__ == "__main__":
    main()
