#!/usr/bin/env python3
"""Draw the B0 candidate-question lists (second-benchmark screening).

Three candidate sets, all sampled with the FIXED seed 20261117 and never re-drawn:
  * GSM8K   : 200 questions from data/raw/gsm8k_test.jsonl (test split, 1319 rows).
              Gold = the number after the final '####' (commas stripped, kept as string).
  * BBEH    : 35 questions per task, across all 23 BIG-Bench Extra Hard tasks
              (data/raw/bbeh/bbeh/benchmark_tasks/<task>/task.json, 4520 rows total).
  * OlymMATH: full take (no sampling) of EN-EASY (100) + EN-HARD (100).

Writes question-list JSONL files and a single manifest recording the rule, seed and ids.
Reads no experiment output. Deterministic: re-running produces identical files.

Usage: python3 scripts/sample_b0_candidate_sets.py
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = 20261117
GSM8K_SRC = REPO / "data/raw/gsm8k_test.jsonl"
GSM8K_N = 200
BBEH_TASK_DIR = REPO / "data/raw/bbeh/bbeh/benchmark_tasks"
BBEH_PER_TASK = 35
OLYM_EASY = REPO / "data/raw/olymmath/data/OlymMATH-EN-EASY.jsonl"
OLYM_HARD = REPO / "data/raw/olymmath/data/OlymMATH-EN-HARD.jsonl"

_GSM8K_FINAL_RE = re.compile(r"####\s*(.+)$")

def _gsm8k_gold(answer: str) -> str:
    m = _GSM8K_FINAL_RE.search(answer or "")
    if not m:
        return ""
    return m.group(1).strip().replace(",", "").strip(".")

def sample_gsm8k(rng) -> list[dict]:
    rows = [json.loads(l) for l in GSM8K_SRC.open(encoding="utf-8") if l.strip()]
    idxs = rng.sample(range(len(rows)), GSM8K_N)
    out = []
    for j, i in enumerate(idxs):
        r = rows[i]
        out.append({
            "task_id": f"gsm8k_b0_{j:03d}",
            "question": r.get("question", "").strip(),
            "gold_answer": _gsm8k_gold(r.get("answer", "")),
            "answer_raw": r.get("answer", ""),
            "benchmark": "gsm8k", "split": "test", "task": "",
            "source_index": i,
        })
    return out

def sample_bbeh(rng) -> list[dict]:
    task_dirs = sorted(p for p in BBEH_TASK_DIR.iterdir() if p.is_dir())
    out = []
    for td in task_dirs:
        task = td.name
        with (td / "task.json").open(encoding="utf-8") as _f:
            data = json.load(_f)
        examples = data["examples"]
        idxs = rng.sample(range(len(examples)), BBEH_PER_TASK)
        for j, i in enumerate(idxs):
            ex = examples[i]
            out.append({
                "task_id": f"bbeh_{task}_{j:03d}",
                "question": ex["input"].strip(),
                "gold_answer": str(ex.get("target", "")),
                "benchmark": "bbeh", "split": "", "task": task,
                "source_index": i,
            })
    return out

def take_olymmath() -> list[dict]:
    out = []
    for split, path in (("EASY", OLYM_EASY), ("HARD", OLYM_HARD)):
        for j, line in enumerate(path.open(encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out.append({
                "task_id": f"olymmath_{split.lower()}_{j:03d}",
                "question": r["problem"].strip(),
                "gold_answer": str(r.get("answer", "")),
                "benchmark": "olymmath", "split": split, "task": "",
                "subject": r.get("subject", ""),
                "unique_id": r.get("unique_id", ""),
                "source_index": j,
            })
    return out

def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main() -> int:
    import random
    # One independent RNG per benchmark (each seeded with the SAME fixed seed), so a
    # single benchmark's draw does not depend on the others' RNG consumption order.
    gsm = sample_gsm8k(random.Random(SEED))
    bbeh = sample_bbeh(random.Random(SEED))
    olym = take_olymmath()

    gsm_path = REPO / "data/raw/b0/gsm8k_b0_200.jsonl"
    bbeh_path = REPO / "data/raw/b0/bbeh_b0_805.jsonl"
    olym_path = REPO / "data/raw/b0/olymmath_b0_200.jsonl"
    _write(gsm_path, gsm)
    _write(bbeh_path, bbeh)
    _write(olym_path, olym)

    manifest = {
        "rule": "B0 second-benchmark candidate sampling, FIXED seed, never re-drawn",
        "seed": SEED,
        "gsm8k": {"n": len(gsm), "file": str(gsm_path.relative_to(REPO)),
                   "source": str(GSM8K_SRC.relative_to(REPO)), "source_rows": 1319},
        "bbeh": {"n": len(bbeh), "per_task": BBEH_PER_TASK,
                  "tasks": sorted({r["task"] for r in bbeh}),
                  "n_tasks": len({r["task"] for r in bbeh}),
                  "per_task_distribution": dict(Counter(r["task"] for r in bbeh)),
                  "file": str(bbeh_path.relative_to(REPO))},
        "olymmath": {"n": len(olym), "split_distribution": dict(Counter(r["split"] for r in olym)),
                      "file": str(olym_path.relative_to(REPO))},
    }
    man_path = REPO / "data/raw/b0_candidate_selection.json"
    man_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")

    print("gsm8k:", len(gsm), "->", gsm_path.relative_to(REPO))
    print("bbeh:", len(bbeh), "tasks:", len(manifest["bbeh"]["tasks"]), "->", bbeh_path.relative_to(REPO))
    print("olymmath:", len(olym), manifest["olymmath"]["split_distribution"], "->", olym_path.relative_to(REPO))
    print("manifest ->", man_path.relative_to(REPO))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
