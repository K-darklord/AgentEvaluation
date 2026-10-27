#!/usr/bin/env python3
"""Build the 150-question NEW HLE set (text-only, stratified by category).

Deterministic (seed=42). Excludes the 50-question pilot and image (VLM-deferred)
rows. Derives the scorer ``shape`` dispatch tag the same way the pilot did:
multipleChoice -> ``mc``; pure number -> ``int``; LaTeX/backslash -> ``symbol``;
otherwise -> ``text``. Writes ``data/raw/hle/hle_150_new.jsonl`` (pilot schema)
plus a selection manifest for audit, so the sample is reproducible.
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
OUT = REPO / "data/raw/hle/hle_150_new.jsonl"
MANIFEST = REPO / "data/raw/hle/hle_150_new_selection.json"

SEED = 42
N = 150

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
    # top up if a category hit its ceiling
    for c in sorted(counts, key=lambda c: -(counts[c] - alloc[c])):
        if rem <= 0:
            break
        add = min(rem, counts[c] - alloc[c])
        if add > 0:
            alloc[c] += add
            rem -= add
    return alloc


def main() -> int:
    df = pq.read_table(PARQUET).to_pandas()
    pilot_ids = {json.loads(l)["id"] for l in PILOT.open(encoding="utf-8") if l.strip()}

    text_only = df[(df["image"].isna() | (df["image"] == ""))]
    text_only = text_only[~text_only["id"].isin(pilot_ids)]

    counts = text_only["category"].value_counts().to_dict()
    alloc = allocate(counts, N)

    rows: list[dict] = []
    by_cat = {c: text_only[text_only["category"] == c] for c in counts}
    for cat, k in alloc.items():
        pool = by_cat[cat]
        pick = pool.sample(n=min(k, len(pool)), random_state=SEED).to_dict("records")
        for r in pick:
            rows.append({
                "id": r["id"],
                "answer_type": r["answer_type"],
                "category": r["category"],
                "raw_subject": r["raw_subject"],
                "shape": derive_shape(r["answer_type"], r["answer"]),
                "answer": r["answer"],
                "question": r["question"],
            })

    rows = rows[:N]
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": SEED,
        "n": len(rows),
        "pilot_excluded": len(pilot_ids),
        "text_only_available": int(len(text_only)),
        "category_distribution": dict(Counter(r["category"] for r in rows)),
        "shape_distribution": dict(Counter(r["shape"] for r in rows)),
        "answer_type_distribution": dict(Counter(r["answer_type"] for r in rows)),
        "ids": [r["id"] for r in rows],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, "n =", len(rows))
    for k in ("seed", "text_only_available", "category_distribution",
              "shape_distribution", "answer_type_distribution"):
        print(f"  {k}:", manifest[k])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())