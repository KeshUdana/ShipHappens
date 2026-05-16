"""
Generates blueprint_setA.json and blueprint_setB.json for FE mocking.

Usage (from backend/):
    uv run python -m ai.gen_samples

set A = first PDF only
set B = both PDFs combined
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from ai.blueprint import _upload_and_extract  # noqa: E402

SAMPLES_DIR = Path(__file__).parent / "samples" / "source"
OUT_DIR = Path(__file__).parent / "samples"


def main() -> None:
    pdfs = sorted(SAMPLES_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"[gen_samples] No PDFs found in {SAMPLES_DIR}. Add sample papers first.")

    print(f"[gen_samples] Found {len(pdfs)} PDF(s): {[p.name for p in pdfs]}")

    # Set A — first PDF only
    print("\n--- Set A (single paper) ---")
    bp_a = _upload_and_extract([pdfs[0]])
    out_a = OUT_DIR / "blueprint_setA.json"
    out_a.write_text(
        json.dumps(bp_a.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[gen_samples] Set A saved -> {out_a}")
    print(f"             subject={bp_a.subject!r}  sections={len(bp_a.sections)}  marks={bp_a.total_marks}")

    # Set B — all PDFs combined (or second PDF alone if only 1 exists)
    print("\n--- Set B (all papers combined) ---")
    bp_b = _upload_and_extract(pdfs if len(pdfs) > 1 else pdfs)
    out_b = OUT_DIR / "blueprint_setB.json"
    out_b.write_text(
        json.dumps(bp_b.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[gen_samples] Set B saved -> {out_b}")
    print(f"             subject={bp_b.subject!r}  sections={len(bp_b.sections)}  marks={bp_b.total_marks}")

    print("\n[gen_samples] DONE. Both sample blueprints generated successfully.")


if __name__ == "__main__":
    main()
