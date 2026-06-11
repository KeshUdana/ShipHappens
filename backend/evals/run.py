"""
Deterministic eval runner.

Usage (from backend/):
    uv run python -m evals.run                      # live: real Gemini calls
    uv run python -m evals.run --offline            # checks stored sample papers, no AI calls
    uv run python -m evals.run --cases 1            # limit number of golden cases
    uv run python -m evals.run --notes "post-prompt-tweak"

Writes one EvalRun + many EvalResult rows; prints a summary table.
Exits non-zero if any hard check failed (usable as a regression gate).
"""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
# ai.client reads GOOGLE_API_KEY from os.environ at import time.
load_dotenv(BACKEND_DIR / ".env", override=False)

import argparse
import logging
import subprocess
import sys
from collections import Counter
from typing import Optional
from uuid import UUID

from sqlmodel import select

from ai.client import fast_model, pro_model
from ai.schemas import AnswerKeySchema, BlueprintSchema, PaperSchema
from evals.db import eval_session, init_eval_tables
from evals.models import EvalResult, EvalRun
from evals.usage import UsageCollector, collect_usage

logger = logging.getLogger("evals")

DRIFT_TOLERANCE_PCT = 10.0
NOVELTY_SIMILARITY_MAX = 0.90  # regenerated question must be < this similar to original

GOLDEN_DIR = Path(__file__).parent / "golden"
SAMPLES_DIR = BACKEND_DIR / "ai" / "samples"


# ── Recording ────────────────────────────────────────────────────────────────


class Recorder:
    def __init__(self, session, run_id: UUID) -> None:
        self.session = session
        self.run_id = run_id
        self.failures = 0
        self.total = 0

    def add(
        self,
        surface: str,
        case_id: str,
        metric: str,
        value: float,
        passed: Optional[bool] = None,
        detail: Optional[dict] = None,
        usage: Optional[UsageCollector] = None,
    ) -> None:
        self.total += 1
        if passed is False:
            self.failures += 1
        row = EvalResult(
            run_id=self.run_id,
            surface=surface,
            case_id=case_id,
            metric=metric,
            value=float(value),
            passed=passed,
            detail=detail or {},
            tokens_in=usage.tokens_in if usage else 0,
            tokens_out=usage.tokens_out if usage else 0,
            cost_usd=usage.cost_usd if usage else 0.0,
        )
        self.session.add(row)
        self.session.commit()
        mark = "PASS" if passed else ("FAIL" if passed is False else "info")
        print(f"  [{mark:>4}] {surface}/{case_id} :: {metric} = {value:.3f}")


# ── Golden data loading ──────────────────────────────────────────────────────


def load_golden_blueprints() -> list[tuple[str, BlueprintSchema]]:
    golden = GOLDEN_DIR / "blueprints"
    files = sorted(golden.glob("*.json")) if golden.exists() else []
    if not files:
        files = sorted(SAMPLES_DIR.glob("blueprint_set*.json"))
        if files:
            print(f"(golden/blueprints empty — falling back to {len(files)} ai/samples blueprint(s))")
    return [
        (f.stem, BlueprintSchema.model_validate_json(f.read_text(encoding="utf-8")))
        for f in files
    ]


def load_sample_paper(case_id: str) -> Optional[PaperSchema]:
    """Offline mode: pair blueprint_setA -> paper_setA.json etc."""
    name = case_id.replace("blueprint_", "paper_") + ".json"
    path = SAMPLES_DIR / name
    if not path.exists():
        return None
    return PaperSchema.model_validate_json(path.read_text(encoding="utf-8"))


# ── Deterministic paper checks ───────────────────────────────────────────────


def _drift_pct(actual: int, expected: int) -> float:
    if expected == 0:
        return 100.0
    return abs(actual - expected) / expected * 100.0


