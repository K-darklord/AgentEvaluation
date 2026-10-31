#!/usr/bin/env python3
"""Build the 400-question HLE main set (text-only, stratified by category).

Composition (frozen 2026-10-31 standard):
  - the ORIGINAL 200 questions are kept verbatim (50 pilot + 150 hle150);
  - an additional 200 are sampled (seed=42, category-stratified) from the
    remaining text-only pool, with no id overlap against the fixed 200.
Total = 400 unique questions in the pilot schema.

Deterministic (seed=42). Shape dispatch mirrors build_hle_150_set.py:
  multipleChoice -> mc; pure number -> int; LaTeX/backslash -> symbol; else text.

Writes:
  data/raw/hle/hle_400_new.jsonl          (pilot schema, 400 rows)
  data/raw/hle/hle_400_new_selection.json  (manifest for audit)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
PARQUET = REPO / "data/raw/hle/data/test-00000-of-00001.parquet"
PILOT = REPO / "data/raw/hle/hle_50_pilot.jsonl"
HLE150 = REPO / "data/raw/hle/hle_150_new.jsonl"
OUT = REPO / "data/raw/hle/hle_400_new.jsonl"
MANIFEST = REPO / "data/raw/hle/hle_400_new_selection.json"

SEED = 42
N_TOTAL = 400
FIELDS = ["id", "answer_type", "category", "raw_subject", "shape", "answer", "question"]

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def derive_shape(answer_type: str, answer: str) -> str:
    if answer_type == "multipleChoice":
        return "mc"
    a = (answer or "").strip()
    if _NUM_RE.fullmatch(a):
        return "int"
    if "$" in a or "\\" in a:
        return "symbol"
    return "text"


def load_jsonl(path: Path) -> list[dict]:
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    return [{k: r[k] for k in FIELDS} for r in rows]


def allocate(counts: dict[str, int], n: int) -> dict[str, int]:
    """Proportional (largest-remainder) allocation, min 1 per non-empty category."""
    total = sum(counts.values())
    quota = {c: n * v / total for c, v in counts.items() if total > 0}
    base = {c: int(q) for c, q in quota.items()}
    for c in counts:
        if counts[c] > 0 and base[c] == 0:
            base[c] = 1  # keep tiny categories represented
    alloc = dict(base)
    rem = n - sum(alloc.values())
    order = sorted(counts, key=lambda c: -(quota[c] - base[c]))
    for c in order:
        if rem <= 0:
            break
        if alloc[c] >= counts[c]:
            continue
        alloc[c] += 1
        rem -= 1
    for c in sorted(counts, key=lambda c: -(counts[c] - alloc[c])):
        if rem <= 0:
            break
        add = min(rem, counts[c] - alloc[c])
        if add > 0:
            alloc[c] += add
            rem -= add
    return alloc


def main() -> int:
    old_pilot = load_jsonl(PILOT)
    old_150 = load_jsonl(HLE150)
    fixed = old_pilot + old_150
    fixed_ids = {r["id"] for r in fixed}
    assert len(fixed) == 200 and len(fixed_ids) == 200, "fixed 200 must be unique"

    df = pq.read_table(PARQUET).to_pandas()
    text_only = df[(df["image"].isna() | (df["image"] == ""))]
    pool = text_only[~text_only["id"].isin(fixed_ids)]

    n_new = N_TOTAL - len(fixed)
    counts = pool["category"].value_counts().to_dict()
    alloc = allocate(counts, n_new)

    new_rows: list[dict] = []
    by_cat = {c: pool[pool["category"] == c] for c in counts}
    for cat, k in alloc.items():
        pick = by_cat[cat].sample(n=min(k, len(by_cat[cat])), random_state=SEED).to_dict("records")
        for r in pick:
            new_rows.append({
                "id": r["id"],
                "answer_type": r["answer_type"],
                "category": r["category"],
                "raw_subject": r["raw_subject"],
                "shape": derive_shape(r["answer_type"], r["answer"]),
                "answer": r["answer"],
                "question": r["question"],
            })

    new_rows = new_rows[:n_new]
    rows = fixed + new_rows
    assert len(rows) == N_TOTAL and len({r["id"] for r in rows}) == N_TOTAL, "400 unique required"

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": SEED,
        "n": len(rows),
        "fixed_old": {"pilot": len(old_pilot), "hle150": len(old_150)},
        "new_sampled": len(new_rows),
        "text_only_available": int(len(text_only)),
        "pool_after_exclusion": int(len(pool)),
        "category_distribution": dict(Counter(r["category"] for r in rows)),
        "shape_distribution": dict(Counter(r["shape"] for r in rows)),
        "answer_type_distribution": dict(Counter(r["answer_type"] for r in rows)),
        "ids": [r["id"] for r in rows],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, "n =", len(rows))
    print("  fixed =", len(fixed), " new =", len(new_rows))
    for k in ("seed", "text_only_available", "pool_after_exclusion"):
        print(f"  {k}:", manifest[k])
    print("  category_distribution:", manifest["category_distribution"])
    print("  shape_distribution:", manifest["shape_distribution"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
