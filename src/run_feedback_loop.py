"""
run_feedback_loop.py
====================
Phase 1 (probe): the bounded feedback--self-correction loop.

This drives the L3/L4 observation experiment. For each (model, task) we run a
baseline solve (round 0, no feedback), then up to R feedback rounds. In every
feedback round the weak critic inspects the previous answer (gold-free: question
similarity + answer similarity vs. the wrong bank) and returns a Top-K error
direction + an estimated error probability; the agent then re-solves the SAME
question independently (fresh context, shared tool cache), but the previous
answer and the critic feedback are injected as an extra user message.

Design decisions (2026-10-06):
  - independent re-solve (not multi-turn continuation): matches the existing
    stateless ``HuggingFaceAgent.solve`` and does not alter the agent's natural
    single-question behaviour. Tool results are cached ACROSS rounds so a finance
    task does not re-fetch the same document every round.
  - temperature = 0 (deterministic), seed = None (temp=0 => seed is a no-op).
  - scoring is a ZERO-LLM deterministic pass (T1 rules only): enough to drive
    early stopping and the six end-states. It is NOT the same as the baseline's
    full T1+T2 score (finance T1+rubric only), so the round-0 accuracy here is a
    lower-bound proxy, not a re-statement of the baseline accuracy.
  - early stopping: stop once the final answer is unchanged for N consecutive
    rounds (N=3), to keep finance questions from over-oscillating.
  - six end-states (see RESEARCH_PLAN §5.10) classify each task's trajectory.

Reproducibility: fully deterministic given (model, task, critic); no randomness.
One command:
  python3 src/run_feedback_loop.py --models deepseek-v4-flash --num-tasks 5
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_phase1_tasks
from src.build_weak_critic import (  # noqa: E402
    TOP_K, WeakCritic, _family_base_rates, _task_family,
)
from src.evaluator import (  # noqa: E402
    _rubric_coverage_normalized, _score_bfcl, _score_math500, _score_mmlu_pro,
    _score_t1_numeric, _score_t2_llm_semantic,
)

# ---- loop hyperparameters (reproducibility) ----
MAX_ROUNDS = 10        # feedback rounds (round 0 = baseline, rounds 1..R = feedback)
EARLY_STOP_N = 3       # stop once answer unchanged for N consecutive rounds
TIER = "C"             # critic feedback tier (C = type + prob + cause + attention)


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _load_bank() -> list[dict]:
    bank_path = REPO_ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
    with open(bank_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _is_correct(family: str | None, row: dict) -> bool:
    """Zero-LLM deterministic correctness (T1 rules only). family from task_id prefix."""
    if row.get("api_failure"):
        return False
    if not family:
        return False
    thresh = config.FINAL_PASS_THRESHOLD
    try:
        if family == "math":
            return _score_t1_numeric(row) >= thresh
        if family == "math500":
            return _score_math500(row) >= thresh
        if family == "mmlu_pro":
            return _score_mmlu_pro(row) >= thresh
        if family == "bfcl":
            return _score_bfcl(row) >= thresh
        if family == "finance":
            # quantitative (T1 numeric) or rubric-covered -> zero-LLM pass
            if _score_t1_numeric(row) >= thresh or _rubric_coverage_normalized(row):
                return True
            # qualitative answer T1 cannot settle -> T2 LLM judge rescue (registered
            # intervention). All answers are still recorded, so a bad judge call can be
            # re-scored offline afterwards.
            t2, dealbreaker = _score_t2_llm_semantic(row)
            return (not dealbreaker) and (t2 >= thresh)
    except Exception:
        return False
    return False


def _norm_ans(s) -> str:
    """Light answer normalization for early-stop comparison (case/whitespace only)."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _feedback_message(prev_answer: str, critic_text: str) -> str:
    """Self-contained re-solve prompt: previous answer + critic feedback + revision
    instruction. The agent decides itself whether to revise (no forced output format)."""
    return (
        "A reviewer looked at your PREVIOUS answer to this question and gave feedback.\n"
        f"Your previous answer was:\n\"\"\"\n{prev_answer}\n\"\"\"\n\n"
        f"Reviewer feedback:\n{critic_text}\n\n"
        "Reconsider the question and provide your final answer again. "
        "If you believe your previous answer was already correct, keep it as is."
    )


