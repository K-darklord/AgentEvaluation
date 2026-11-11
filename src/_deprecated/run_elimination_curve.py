"""run_elimination_curve.py — semantic-trajectory self-evaluator: full one-by-one ranking.

For each non-mode question, iteratively eliminate the single most implausible
candidate (semantic: reconstructed reasoning chain + transition sequence, NO
question text) until one remains. This yields the full elimination ORDER, from
which we draw the survival curve of the correct answer as candidates are removed
one by one (vs. a simulated random-elimination baseline).

Reuses v1 narration (no re-generation) and v1's treatment prompt structure for
comparability. Evaluator thinking DISABLED (structured judgment -> clean token).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

import os
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"; os.environ["no_proxy"] = "*"

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.run_self_evaluator import (load_nonmode_subset, _answers_block,  # noqa: E402
                                    _transition_block, _clip, parse_index)

TRAJ = ROOT / "experiments/experiments/a3_new_20261010_t0.7/deepseek-v4-flash/loop_trajectories.jsonl"
V1_RECORDS = ROOT / "experiments/self_evaluator_20261011/records.jsonl"
MODEL_KEY = "deepseek-v4-flash"
EVALUATOR_MAX_TOKENS = 512


def _answers_block_subset(cands: list[dict], total: int) -> str:
    return "\n".join(f"[{c['label']}] {_clip(c['raw'])}   (appeared {c['count']}/{total} times)" for c in cands)


def iterative_eval_prompt(t: dict, narration: str, remaining: list[dict]) -> str:
    return (
        "You are a meta-cognitive evaluator. A solver model produced distinct answers "
        "across repeated attempts and switched between them. Below are the REMAINING "
        "candidates (some already eliminated), the full transition sequence, and a "
        "reconstructed reasoning chain for every answer.\n\n"
        "Your ONLY job: identify the SINGLE most implausible answer among the REMAINING "
        "candidates and ELIMINATE it. Evaluate the internal consistency / plausibility of "
        "each answer's reasoning state. Do NOT re-solve and do NOT say which is 'correct'.\n\n"
        f"REMAINING ANSWERS:\n{_answers_block_subset(remaining, t['total'])}\n\n"
        f"FULL TRANSITION SEQUENCE (round order):\n{_transition_block(t)}\n\n"
        f"RECONSTRUCTED REASONING CHAINS:\n{narration.strip()}\n\n"
        "Respond with ONLY the index number (e.g. \"2\") of the answer you eliminate. Nothing else."
    )


def call_text(agent, prompt):
    return agent._call_llm_text([{"role": "user", "content": prompt}], max_tokens=EVALUATOR_MAX_TOKENS)[0]


def run_ranking(agent, t, narration):
    remaining = [dict(c) for c in t["cands"]]
    n_orig = len(remaining)
    steps = []
    aborted = False
    while len(remaining) > 1:
        try:
            out = call_text(agent, iterative_eval_prompt(t, narration, remaining))
            lab = parse_index(out, n_orig)
        except Exception as e:
            lab = None; out = f"API FAILURE: {e}"
        still = [c for c in remaining if c["label"] == lab]
        if lab is None or not still:
            aborted = True
            break
        victim = still[0]
        remaining = [c for c in remaining if c["label"] != lab]
        steps.append({
            "step": len(steps), "eliminated_label": lab,
            "eliminated_correct": bool(victim["is_correct"]),
            "still_has_correct": any(c["is_correct"] for c in remaining),
            "n_remaining": len(remaining),
            "parse": out.strip()[:60],
        })
    return {"task_id": t["task_id"], "family": t["family"], "n_orig": n_orig,
            "steps": steps, "aborted": aborted,
            "final_label": remaining[0]["label"] if remaining else None,
            "final_correct": bool(remaining[0]["is_correct"]) if remaining else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--out", type=str, default=str(ROOT / "experiments/elimination_curve_20261011"))
    args = ap.parse_args()

    subset = load_nonmode_subset(TRAJ)
    v1 = {r["task_id"]: r for r in (json.loads(l) for l in open(V1_RECORDS, encoding="utf-8"))}
    if args.n:
        subset = subset[: args.n]

    entry = config.PHASE1_MODELS[MODEL_KEY]
    agent = HuggingFaceAgent(model=entry["model"], token=entry["api_key"],
                             base_url=entry["base_url"], max_tokens=EVALUATOR_MAX_TOKENS,
                             temperature=0.0, seed=None, enable_thinking=False)

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(subset, 1):
        rec = run_ranking(agent, t, v1[t["task_id"]]["narration"])
        if rec["steps"]:
            last = rec["steps"][-1]
            print(f"[{i}/{len(subset)}] {t['task_id']:<10} n={rec['n_orig']} "
                  f"eliminations={len(rec['steps'])} first_correct_killed_at="
                  f"{next((s['step'] for s in rec['steps'] if s['eliminated_correct']), 'never')} "
                  f"final_correct={rec['final_correct']} aborted={rec['aborted']}", flush=True)
        else:
            print(f"[{i}/{len(subset)}] {t['task_id']:<10} ABORTED no steps", flush=True)
        with open(out_dir / "records.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("DONE")


if __name__ == "__main__":
    main()
