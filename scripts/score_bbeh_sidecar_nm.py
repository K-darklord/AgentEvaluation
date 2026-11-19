#!/usr/bin/env python3
"""B1 scoring for the memory-manipulation arms (docs/MEMORY_MANIPULATION_SPEC_v3_1.md, section 3).

Scores GNM (800) and GKI (400) with the SAME official rule functions as
scripts/score_bbeh_sidecar.py (src.bbeh_eval.evaluate_correctness / answer_key, verbatim),
writing experiments/hle400/t3/bbeh_sidecar_nm.json in the spec format
  {"arms": {"GNM": {task_id: [{"c": bool, "k": key|None}, ...]}, "GKI": {...}}}
Every round of every trajectory must produce a row; otherwise the run aborts.

Run: python3 scripts/score_bbeh_sidecar_nm.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.bbeh_eval import evaluate_correctness, answer_key  # noqa: E402

MODEL = "qwen3.8-flash-payg"
ARMS = ["GNM", "GKI"]
OUT = REPO / "experiments" / "hle400" / "t3" / "bbeh_sidecar_nm.json"


def traj_path(arm: str) -> Path:
    return REPO / "experiments" / f"b1_{arm}_hard_{MODEL}" / MODEL / "loop_trajectories.jsonl"


def main() -> None:
    arms = {}
    for arm in ARMS:
        p = traj_path(arm)
        if not p.exists():
            print(f"[fatal] missing {p}", flush=True)
            sys.exit(1)
        task_rows = {}
        for line in p.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            tid = d["task_id"]
            gold = d.get("gold_answer", "")
            rounds = d.get("rounds", [])
            rows = []
            for r in rounds:
                fa = r.get("final_answer", "")
                fr = r.get("finish_reason", "")
                rows.append({
                    "c": bool(evaluate_correctness(fa, gold)),
                    "k": answer_key(fa, fr),
                })
            if len(rows) != len(rounds):
                print(f"[fatal] {tid}: rows {len(rows)} != rounds {len(rounds)}", flush=True)
                sys.exit(1)
            task_rows[tid] = rows
        arms[arm] = task_rows
        print(f"[{arm}] {len(task_rows)} tasks, {sum(len(v) for v in task_rows.values())} rounds", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"arms": arms}, open(OUT, "w"), ensure_ascii=False)
    print(f"wrote {OUT}", flush=True)
    for arm in ARMS:
        n_tasks = len(arms[arm])
        n_rounds = sum(len(v) for v in arms[arm].values())
        n_nokey = sum(1 for v in arms[arm].values() for x in v if x["k"] is None)
        print(f"  {arm:5s} tasks={n_tasks:4d} rounds={n_rounds} no_key_rounds={n_nokey}", flush=True)


if __name__ == "__main__":
    main()