def _round_record(r: int, result, correct: bool, evidence, error, no_signal,
                  top3) -> dict:
    return {
        "round": r,
        "final_answer": result.final_answer,
        "is_correct": correct,
        "evidence": round(evidence, 4) if evidence is not None else None,
        "error_score": round(error, 4) if error is not None else None,
        "no_signal": no_signal,
        "top3": [{"leaf": l, "prob": round(p, 4)} for l, p in (top3 or [])],
        "tool_calls": result.tool_calls,
        "latency_ms": result.total_latency_ms,
        "api_failure": result.api_failure,
        "prompt_tokens": result.total_prompt_tokens,
        "completion_tokens": result.total_completion_tokens,
    }


def _end_state(corrects: list[bool]) -> int:
    """Six end-states (RESEARCH_PLAN §5.10) from the per-round correctness vector."""
    start, final = corrects[0], corrects[-1]
    if start and final:
        return 1 if all(corrects) else 3   # 1: L4 full; 3: L4 weak but recoverable
    if start and not final:
        return 2                            # 2: L4 deficit (misled into an error)
    if not start and final:
        return 4                            # 4: L3 + L4 full (activated then locked)
    return 5 if any(corrects[1:]) else 6    # 5: L3 present / L4 deficit; 6: L3 absent


def _run_task_loop(agent, critic, task, tier, max_rounds, early_stop_n) -> dict:
    family = _task_family(task.task_id)
    tool_cache: dict = {}
    records: list[dict] = []

    def score(result) -> bool:
        row = {
            "task_id": task.task_id, "category": task.category,
            "gold_answer": task.gold_answer, "final_answer": result.final_answer,
            "metadata": task.metadata, "api_failure": result.api_failure,
            "prompt": task.prompt, "trajectory": result.trajectory,
        }
        return _is_correct(family, row)

    # round 0: baseline (no feedback)
    result = agent.solve(task, feedback=None, tool_cache=tool_cache)
    prev_answer = result.final_answer
    records.append(_round_record(0, result, score(result), None, None, None, None))

    streak = 1
    for r in range(1, max_rounds + 1):
        if family is None:
            break  # critic has no leaves for this family -> cannot give feedback
        pred, evidence, error = critic._predict(
            family, task.prompt, prev_answer,
            exclude_task_ids={task.task_id}, k=TOP_K)
        no_signal = (pred == [])
        fb_text = critic.build_prompt(pred, tier, error_score=error)
        result = agent.solve(task, feedback=_feedback_message(prev_answer, fb_text),
                             tool_cache=tool_cache)
        correct = score(result)
        new_answer = result.final_answer
        streak = streak + 1 if _norm_ans(new_answer) == _norm_ans(prev_answer) else 1
        prev_answer = new_answer
        records.append(_round_record(r, result, correct, evidence, error, no_signal, pred))
        if streak >= early_stop_n:
            break

    corrects = [rec["is_correct"] for rec in records]
    return {
        "task_id": task.task_id,
        "family": family,
        "gold_answer": task.gold_answer,
        "prompt": task.prompt,
        "rounds": records,
        "n_rounds": len(records),
        "start_correct": corrects[0],
        "final_correct": corrects[-1],
        "correct_appeared": any(corrects),
        "end_state": _end_state(corrects),
    }