def check_paper(rec: Recorder, case_id: str, paper: PaperSchema, blueprint: BlueprintSchema) -> None:
    surface = "generation"
    all_qs = [q for s in paper.sections for q in s.questions]

    rec.add(surface, case_id, "section_count_match",
            1.0 if len(paper.sections) == len(blueprint.sections) else 0.0,
            passed=len(paper.sections) == len(blueprint.sections),
            detail={"expected": len(blueprint.sections), "actual": len(paper.sections)})

    actual_total = sum(q.marks for q in all_qs)
    drift = _drift_pct(actual_total, blueprint.total_marks)
    rec.add(surface, case_id, "total_marks_drift_pct", drift,
            passed=drift <= DRIFT_TOLERANCE_PCT,
            detail={"expected": blueprint.total_marks, "actual": actual_total})

    bp_marks = {s.id: s.marks for s in blueprint.sections}
    for sec in paper.sections:
        expected = bp_marks.get(sec.id)
        if expected is None:
            rec.add(surface, case_id, f"section_id_unknown:{sec.id}", 1.0, passed=False,
                    detail={"section_id": sec.id, "known_ids": list(bp_marks)})
            continue
        actual = sum(q.marks for q in sec.questions)
        sec_drift = _drift_pct(actual, expected)
        rec.add(surface, case_id, f"section_marks_drift_pct:{sec.id}", sec_drift,
                passed=sec_drift <= DRIFT_TOLERANCE_PCT,
                detail={"expected": expected, "actual": actual})

    dupes = [qid for qid, n in Counter(q.id for q in all_qs).items() if n > 1]
    rec.add(surface, case_id, "duplicate_question_ids", float(len(dupes)),
            passed=not dupes, detail={"duplicates": dupes})

    empty = [q.id for q in all_qs if not q.prompt.strip()]
    rec.add(surface, case_id, "empty_prompts", float(len(empty)),
            passed=not empty, detail={"question_ids": empty})

    with_subparts = [q for q in all_qs if q.sub_parts]
    bad_sums = [
        q.id for q in with_subparts
        if sum(sp.marks for sp in q.sub_parts) != q.marks
    ]
    rec.add(surface, case_id, "subpart_marks_mismatch", float(len(bad_sums)),
            passed=not bad_sums,
            detail={"question_ids": bad_sums, "questions_with_subparts": len(with_subparts)})


# ── Live surfaces ────────────────────────────────────────────────────────────


def run_generation(rec: Recorder, case_id: str, blueprint: BlueprintSchema) -> Optional[PaperSchema]:
    from ai.generate import generate_paper

    print(f"\n--- generation: {case_id} (live Gemini call, may take 1-2 min) ---")
    with collect_usage() as usage:
        try:
            paper = generate_paper(blueprint, [])
        except Exception as exc:
            rec.add("generation", case_id, "schema_valid", 0.0, passed=False,
                    detail={"error": str(exc)[:500]}, usage=usage)
            return None
    rec.add("generation", case_id, "schema_valid", 1.0, passed=True,
            detail={"attempts": usage.attempts, "failed_attempts": usage.failed_attempts},
            usage=usage)
    rec.add("generation", case_id, "retry_count", float(usage.failed_attempts))
    check_paper(rec, case_id, paper, blueprint)
    return paper


def run_regenerate(rec: Recorder, case_id: str, paper: PaperSchema, blueprint: BlueprintSchema,
                   n_questions: int = 2) -> None:
    from ai.dedup import _cosine, _embed_texts
    from ai.regenerate import regenerate_question

    surface = "regenerate"
    targets = [s.questions[0] for s in paper.sections if s.questions][:n_questions]
    for original in targets:
        print(f"\n--- regenerate: {case_id}/{original.id} ---")
        with collect_usage() as usage:
            try:
                fresh = regenerate_question(paper, blueprint, original.id, None)
            except Exception as exc:
                rec.add(surface, case_id, f"regen_ok:{original.id}", 0.0, passed=False,
                        detail={"error": str(exc)[:500]}, usage=usage)
                continue

        invariants_ok = (
            fresh.id == original.id
            and fresh.number == original.number
            and abs(fresh.marks - original.marks) <= 2
        )
        rec.add(surface, case_id, f"invariants_preserved:{original.id}",
                1.0 if invariants_ok else 0.0, passed=invariants_ok,
                detail={"original": {"id": original.id, "number": original.number, "marks": original.marks},
                        "fresh": {"id": fresh.id, "number": fresh.number, "marks": fresh.marks}},
                usage=usage)

        try:
            embs = _embed_texts([original.prompt, fresh.prompt])
            sim = _cosine(embs[0], embs[1])
            rec.add(surface, case_id, f"novelty_similarity:{original.id}", sim,
                    passed=sim < NOVELTY_SIMILARITY_MAX,
                    detail={"original_prompt": original.prompt[:200], "fresh_prompt": fresh.prompt[:200]})
        except Exception as exc:
            logger.warning("Novelty embedding failed: %s", exc)


