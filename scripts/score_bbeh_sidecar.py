#!/usr/bin/env python3
"""B1 scoring: per-round BBEH official correctness + candidate key -> bbeh_sidecar.json.

Reads every B1 arm x group loop_trajectories.jsonl and, for each round, computes
  c = evaluate_correctness(final_answer, gold_answer)   # official BBEH scorer, verbatim
  k = answer_key(final_answer, finish_reason)           # preprocess_sample; numeric or None
writes experiments/hle400/t3/bbeh_sidecar.json in the spec format
  {"arms": {arm: {task_id: [{"c": bool, "k": key|None}, ... per round]}}}

Run: python3 scripts/score_bbeh_sidecar.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.bbeh_eval import evaluate_correctness, answer_key  # noqa: E402

MODEL = "qwen3.8-flash-payg"
ARMS = ["A", "A2", "A2P", "C2", "A3", "A2PY"]
GROUPS = ["hard", "easy"]
OUT = REPO / "experiments" / "hle400" / "t3" / "bbeh_sidecar.json"


def traj_path(arm: str, group: str) -> Path:
    return REPO / "experiments" / f"b1_{arm}_{group}_{MODEL}" / MODEL / "loop_trajectories.jsonl"


def main() -> None:
    arms = {}
    for arm in ARMS:
        task_rows = {}
        for group in GROUPS:
            p = traj_path(arm, group)
            if not p.exists():
                print(f"[warn] missing {p}", flush=True)
                continue
            for line in p.open(encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                tid = d["task_id"]
                gold = d.get("gold_answer", "")
                rows = []
                for r in d.get("rounds", []):
                    fa = r.get("final_answer", "")
                    fr = r.get("finish_reason", "")
                    rows.append({
                        "c": bool(evaluate_correctness(fa, gold)),
                        "k": answer_key(fa, fr),
                    })
                task_rows[tid] = rows
        arms[arm] = task_rows
        print(f"[{arm}] {len(task_rows)} tasks", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"arms": arms}, open(OUT, "w"), ensure_ascii=False)
    print(f"wrote {OUT}", flush=True)
    for arm in ARMS:
        n_tasks = len(arms.get(arm, {}))
        n_rounds = sum(len(v) for v in arms.get(arm, {}).values())
        print(f"  {arm:5s} tasks={n_tasks:4d} rounds={n_rounds}", flush=True)


if __name__ == "__main__":
    main()
