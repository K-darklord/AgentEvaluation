#!/usr/bin/env python3
"""run_stageb_batched.py
=======================
Re-run every Stage-B non-settle target on ONE rationale protocol (twostage,
with INT-25 applied) in <=CHUNK-sized batches, running check_rationale_health
after each batch and aborting on FAIL. Task lists are read from the EXISTING
experiment dirs (ground truth for the correct (model, task_set) grouping); only
the protocol changes (reason_line -> twostage for deepseek/qwen; INT-25 fixed
twostage for glm).

Separate out-dir per chunk -> no resume/n_tasks ambiguity; merge later.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXP = REPO / "experiments"
CHUNK = 30
CONCURRENCY = 6

# model key -> short dir prefix used by the existing stageb_non_settle_* dirs
SHORT = {"glm-5.3": "glm", "deepseek-v4-flash": "deepseek", "qwen3.8-flash": "qwen"}

# execution order (largest/riskiest groups later, validated glide path first)
GROUPS = [
    ("glm-5.3", "phase1"),
    ("glm-5.3", "new"),
    ("glm-5.3", "gpqa"),
    ("deepseek-v4-flash", "gpqa"),
    ("deepseek-v4-flash", "new"),
    ("deepseek-v4-flash", "phase1"),
    ("qwen3.8-flash", "phase1"),
    ("qwen3.8-flash", "new"),
    ("qwen3.8-flash", "gpqa"),
]


def existing_task_ids(model: str, task_set: str) -> list[str]:
    short = SHORT[model]
    d = EXP / f"stageb_non_settle_{short}_{task_set}_20261018" / model / "loop_trajectories.jsonl"
    ids = []
    for l in d.read_text(encoding="utf-8").splitlines():
        if l.strip():
            ids.append(json.loads(l)["task_id"])
    return sorted(set(ids))


def chunks(ids: list[str], n: int) -> list[list[str]]:
    return [ids[i:i + n] for i in range(0, len(ids), n)]


def run(cmd: list[str]) -> int:
    print("  $ " + " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO)


def main() -> int:
    dry = "--dry-run" in sys.argv
    for model, ts in GROUPS:
        ids = existing_task_ids(model, ts)
        parts = chunks(ids, CHUNK)
        short = SHORT[model]
        for i, part in enumerate(parts):
            suffix = f"_c{i + 1}" if len(parts) > 1 else ""
            out_dir = f"stageb_twostage_{short}_{ts}_20261018{suffix}"
            tasks = ",".join(part)
            cmd = ["python3", "src/run_feedback_loop.py",
                   "--models", model, "--task-set", ts, "--tasks", tasks,
                   "--rationale-mode", "twostage",
                   "--concurrency", str(CONCURRENCY),
                   "--out-dir", out_dir]
            print(f"== {model} {ts} batch {i + 1}/{len(parts)} ({len(part)} tasks) -> {out_dir}")
            if dry:
                continue
            if run(cmd) != 0:
                print(f"FAIL: run_feedback_loop returned nonzero for {out_dir}")
                return 1
            if run(["python3", "scripts/check_rationale_health.py", "--dir", str(EXP / out_dir)]) != 0:
                print(f"FAIL: rationale health check failed for {out_dir}; halting")
                return 1
    print("ALL BATCHES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
