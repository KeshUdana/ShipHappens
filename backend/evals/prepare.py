"""
Golden-dataset intake tool.

Usage (from backend/):
    uv run python -m evals.prepare                   # validate PDFs in golden/pdfs/
    uv run python -m evals.prepare --extract-drafts  # also generate draft ground-truth
                                                     # blueprints for PDFs missing one

Workflow:
  1. Drop past-paper PDFs into evals/golden/pdfs/
  2. Run this to verify each PDF is usable (opens, has pages, has extractable text).
  3. Run with --extract-drafts: each PDF without an expected blueprint gets a
     Gemini-extracted DRAFT saved to evals/golden/expected/<stem>.blueprint.draft.json.
  4. A human reviews/corrects the draft and renames it to <stem>.blueprint.json —
     that corrected file is the ground truth the eval runner scores against.
"""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

import argparse
import sys

import fitz  # pymupdf

GOLDEN_DIR = Path(__file__).parent / "golden"
PDF_DIR = GOLDEN_DIR / "pdfs"
EXPECTED_DIR = GOLDEN_DIR / "expected"

MIN_TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is probably scanned images


def validate_pdf(path: Path) -> dict:
    """Open the PDF and report whether it's usable for evals."""
    info: dict = {"file": path.name, "ok": False, "problems": []}
    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        info["problems"].append(f"cannot open: {exc}")
        return info

    try:
        info["pages"] = doc.page_count
        if doc.page_count == 0:
            info["problems"].append("0 pages")
        text_chars = sum(len(page.get_text()) for page in doc)  # type: ignore[attr-defined]
        info["text_chars"] = text_chars
        avg = text_chars / doc.page_count if doc.page_count else 0
        info["avg_chars_per_page"] = round(avg)
        if avg < MIN_TEXT_CHARS_PER_PAGE:
            info["problems"].append(
                f"very little extractable text ({avg:.0f} chars/page) — likely a scanned/"
                "image-only PDF. Blueprint extraction may still work (Gemini reads images), "
                "but the dedup surface needs text and will be unreliable."
            )
        if doc.is_encrypted:
            info["problems"].append("encrypted PDF")
    finally:
        doc.close()

    info["ok"] = not any(
        p.startswith(("cannot open", "0 pages", "encrypted")) for p in info["problems"]
    )
    return info


def extract_draft(pdf: Path) -> Path:
    """Run blueprint extraction once and save the result as a draft for human review."""
    from ai.blueprint import _upload_and_extract

    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = EXPECTED_DIR / f"{pdf.stem}.blueprint.draft.json"
    blueprint = _upload_and_extract([pdf])
    draft_path.write_text(blueprint.model_dump_json(indent=2), encoding="utf-8")
    return draft_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate golden PDFs and draft ground truth")
    parser.add_argument("--extract-drafts", action="store_true",
                        help="Generate draft expected-blueprints for PDFs missing one (Gemini calls)")
    args = parser.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found. Drop past papers into:\n  {PDF_DIR}")
        return 1

    print(f"Validating {len(pdfs)} PDF(s) in {PDF_DIR}\n")
    any_bad = False
    usable: list[Path] = []
    for pdf in pdfs:
        info = validate_pdf(pdf)
        status = "OK " if info["ok"] else "BAD"
        print(f"[{status}] {info['file']}: {info.get('pages', '?')} pages, "
              f"{info.get('text_chars', 0):,} text chars")
        for p in info["problems"]:
            print(f"       ! {p}")
        if info["ok"]:
            usable.append(pdf)
        else:
            any_bad = True

    # Ground-truth status
    print("\nGround-truth status:")
    missing: list[Path] = []
    for pdf in usable:
        final = EXPECTED_DIR / f"{pdf.stem}.blueprint.json"
        draft = EXPECTED_DIR / f"{pdf.stem}.blueprint.draft.json"
        if final.exists():
            print(f"  [ready ] {pdf.stem} — expected blueprint present")
        elif draft.exists():
            print(f"  [review] {pdf.stem} — DRAFT exists: correct it, then rename "
                  f"'{draft.name}' -> '{final.name}'")
        else:
            print(f"  [none  ] {pdf.stem} — no ground truth yet")
            missing.append(pdf)

    if args.extract_drafts and missing:
        print(f"\nExtracting draft blueprints for {len(missing)} PDF(s)…")
        for pdf in missing:
            try:
                draft = extract_draft(pdf)
                print(f"  draft written: {draft.relative_to(GOLDEN_DIR.parent)}")
            except Exception as exc:
                print(f"  FAILED for {pdf.name}: {exc}")
        print("\nNow review each draft, fix any extraction mistakes, and rename "
              "*.blueprint.draft.json -> *.blueprint.json to promote it to ground truth.")
    elif missing:
        print(f"\n{len(missing)} PDF(s) lack ground truth. "
              "Re-run with --extract-drafts to generate review drafts.")

    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
