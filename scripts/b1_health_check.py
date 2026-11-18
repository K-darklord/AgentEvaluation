#!/usr/bin/env python3
"""B1 BBEH health check (docs/SECOND_BENCHMARK_SPEC.md, run-health only, no correctness).

Two modes:
  a : five loop arms (A/A2/A2P/C2/A3) on the hard first-16 questions, before full run.
  b : A2PY (token-yoked) on the hard first-16 questions, before full A2PY.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
M = "qwen3.8-flash-payg"
GROUP = "hard"


def traj(arm: str) -> dict:
    f = AGENT_ROOT / f"experiments/b1_{arm}_{GROUP}_{M}" / M / "loop_trajectories.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out[d["task_id"]] = d
    return out


def round_tokens(r: dict, kind: str) -> int:
    if kind == "solver":
        return (r.get("prompt_tokens", 0) + r.get("completion_tokens", 0)
                + r.get("reasoning_tokens", 0))
    return (r.get("critic_prompt_tokens", 0) + r.get("critic_completion_tokens", 0)
            + r.get("critic_reasoning_tokens", 0))


def health_a():
    arms = ["A", "A2", "A2P", "C2", "A3"]
    print(f"== B1 health check (a): hard first-16, arms {arms} ==\n")
    for arm in arms:
        t = traj(arm)
        n_q = len(t)
        api_fail_rounds = 0
        api_fail_q = 0
        trunc_rounds = 0
        total_rounds = 0
        n_rounds = []
        solver_tok = []
        critic_tok = []
        critic_fb = 0
        for tid, d in t.items():
            q_fail = False
            for r in d["rounds"]:
                total_rounds += 1
                if r.get("api_failure"):
                    api_fail_rounds += 1
                    q_fail = True
                if r.get("finish_reason") == "length":
                    trunc_rounds += 1
                if r.get("critic_fallback"):
                    critic_fb += 1
                solver_tok.append(round_tokens(r, "solver"))
                critic_tok.append(round_tokens(r, "critic"))
            if q_fail:
                api_fail_q += 1
            n_rounds.append(d.get("n_rounds", len(d["rounds"])))
        tr = trunc_rounds / total_rounds if total_rounds else 0.0
        print(f"[{arm}] questions={n_q}/16  rounds={total_rounds}  "
              f"api_fail_q={api_fail_q} api_fail_rounds={api_fail_rounds}")
        print(f"      trunc_rate={tr:.3f} ({trunc_rounds}/{total_rounds})  "
              f"critic_fallback_rounds={critic_fb}")
        print(f"      rounds/q: min={min(n_rounds) if n_rounds else 0} "
              f"med={sorted(n_rounds)[len(n_rounds)//2] if n_rounds else 0} "
              f"max={max(n_rounds) if n_rounds else 0}")
        if solver_tok:
            ss = sorted(solver_tok)
            print(f"      solver_tok/round: min={ss[0]} med={ss[len(ss)//2]} "
                  f"max={ss[-1]}  sum={sum(ss)}")
        if any(critic_tok):
            cs = sorted(critic_tok)
            print(f"      critic_tok/round: min={cs[0]} med={cs[len(cs)//2]} "
                  f"max={cs[-1]}  sum={sum(cs)}")
        print()
    return 0


def health_b():
    budget_file = AGENT_ROOT / "experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    t = traj("A2PY")
    print(f"== B1 health check (b): A2PY hard first-16, questions={len(t)} ==\n")
    budgets = {}
    if budget_file.exists():
        budgets = json.loads(budget_file.read_text(encoding="utf-8"))
    ceiling = 0
    for tid, d in t.items():
        cum = sum(round_tokens(r, "solver") for r in d["rounds"])
        b = budgets.get(tid)
        if b is not None:
            ratio = cum / b if b else float("inf")
            if ratio >= 1.0:
                ceiling += 1
            print(f"  {tid}: rounds={d.get('n_rounds', len(d['rounds']))} "
                  f"cum_tok={cum} budget={b} ratio={ratio:.2f}")
        else:
            print(f"  {tid}: rounds={d.get('n_rounds', len(d['rounds']))} cum_tok={cum} budget=MISSING")
    print(f"\n  ceiling-hit questions: {ceiling}/{len(t)}")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "a"
    if mode == "a":
        sys.exit(health_a())
    elif mode == "b":
        sys.exit(health_b())
    else:
        print("unknown mode", file=sys.stderr)
        sys.exit(2)
