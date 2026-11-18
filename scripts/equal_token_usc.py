#!/usr/bin/env python3
"""Equal-token USC selection for A3Y (docs/EQUAL_TOKEN_SAMPLES_SPEC.md sec 1-2).

Reuses scripts/s2_usc.py's USC_PROMPT, parse_selection, plain_vote, ordered_for,
build_prompt and build_agent verbatim (the prompt, parse and failure rules are NOT
changed). Reads the A3Y trajectory (all sample rounds, EXCLUDING the round-0 T=0
anchor), hands every sample answer to the SAME model that generated them, and records
the selected round. Interface errors are NOT written as records: retry, then 5
consecutive interface errors abort the run.

Output: experiments/hle400/t3/usc_confirm_{qwen,deepseek}.jsonl
  {task_id, arm, n_responses, order, selected_round, raw_output, parse_ok,
   prompt_tokens, completion_tokens, reasoning_tokens, endpoint}
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import threading
import time
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))
sys.path.insert(0, str(AGENT_ROOT / "scripts"))

import src.score_hle_arms as sha  # noqa: E402
from src import config  # noqa: E402
from src.run_feedback_loop import _DaemonThreadPoolExecutor, _force_no_proxy  # noqa: E402
from s2_usc import (USC_PROMPT, parse_selection, plain_vote, ordered_for,  # noqa: E402
                    build_prompt, build_agent)

ENDPOINTS = {
    "qwen": "qwen3.8-flash-payg",
    "deepseek": "deepseek-v4-flash-payg",
}


class AbortError(Exception):
    pass


def _max_tokens(endpoint: str) -> int:
    return (config.PHASE1_MODELS[endpoint].get("thinking_budget", 0)
            + config.REASONING_CONTENT_MARGIN)


def _call_once(agent, prompt):
    """Single interface call with retry/abort (mirrors s2_usc._call_once, fixed endpoint)."""
    consec = 0
    while True:
        try:
            content, _reasoning, res = agent._call_llm_text(
                [{"role": "user", "content": prompt}])
            return content, res
        except Exception as e:  # noqa: BLE001
            consec += 1
            if consec >= 5:
                raise AbortError(f"5 consecutive interface errors, last: {e}")
            time.sleep(1.0)


def _parse_response(content, res, K, max_tok):
    u = getattr(res, "usage", None)
    pt = getattr(u, "prompt_tokens", 0) or 0
    ct = getattr(u, "completion_tokens", 0) or 0
    rt = getattr(u, "reasoning_tokens", 0) or 0
    fr = getattr(res, "finish_reason", None)
    truncated = (fr == "length") or (ct >= max_tok)
    if truncated:
        return None, pt, ct, rt
    x = parse_selection(content)
    if x is not None and 1 <= x <= K:
        return x - 1, pt, ct, rt
    return None, pt, ct, rt


def run_one(agent, tid, arm, question, ordered_rounds, rounds, meta, endpoint, max_tok):
    K = len(ordered_rounds)
    prompt = build_prompt(question, ordered_rounds, rounds)
    last = ("", 0, 0, 0)
    for _attempt in range(2):
        content, res = _call_once(agent, prompt)
        idx, pt, ct, rt = _parse_response(content, res, K, max_tok)
        last = (content, pt, ct, rt)
        if idx is not None:
            return {"task_id": tid, "arm": arm, "n_responses": len(ordered_rounds),
                    "order": ordered_rounds, "selected_round": ordered_rounds[idx],
                    "raw_output": content, "parse_ok": True,
                    "prompt_tokens": pt, "completion_tokens": ct,
                    "reasoning_tokens": rt, "endpoint": endpoint}
    content, pt, ct, rt = last
    selected = plain_vote(tid, ordered_rounds, rounds, meta)
    return {"task_id": tid, "arm": arm, "n_responses": len(ordered_rounds),
            "order": ordered_rounds, "selected_round": selected,
            "raw_output": content, "parse_ok": False,
            "prompt_tokens": pt, "completion_tokens": ct,
            "reasoning_tokens": rt, "endpoint": endpoint}


def load_a3y_rounds(traj_path: Path) -> dict:
    """Return {task_id: {sample_round_index: round_record}} (round 0 anchor excluded)."""
    out = {}
    if not traj_path.exists():
        return out
    for line in traj_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        rounds = d.get("rounds", [])
        out[d["task_id"]] = {r["round"]: r for r in rounds if (r.get("round") or 0) >= 1}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["qwen", "deepseek"])
    ap.add_argument("--tasks", default=None, help="comma-separated task ids (health gate)")
    ap.add_argument("--workers", type=int, default=120)
    a = ap.parse_args()

    _force_no_proxy()
    endpoint = ENDPOINTS[a.model]
    agent = build_agent(endpoint)
    max_tok = _max_tokens(endpoint)

    # out-dir is conf_A3Y_<endpoint> (endpoint == model name == output subdir),
    # see scripts/run_a3y_confirm.sh: OUT="conf_A3Y_$M".
    traj_path = (AGENT_ROOT / "experiments" / f"conf_A3Y_{endpoint}"
                 / endpoint / "loop_trajectories.jsonl")

    idx = {}
    # meta (gold) comes straight from the trajectory record; question from "prompt".
    rounds_by_task = load_a3y_rounds(traj_path)
    meta_by_task = {}
    question_by_task = {}
    for line in traj_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        meta_by_task[d["task_id"]] = {"gold": d.get("gold_answer", "")}
        question_by_task[d["task_id"]] = d.get("prompt", "")

    OUT = AGENT_ROOT / "experiments" / "hle400" / "t3" / f"usc_confirm_{a.model}.jsonl"
    OUT.parent.mkdir(parents=True, exist_ok=True)

    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["task_id"])
            except Exception:
                continue

    wanted = None
    if a.tasks:
        wanted = set(x.strip() for x in a.tasks.split(",") if x.strip())

    jobs = []
    for tid in sorted(rounds_by_task):
        if tid in done:
            continue
        if wanted is not None and tid not in wanted:
            continue
        jobs.append(tid)

    print(f"[A3Y-USC] model={a.model} endpoint={endpoint} jobs={len(jobs)}", flush=True)
    if not jobs:
        print("[A3Y-USC] nothing to do", flush=True)
        return 0

    write_lock = threading.Lock()
    fh = OUT.open("a", encoding="utf-8")
    done_n = 0
    parse_fail = 0

    def process(tid):
        ordered = ordered_for(tid, rounds_by_task[tid])
        return run_one(agent, tid, "A3Y", question_by_task[tid], ordered,
                       rounds_by_task[tid], meta_by_task[tid], endpoint, max_tok)

    ex = _DaemonThreadPoolExecutor(max_workers=a.workers)
    try:
        futs = {ex.submit(process, t): t for t in jobs}
        for fut in concurrent.futures.as_completed(futs):
            tid = futs[fut]
            try:
                rec = fut.result()
            except AbortError as e:
                print(f"[A3Y-USC] ABORT: {e}", flush=True)
                ex.shutdown(wait=False, cancel_futures=True)
                fh.close()
                return 1
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR {tid}: {e}", flush=True)
                continue
            with write_lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            done_n += 1
            if not rec["parse_ok"]:
                parse_fail += 1
            if done_n % 50 == 0 or done_n == len(jobs):
                print(f"  {done_n}/{len(jobs)} done parse_fail={parse_fail}", flush=True)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
        fh.close()

    print(f"[A3Y-USC] complete: {done_n} rows -> {OUT}", flush=True)
    print(f"[A3Y-USC] parse_fail={parse_fail}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
