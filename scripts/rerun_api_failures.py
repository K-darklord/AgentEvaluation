#!/usr/bin/env python3
"""Rerun tasks that contain api_failure rounds (frozen-data repair, rule 1 + rule 3).

Rule 1: any trajectory with an api_failure round is invalid -> rerun the WHOLE task;
        A3 only resamples the failed sample rounds (or replaces the failed round-0).
Rule 3: interface failures are retried and never written (fixed in
        run_feedback_loop._solve_with_retry); error text never enters final_answer
        or the early-stop streak.

Modes:
  full            rerun the whole task via _run_task_loop (A / A2 / A2P / C2 / C3).
  resample        A3: resample only the failed i.i.d. sample rounds (1..n-1).
  replace_round0  A3: replace round 0 from the (already fixed) A arm trajectory.

Endpoint: A2/A3/C3 originally ran on the token-plan model (quota exhausted), so they
rerun on the payg model; every rerun record stores "endpoint". A2PRIME/C2 were payg.

Backup: the original trajectory file is copied to <file>.bak_apifail_<ts> before any
rewrite. Rerun records replace the bad records in-place (order preserved).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from collections import deque
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.run_feedback_loop as rfl  # noqa: E402
from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.benchmark import load_hle_questions  # noqa: E402
from src.egte_critic import Level3Critic  # noqa: E402
from src.strong_critic import StrongCritic  # noqa: E402

TIER = "C"
MAX_ROUNDS = 10
EARLY_STOP_N = 3
MAX_TOKENS = config.REASONING_BENCH_MAX_TOKENS


def build_agent(model: str, temperature: float):
    entry = config.PHASE1_MODELS[model]
    return HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=MAX_TOKENS, temperature=temperature,
        seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"))


def build_critic(model: str, arm: str, bank_model: str = ""):
    if arm == "C2":
        return StrongCritic.load(model, bank_free=True)
    if arm == "C3":
        # bank keyed by the original token-plan model name; LLM on the payg model
        weak = Level3Critic.load(bank_model or model)
        return StrongCritic(weak.entries, config.PHASE1_MODELS[model], bank_free=False)
    return None


def load_bad_tasks(traj_path: Path):
    """Return list of (task_id, [failed_round_numbers...])."""
    bad = []
    for line in traj_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        fr = [r.get("round") for r in d.get("rounds", []) if r.get("api_failure")]
        if fr:
            bad.append((d["task_id"], fr))
    return bad


def score_row(task, result, family, answer=None):
    return {
        "task_id": task.task_id, "category": task.category,
        "gold_answer": task.gold_answer,
        "final_answer": result.final_answer if answer is None else answer,
        "reasoning_content": result.reasoning_content or "",
        "finish_reason": result.finish_reason or "",
        "metadata": task.metadata, "api_failure": result.api_failure,
        "prompt": task.prompt, "trajectory": result.trajectory,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="A / A2 / A2P / C2 / C3")
    ap.add_argument("--model", required=True, help="endpoint model name")
    ap.add_argument("--traj", required=True, help="trajectory file to repair")
    ap.add_argument("--a-source", default="", help="A arm trajectory (A2/A2P/C2/C3/A3)")
    ap.add_argument("--mode", default="full", choices=["full", "resample", "replace_round0"])
    ap.add_argument("--bank-model", default="", help="bank name for C3 (original token-plan name)")
    ap.add_argument("--smoke", action="store_true", help="only 2 bad tasks per arm")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    rfl._force_no_proxy()
    traj_path = Path(args.traj)
    a_source = Path(args.a_source) if args.a_source else None

    temperature = 0.7 if args.arm == "A3" else 0.0
    max_rounds = MAX_ROUNDS
    if args.arm == "A":
        max_rounds = 0

    agent = build_agent(args.model, temperature)
    critic = build_critic(args.model, args.arm, args.bank_model)

    tasks = load_hle_questions()
    task_by_id = {t.task_id: t for t in tasks}

    # A-seeding round 0 (for A2/A2P/C2/C3/A3 arms).
    a_round0 = {}
    if a_source is not None and a_source.exists():
        a_round0 = rfl._load_a_round0_by_task(a_source)

    bad = load_bad_tasks(traj_path)
    if args.smoke:
        bad = bad[:2]
    elif args.limit:
        bad = bad[: args.limit]
    if not bad:
        print(f"[rerun] {args.arm}: nothing to do", flush=True)
        return 0

    print(f"[rerun] {args.arm} mode={args.mode} model={args.model} "
          f"bad_tasks={len(bad)}", flush=True)

    # Backup the original file once.
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = traj_path.with_name(traj_path.name + f".bak_apifail_{ts}")
    shutil.copy2(traj_path, bak)
    print(f"[rerun] backup -> {bak}", flush=True)

    # Load all records and index by task_id (keep first occurrence order).
    records = [json.loads(l) for l in traj_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rec_by_id = {r["task_id"]: r for r in records}

    err_lock = threading.Lock()
    consec_errors = [0]

    def run_full(tid):
        task = task_by_id.get(tid)
        if task is None:
            return None, f"task not found: {tid}"
        a0 = a_round0.get(tid)
        rec = rfl._run_task_loop(agent, critic, task, TIER, max_rounds,
                                 EARLY_STOP_N, args.arm, "off", None, None, a0)
        if any(r.get("api_failure") for r in rec.get("rounds", [])):
            return None, f"still has api_failure: {tid}"
        rec["endpoint"] = args.model
        return rec, None

    def run_resample(tid, failed_rounds):
        task = task_by_id.get(tid)
        if task is None:
            return None, f"task not found: {tid}"
        rec = rec_by_id[tid]
        family = rfl._task_family(tid)
        tool_cache = {}
        new_rounds = []
        for rnum in failed_rounds:
            result = rfl._solve_with_retry(agent, task, tool_cache=tool_cache)
            correct = rfl._is_correct(family, score_row(task, result, family))
            rd = rfl._round_record(rnum, result, correct, None, None, None, None, args.arm)
            new_rounds.append((rnum, rd))
        return new_rounds, None

    def run_replace_round0(tid, failed_rounds):
        a0 = a_round0.get(tid)
        if a0 is None:
            return None, f"A round0 missing: {tid}"
        return ("round0", a0), None

    # Run concurrently (rule 1 rerun); agent/critic are stateless HTTP clients and
    # are shared across worker threads. InterfaceAbortError aborts the whole batch.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _work(item):
        tid, failed_rounds = item
        try:
            if args.mode == "full":
                rec, err = run_full(tid)
            elif args.mode == "resample":
                rec, err = run_resample(tid, failed_rounds)
            else:  # replace_round0
                rec, err = run_replace_round0(tid, failed_rounds)
            return tid, rec, err, None
        except rfl.InterfaceAbortError as e:
            return tid, None, None, f"{e}"
        except Exception as e:  # noqa: BLE001
            return tid, None, f"{type(e).__name__}: {e}", None

    results = {}
    errors = {}
    abort_msg = None
    done = 0
    workers = max(1, args.workers)
    print(f"[rerun] workers={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_work, item) for item in bad]
        for fut in as_completed(futures):
            tid, rec, err, abt = fut.result()
            if abt is not None:
                abort_msg = abt
                print(f"  ABORT {tid}: {abt}", flush=True)
                for f in futures:
                    f.cancel()
                break
            if err:
                errors[tid] = err
                print(f"  ERROR {tid}: {err}", flush=True)
            else:
                results[tid] = rec
                done += 1
                print(f"  {done}/{len(bad)} {tid} done", flush=True)

    if abort_msg is not None:
        print(f"[rerun] aborted: {abort_msg}", flush=True)
        return 1

    # Apply results back to records.
    for tid, val in results.items():
        if args.mode == "full":
            rec_by_id[tid] = val
        elif args.mode == "resample":
            rec = rec_by_id[tid]
            by_round = {r["round"]: r for r in rec["rounds"]}
            for rnum, rd in val:
                by_round[rnum] = rd
            rec["rounds"] = [by_round[i] for i in range(len(rec["rounds"]))]
            rec["endpoint"] = args.model
        else:  # replace_round0
            rec = rec_by_id[tid]
            tag, a0 = val
            a0 = dict(a0)
            a0["round"] = 0
            a0["arm"] = args.arm
            rec["rounds"][0] = a0
            rec["endpoint"] = args.model

    # Write back (preserve original order).
    out_lines = []
    for r in records:
        out_lines.append(json.dumps(rec_by_id.get(r["task_id"], r), ensure_ascii=False))
    traj_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    # Verify no api_failure remains.
    remaining = [t for t, fr in load_bad_tasks(traj_path)]
    print(f"[rerun] {args.arm}: done={done} errors={len(errors)} "
          f"remaining_api_failure={len(remaining)}", flush=True)
    if errors:
        print(f"[rerun] {args.arm} errors: {errors}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
