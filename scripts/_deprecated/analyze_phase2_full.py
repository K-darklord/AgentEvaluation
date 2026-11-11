"""
analyze_phase2_full.py
======================
Full-data A3 vs C comparison for RSI Phase 2 (deepseek-v4-flash only).

Reproduces the three independent comparison dimensions from RESEARCH_PLAN
section 2.3 / PHASE2_SUMMARY section 2.7, plus settle + headroom, across EVERY
task block (not just GPQA):

  dimension 1  activation  = P(correct answer appears at least once)
  dimension 2  mode / vote = modal committed answer == gold
  dimension 3  final @1    = round-0 correct  vs  last-round correct
  settle       = trailing run of >= 3 identical committed answers
  headroom     = activated (correct appeared) but not locked (final wrong)

Commitment identity is reproduced faithfully from the C-arm runtime via
``src/transition_extract.py`` (the same routine Stage B consumes), so the mode /
vote / settle columns are consistent across the old (final_answer-only) and new
(committed_answer) data formats.

Usage:
  python3 scripts/analyze_phase2_full.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src.transition_extract import extract_task  # noqa: E402

MODEL = "deepseek-v4-flash"

# ---- canonical RUN PAIRS (arm -> task block -> run dirs) ----
# bfcl / finance excluded from voteable set (scorer/prompt drift, PHASE2_SUMMARY sec 4).
# C phase1 merges the stale phase1 run with the mmlu_pro rerun (scorer fix); the
# rerun's mmlu_pro rows share the same task_ids and override the stale ones.
RUNS = {
    "A3": {
        "phase1 (math/math500/mmlu_pro)": ["experiments/experiments/a3_phase1_20261010_t0.7"],
        "new (aime/gpqa/bbh)":            ["experiments/experiments/a3_new_20261010_t0.7"],
        "gpqa 051-198":                   ["experiments/a3_gpqa_full_deepseek_20261013"],
    },
    "C": {
        "phase1 (math/math500/mmlu_pro)": [
            "experiments/feedback_loop_20261006_173715",
            "experiments/feedback_loop_C_mmlu_pro_rerun_20261012",
        ],
        "new (aime/gpqa/bbh)":            ["experiments/feedback_loop_C_20261008"],
        "gpqa 051-198":                   ["experiments/feedback_loop_C_20261015_175552"],
    },
}

# Tasks excluded from the gpqa block pending the 32768 re-run (INT-26 length pollution):
#   gpqa_089/131/186 -> A3 lost commit under context length
#   gpqa_187        -> C transition truncated
EXCLUDE = {"gpqa_089", "gpqa_131", "gpqa_186", "gpqa_187"}

# families kept in the voteable set (bfcl / finance dropped for protocol drift)
KEEP_FAMILIES = {"math", "math500", "mmlu_pro", "aime", "gpqa", "bbh"}

# discrete-answer families (letter / single integer): mode / vote is meaningful.
# numeric free-form families (math / math500) yield a degenerate mode and are
# excluded from Claim-2 (mode/vote) comparisons only.
DISCRETE = {"mmlu_pro", "aime", "gpqa", "bbh"}


def load_records(run_dirs: list[str]) -> list[dict]:
    """Merge trajectories across run dirs; a later dir overrides the same task_id."""
    merged: dict[str, dict] = {}
    for run_dir in run_dirs:
        traj = REPO_ROOT / run_dir / MODEL / "loop_trajectories.jsonl"
        with open(traj, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("family") not in KEEP_FAMILIES:
                    continue
                if rec.get("task_id") in EXCLUDE:
                    continue
                merged[rec.get("task_id")] = extract_task(rec)
    return list(merged.values())


def task_metrics(t: dict) -> dict:
    """Single-task metrics (mode / vote / settle / headroom) from a transition record."""
    freq = t["frequency"]           # candidate -> count (committed sequence)
    gold = t["gold"]
    candidates = t["candidates"]
    rounds = t["rounds"]

    ans_seq = [rounds[i]["ans"] for i in range(len(rounds))]
    mode = None
    if candidates:
        last_idx = {a: i for i, a in enumerate(ans_seq)}
        mode = max(candidates, key=lambda a: (freq[a], last_idx[a]))

    settled = t["settled_ans"] is not None
    settled_correct = (t["settled_ans"] == gold) if settled else None

    activated = bool(t["correct_appeared"])
    final_correct = bool(t["final_correct"])

    return {
        "task_id": t["task_id"],
        "family": t["family"],
        "n_rounds": t["n_rounds"],
        "start_correct": bool(t["start_correct"]),
        "final_correct": final_correct,
        "activated": activated,
        "mode_correct": (mode == gold) if mode is not None else False,
        "settled": settled,
        "settled_correct": settled_correct,
        "headroom": activated and not final_correct,
        "locked": activated and final_correct,
        "never": not activated,
    }


def pct(x, n):
    return f"{x/n:6.1%} ({x}/{n})" if n else "   n/a"


def aggregate(metrics: list[dict]) -> dict:
    n = len(metrics)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "activation": sum(1 for m in metrics if m["activated"]),
        "start": sum(1 for m in metrics if m["start_correct"]),
        "final": sum(1 for m in metrics if m["final_correct"]),
        "mode": sum(1 for m in metrics if m["mode_correct"]),
        "settle_n": sum(1 for m in metrics if m["settled"]),
        "settle_c": sum(1 for m in metrics if m["settled_correct"] is True),
        "headroom": sum(1 for m in metrics if m["headroom"]),
        "locked": sum(1 for m in metrics if m["locked"]),
        "never": sum(1 for m in metrics if m["never"]),
    }


def main() -> None:
    order = ["phase1 (math/math500/mmlu_pro)", "new (aime/gpqa/bbh)", "gpqa 051-198"]
    agg = {}
    per_family = {}

    for arm, blocks in RUNS.items():
        for block, run_dirs in blocks.items():
            metrics = [task_metrics(t) for t in load_records(run_dirs)]
            agg[(arm, block)] = aggregate(metrics)
            fam = defaultdict(list)
            for m in metrics:
                fam[m["family"]].append(m)
            per_family[(arm, block)] = {f: aggregate(fm) for f, fm in fam.items()}

    print("=" * 120)
    print("PHASE-2 FULL-DATA COMPARISON  (deepseek-v4-flash, excluded:", sorted(EXCLUDE), ")")
    print("=" * 120)

    header = (f"{'block':30} {'arm':3} {'n':>4} {'act':>13} {'@1':>13} "
              f"{'final':>13} {'mode':>13} {'settle%':>8} {'settleAcc':>9} {'headroom':>9}")
    print(header)
    print("-" * 120)
    for block in order:
        for arm in ["A3", "C"]:
            m = agg.get((arm, block), {})
            if not m or m.get("n") == 0:
                continue
            settle_pct = m["settle_n"] / m["n"]
            print(f"{block:30} {arm:3} {m['n']:4} "
                  f"{pct(m['activation'], m['n']):>13} "
                  f"{pct(m['start'], m['n']):>13} "
                  f"{pct(m['final'], m['n']):>13} "
                  f"{pct(m['mode'], m['n']):>13} "
                  f"{settle_pct:7.1%} "
                  f"{pct(m['settle_c'], m['settle_n']):>9} "
                  f"{m['headroom']:>9}")
        print()

    print("=" * 120)
    print("PER-FAMILY (activation / @1 / final / mode)")
    print("=" * 120)
    print(f"{'block':26} {'fam':9} {'arm':3} {'n':>4} {'act':>12} {'@1':>12} {'final':>12} {'mode':>12}")
    print("-" * 120)
    for block in order:
        for arm in ["A3", "C"]:
            fams = per_family.get((arm, block), {})
            for fam in sorted(fams):
                m = fams[fam]
                print(f"{block:26} {fam:9} {arm:3} {m['n']:4} "
                      f"{pct(m['activation'], m['n']):>12} "
                      f"{pct(m['start'], m['n']):>12} "
                      f"{pct(m['final'], m['n']):>12} "
                      f"{pct(m['mode'], m['n']):>12}")
        if block != order[-1]:
            print()

    print("=" * 120)
    print("C - A3 MATCHED DELTAS (paired by task_id; positive = C better)")
    print("=" * 120)
    for block in order:
        a3 = {m["task_id"]: m for m in [task_metrics(t) for t in load_records(RUNS["A3"][block])]}
        c = {m["task_id"]: m for m in [task_metrics(t) for t in load_records(RUNS["C"][block])]}
        common = [tid for tid in a3 if tid in c]
        n = len(common)
        n_disc = sum(1 for tid in common if a3[tid]["family"] in DISCRETE)
        def cnt(key, fam_filter=None):
            oa = oc = 0
            for tid in common:
                if fam_filter and a3[tid]["family"] not in fam_filter:
                    continue
                oa += a3[tid][key]
                oc += c[tid][key]
            return oa, oc
        a_act, c_act = cnt("activated")
        a_fin, c_fin = cnt("final_correct")
        a_mod, c_mod = cnt("mode_correct", fam_filter=DISCRETE)
        a_hea, c_hea = cnt("headroom")
        print(f"{block:30} matched n={n:4}  "
              f"activation {a_act:3}->{c_act:3} ({c_act-a_act:+3}) | "
              f"final {a_fin:3}->{c_fin:3} ({c_fin-a_fin:+3}) | "
              f"mode(discrete n={n_disc}) {a_mod:3}->{c_mod:3} ({c_mod-a_mod:+3}) | "
              f"headroom {a_hea:3}->{c_hea:3} ({c_hea-a_hea:+3})")


if __name__ == "__main__":
    main()
