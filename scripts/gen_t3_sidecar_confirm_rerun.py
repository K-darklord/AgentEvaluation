#!/usr/bin/env python3
"""V1 variance frozen scoring -> is_correct_t3_sidecar_confirm_rerun.json.

Same frozen protocol as gen_t3_sidecar_confirm.py (trunc > T1 > astra K1 > K3 rules),
scoring ONLY the two V1 rerun arms (C2r, A2PYr) on hle_401..800. The frozen K3 rules
are keyed hle_001..400 and do not fire here (kept verbatim). Astra K1 verdicts are read
from and appended to astra_verdicts_confirm.jsonl (deterministic per task_id+final_answer).

Run:  python3 scripts/gen_t3_sidecar_confirm_rerun.py [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

# Reuse the frozen protocol functions from the S1 confirmation scorer (rules unchanged).
_spec = importlib.util.spec_from_file_location(
    "gen_confirm", str(AGENT_ROOT / "scripts/gen_t3_sidecar_confirm.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

import src.hle_scorer as hs  # noqa: E402
from src.score_hle_arms import read_traj  # noqa: E402

M = "qwen3.8-flash-payg"
ARMS = ["C2", "A2PY"]
T3 = AGENT_ROOT / "experiments/hle400/t3"
SIDECAR_OUT = T3 / "is_correct_t3_sidecar_confirm_rerun.json"
ARM_DIRS = {
    "C2": "conf_C2r_qwen3.8-flash-payg",
    "A2PY": "conf_A2PYr_qwen3.8-flash-payg",
}


def traj_path(arm):
    return AGENT_ROOT / "experiments" / ARM_DIRS[arm] / M / "loop_trajectories.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no live astra calls")
    args = ap.parse_args()

    idx = gen.load_confirm_index()
    astra_cache = gen.load_astra_cache()

    todo = []
    for arm in ARMS:
        traj = read_traj(traj_path(arm))
        if not traj:
            print(f"ERROR: no trajectory for {arm}", file=sys.stderr)
            return 1
        for tid in sorted(traj):
            meta = idx[tid]
            for r in traj[tid]["rounds"]:
                fa = (r.get("final_answer") or "").strip()
                if r.get("finish_reason") == "length":
                    continue
                if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
                    continue
                key = (tid, fa)
                if key in astra_cache:
                    continue
                todo.append(key)

    seen = set()
    unique_todo = []
    for key in todo:
        if key in seen:
            continue
        seen.add(key)
        unique_todo.append(key)

    print(f"astra: cached={sum(1 for v in astra_cache.values() if v is not None)} "
          f"todo={len(unique_todo)} dry_run={args.dry_run}", flush=True)

    if not args.dry_run and unique_todo:
        gen.ASTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        fh = gen.ASTRA_CACHE.open("a", encoding="utf-8")

        def process(key):
            tid, fa = key
            m = idx[tid]
            verdict, served = gen.astra_judge(m["question"], m["gold"], fa)
            if verdict is None:
                verdict = False
            return {"task_id": tid, "final_answer": fa, "c": verdict,
                    "served_model": served}

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(process, k): k for k in unique_todo}
            for n, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                astra_cache[(rec["task_id"], rec["final_answer"])] = rec["c"]
                if n % 50 == 0 or n == len(unique_todo):
                    print(f"  astra {n}/{len(unique_todo)}", flush=True)
        fh.close()

    arms_out = {}
    stats = Counter()
    for arm in ARMS:
        traj = read_traj(traj_path(arm))
        arm_rows = {}
        for tid in sorted(traj):
            meta = idx[tid]
            rows = []
            for r in traj[tid]["rounds"]:
                s = gen.score_round(meta, tid, r, astra_cache, dry_run=args.dry_run)
                if s.get("c") is None:
                    rows.append(s)
                    continue
                adj = gen.adjudicate(tid, (r.get("final_answer") or "").strip())
                if adj is not None:
                    v, _reason, _conf, _ask = adj
                    s = {"c": v, "s": "adjudicated", "adj": True}
                rows.append(s)
                stats[s["s"]] += 1
            arm_rows[tid] = rows
        arms_out[arm] = arm_rows

    out = {
        "note": "V1 variance rerun sidecar; frozen protocol (trunc > T1 > astra K1 > K3 rules). "
                "K3 rules reused verbatim (do not fire on hle_401..800).",
        "stats": dict(stats),
        "arms": arms_out,
    }
    if not args.dry_run:
        SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
        SIDECAR_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"\n== rerun sidecar stats ==\n  {dict(stats)}", flush=True)
        print(f"-> {SIDECAR_OUT}", flush=True)
    else:
        print(f"\n== dry-run: stats ==\n  {dict(stats)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
