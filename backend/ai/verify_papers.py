import json
from collections import Counter
from pathlib import Path

SAMPLES = Path(__file__).parent / "samples"

for name in ["paper_setA", "paper_setB"]:
    d = json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    all_q = [q for s in d["sections"] for q in s["questions"]]
    ids = [q["id"] for q in all_q]
    total = sum(q["marks"] for q in all_q)
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    empty = [q["id"] for q in all_q if not q["prompt"].strip()]
    expected = d["total_marks"]
    marks_ok = "OK" if total == expected else f"FAIL (got {total}, expected {expected})"
    ids_ok = "OK" if not dupes else f"DUPES: {dupes}"
    print(f"{name}: marks={marks_ok}  unique_ids={ids_ok}  questions={len(all_q)}  empty_prompts={empty or 'none'}")
    print(f"  title: {d['title']}")
    print(f"  sections: {[s['id'] for s in d['sections']]}")
    print()