def run_feedback_loop(models=None, num_tasks=0, max_rounds=MAX_ROUNDS,
                      early_stop_n=EARLY_STOP_N, tier=TIER, concurrency=None) -> dict:
    _force_no_proxy()
    tasks = load_phase1_tasks()
    if num_tasks:
        tasks = tasks[:num_tasks]
    if concurrency is None:
        concurrency = config.RUNNER_CONCURRENCY

    critic = WeakCritic(_load_bank(), base_rates=_family_base_rates())

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = REPO_ROOT / "experiments" / f"feedback_loop_{run_id}"
    out_root.mkdir(parents=True, exist_ok=True)

    names = models or [m for m in config.PHASE1_MODELS if config.PHASE1_MODELS[m].get("api_key")]
    summary = {
        "run_id": run_id, "max_rounds": max_rounds, "early_stop_n": early_stop_n,
        "tier": tier, "temperature": 0.0, "seed": None, "n_tasks": len(tasks),
        "concurrency": concurrency, "models": {},
    }

    for name in names:
        entry = config.PHASE1_MODELS[name]
        agent = HuggingFaceAgent(
            model=entry["model"], token=entry.get("api_key"),
            base_url=entry["base_url"], max_tokens=1024, temperature=0.0,
            seed=None, enable_thinking=entry.get("enable_thinking"))
        model_dir = out_root / name
        model_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== feedback loop [{name}] model={entry['model']} "
              f"tasks={len(tasks)} R={max_rounds} N={early_stop_n} tier={tier} ===")

        per_task = [None] * len(tasks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(_run_task_loop, agent, critic, task, tier,
                              max_rounds, early_stop_n): i
                    for i, task in enumerate(tasks)}
            done = 0
            for fut in concurrent.futures.as_completed(futs):
                per_task[futs[fut]] = fut.result()
                done += 1
                print(f"  [{name}] {done}/{len(tasks)} tasks done", flush=True)

        # write loop trajectories (one JSON line per task)
        traj_path = model_dir / "loop_trajectories.jsonl"
        with traj_path.open("w", encoding="utf-8") as f:
            for t in per_task:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")

        # aggregate
        n = len(per_task)
        init_correct = sum(1 for t in per_task if t["start_correct"])
        final_correct = sum(1 for t in per_task if t["final_correct"])
        states = Counter(t["end_state"] for t in per_task)
        wrong_start = [t for t in per_task if not t["start_correct"] and t["family"]]
        right_start = [t for t in per_task if t["start_correct"]]
        activation = (sum(1 for t in wrong_start
                          if any(r["is_correct"] for r in t["rounds"][1:]))
                      / len(wrong_start)) if wrong_start else 0.0
        locked = (sum(1 for t in right_start if t["end_state"] == 1)
                  / len(right_start)) if right_start else 0.0
        misled = (sum(1 for t in right_start if t["end_state"] == 2)
                  / len(right_start)) if right_start else 0.0
        avg_rounds = sum(t["n_rounds"] for t in per_task) / n if n else 0.0

        m = {
            "model_id": entry["model"],
            "init_accuracy": round(init_correct / n, 4) if n else 0.0,
            "final_accuracy": round(final_correct / n, 4) if n else 0.0,
            "end_state_distribution": {str(k): v for k, v in sorted(states.items())},
            "l3_activation_rate": round(activation, 4),
            "l4_lock_rate": round(locked, 4),
            "l4_misled_rate": round(misled, 4),
            "avg_rounds": round(avg_rounds, 2),
            "total_prompt_tokens": sum(r["prompt_tokens"] for t in per_task for r in t["rounds"]),
            "total_completion_tokens": sum(r["completion_tokens"] for t in per_task for r in t["rounds"]),
        }
        summary["models"][name] = m
        (out_root / "loop_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [{name}] init={m['init_accuracy']:.2%} final={m['final_accuracy']:.2%} "
              f"states={m['end_state_distribution']} L3_act={m['l3_activation_rate']:.2%} "
              f"L4_lock={m['l4_lock_rate']:.2%} L4_misled={m['l4_misled_rate']:.2%} "
              f"avg_rounds={m['avg_rounds']} "
              f"tok={m['total_prompt_tokens']}+{m['total_completion_tokens']}")

    (out_root / "loop_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== feedback loop summary -> {out_root / 'loop_summary.json'} ===")
    return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Phase-1 feedback loop (L3/L4 probe)")
    ap.add_argument("--models", default="",
                    help="comma-separated model names (default: all with api_key)")
    ap.add_argument("--num-tasks", type=int, default=0, help="limit tasks (0 = all 250)")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--early-stop", type=int, default=EARLY_STOP_N)
    ap.add_argument("--tier", default=TIER, choices=["A", "B", "C"])
    ap.add_argument("--concurrency", type=int, default=0, help="0 = config default")
    a = ap.parse_args()

    run_feedback_loop(
        models=[m for m in a.models.split(",") if m] or None,
        num_tasks=a.num_tasks,
        max_rounds=a.max_rounds,
        early_stop_n=a.early_stop,
        tier=a.tier,
        concurrency=(a.concurrency or None),
    )
