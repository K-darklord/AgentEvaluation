#!/usr/bin/env python3
"""Addendum confirmation scoring (qwen A3 + C2Q + C2QY) -> is_correct_t3_sidecar_confirm2.json.

Frozen per-round protocol, identical to gen_t3_sidecar_confirm.py (trunc > T1 > astra K1
> K3 rules). Three sections (docs/SELECTION_CONFIRMATION_ADDENDUM.md sec 2):

  A3    : self-consistency (round 0 = conf_A greedy T=0; rounds 1..9 = i.i.d. T=0.7)
  C2Q   : question-only critique, natural stop (early-stop 3, max 10)
  C2QY  : C2Q resumed to the token budget (max 100); its rounds that already exist in
          C2Q (the resume prefix, kept verbatim) copy C2Q's verdicts EXACTLY; only the
          continuation rounds past C2Q are scored fresh.

astra K1 verdicts reuse the shared astra_verdicts_confirm.jsonl cache (a verdict for a
given question+answer is model-independent).

Run:  python3 scripts/gen_t3_sidecar_confirm2.py [--dry-run]
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
T3 = AGENT_ROOT / "experiments/hle400/t3"
SIDECAR_OUT = T3 / "is_correct_t3_sidecar_confirm2.json"

# arm -> experiment dir (addendum runs).
ARM_DIRS = {
    "A3":   "conf_A3_qwen3.8-flash-payg",
    "C2Q":  "conf_C2Q_qwen3.8-flash-payg",
    "C2QY": "yoke_C2QY_confirm_qwen3.8-flash-payg",
}


def traj_path(arm: str) -> Path:
    return AGENT_ROOT / "experiments" / ARM_DIRS[arm] / M / "loop_trajectories.jsonl"


def _fresh_key(meta, tid, r, astra_cache):
    """Return the (tid, final_answer) astra key if this round needs a fresh verdict, else None."""
    fa = (r.get("final_answer") or "").strip()
    if r.get("finish_reason") == "length":
        return None
    if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
        return None
    key = (tid, fa)
    if key in astra_cache:
        return None
    return key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no live astra calls")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    idx = gen.load_confirm_index()
    astra_cache = gen.load_astra_cache()

    traj = {a: read_traj(traj_path(a)) for a in ARM_DIRS}
    for a, t in traj.items():
        if not t:
            print(f"ERROR: no trajectory for {a}", file=sys.stderr)
            return 1

    # ---- collect fresh astra keys ----
    seen = set()
    todo = []
    for arm in ("A3", "C2Q"):
        for tid in sorted(traj[arm]):
            meta = idx[tid]
            for r in traj[arm][tid]["rounds"]:
                k = _fresh_key(meta, tid, r, astra_cache)
                if k and k not in seen:
                    seen.add(k)
                    todo.append(k)
    # C2QY: only continuation rounds (index >= len(C2Q rounds)) are scored fresh;
    # the resume prefix is copied from C2Q verbatim.
    c2q = traj["C2Q"]
    for tid in sorted(traj["C2QY"]):
        meta = idx[tid]
        n_c2q = len(c2q[tid]["rounds"])
        for i, r in enumerate(traj["C2QY"][tid]["rounds"]):
            if i < n_c2q:
                continue
            k = _fresh_key(meta, tid, r, astra_cache)
            if k and k not in seen:
                seen.add(k)
                todo.append(k)

    print(f"astra: cached={sum(1 for v in astra_cache.values() if v is not None)} "
          f"todo={len(todo)} dry_run={args.dry_run}", flush=True)

    if not args.dry_run and todo:
        gen.ASTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        fh = gen.ASTRA_CACHE.open("a", encoding="utf-8")

        def process(key):
            tid, fa = key
            m = idx[tid]
            verdict, served = gen.astra_judge(m["question"], m["gold"], fa)
            return {"task_id": tid, "final_answer": fa, "c": verdict,
                    "served_model": served}

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(process, k): k for k in todo}
            for n, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                astra_cache[(rec["task_id"], rec["final_answer"])] = rec["c"]
                if n % 50 == 0 or n == len(todo):
                    print(f"  astra {n}/{len(todo)}", flush=True)
        fh.close()

    def score_round_full(meta, tid, r):
        s = gen.score_round(meta, tid, r, astra_cache, dry_run=args.dry_run)
        if s.get("c") is None:
            return s
        adj = gen.adjudicate(tid, (r.get("final_answer") or "").strip())
        if adj is not None:
            v, _reason, _conf, _ask = adj
            s = {"c": v, "s": "adjudicated", "adj": True}
        return s

    stats = Counter()
    arms_out = {}

    # A3 then C2Q: score every round.
    for arm in ("A3", "C2Q"):
        arm_rows = {}
        for tid in sorted(traj[arm]):
            meta = idx[tid]
            rows = [score_round_full(meta, tid, r) for r in traj[arm][tid]["rounds"]]
            for s in rows:
                if s.get("c") is not None:
                    stats[s["s"]] += 1
            arm_rows[tid] = rows
        arms_out[arm] = arm_rows

    # C2QY: prefix copied verbatim from C2Q; continuation scored fresh.
    c2q_rows = arms_out["C2Q"]
    arm_rows = {}
    copied = 0
    fresh = 0
    for tid in sorted(traj["C2QY"]):
        meta = idx[tid]
        rows = []
        n_c2q = len(c2q_rows[tid])
        for i, r in enumerate(traj["C2QY"][tid]["rounds"]):
            if i < n_c2q:
                rows.append(c2q_rows[tid][i])
                copied += 1
                continue
            s = score_round_full(meta, tid, r)
            rows.append(s)
            if s.get("c") is not None:
                stats[s["s"]] += 1
                fresh += 1
        arm_rows[tid] = rows
    arms_out["C2QY"] = arm_rows

    out = {
        "note": "qwen addendum confirmation sidecar (A3 + C2Q + C2QY); frozen protocol "
                "(trunc > T1 > astra K1 > K3 rules). C2QY resume-prefix rounds copied "
                f"verbatim from C2Q ({copied} copied, {fresh} fresh continuation).",
        "stats": dict(stats),
        "arms": arms_out,
    }
    if not args.dry_run:
        SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
        SIDECAR_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"\n== addendum sidecar stats ==\n  {dict(stats)}", flush=True)
        print(f"-> {SIDECAR_OUT}", flush=True)
    else:
        print(f"\n== dry-run: stats ==\n  {dict(stats)}", flush=True)
        for arm in ("A3", "C2Q", "C2QY"):
            print(f"  {arm}: {len(arms_out[arm])} tasks", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
