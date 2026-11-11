"""resume_hle150_failed.py
=========================
One-shot recovery for the broken 2026-10-27 overnight HLE-150 run.

Why this exists
---------------
The 2026-10-27 ~00:51 HLE-150 generation (`experiments/hle150_{A,A2,A3,A3C3,C3}`)
ran without a Token-Plan API key (`.env` gained `TOKEN_PLAN_API_KEY` later that
morning). The missing key pushed most round-0 solves into `api_failure`, and
`run_feedback_loop.py` records those tasks with `is_correct=False` (end_state 6),
which polluted every arm's metrics.

A plain resume (`--out-dir <arm>`) does NOT help: its checkpoint loader treats
every task already present in `loop_trajectories.jsonl` as finished — including
api_failure tasks — so it re-runs nothing. This script therefore, per arm:

  1. backs up the arm's `loop_trajectories.jsonl` (audit trail), then
  2. drops every task line whose rounds contain an `api_failure`, keeping only
     the tasks that truly completed (the checkpoint then skips only those), and
  3. re-invokes `run_feedback_loop.py --out-dir <arm>` so the pending (= failed)
     tasks are re-solved now that the API key is present.

One-shot guard
--------------
A marker file `experiments/.hle150_resume_done` is written only after every arm
finishes successfully. Any later invocation sees the marker and exits without
doing any work (zero token spend), so a daily cron can never re-run the loop.

Usage
-----
    python3 scripts/resume_hle150_failed.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL = "deepseek-v4-flash"
HLE150_DATA = REPO_ROOT / "data" / "raw" / "hle" / "hle_150_new.jsonl"
MARKER = REPO_ROOT / "experiments" / ".hle150_resume_done"

# Per-arm flags captured from each arm's loop_summary.json (2026-10-27 run).
# temperature / max_rounds / concurrency MUST match the original run so the
# re-solved tasks are byte-comparable with the surviving ones.
#   arm            temperature  max_rounds  concurrency
ARMS = {
    "hle150_A":    {"arm": "A",    "temperature": "0.0", "max_rounds": "0",  "concurrency": "4"},
    "hle150_A2":   {"arm": "A2",   "temperature": "0.0", "max_rounds": "10", "concurrency": "6"},
    "hle150_A3":   {"arm": "A3",   "temperature": "0.7", "max_rounds": "10", "concurrency": "8"},
    "hle150_A3C3": {"arm": "A3C3", "temperature": "0.7", "max_rounds": "10", "concurrency": "8"},
    "hle150_C3":   {"arm": "C3",   "temperature": "0.0", "max_rounds": "10", "concurrency": "8"},
}

# A3C3 is deferred (2026-10-29): its round 0 must reuse A3's majority-vote
# consensus rather than re-sample K=10 self-consistency. Until that rework lands
# this script skips A3C3; it is re-run later via a dedicated consensus-reuse path.
SKIP_ARMS = {"hle150_A3C3"}


def _load_dotenv() -> None:
    """Load TOKEN_PLAN_API_KEY etc. from the repo .env (never committed)."""
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _traj_path(arm_dir: str) -> Path:
    return REPO_ROOT / "experiments" / arm_dir / MODEL / "loop_trajectories.jsonl"


def _task_is_bad(rec: dict) -> bool:
    """A task must be re-run if any round hit api_failure (quota/timeout/hang).
    finish_reason=length is NOT re-run: on HLE that is the model "rambling"
    (spilling hidden reasoning into the visible answer) — a real wrong answer,
    not a truncated good one — so it is scored as-is, not re-run."""
    return any(r.get("api_failure") for r in rec.get("rounds", []))


def _filter_failed(jsonl_path: Path) -> list[str]:
    """Back up the arm's trajectory file, then keep only clean tasks (no
    api_failure, no finish_reason=length) — the ones the checkpoint may skip.
    Returns the task_ids that were dropped (= the ones to be re-run)."""
    if not jsonl_path.exists():
        return []
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    good, failed = [], []
    for raw in lines:
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            good.append(raw)  # torn/partial trailing line: keep, ignore
            continue
        if _task_is_bad(rec):
            failed.append(rec.get("task_id", ""))
        else:
            good.append(raw)
    if not failed:
        return []
    bak = jsonl_path.with_name(
        f"{jsonl_path.name}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    jsonl_path.replace(bak)
    jsonl_path.write_text("\n".join(good) + ("\n" if good else ""), encoding="utf-8")
    return failed


def _missing_ids(jsonl_path: Path, all_ids: list[str]) -> list[str]:
    """Task ids the loader will produce but that are absent from the trajectory
    (never run / lost in a torn write) — these are re-solved by the checkpoint."""
    present = set()
    if jsonl_path.exists():
        for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                present.add(json.loads(raw).get("task_id"))
            except json.JSONDecodeError:
                continue
    return [t for t in all_ids if t not in present]


def _count_failed(jsonl_path: Path) -> int:
    """Count remaining bad (api_failure) tasks."""
    if not jsonl_path.exists():
        return 0
    n = 0
    for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if _task_is_bad(rec):
            n += 1
    return n


def _resume(arm_dir: str, cfg: dict) -> int:
    """Re-run run_feedback_loop.py for one arm's pending (failed) tasks."""
    cmd = [
        sys.executable, str(REPO_ROOT / "src" / "run_feedback_loop.py"),
        "--task-set", "hle",
        "--arm", cfg["arm"],
        "--models", MODEL,
        "--out-dir", arm_dir,
        "--max-rounds", cfg["max_rounds"],
        "--early-stop", "3",
        "--temperature", cfg["temperature"],
        "--concurrency", cfg["concurrency"],
        "--rationale-mode", "off",
    ]
    env = os.environ.copy()
    env["HLE_DATA_PATH"] = str(HLE150_DATA)
    return subprocess.run(cmd, cwd=REPO_ROOT, env=env).returncode


