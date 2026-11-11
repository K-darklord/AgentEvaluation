#!/usr/bin/env python3
"""S1: A3 arm — generate rounds 10 and 11 (revised per spec section 6).

Section 6 fixes:
  2. api_failure samples do NOT count as done — they are resampled. Quota exhaustion
     switches the endpoint to deepseek-v4-flash-payg.
  3. Every round record + the task record store the endpoint actually used.

Settings unchanged from the original A3 arm: temperature 0.7, thinking_budget 16384 +
REASONING_CONTENT_MARGIN 8192 => max_tokens 24576, deepseek-v4-flash-0731 weights.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
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

EXTRA_ROUNDS = (10, 11)
ENDPOINT_TOKEN_PLAN = "deepseek-v4-flash"
ENDPOINT_PAYG = "deepseek-v4-flash-payg"
_QUOTA_KEYWORDS = ("insufficient", "quota", "额度", "余额", "欠费", "depleted", "exhausted")

_lock = threading.Lock()
_model = ENDPOINT_TOKEN_PLAN
_agent = None


def build_agent(model_name: str):
    entry = config.PHASE1_MODELS[model_name]
    return HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=config.REASONING_BENCH_MAX_TOKENS,
        temperature=0.7, seed=None,
        enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"))


def get_agent():
    global _agent
    with _lock:
        if _agent is None:
            _agent = build_agent(_model)
        return _agent


def switch_to_payg():
    global _agent, _model
    with _lock:
        if _model != ENDPOINT_PAYG:
            _model = ENDPOINT_PAYG
            _agent = build_agent(ENDPOINT_PAYG)
            print("[S1] quota -> switched endpoint to deepseek-v4-flash-payg", flush=True)


def endpoint_of(agent):
    return (ENDPOINT_PAYG
            if getattr(agent, "base_url", "") == config.DASHSCOPE_BASE_URL
            else ENDPOINT_TOKEN_PLAN)


def _is_quota_str(s):
    return any(k in (s or "").lower() for k in _QUOTA_KEYWORDS)


def solve_two(task):
    family = rfl._task_family(task.task_id)
    tool_cache = {}

    def score(result, answer=None):
        row = {
            "task_id": task.task_id, "category": task.category,
            "gold_answer": task.gold_answer,
            "final_answer": result.final_answer if answer is None else answer,
            "reasoning_content": result.reasoning_content or "",
            "finish_reason": result.finish_reason or "",
            "metadata": task.metadata, "api_failure": result.api_failure,
            "prompt": task.prompt, "trajectory": result.trajectory,
        }
        return rfl._is_correct(family, row)

    records = []
    for r in EXTRA_ROUNDS:
        agent = get_agent()
        result = agent.solve(task, feedback=None, tool_cache=tool_cache)
        rec = rfl._round_record(r, result, score(result),
                                None, None, None, None, "A3")
        rec["endpoint"] = endpoint_of(agent)
        records.append(rec)

    corrects = [rec["is_correct"] for rec in records]
    return {
        "task_id": task.task_id, "arm": "A3", "family": family,
        "gold_answer": task.gold_answer, "prompt": task.prompt,
        "rounds": records, "n_rounds": len(records),
        "start_correct": corrects[0], "final_correct": corrects[-1],
        "correct_appeared": any(corrects), "end_state": rfl._end_state(corrects),
        "endpoint": records[-1]["endpoint"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=ENDPOINT_TOKEN_PLAN)
    ap.add_argument("--smoke", action="store_true", help="first 10 tasks only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=config.RUNNER_CONCURRENCY)
    ap.add_argument("--task-offset", type=int, default=0)
    args = ap.parse_args()

    global _model
    with _lock:
        _model = args.model

    rfl._force_no_proxy()
    tasks = load_hle_questions()
    if args.task_offset:
        tasks = tasks[args.task_offset:]
    if args.smoke:
        tasks = tasks[:10]
    elif args.limit:
        tasks = tasks[:args.limit]

    out_dir = AGENT_ROOT / "experiments" / "hle400_A3_extra" / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    traj_path = out_dir / "loop_trajectories.jsonl"

    done_ids = rfl._load_completed(traj_path)
    pending = deque([t for t in tasks if t.task_id not in done_ids])
    total = len(pending)
    print(f"[S1] model={args.model} tasks={len(tasks)} done={len(done_ids)} "
          f"pending={total} rounds={EXTRA_ROUNDS}", flush=True)
    if not pending:
        print("[S1] nothing to do", flush=True)
        return 0

    solve_timeout = float(os.getenv("AGENTEVALUATION_SOLVE_TIMEOUT", "900"))
    ex = rfl._DaemonThreadPoolExecutor(max_workers=args.workers)
    in_flight = {}
    deadline = {}
    done = 0
    api_fail = 0

    def submit_one():
        if not pending:
            return
        task = pending.popleft()
        fut = ex.submit(solve_two, task)
        in_flight[fut] = task
        deadline[fut] = time.monotonic() + solve_timeout * (len(EXTRA_ROUNDS) + 1)

    for _ in range(args.workers):
        submit_one()

    try:
        while in_flight:
            now = time.monotonic()
            for fut in [f for f, d in deadline.items() if d <= now]:
                t = in_flight.pop(fut)
                deadline.pop(fut, None)
                fut.cancel()
                print(f"  TIMEOUT {t.task_id} (re-queued)", flush=True)
                pending.append(t)
                submit_one()
            if not in_flight:
                break
            wait_for = max(min(deadline.values()) - now, 0.0)
            finished, _ = concurrent.futures.wait(
                in_flight, timeout=wait_for,
                return_when=concurrent.futures.FIRST_COMPLETED)
            for fut in finished:
                if fut not in in_flight:
                    continue
                deadline.pop(fut, None)
                t = in_flight.pop(fut)
                try:
                    rec = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  ERROR {t.task_id}: {e} (re-queued)", flush=True)
                    pending.append(t)
                    submit_one()
                    continue
                failed = [r for r in rec["rounds"] if r.get("api_failure")]
                if failed:
                    if any(_is_quota_str(r.get("final_answer")) for r in failed):
                        switch_to_payg()
                    api_fail += len(failed)
                    print(f"  RESAMPLE {t.task_id} (api_failure={len(failed)}, "
                          f"re-queued)", flush=True)
                    pending.append(t)
                    submit_one()
                    continue
                rfl._append_record(traj_path, rec)
                done += 1
                print(f"  {done}/{total} tasks done (api_fail={api_fail})", flush=True)
                submit_one()
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    print(f"[S1] complete: {done} tasks written -> {traj_path}", flush=True)
    print(f"[S1] api_failure samples resampled: {api_fail}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