def run_answer_key(rec: Recorder, case_id: str, paper: PaperSchema) -> None:
    from ai.answer_key import generate_answer_key

    surface = "answer_key"
    print(f"\n--- answer_key: {case_id} ---")
    with collect_usage() as usage:
        try:
            key: AnswerKeySchema = generate_answer_key(paper)
        except Exception as exc:
            rec.add(surface, case_id, "key_generated", 0.0, passed=False,
                    detail={"error": str(exc)[:500]}, usage=usage)
            return
    rec.add(surface, case_id, "key_generated", 1.0, passed=True, usage=usage)

    paper_qids = {q.id for s in paper.sections for q in s.questions}
    answered = {a.question_id for s in key.sections for a in s.answers}
    missing = sorted(paper_qids - answered)
    coverage = 1.0 - (len(missing) / len(paper_qids)) if paper_qids else 0.0
    rec.add(surface, case_id, "answer_coverage", coverage, passed=not missing,
            detail={"missing_question_ids": missing, "extra_ids": sorted(answered - paper_qids)})

    # Sub-part answer coverage
    expected_subparts = {
        (q.id, sp.label)
        for s in paper.sections for q in s.questions for sp in q.sub_parts
    }
    got_subparts = {
        (a.question_id, spa.label)
        for s in key.sections for a in s.answers for spa in a.sub_part_answers
    }
    sp_missing = sorted(expected_subparts - got_subparts)
    sp_cov = 1.0 - (len(sp_missing) / len(expected_subparts)) if expected_subparts else 1.0
    rec.add(surface, case_id, "subpart_answer_coverage", sp_cov, passed=not sp_missing,
            detail={"missing": [f"{q}/{l}" for q, l in sp_missing][:20]})

    rec.add(surface, case_id, "total_marks_match",
            1.0 if key.total_marks == paper.total_marks else 0.0,
            passed=key.total_marks == paper.total_marks,
            detail={"paper": paper.total_marks, "key": key.total_marks})


def run_blueprint(rec: Recorder) -> None:
    """Blueprint-extraction accuracy vs human-verified ground truth.

    Needs golden/pdfs/<x>.pdf paired with golden/expected/<x>.blueprint.json
    (create drafts with: uv run python -m evals.prepare --extract-drafts).
    """
    from ai.blueprint import _upload_and_extract

    expected_dir = GOLDEN_DIR / "expected"
    pdfs = sorted((GOLDEN_DIR / "pdfs").glob("*.pdf")) if (GOLDEN_DIR / "pdfs").exists() else []
    pairs = [
        (pdf, expected_dir / f"{pdf.stem}.blueprint.json")
        for pdf in pdfs
        if (expected_dir / f"{pdf.stem}.blueprint.json").exists()
    ]
    if not pairs:
        print("\n(blueprint surface skipped — needs golden/pdfs/*.pdf + "
              "golden/expected/*.blueprint.json; see evals/prepare.py)")
        return

    surface = "blueprint"
    for pdf, exp_path in pairs:
        case_id = pdf.stem
        expected = BlueprintSchema.model_validate_json(exp_path.read_text(encoding="utf-8"))
        print(f"\n--- blueprint: {case_id} (live extraction) ---")
        with collect_usage() as usage:
            try:
                actual = _upload_and_extract([pdf])
            except Exception as exc:
                rec.add(surface, case_id, "extraction_ok", 0.0, passed=False,
                        detail={"error": str(exc)[:500]}, usage=usage)
                continue
        rec.add(surface, case_id, "extraction_ok", 1.0, passed=True, usage=usage)

        rec.add(surface, case_id, "section_count_match",
                1.0 if len(actual.sections) == len(expected.sections) else 0.0,
                passed=len(actual.sections) == len(expected.sections),
                detail={"expected": len(expected.sections), "actual": len(actual.sections)})

        rec.add(surface, case_id, "total_marks_match",
                1.0 if actual.total_marks == expected.total_marks else 0.0,
                passed=actual.total_marks == expected.total_marks,
                detail={"expected": expected.total_marks, "actual": actual.total_marks})

        dur_drift = _drift_pct(actual.duration_minutes, expected.duration_minutes)
        rec.add(surface, case_id, "duration_drift_pct", dur_drift,
                passed=dur_drift <= DRIFT_TOLERANCE_PCT,
                detail={"expected": expected.duration_minutes, "actual": actual.duration_minutes})

        # Section ids vary between extractions; compare the marks structure instead.
        exp_marks = sorted(s.marks for s in expected.sections)
        act_marks = sorted(s.marks for s in actual.sections)
        rec.add(surface, case_id, "section_marks_structure_match",
                1.0 if exp_marks == act_marks else 0.0,
                passed=exp_marks == act_marks,
                detail={"expected": exp_marks, "actual": act_marks})


