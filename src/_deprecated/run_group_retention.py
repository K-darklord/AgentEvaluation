"""run_group_retention.py — Stage B v2: sqrt(n)-group iterative elimination.

Reuses the v1 narration (reasoning chains already reconstructed per candidate),
so NO narration re-generation cost. For each non-mode question, for each k in
{2, ceil(sqrt(n))}, we run an iterative elimination tournament:

  while more than 1 candidate remains:
      partition survivors into k groups (strided interleave by frequency rank,
      so each group mixes high/low-frequency answers and the rare-correct answer
      is not concentrated into one doomed group);
      self-evaluator (NO question, state eval, WITH reasoning chain) removes the
      single group LEAST likely to contain the correct answer;
      recurse on survivors.

Metrics
-------
  round-1 retention   = P(correct answer survives the first cut)  vs (k-1)/k
  final-survivor acc  = P(final survivor == correct)             vs 1/n (random)
                        and vs A3 mode accuracy (no-evaluator baseline)

The self-evaluator is the SAME model (deepseek-v4-flash) that produced the A3
trajectories — a true "self" predicate, gold-free, question-free.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        kk, vv = line.split("=", 1)
        os.environ.setdefault(kk.strip(), vv.strip().strip('"').strip("'"))
for kk in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(kk, None)
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.run_self_evaluator import load_nonmode_subset  # noqa: E402

TRAJ = ROOT / "experiments/experiments/a3_new_20261010_t0.7/deepseek-v4-flash/loop_trajectories.jsonl"
V1_RECORDS = ROOT / "experiments/self_evaluator_20261011/records.jsonl"
MODEL_KEY = "deepseek-v4-flash"
EVALUATOR_MAX_TOKENS = 2048
MAX_ANSWER_CHARS = 120


def _clip(s: str, n: int = MAX_ANSWER_CHARS) -> str:
    s = str(s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def k_targets(n: int) -> list[int]:
    ks = {2, math.ceil(math.sqrt(n))}
    return sorted(ks)


def strided_groups(cands: list[dict], k: int) -> list[list[dict]]:
    """Round-robin interleave by frequency rank (cands already sorted desc by count).
    Each group mixes high/mid/low-frequency answers -> protects the rare-correct answer."""
    groups = [[] for _ in range(k)]
    for i, c in enumerate(cands):
        groups[i % k].append(c)
    return groups


def group_prompt(groups: list[list[dict]], narration: str, total: int) -> str:
    k = len(groups)
    lines = ["You are a meta-cognitive evaluator. A solver model produced several "
             "distinct answers across repeated independent attempts. The answers are "
             "partitioned into groups. A reconstructed reasoning chain for each answer "
             "is provided below.",
             "",
             "Your ONLY job: eliminate the single group LEAST likely to contain the "
             "correct answer. Judge each group by the internal plausibility / "
             "consistency of its members' reasoning states. Do NOT re-solve anything "
             "and do NOT state which single answer is correct.", ""]
    for gi, g in enumerate(groups, 1):
        mem = " | ".join(f"[{c['label']}] {_clip(c['raw'])} (x{c['count']}/{total})" for c in g)
        lines.append(f"Group {gi}: {mem}")
    lines.append("")
    lines.append("RECONSTRUCTED REASONING CHAINS (ANSWER [k] -> chain):")
    lines.append(narration.strip())
    lines.append("")
    lines.append(f"Respond with ONLY the group number (1..{k}) you eliminate. Nothing else.")
    return "\n".join(lines)


def parse_group(text: str, k: int):
    nums = [int(x) for x in re.findall(r"\d+", text or "")]
    for x in reversed(nums):
        if 1 <= x <= k:
            return x
    return None


def call_text(agent: HuggingFaceAgent, prompt: str):
    return agent._call_llm_text([{"role": "user", "content": prompt}],
                                max_tokens=EVALUATOR_MAX_TOKENS)[0]


def run_tournament(agent: HuggingFaceAgent, t: dict, narration: str, k_target: int) -> dict:
    S = [dict(c) for c in t["cands"]]  # copy; each has label/raw/count/is_correct
    n_orig = len(S)
    rounds = []
    aborted = False
    while len(S) > 1:
        k = min(k_target, len(S))
        groups = strided_groups(S, k)
        prompt = group_prompt(groups, narration, t["total"])
        n_before = len(S)
        try:
            out = call_text(agent, prompt)
            g = parse_group(out, k)
            api_fail = False
        except Exception as e:
            out = f"API FAILURE: {e}"
            g = None
            api_fail = True
        if g is None:
            aborted = True
            rounds.append({"round": len(rounds), "n_before": n_before, "k": k,
                           "eliminated_group": None, "correct_in_eliminated": None,
                           "parse": out.strip()[:200], "api_failure": api_fail})
            break
        eliminated = groups[g - 1]
        correct_in_elim = any(c["is_correct"] for c in eliminated)
        rounds.append({"round": len(rounds), "n_before": n_before, "k": k,
                       "eliminated_group": g, "correct_in_eliminated": correct_in_elim,
                       "parse": out.strip()[:80]})
        S = [c for c in S if c not in eliminated]

    survivor = S[0] if len(S) == 1 else None
    return {
        "task_id": t["task_id"], "family": t["family"], "k_target": k_target,
        "n_orig": n_orig, "rounds": rounds, "aborted": aborted,
        "final_survivor_correct": (survivor["is_correct"] if survivor else None),
        "final_survivor_label": (survivor["label"] if survivor else None),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="limit to first N questions (0=all)")
    ap.add_argument("--k", type=int, default=0, help="override k (0=scan {2, ceil(sqrt(n))})")
    ap.add_argument("--out", type=str, default=str(ROOT / "experiments/group_retention_20261011"))
    args = ap.parse_args()

    subset = load_nonmode_subset(TRAJ)
    v1 = {r["task_id"]: r for r in (json.loads(l) for l in open(V1_RECORDS, encoding="utf-8"))}
    print(f"[load] non-mode={len(subset)}  v1_narration={len(v1)}")
    if args.n:
        subset = subset[: args.n]

    missing = [t["task_id"] for t in subset if t["task_id"] not in v1 or not v1[t["task_id"]].get("narration")]
    if missing:
        print(f"[warn] missing narration for {len(missing)}: {missing}")

    entry = config.PHASE1_MODELS[MODEL_KEY]
    # Evaluator = structured "eliminate a group" judgment, NOT a reasoning benchmark.
    # Disable thinking so deepseek-v4-flash stops intermittently dumping its answer into
    # reasoning_content and leaving content empty (CoT leaks into parse_group). Clean token.
    agent = HuggingFaceAgent(model=entry["model"], token=entry["api_key"],
                             base_url=entry["base_url"], max_tokens=EVALUATOR_MAX_TOKENS,
                             temperature=0.0, seed=None, enable_thinking=False)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_recs = []
    for i, t in enumerate(subset, 1):
        n = len(t["cands"])
        ks = [args.k] if args.k else k_targets(n)
        for kt in ks:
            rec = run_tournament(agent, t, v1[t["task_id"]]["narration"], kt)
            rec["latency_s"] = round(sum(0 for _ in []), 1)  # placeholder
            all_recs.append(rec)
            fs = rec["final_survivor_correct"]
            r1 = rec["rounds"][0]["correct_in_eliminated"] if rec["rounds"] else None
            r1ret = (None if r1 is None else (not r1))
            print(f"[{i}/{len(subset)}] {t['task_id']:<10} n={n} k={kt} "
                  f"rounds={len(rec['rounds'])} round1_retain={r1ret} "
                  f"final_survivor_correct={fs} aborted={rec['aborted']}", flush=True)
            with open(out_dir / "records.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- aggregate ----
    from collections import defaultdict
    byk = defaultdict(list)
    for rec in all_recs:
        byk[rec["k_target"]].append(rec)

    n_tasks = len(subset)
    mode_acc = sum(1 for t in subset if t["mode"]["is_correct"]) / n_tasks
    mean_rand = sum(1.0 / len(t["cands"]) for t in subset) / n_tasks

    summary = {"n_tasks": n_tasks, "a3_mode_acc": mode_acc, "random_survivor_baseline": mean_rand,
               "per_k": {}}
    print(f"\n================ SUMMARY ================")
    print(f"n_tasks={n_tasks}  A3_mode_acc(baseline)={mode_acc:.3f}  "
          f"random_survivor_baseline={mean_rand:.3f}")
    for kt in sorted(byk):
        recs = byk[kt]
        valid = [r for r in recs if not r["aborted"] and r["final_survivor_correct"] is not None]
        fs_acc = sum(r["final_survivor_correct"] for r in valid) / len(valid) if valid else None
        r1 = [r["rounds"][0]["correct_in_eliminated"] for r in recs
              if r["rounds"] and r["rounds"][0]["correct_in_eliminated"] is not None]
        r1_retain = (1.0 - sum(r1) / len(r1)) if r1 else None
        base_retain = (kt - 1) / kt
        print(f"\n[k={kt}] n_experiments={len(recs)}  "
              f"final_survivor_acc={fs_acc if fs_acc is None else f'{fs_acc:.3f}'}  "
              f"(random={mean_rand:.3f}, mode={mode_acc:.3f})")
        print(f"        round1_retain={r1_retain if r1_retain is None else f'{r1_retain:.3f}'}  "
              f"baseline(k-1)/k={base_retain:.3f}")
        summary["per_k"][str(kt)] = {
            "final_survivor_acc": fs_acc, "round1_retain": r1_retain,
            "baseline_retain": base_retain, "n_valid": len(valid)}

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\nDONE")


if __name__ == "__main__":
    main()
