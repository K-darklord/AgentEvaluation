#!/usr/bin/env python3
"""Draw the two new question sets for docs/MODEL_DEPENDENCE_SPEC.md (400 + 400, text-only, stratified by category).
Same rule as build_hle_400_set.py: text-only pool, proportional largest-remainder allocation by category, pandas
sample with a fixed seed. The 400 questions already used (data/raw/hle/hle_400_new.jsonl) are excluded; stage 2 is
drawn from what remains after stage 1. Needs pyarrow and pandas (run on the machine that built the 400 set).
Writes data/raw/hle/hle_confirm_s1.jsonl, hle_confirm_s2.jsonl (schema of hle_400_new.jsonl) and
data/raw/hle/hle_confirm_selection.json. Reads no experiment output.
Usage: python3 scripts/build_hle_confirm_sets.py"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from build_hle_400_set import allocate, derive_shape, PARQUET  # same allocation and shape rules
USED = REPO / "data/raw/hle/hle_400_new.jsonl"
SEEDS = {"s1": 20261116, "s2": 20261117}
N = 400

def main() -> int:
    used = {json.loads(l)["id"] for l in USED.open(encoding="utf-8") if l.strip()}
    assert len(used) == 400
    df = pq.read_table(PARQUET).to_pandas()
    text_only = df[(df["image"].isna() | (df["image"] == ""))]
    pool = text_only[~text_only["id"].isin(used)]
    manifest = {"rule": "text-only, not among the 400 used, proportional allocation by category, fixed seeds", "seeds": SEEDS,
                "text_only_available": int(len(text_only)), "pool_after_exclusion": int(len(pool)), "sets": {}}
    for name, seed in SEEDS.items():
        counts = pool["category"].value_counts().to_dict()
        alloc = allocate(counts, N)
        rows = []
        for cat, k in alloc.items():
            sub = pool[pool["category"] == cat]
            for r in sub.sample(n=min(k, len(sub)), random_state=seed).to_dict("records"):
                rows.append({"id": r["id"], "answer_type": r["answer_type"], "category": r["category"], "raw_subject": r["raw_subject"],
                             "shape": derive_shape(r["answer_type"], r["answer"]), "answer": r["answer"], "question": r["question"]})
        rows = rows[:N]
        assert len(rows) == N and len({r["id"] for r in rows}) == N
        out = REPO / f"data/raw/hle/hle_confirm_{name}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        ids = {r["id"] for r in rows}
        pool = pool[~pool["id"].isin(ids)]
        manifest["sets"][name] = {"n": N, "file": str(out.relative_to(REPO)), "category_distribution": dict(Counter(r["category"] for r in rows)),
                                  "answer_type_distribution": dict(Counter(r["answer_type"] for r in rows)), "ids": [r["id"] for r in rows]}
        print("wrote", out, "categories", manifest["sets"][name]["category_distribution"])
    (REPO / "data/raw/hle/hle_confirm_selection.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
