#!/usr/bin/env python3
"""Equal-token samples (E2) frozen scoring -> is_correct_t3_sidecar_confirm3.json (qwen)
and is_correct_t3_sidecar_confirm_ds2.json (deepseek).

docs/EQUAL_TOKEN_SAMPLES_SPEC.md sec 2 / sec 5.5. Frozen per-round protocol, identical to
scripts/gen_t3_sidecar_confirm.py (trunc > T1 > astra K1 > K3 rules; the K3 rules are keyed
hle_001..400 and do not fire on hle_401..1200).

Two sections per model:
  A3Y : per-round verdicts aligned with the A3Y trajectory's rounds list (index 0 = the
        T=0 anchor; 1..9 = the nine i.i.d. samples copied VERBATIM from the existing A3
        sidecar; >=10 = the continuation samples scored fresh).
  USC : one item per question {c, s, selected_round, parse_ok}, where c/s are the verdict
        of the sample selected by USC (selected_round is the sample round number, which
        equals its positional index in the trajectory rounds list).

astra K1 verdicts reuse the shared astra_verdicts_confirm.jsonl cache (a verdict for a
given question+answer is model-independent).

Run:  python3 scripts/gen_t3_sidecar_confirm3.py --model qwen [--dry-run]
      python3 scripts/gen_t3_sidecar_confirm3.py --model deepseek [--dry-run]
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

_spec = importlib.util.spec_from_file_location(
    "gen_confirm", str(AGENT_ROOT / "scripts/gen_t3_sidecar_confirm.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

import src.hle_scorer as hs  # noqa: E402
from src.score_hle_arms import read_traj  # noqa: E402

T3 = AGENT_ROOT / "experiments/hle400/t3"

MODELS = {
    "qwen": {
        "M": "qwen3.8-flash-payg",
        "a3_sidecar": "is_correct_t3_sidecar_confirm2.json",
        "out": "is_correct_t3_sidecar_confirm3.json",
        "usc": "usc_confirm_qwen.jsonl",
    },
    "deepseek": {
        "M": "deepseek-v4-flash-payg",
        "a3_sidecar": "is_correct_t3_sidecar_confirm_ds.json",
        "out": "is_correct_t3_sidecar_confirm_ds2.json",
        "usc": "usc_confirm_deepseek.jsonl",
    },
}


def a3y_traj_path(m):
    return AGENT_ROOT / "experiments" / f"conf_A3Y_{m}" / m / "loop_trajectories.jsonl"


def conf_a3_traj_path(m):
    return AGENT_ROOT / "experiments" / f"conf_A3_{m}" / m / "loop_trajectories.jsonl"


def load_usc(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out[d["task_id"]] = d
    return out


def _fresh_key(meta, tid, r, astra_cache):
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
    ap.add_argument("--model", required=True, choices=["qwen", "deepseek"])
    ap.add_argument("--dry-run", action="store_true", help="no live astra calls")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cfg = MODELS[args.model]
    M = cfg["M"]
    SIDECAR_OUT = T3 / cfg["out"]

    idx = gen.load_confirm_index()
    astra_cache = gen.load_astra_cache()

    traj = read_traj(a3y_traj_path(M))
    if not traj:
        print(f"ERROR: no A3Y trajectory for {M}", file=sys.stderr)
        return 1
    a3 = read_traj(conf_a3_traj_path(M))
    if not a3:
        print(f"ERROR: no conf_A3 trajectory for {M}", file=sys.stderr)
        return 1

    a3_sidecar = json.load(open(T3 / cfg["a3_sidecar"], encoding="utf-8"))["arms"]["A3"]
    usc = load_usc(T3 / cfg["usc"])

    # ---- safety: A3Y first 10 rounds verbatim vs conf_A3, and round==position invariant ----
    for tid in sorted(traj):
        r3 = a3[tid]["rounds"]
        ry = traj[tid]["rounds"]
        assert len(r3) == 10, (tid, len(r3))
        assert len(a3_sidecar[tid]) == 10, (tid, len(a3_sidecar[tid]))
        for i in range(10):
            assert r3[i].get("final_answer") == ry[i].get("final_answer"), (tid, i)
            assert r3[i].get("finish_reason") == ry[i].get("finish_reason"), (tid, i)
        for i, r in enumerate(ry):
            assert r.get("round") == i, (tid, i, r.get("round"))

    # ---- collect fresh astra keys (continuation samples only) ----
    seen = set()
    todo = []
    for tid in sorted(traj):
        meta = idx[tid]
        for i, r in enumerate(traj[tid]["rounds"]):
            if i < 10:
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
    a3y_out = {}
    for tid in sorted(traj):
        meta = idx[tid]
        rows = []
        for i, r in enumerate(traj[tid]["rounds"]):
            if i < 10:
                rows.append(a3_sidecar[tid][i])
            else:
                s = score_round_full(meta, tid, r)
                rows.append(s)
                if s.get("c") is not None:
                    stats[s["s"]] += 1
        a3y_out[tid] = rows

    usc_out = {}
    for tid in sorted(a3y_out):
        rec = usc[tid]
        sr = rec.get("selected_round")
        if sr is None or sr >= len(a3y_out[tid]):
            usc_out[tid] = {"c": None, "s": None,
                            "selected_round": sr, "parse_ok": rec.get("parse_ok")}
        else:
            s = a3y_out[tid][sr]
            usc_out[tid] = {"c": s.get("c"), "s": s.get("s"),
                            "selected_round": sr, "parse_ok": rec.get("parse_ok")}

    out = {
        "note": f"Equal-token samples (E2) sidecar for {M}; frozen protocol "
                "(trunc > T1 > astra K1 > K3 rules). A3Y rounds 0..9 copied verbatim "
                "from the existing A3 sidecar; USC one item per question.",
        "stats": dict(stats),
        "arms": {"A3Y": a3y_out, "USC": usc_out},
    }
    if not args.dry_run:
        SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
        SIDECAR_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"\n== {args.model} equal-token samples sidecar stats ==\n  {dict(stats)}", flush=True)
        print(f"-> {SIDECAR_OUT}", flush=True)
    else:
        print(f"\n== dry-run: stats ==\n  {dict(stats)}", flush=True)
        print(f"  A3Y tasks={len(a3y_out)} USC tasks={len(usc_out)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
