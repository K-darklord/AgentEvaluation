#!/usr/bin/env python3
"""C2 bank-free critic arm — K1 astra per-round sidecar generator.

Reproduces the exact K1 methodology that built
``experiments/hle400/t3/is_correct_t3_sidecar.json`` (arms A/A2/A3/C3), applied to
the pre-registered C2 arm (bank-free critic). Per-round verdict:

    finish_reason == "length"        -> {"c": false, "s": "trunc"}   (top priority)
    else T1 deterministic match      -> {"c": true,  "s": "t1"}
    else astra (gpt-6-astra) K=1     -> {"c": bool,  "s": "astra_true"/"astra_false"}

T1 uses ``hle_scorer.score_t1`` (deterministic, token-free); the astra judge re-reads
only the committed final_answer (never CoT), one verdict per unique
(task_id, final_answer). This K1 drift-free pipeline replaces the non-deterministic
deepseek-v4-pro T2 rescue with astra (docs/HLE_SCORER.md §1.1/§1.2) — no T2 judge.

Inputs:
    data/raw/hle/hle_400_new.jsonl
    experiments/hle400_C2/deepseek-v4-flash-payg/loop_trajectories.jsonl   (valid, NOT INVALID_429)
Outputs:
    experiments/hle400_C2/t3/astra_verdicts.jsonl           (resumable K1 astra cache)
    experiments/hle400/t3/is_correct_t3_sidecar_C2.json     (C2 arm + stats)

Resumable + flush-per-row. astra calls record served_model to catch gateway downgrade.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.score_hle_arms  # noqa: E402,F401  (_load_dotenv + _force_no_proxy)
import src.hle_scorer as hs  # noqa: E402
from src import config  # noqa: E402
import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

from src.score_hle_arms import load_index, read_traj  # noqa: E402

INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
C2_TRAJ = AGENT_ROOT / "experiments/hle400_C2/deepseek-v4-flash-payg/loop_trajectories.jsonl"
ASTRA_CACHE = AGENT_ROOT / "experiments/hle400_C2/t3/astra_verdicts.jsonl"
SIDECAR_OUT = AGENT_ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_C2.json"

_client = None
_client_lock = threading.Lock()


def get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(
                    base_url=config.ASTRA_BASE_URL,
                    api_key=config.ASTRA_API_KEY,
                    timeout=httpx.Timeout(150.0, connect=15.0),
                )
    return _client


def astra_once(question, gold, response):
    client = get_client()
    prompt = hs.JUDGE_PROMPT.format(question=question, response=response[:4000], gold=gold)
    r = client.chat.completions.create(
        model=config.ASTRA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )
    txt = r.choices[0].message.content or ""
    return txt, getattr(r, "model", None)


def astra_judge(question, gold, response):
    """Verdict with up to 3 retries on empty/ambiguous/error. Returns (bool|None, served_model)."""
    last_served = None
    for _ in range(3):
        try:
            txt, served = astra_once(question, gold, response)
            up = txt.strip().upper()
            if up.startswith("CORRECT"):
                return True, served
            if up.startswith("INCORRECT"):
                return False, served
            last_served = served
        except Exception as e:  # noqa: BLE001
            last_served = f"ERR:{type(e).__name__}"
    return None, last_served


def classify(idx, traj):
    """Deterministic pass: trunc + T1 filled; T1-missed rows return a None placeholder.

    Returns (rows_map, todo) where rows_map[tid] is a list of verdict dicts (or None
    placeholder for astra-needed rounds) and todo is the ordered unique set of
    (task_id, final_answer) keys that need an astra verdict.
    """
    rows_map, todo = {}, {}
    for tid in sorted(traj):
        meta = idx[tid]
        rows = []
        for r in traj[tid]["rounds"]:
            fa = r.get("final_answer", "")
            if r.get("finish_reason") == "length":
                rows.append({"c": False, "s": "trunc"})
            elif hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
                rows.append({"c": True, "s": "t1"})
            else:
                rows.append(None)
                todo[(tid, fa)] = None
        rows_map[tid] = rows
    return rows_map, todo


def load_cache():
    """Re-read astra cache; last verdict per key wins (handles re-judge append duplication)."""
    cache = {}
    if ASTRA_CACHE.exists():
        for line in ASTRA_CACHE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cache[(d["task_id"], d["final_answer"])] = d.get("verdict")
    return cache


def judge_todo(idx, todo, workers, limit=0):
    """Judge every unique (task_id, final_answer) needing astra; resumable; returns full cache."""
    cache = load_cache()
    to_judge = [(tid, fa) for (tid, fa) in todo if cache.get((tid, fa)) is None]
    if limit and limit > 0:
        to_judge = to_judge[:limit]
    print(f"astra: cached={sum(1 for v in cache.values() if v is not None)} "
          f"todo={len(todo)} to_judge={len(to_judge)}", flush=True)

    if to_judge:
        ASTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        fh = ASTRA_CACHE.open("a", encoding="utf-8")

        def process(key):
            tid, fa = key
            m = idx[tid]
            verdict, served = astra_judge(m["question"], m["gold"], fa)
            return {"task_id": tid, "final_answer": fa,
                    "verdict": verdict, "served_model": served}

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process, k): k for k in to_judge}
            for i, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    if i % 50 == 0 or i == len(to_judge):
                        print(f"  astra {i}/{len(to_judge)}", flush=True)
                cache[(rec["task_id"], rec["final_answer"])] = rec["verdict"]
        fh.close()

    return cache


def assemble(idx, traj, rows_map, cache):
    """Rebuild the full C2 sidecar arm from the astra cache (None -> conservative wrong)."""
    arms = {}
    stats = Counter()
    unresolved = 0
    for tid in sorted(traj):
        meta = idx[tid]
        rounds = traj[tid]["rounds"]
        out_rows = []
        for i, r in enumerate(rounds):
            placeholder = rows_map[tid][i]
            if placeholder is not None and placeholder.get("s") in ("trunc", "t1"):
                v = placeholder
            else:
                fa = r.get("final_answer", "")
                if r.get("finish_reason") == "length":
                    v = {"c": False, "s": "trunc"}
                elif hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
                    v = {"c": True, "s": "t1"}
                else:
                    verdict = cache.get((tid, fa))
                    if verdict is None:
                        unresolved += 1
                        verdict = False
                    v = {"c": bool(verdict), "s": "astra_true" if verdict else "astra_false"}
            out_rows.append(v)
            stats[v["s"]] += 1
        arms[tid] = out_rows

    total = sum(stats.values())
    out = {
        "arm": "C2",
        "note": "K1 astra sidecar for C2 (bank-free critic); same methodology as A/A2/A3/C3 "
                "(scripts/c2_k1_sidecar.py). Per-round: trunc > T1 > astra.",
        "stats": {"t1": stats["t1"], "astra_true": stats["astra_true"],
                  "astra_false": stats["astra_false"], "trunc": stats["trunc"],
                  "total": total},
        "arms": {"C2": arms},
    }
    SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIDECAR_OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n== C2 K1 sidecar stats ==\n  {dict(stats)}  total={total}", flush=True)
    if unresolved:
        print(f"  WARNING: {unresolved} unresolved astra verdicts mapped to false "
              f"(re-run to resolve)", flush=True)
    print(f"\n-> {SIDECAR_OUT}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true",
                    help="classify only (trunc+T1), report counts, no astra calls")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the number of astra calls (0 = unlimited; smoke test)")
    args = ap.parse_args()

    if not config.ASTRA_API_KEY:
        print("ERROR: ASTRA_API_KEY is empty", file=sys.stderr)
        return 1

    idx = load_index(INDEX)
    traj = read_traj(C2_TRAJ)
    if len(traj) != 400:
        print(f"WARNING: C2 traj has {len(traj)} tasks (expected 400)", flush=True)

    rows_map, todo = classify(idx, traj)
    prelim = Counter()
    for tid in rows_map:
        for v in rows_map[tid]:
            if v is not None and v["s"] == "trunc":
                prelim["trunc"] += 1
            elif v is not None and v["s"] == "t1":
                prelim["t1"] += 1
            else:
                prelim["astra"] += 1
    print(f"C2 tasks={len(traj)} rounds={sum(len(rows_map[t]) for t in rows_map)}", flush=True)
    print(f"classify: {dict(prelim)}  unique_astra_todo={len(todo)}", flush=True)

    if args.dry_run:
        return 0

    cache = judge_todo(idx, todo, args.workers, limit=args.limit)
    assemble(idx, traj, rows_map, cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())