def run_dedup(rec: Recorder) -> None:
    """Dedup recall against seeded duplicates. Needs golden/pdfs + seeded_duplicates.json."""
    import json as _json

    from ai.dedup import check_duplicates
    from ai.schemas import Question, SectionPaper

    pdfs = sorted((GOLDEN_DIR / "pdfs").glob("*.pdf")) if (GOLDEN_DIR / "pdfs").exists() else []
    seeds_file = GOLDEN_DIR / "seeded_duplicates.json"
    if not pdfs or not seeds_file.exists():
        print("\n(dedup surface skipped — add golden/pdfs/*.pdf and golden/seeded_duplicates.json)")
        return

    seeds: list[str] = _json.loads(seeds_file.read_text(encoding="utf-8"))
    print(f"\n--- dedup: {len(seeds)} seeded duplicates vs {len(pdfs)} PDF(s) ---")
    fake_paper = PaperSchema(
        title="dedup-probe", duration_minutes=0, total_marks=0, instructions=[],
        sections=[SectionPaper(
            id="seeded", title="Seeded", marks=0, instructions="",
            questions=[
                Question(id=f"seed{i}", number=str(i), marks=1, type="seed", prompt=text)
                for i, text in enumerate(seeds)
            ],
        )],
    )
    warnings = check_duplicates(fake_paper, pdfs)
    flagged = {w.question_id for w in warnings}
    recall = len(flagged) / len(seeds) if seeds else 0.0
    rec.add("dedup", "seeded", "recall", recall, passed=recall >= 0.8,
            detail={"flagged": sorted(flagged), "total_seeds": len(seeds)})


# ── Main ─────────────────────────────────────────────────────────────────────


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND_DIR, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="ShipHappens AI eval runner")
    parser.add_argument("--offline", action="store_true",
                        help="Score stored sample papers only — no Gemini calls")
    parser.add_argument("--cases", type=int, default=None, help="Limit number of golden cases")
    parser.add_argument("--skip-regenerate", action="store_true")
    parser.add_argument("--skip-answer-key", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    init_eval_tables()

    cases = load_golden_blueprints()
    if args.cases:
        cases = cases[: args.cases]
    if not cases:
        print("No golden blueprints found (golden/blueprints or ai/samples). Nothing to do.")
        return 1

    with eval_session() as session:
        run = EvalRun(
            git_sha=_git_sha(),
            suite="deterministic",
            generation_model=f"{pro_model}->{fast_model}",
            offline=args.offline,
            notes=args.notes,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        print(f"Eval run {run.id} (sha={run.git_sha}, offline={args.offline}, {len(cases)} case(s))")

        rec = Recorder(session, run.id)

        for case_id, blueprint in cases:
            if args.offline:
                paper = load_sample_paper(case_id)
                if paper is None:
                    print(f"\n(no stored sample paper for {case_id} — skipping)")
                    continue
                print(f"\n--- generation (offline): {case_id} ---")
                check_paper(rec, case_id, paper, blueprint)
            else:
                paper = run_generation(rec, case_id, blueprint)
                if paper is None:
                    continue
                if not args.skip_regenerate:
                    run_regenerate(rec, case_id, paper, blueprint)
                if not args.skip_answer_key:
                    run_answer_key(rec, case_id, paper)

        if not args.offline:
            run_blueprint(rec)
            run_dedup(rec)

        # Summary
        results = session.exec(
            select(EvalResult).where(EvalResult.run_id == run.id)
        ).all()
        cost = sum(r.cost_usd for r in results)
        tokens = sum(r.tokens_in + r.tokens_out for r in results)
        print("\n" + "=" * 60)
        print(f"Run {run.id}")
        print(f"  checks: {rec.total}   failed: {rec.failures}")
        print(f"  tokens: {tokens:,}   est. cost: ${cost:.4f}")
        print("=" * 60)
        return 1 if rec.failures else 0


if __name__ == "__main__":
    sys.exit(main())