def main() -> int:
    _load_dotenv()
    if MARKER.exists():
        print(f"resume already done (marker {MARKER} exists); no-op.", flush=True)
        return 0
    if not os.environ.get("TOKEN_PLAN_API_KEY"):
        print("ERROR: TOKEN_PLAN_API_KEY is empty — abort (would re-fail).", flush=True)
        return 2
    if not HLE150_DATA.exists():
        print(f"ERROR: HLE data not found: {HLE150_DATA}", flush=True)
        return 2

    # Task ids the loader will produce, in jsonl order (hle_001..hle_150).
    with HLE150_DATA.open(encoding="utf-8") as f:
        all_ids = [f"hle_{i:03d}" for i, l in enumerate(f, start=1) if l.strip()]

    failed_any = False
    for arm_dir, cfg in ARMS.items():
        if arm_dir in SKIP_ARMS:
            print(f"[{arm_dir}] SKIPPED (deferred: A3 consensus reuse not yet "
                  f"implemented)", flush=True)
            continue
        traj = _traj_path(arm_dir)
        # missing = genuinely never-run tasks (absent BEFORE we drop failures),
        # so the count is not confounded with the api_failure lines we drop below.
        missing = _missing_ids(traj, all_ids)
        dropped = _filter_failed(traj)
        print(f"[{arm_dir}] drop {len(dropped)} api_failure + {len(missing)} unrun "
              f"-> re-run", flush=True)
        if dropped or missing:
            rc = _resume(arm_dir, cfg)
            print(f"[{arm_dir}] resume exit={rc}", flush=True)
            failed_any = failed_any or (rc != 0)
        else:
            print(f"[{arm_dir}] nothing to re-run", flush=True)

    still_bad = {}
    for arm_dir in ARMS:
        if arm_dir in SKIP_ARMS:
            continue
        c = _count_failed(_traj_path(arm_dir))
        m = len(_missing_ids(_traj_path(arm_dir), all_ids))
        still_bad[arm_dir] = c + m
        print(f"[{arm_dir}] residual bad after resume: {c} api_failure + {m} unrun",
              flush=True)

    skipped = [a for a in SKIP_ARMS if a in ARMS]
    if failed_any or any(still_bad.values()):
        print("ERROR: arms still have bad tasks; marker NOT written (safe to retry).",
              flush=True)
        print(f"residual: {still_bad}", flush=True)
        return 1
    if skipped:
        print(f"SKIPPED {skipped} (deferred); marker NOT written.", flush=True)
        return 0
    MARKER.write_text("done\n", encoding="utf-8")
    print(f"all arms clean; wrote marker {MARKER}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())