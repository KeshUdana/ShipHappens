# Golden evaluation dataset

The eval runner scores the AI pipeline against the cases in this folder.

## Layout

```
golden/
  pdfs/       <-- DROP PAST-PAPER PDFs HERE (the input location)
  expected/   <x>.blueprint.json — human-verified ground truth per PDF
              <x>.blueprint.draft.json — machine drafts awaiting human review
  blueprints/ *.json — hand-checked BlueprintSchema files that drive the
              generation suite (falls back to ai/samples/ when empty)
  seeded_duplicates.json — JSON list of question strings copied (near-)verbatim
              from the PDFs, for measuring dedup recall
```

## Workflow

```powershell
# 1. Drop PDFs into golden/pdfs/, then verify they're usable
uv run python -m evals.prepare

# 2. Generate draft ground truth for each PDF (one Gemini call per PDF)
uv run python -m evals.prepare --extract-drafts

# 3. HUMAN STEP: open each expected/<x>.blueprint.draft.json, correct any
#    extraction mistakes (marks, sections, duration), then rename it to
#    expected/<x>.blueprint.json — the corrected file is the ground truth.

# 4. Run the suite — blueprint + dedup surfaces now activate automatically
uv run python -m evals.run
```

## Which surfaces need ground truth?

| Surface | Ground truth needed? | Why |
|---|---|---|
| Blueprint extraction | **Yes** — `expected/*.blueprint.json` | Only a human can confirm the AI read the PDF correctly |
| Dedup | **Yes** — `seeded_duplicates.json` | Recall needs known-positive labels |
| Generation | No | Scored against the blueprint's own constraints |
| Regeneration | No | Scored on invariants + novelty vs the original |
| Answer key | No | Scored on 1:1 coverage of the paper |
