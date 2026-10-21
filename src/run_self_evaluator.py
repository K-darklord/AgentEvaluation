"""run_self_evaluator.py — Stage B self-evaluator elimination experiment.

Goal
----
Test whether re-invoking the SAME model as an independent "self-evaluator" can
eliminate a wrong answer on the non-mode questions (questions where the A3
isotropic temperature sampling did NOT converge to a clear attractor).

Protocol (per non-mode question, 3 calls):
  1. narration   -- sees the QUESTION; reconstructs a reasoning chain for each
                    distinct answer that appeared (fill the missing CoT).
  2. evaluator-T -- independent call, NO question text; input = distinct answers
                    + their transition log + the narration reasoning chains;
                    output = the single most implausible answer to ELIMINATE.
  3. evaluator-bare -- independent call, NO question text; input = distinct
                    answers + frequency only (no reasoning, no transition);
                    output = the single answer to eliminate. (baseline ablation)

Metric
------
  elimination precision = P(eliminated candidate is wrong)   [cuts-wrong rate]
  joined by a per-question random-select baseline (#wrong / #cands), and the
  mode-of-survivors accuracy change (locking upside).

The evaluator is a STATE evaluator, not an ANSWER evaluator: it never re-solves
and never sees the question, so it cannot be dragged into re-deriving the answer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# ---- env (standard loader; strip proxies that wedge the API) ----
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402

TRAJ = ROOT / "experiments/experiments/a3_new_20261010_t0.7/deepseek-v4-flash/loop_trajectories.jsonl"
MODEL_KEY = "deepseek-v4-flash"
NARRATION_MAX_TOKENS = 4096
EVALUATOR_MAX_TOKENS = 2048
MAX_ANSWER_CHARS = 200


def _norm_ans(s: str) -> str:
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")


def _clip(s: str, n: int = MAX_ANSWER_CHARS) -> str:
    s = str(s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# load the A3 trajectory, identify the non-mode subset, build per-question
# candidate lists + transition logs.
# --------------------------------------------------------------------------- #
def load_nonmode_subset(traj_path: Path) -> list[dict]:
    tasks = []
    for line in open(traj_path, encoding="utf-8"):
        rec = json.loads(line)
        cands = []
        norm_to_i = {}
        first_seen = {}
        transitions = []
        for r in rec["rounds"]:
            raw = r.get("final_answer")
            norm = _norm_ans(raw)
            if norm in norm_to_i:
                cands[norm_to_i[norm]]["count"] += 1
                idx = norm_to_i[norm]
            else:
                norm_to_i[norm] = len(cands)
                idx = len(cands)
                cands.append({"norm": norm, "raw": raw, "count": 1,
                              "is_correct": bool(r["is_correct"])})
                first_seen[norm] = len(cands) - 1
            transitions.append(idx)
        # stable label order: descending count, tiebreak by first appearance
        order = sorted(range(len(cands)),
                       key=lambda i: (-cands[i]["count"], first_seen[cands[i]["norm"]]))
        relabel = {old: new + 1 for new, old in enumerate(order)}  # 1-based labels
        cands_sorted = [cands[i] for i in order]
        for c, lab in zip(cands_sorted, range(1, len(cands_sorted) + 1)):
            c["label"] = lab
        transitions_labeled = [relabel[i] for i in transitions]
        total = len(rec["rounds"])
        mode = max(cands_sorted, key=lambda c: (c["count"], -c["label"]))
        tasks.append({
            "task_id": rec["task_id"], "family": rec["family"],
            "gold": rec.get("gold_answer"), "prompt": rec["prompt"],
            "cands": cands_sorted, "transitions": transitions_labeled,
            "mode": mode, "total": total,
        })

    vote_wrong = {t["task_id"] for t in tasks if not t["mode"]["is_correct"]}
    flat = {t["task_id"] for t in tasks if t["mode"]["count"] / t["total"] < 0.5}
    subset = [t for t in tasks if t["task_id"] in (vote_wrong | flat) and len(t["cands"]) >= 2]
    return subset


# --------------------------------------------------------------------------- #
# prompts
# --------------------------------------------------------------------------- #
def _answers_block(t: dict) -> str:
    lines = []
    for c in t["cands"]:
        lines.append(f"[{c['label']}] {_clip(c['raw'])}   (appeared {c['count']}/{t['total']} times)")
    return "\n".join(lines)


def _transition_block(t: dict) -> str:
    return " -> ".join(f"[{lab}]" for lab in t["transitions"])


def narration_prompt(t: dict) -> str:
    return (
        "Below is a problem and the sequence of answers a solver model produced "
        "across repeated independent attempts. The solver oscillated and never "
        "settled on one answer.\n\n"
        "Your task is to RECONSTRUCT, for each distinct answer that appeared, the "
        "most plausible reasoning chain that would lead a solver to that answer, and "
        "the uncertainty or error mechanism that could produce it.\n\n"
        "Do NOT re-solve the problem. Do NOT state which answer is correct. Only "
        "reconstruct each answer's internal reasoning state.\n\n"
        f"PROBLEM:\n{t['prompt']}\n\n"
        f"DISTINCT ANSWERS:\n{_answers_block(t)}\n\n"
        f"ANSWER TRANSITION SEQUENCE (round order):\n{_transition_block(t)}\n\n"
        "For each distinct answer [1], [2], ... output:\n"
        "  ANSWER [k]: <the answer>\n"
        "  Reasoning chain: <step-by-step reasoning that leads to this answer>\n"
        "  Error/uncertainty mechanism: <why a solver might produce this and be unsure>\n"
    )


def evaluator_treatment_prompt(t: dict, narration: str) -> str:
    return (
        "You are a meta-cognitive evaluator. You are shown distinct answers a solver "
        "model produced across repeated attempts, the sequence in which it switched "
        "between them, and a reconstructed reasoning chain for each answer.\n\n"
        "Your ONLY job is to identify the SINGLE most implausible answer and "
        "ELIMINATE it. Evaluate the internal consistency / plausibility of each "
        "answer's reasoning state. Do NOT re-solve anything and do NOT say which "
        "answer is 'correct'.\n\n"
        f"DISTINCT ANSWERS:\n{_answers_block(t)}\n\n"
        f"TRANSITION SEQUENCE (round order):\n{_transition_block(t)}\n\n"
        f"RECONSTRUCTED REASONING CHAINS:\n{narration.strip()}\n\n"
        "Respond with ONLY the index number (e.g. \"2\") of the answer you would "
        "eliminate. Nothing else."
    )


def evaluator_bare_prompt(t: dict) -> str:
    return (
        "You are a meta-cognitive evaluator. You are shown distinct answers a solver "
        "model produced across repeated attempts, with how often each appeared.\n\n"
        "Your ONLY job is to identify the SINGLE most implausible answer and "
        "ELIMINATE it, using only the answers themselves and their frequencies.\n\n"
        f"DISTINCT ANSWERS:\n{_answers_block(t)}\n\n"
        "Respond with ONLY the index number (e.g. \"2\") of the answer you would "
        "eliminate. Nothing else."
    )


def parse_index(text: str, n: int):
    """Return the elimination label (1..n): the LAST integer in range (reasoning
    models emit the decision last)."""
    nums = [int(x) for x in re.findall(r"\d+", text or "")]
    for x in reversed(nums):
        if 1 <= x <= n:
            return x
    return None


def call_text(agent: HuggingFaceAgent, prompt: str, max_tokens: int):
    messages = [{"role": "user", "content": prompt}]
    out, _reasoning, _resp = agent._call_llm_text(messages, max_tokens=max_tokens)
    return out


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
def run_one(agent: HuggingFaceAgent, t: dict) -> dict:
    rec = {
        "task_id": t["task_id"], "family": t["family"],
        "n_cands": len(t["cands"]),
        "mode_label": t["mode"]["label"], "mode_correct": t["mode"]["is_correct"],
        "mode_frac": round(t["mode"]["count"] / t["total"], 3),
    }
    wrong_idx = [c["label"] for c in t["cands"] if not c["is_correct"]]
    rec["random_baseline"] = len(wrong_idx) / len(t["cands"])

    # 1. narration (sees question)
    try:
        rec["narration"] = call_text(agent, narration_prompt(t), NARRATION_MAX_TOKENS)
        rec["narration_api_failure"] = False
    except Exception as e:
        rec["narration"] = f"API FAILURE: {e}"
        rec["narration_api_failure"] = True

    # 2+3. evaluator treatment (+ reasoning) and bare (freq only)
    for arm in ("treatment", "bare"):
        try:
            prompt = (evaluator_treatment_prompt(t, rec["narration"])
                      if arm == "treatment" else evaluator_bare_prompt(t))
            out = call_text(agent, prompt, EVALUATOR_MAX_TOKENS)
            lab = parse_index(out, len(t["cands"]))
            rec[f"elim_{arm}_raw"] = out.strip()[:500]
            rec[f"elim_{arm}_label"] = lab
            rec[f"elim_{arm}_api_failure"] = False
            if lab is not None:
                victim = next(c for c in t["cands"] if c["label"] == lab)
                rec[f"elim_{arm}_victim_wrong"] = (not victim["is_correct"])
                survivors = [c for c in t["cands"] if c["label"] != lab]
                new_mode = max(survivors, key=lambda c: (c["count"], -c["label"]))
                rec[f"elim_{arm}_mode_after_correct"] = new_mode["is_correct"]
            else:
                rec[f"elim_{arm}_victim_wrong"] = None
                rec[f"elim_{arm}_mode_after_correct"] = None
        except Exception as e:
            rec[f"elim_{arm}_raw"] = f"API FAILURE: {e}"
            rec[f"elim_{arm}_label"] = None
            rec[f"elim_{arm}_api_failure"] = True
            rec[f"elim_{arm}_victim_wrong"] = None
            rec[f"elim_{arm}_mode_after_correct"] = None

    return rec


def summarize(records: list[dict]) -> dict:
    def score(arm: str):
        valid = [r for r in records if r[f"elim_{arm}_label"] is not None]
        n = len(valid)
        if n == 0:
            return {"n": 0, "precision": None, "baseline": None, "rescue": 0}
        prec = sum(r[f"elim_{arm}_victim_wrong"] for r in valid) / n
        base = sum(r["random_baseline"] for r in valid) / n
        rescue = sum(1 for r in valid
                     if (not r["mode_correct"]) and r[f"elim_{arm}_mode_after_correct"])
        return {"n": n, "precision": prec, "baseline": base, "rescue": rescue}

    out = {
        "n_questions": len(records),
        "n_parse_fail_treatment": sum(1 for r in records if r["elim_treatment_label"] is None),
        "n_parse_fail_bare": sum(1 for r in records if r["elim_bare_label"] is None),
        "treatment": score("treatment"),
        "bare": score("bare"),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="limit to first N questions (0 = all)")
    ap.add_argument("--out", type=str, default=str(ROOT / "experiments/self_evaluator_20261011"))
    args = ap.parse_args()

    subset = load_nonmode_subset(TRAJ)
    print(f"[load] non-mode subset size = {len(subset)}")
    if args.n:
        subset = subset[: args.n]
        print(f"[run] limited to first {args.n} questions")

    entry = config.PHASE1_MODELS[MODEL_KEY]
    agent = HuggingFaceAgent(model=entry["model"], token=entry["api_key"],
                             base_url=entry["base_url"], max_tokens=NARRATION_MAX_TOKENS,
                             temperature=0.0, seed=None)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for i, t in enumerate(subset, 1):
        t0 = time.time()
        rec = run_one(agent, t)
        rec["latency_s"] = round(time.time() - t0, 1)
        records.append(rec)
        te = rec["elim_treatment_victim_wrong"]
        be = rec["elim_bare_victim_wrong"]
        print(f"[{i}/{len(subset)}] {t['task_id']:<10} cands={rec['n_cands']} "
              f"mode_frac={rec['mode_frac']} treat_victim_wrong={te} bare_victim_wrong={be} "
              f"({rec['latency_s']}s)", flush=True)
        with open(out_dir / "records.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = summarize(records)
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n================ SUMMARY ================")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for arm in ("treatment", "bare"):
        s = summary[arm]
        if s["n"]:
            delta = s["precision"] - s["baseline"]
            print(f"\n[{arm}] n={s['n']}  elimination-precision={s['precision']:.3f}  "
                  f"random-baseline={s['baseline']:.3f}  Δ={delta:+.3f}  "
                  f"rescued_wrong_mode={s['rescue']}")
    print("\nDONE")


if __name__ == "__main__":
    main()
