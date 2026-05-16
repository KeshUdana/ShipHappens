"""
Generates paper_setA.json and paper_setB.json for FE mocking.

Loads the blueprint samples already committed, re-uploads the PDFs to get
fresh Gemini URIs, then calls generate_paper for each set.

Usage (from backend/):
    uv run python -m ai.gen_paper_samples

Outputs:
    backend/ai/samples/paper_setA.json   (generated from blueprint_setA)
    backend/ai/samples/paper_setB.json   (generated from blueprint_setB)
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from ai.blueprint import _upload_pdf          # noqa: E402
from ai.generate import generate_paper        # noqa: E402
from ai.schemas import BlueprintSchema        # noqa: E402

SAMPLES_DIR = Path(__file__).parent / "samples"
SOURCE_DIR = SAMPLES_DIR / "source"


def _load_blueprint(path: Path) -> BlueprintSchema:
    return BlueprintSchema.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    pdfs = sorted(SOURCE_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"[gen_paper_samples] No PDFs in {SOURCE_DIR}")

    print(f"[gen_paper_samples] Found {len(pdfs)} PDF(s): {[p.name for p in pdfs]}")

    # Upload PDFs once and reuse URIs across both sets
    print("[gen_paper_samples] Uploading PDFs to Gemini Files API...")
    uris = [_upload_pdf(p) for p in pdfs]
    uri_setA = uris[:1]       # set A uses first PDF only
    uri_setB = uris           # set B uses all PDFs

    # --- Set A ---
    print("\n--- Set A ---")
    bp_a = _load_blueprint(SAMPLES_DIR / "blueprint_setA.json")
    print(f"[gen_paper_samples] Blueprint: {bp_a.subject}  {bp_a.total_marks} marks  {len(bp_a.sections)} sections")
    paper_a = generate_paper(bp_a, uri_setA)
    out_a = SAMPLES_DIR / "paper_setA.json"
    out_a.write_text(
        json.dumps(paper_a.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    q_a = sum(len(s.questions) for s in paper_a.sections)
    print(f"[gen_paper_samples] Set A saved -> {out_a}")
    print(f"             title={paper_a.title!r}  questions={q_a}  marks={paper_a.total_marks}")

    # --- Set B ---
    print("\n--- Set B ---")
    bp_b = _load_blueprint(SAMPLES_DIR / "blueprint_setB.json")
    print(f"[gen_paper_samples] Blueprint: {bp_b.subject}  {bp_b.total_marks} marks  {len(bp_b.sections)} sections")
    paper_b = generate_paper(bp_b, uri_setB)
    out_b = SAMPLES_DIR / "paper_setB.json"
    out_b.write_text(
        json.dumps(paper_b.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    q_b = sum(len(s.questions) for s in paper_b.sections)
    print(f"[gen_paper_samples] Set B saved -> {out_b}")
    print(f"             title={paper_b.title!r}  questions={q_b}  marks={paper_b.total_marks}")

    print("\n[gen_paper_samples] DONE. Both sample papers generated successfully.")
    print("FE: swap mock data for real API responses now — schema is locked.")


if __name__ == "__main__":
    main()
