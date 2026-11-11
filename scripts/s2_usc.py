#!/usr/bin/env python3
"""S2: Universal Self-Consistency (USC) selection — revised per spec section 6.

Section 6 fixes applied here:
  1. parse_selection accepts ONLY the full sentence "most consistent response is
     Response N", takes the LAST occurrence, drops the loose "Response N" fallback.
     A truncated visible output (finish_reason=="length" or completion_tokens at the
     cap) is a parse failure.
  2. Interface errors are NOT written as records: retry; 5 consecutive interface
     errors abort the run. (S1 handles api_failure resampling separately.)
  3. Endpoint: token-plan vs payg are the same weights; on quota exhaustion switch to
     deepseek-v4-flash-payg and keep going. Every record stores its endpoint name.

Output: experiments/hle400/t3/usc_result.jsonl
  {task_id, arm, n_responses, order, selected_round, raw_output, parse_ok,
   prompt_tokens, completion_tokens, reasoning_tokens, endpoint}
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import re
import sys
import threading
import time
import zlib
from collections import Counter
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.score_hle_arms as sha  # noqa: E402
from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.score_hle_arms import load_index, read_traj, _key  # noqa: E402

INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
OUT = AGENT_ROOT / "experiments/hle400/t3/usc_result.jsonl"

ENDPOINT_TOKEN_PLAN = "deepseek-v4-flash"
ENDPOINT_PAYG = "deepseek-v4-flash-payg"

ARMS = {
    "A3-9":  {"dir": "hle400_A3", "sub": "deepseek-v4-flash", "slice": (1, 10)},
    "A3-11": {"dir": "hle400_A3", "sub": "deepseek-v4-flash", "slice": (1, 10),
              "extra_dir": "hle400_A3_extra", "extra_sub": "deepseek-v4-flash",
              "extra_rounds": (10, 11)},
    "C2":    {"dir": "hle400_C2", "sub": "deepseek-v4-flash-payg", "slice": None},
    "C3":    {"dir": "hle400_C3", "sub": "deepseek-v4-flash", "slice": None},
    "A2":    {"dir": "hle400_A2", "sub": "deepseek-v4-flash", "slice": None},
    "A2P":   {"dir": "hle400_A2PRIME", "sub": "deepseek-v4-flash-payg", "slice": None},
}

USC_PROMPT = (
    "I have generated the following responses to the question: {question}\n\n"
    "{responses}\n\n"
    "Evaluate these responses. Select the most consistent response based on majority consensus.\n"
    'Start your answer with "The most consistent response is Response X" (without quotes).'
)

# USC max_tokens = thinking_budget(16384) + REASONING_CONTENT_MARGIN(8192) = 24576.
MAX_TOKENS = (config.PHASE1_MODELS[ENDPOINT_TOKEN_PLAN]["thinking_budget"]
              + config.REASONING_CONTENT_MARGIN)

_QUOTA_KEYWORDS = ("insufficient", "quota", "额度", "余额", "欠费", "depleted", "exhausted")

_lock = threading.Lock()
_endpoint = ENDPOINT_TOKEN_PLAN
_agent = None
_consec_errors = 0


class AbortError(Exception):
    pass


def current_endpoint():
    with _lock:
        return _endpoint


def build_agent(endpoint):
    entry = config.PHASE1_MODELS[endpoint]
    return HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=config.REASONING_BENCH_MAX_TOKENS,
        temperature=0.0, seed=None,
        enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"))


def get_agent():
    global _agent
    with _lock:
        if _agent is None:
            _agent = build_agent(_endpoint)
        return _agent


def switch_to_payg():
    global _agent, _endpoint
    with _lock:
        if _endpoint != ENDPOINT_PAYG:
            _endpoint = ENDPOINT_PAYG
            _agent = build_agent(ENDPOINT_PAYG)
            print("[S2-USC] quota -> switched endpoint to deepseek-v4-flash-payg",
                  flush=True)


def _is_quota(e):
    return any(k in str(e).lower() for k in _QUOTA_KEYWORDS)


def _call_once(prompt):
    """Single interface call with retry/switch/abort. Returns (content, res)."""
    global _consec_errors
    while True:
        try:
            agent = get_agent()
            content, _reasoning, res = agent._call_llm_text(
                [{"role": "user", "content": prompt}])
            with _lock:
                _consec_errors = 0
            return content, res
        except AbortError:
            raise
        except Exception as e:  # noqa: BLE001
            if _is_quota(e) and current_endpoint() == ENDPOINT_TOKEN_PLAN:
                switch_to_payg()
                continue
            with _lock:
                _consec_errors += 1
                n = _consec_errors
            if n >= 5:
                raise AbortError(f"5 consecutive interface errors, last: {e}")
            time.sleep(1.0)
            continue


def _parse_response(content, res, K):
    """Return (idx_or_None, prompt_tokens, completion_tokens, reasoning_tokens)."""
    u = getattr(res, "usage", None)
    pt = getattr(u, "prompt_tokens", 0) or 0
    ct = getattr(u, "completion_tokens", 0) or 0
    rt = getattr(u, "reasoning_tokens", 0) or 0
    fr = getattr(res, "finish_reason", None)
    truncated = (fr == "length") or (ct >= MAX_TOKENS)
    if truncated:
        return None, pt, ct, rt
    x = parse_selection(content)
    if x is not None and 1 <= x <= K:
        return x - 1, pt, ct, rt
    return None, pt, ct, rt


def _ok_record(tid, arm, ordered_rounds, content, idx, pt, ct, rt):
    return {"task_id": tid, "arm": arm, "n_responses": len(ordered_rounds),
            "order": ordered_rounds, "selected_round": ordered_rounds[idx],
            "raw_output": content, "parse_ok": True,
            "prompt_tokens": pt, "completion_tokens": ct,
            "reasoning_tokens": rt, "endpoint": current_endpoint()}


def _fallback_record(tid, arm, ordered_rounds, rounds, meta, content, pt, ct, rt):
    selected = plain_vote(tid, ordered_rounds, rounds, meta)
    return {"task_id": tid, "arm": arm, "n_responses": len(ordered_rounds),
            "order": ordered_rounds, "selected_round": selected,
            "raw_output": content, "parse_ok": False,
            "prompt_tokens": pt, "completion_tokens": ct,
            "reasoning_tokens": rt, "endpoint": current_endpoint()}


def run_one(tid, arm, question, ordered_rounds, rounds, meta):
    """USC selection: initial call + 1 retry on parse failure, else fallback vote."""
    K = len(ordered_rounds)
    prompt = build_prompt(question, ordered_rounds, rounds)
    last = ("", 0, 0, 0)
    for _attempt in range(2):
        content, res = _call_once(prompt)
        idx, pt, ct, rt = _parse_response(content, res, K)
        last = (content, pt, ct, rt)
        if idx is not None:
            return _ok_record(tid, arm, ordered_rounds, content, idx, pt, ct, rt)
    content, pt, ct, rt = last
    return _fallback_record(tid, arm, ordered_rounds, rounds, meta, content, pt, ct, rt)


def retry_once(tid, arm, question, ordered_rounds, rounds, meta):
    """Single retry (spec 6.1: retry once for flipped records), else fallback vote."""
    K = len(ordered_rounds)
    prompt = build_prompt(question, ordered_rounds, rounds)
    content, res = _call_once(prompt)
    idx, pt, ct, rt = _parse_response(content, res, K)
    if idx is not None:
        return _ok_record(tid, arm, ordered_rounds, content, idx, pt, ct, rt)
    return _fallback_record(tid, arm, ordered_rounds, rounds, meta, content, pt, ct, rt)


def load_rounds(arm_cfg):
    traj = read_traj(AGENT_ROOT / "experiments" / arm_cfg["dir"] / arm_cfg["sub"]
                     / "loop_trajectories.jsonl")
    out = {}
    for tid, task in traj.items():
        rounds = task["rounds"]
        sl = arm_cfg["slice"]
        idxs = list(range(len(rounds)))[sl[0]:sl[1]] if sl else list(range(len(rounds)))
        out[tid] = {i: rounds[i] for i in idxs}
    if arm_cfg.get("extra_rounds"):
        extra = read_traj(AGENT_ROOT / "experiments" / arm_cfg["extra_dir"]
                          / arm_cfg["extra_sub"] / "loop_trajectories.jsonl")
        lo, hi = arm_cfg["extra_rounds"]
        for tid, task in extra.items():
            out.setdefault(tid, {})
            for r in task["rounds"]:
                if lo <= r["round"] <= hi:
                    out[tid][r["round"]] = r
    return out


def build_prompt(question, ordered_rounds, rounds):
    resp_lines = []
    for pos, i in enumerate(ordered_rounds, 1):
        fa = (rounds[i].get("final_answer") or "").strip()
        resp_lines.append(f"Response {pos}: {fa}")
    return USC_PROMPT.format(question=question, responses="\n".join(resp_lines))


def parse_selection(text):
    """Full sentence only, LAST occurrence. No loose fallback (spec section 6.1)."""
    if not text:
        return None
    matches = list(re.finditer(
        r"most\s+consistent\s+response\s+is\s+Response\s+(\d+)", text, re.I))
    if not matches:
        return None
    return int(matches[-1].group(1))


def plain_vote(tid, ordered_rounds, rounds, meta):
    votes = Counter()
    for i in ordered_rounds:
        k = _key(meta, rounds[i])
        if k is not None:
            votes[k] += 1
    if not votes:
        return None
    winner = votes.most_common(1)[0][0]
    for i in ordered_rounds:
        if _key(meta, rounds[i]) == winner:
            return i
    return ordered_rounds[0] if ordered_rounds else None


def ordered_for(tid, rounds):
    ordered = [i for i in sorted(rounds)
               if rounds[i].get("finish_reason") != "length"
               and (rounds[i].get("final_answer") or "").strip()]
    rng = random.Random(zlib.crc32(tid.encode("utf-8")))
    ordered_shuffled = list(ordered)
    rng.shuffle(ordered_shuffled)
    return ordered_shuffled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default=None, help="comma-separated arms (default all)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=config.RUNNER_CONCURRENCY)
    ap.add_argument("--task-offset", type=int, default=0)
    args = ap.parse_args()

    sha._force_no_proxy() if hasattr(sha, "_force_no_proxy") else None
    import src.run_feedback_loop as rfl
    rfl._force_no_proxy()

    idx = load_index(INDEX)
    if args.arm:
        names = [n.strip() for n in args.arm.split(",") if n.strip()]
        arms = {n: ARMS[n] for n in names}
    else:
        arms = ARMS

    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                done.add((d["task_id"], d["arm"]))
            except Exception:
                continue

    write_lock = threading.Lock()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fh = OUT.open("a", encoding="utf-8")

    jobs = []
    for arm, cfg in arms.items():
        rounds_by_task = load_rounds(cfg)
        for tid in sorted(rounds_by_task):
            if (tid, arm) in done:
                continue
            jobs.append((tid, arm, rounds_by_task[tid]))
    if args.smoke:
        jobs = jobs[:10]
    if args.limit and not args.smoke:
        jobs = jobs[: args.limit]

    print(f"[S2-USC] arms={list(arms)} jobs={len(jobs)}", flush=True)
    if not jobs:
        print("[S2-USC] nothing to do", flush=True)
        return 0

    done_n = 0
    parse_fail = Counter()

    def process(job):
        tid, arm, rounds = job
        ordered_shuffled = ordered_for(tid, rounds)
        return run_one(tid, arm, idx[tid]["question"], ordered_shuffled, rounds, idx[tid])

    ex = rfl._DaemonThreadPoolExecutor(max_workers=args.workers)
    try:
        futs = {ex.submit(process, j): j for j in jobs}
        for fut in concurrent.futures.as_completed(futs):
            try:
                rec = fut.result()
            except AbortError as e:
                print(f"[S2-USC] ABORT: {e}", flush=True)
                ex.shutdown(wait=False, cancel_futures=True)
                fh.close()
                return 1
            except Exception as e:  # noqa: BLE001
                tid, arm = futs[fut][0], futs[fut][1]
                print(f"  ERROR {tid} {arm}: {e}", flush=True)
                continue
            with write_lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            done_n += 1
            if not rec["parse_ok"]:
                parse_fail[rec["arm"]] += 1
            if done_n % 50 == 0 or done_n == len(jobs):
                print(f"  {done_n}/{len(jobs)} done parse_fail={dict(parse_fail)}",
                      flush=True)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
        fh.close()

    print(f"[S2-USC] complete: {done_n} rows -> {OUT}", flush=True)
    print(f"[S2-USC] parse_fail by arm: {dict(parse_fail)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
