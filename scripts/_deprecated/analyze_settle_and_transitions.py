"""
analyze_settle_and_transitions.py
=================================
Correct Phase-2 selector comparison + settle diagnostics (deepseek-v4-flash).

Stage A = SETTLE (3 identical consecutive committed answers = early-stop trigger),
NOT mode, NOT last round (PHASE2_SUMMARY sec 7 item 12).  The A3 arm has no early
stop; its output is the majority vote (mode) over the N=10 i.i.d. samples.

Correct final-answer selector pair:
    A3 -> mode (majority vote)
    C  -> settle

Then dumps the transition chains (committed sequence + rationale) for:
    settle-wrong -> Stage A optimization (settled but locked onto the WRONG answer)
    non-settle   -> Stage B optimization (no 3-run; entered by Stage-B evaluator)

Scope: gpqa block (gpqa_051-198, sole discriminative set) is the only C data with
the transition self-report (rationale), so the chain dump focuses there.

Usage:
  python3 scripts/analyze_settle_and_transitions.py [--chains]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src.transition_extract import extract_task  # noqa: E402

MODEL = "deepseek-v4-flash"

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

KEEP_FAMILIES = {"math", "math500", "mmlu_pro", "aime", "gpqa", "bbh"}


def load_records(run_dirs: list[str]):
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
                merged[rec.get("task_id")] = extract_task(rec)
    return list(merged.values())


def mode_answer(rec: dict):
    freq, cands = rec["frequency"], rec["candidates"]
    if not cands:
        return None
    ans_seq = [r["ans"] for r in rec["rounds"]]
    last_idx = {a: i for i, a in enumerate(ans_seq)}
    return max(cands, key=lambda a: (freq[a], last_idx[a]))


def pct(x, n):
    return f"{x/n:6.1%} ({x}/{n})" if n else "   n/a"


def dump_chain(rec, title):
    print(f"  {title}  task={rec['task_id']}  gold={rec['gold']}  settled={rec['settled_ans']}")
    parts = []
    for r in rec["rounds"]:
        ans = r["ans"] if r["ans"] is not None else "None"
        mark = "ok" if r["correct"] else "--"
        parts.append(f"r{r['r']}:{ans}({mark})")
    print("    seq : " + "  ".join(parts))
    if rec["transitions"]:
        print("    transitions:")
        for tr in rec["transitions"]:
            rat = (tr["rationale"] or "").strip().replace("\n", " ")
            if len(rat) > 120:
                rat = rat[:120] + "..."
            print(f"      r{tr['from_r']}->r{tr['to_r']}  {tr['from']} -> {tr['to']}  | {rat}")
    else:
        print("    transitions: (none)")
    print()


def main():
    order = ["phase1 (math/math500/mmlu_pro)", "new (aime/gpqa/bbh)", "gpqa 051-198"]

    print("=" * 112)
    print("A3 vs C  (A3 = majority VOTE / mode ;  C = SETTLE)   deepseek-v4-flash")
    print("=" * 112)
    hdr = (f"{'block':30} {'n':>4} {'A3 act':>12} {'C act':>12} "
           f"{'A3 vote':>12} {'C settle%':>9} {'C settleAcc':>11} {'A3 head':>8} {'C head':>8}")
    print(hdr)
    print("-" * 112)

    c_gpqa_recs = None
    for block in order:
        a3 = load_records(RUNS["A3"][block])
        c = load_records(RUNS["C"][block])
        if block == "gpqa 051-198":
            c_gpqa_recs = c
        n = len(a3)
        a3_act = sum(1 for r in a3 if r["correct_appeared"])
        c_act = sum(1 for r in c if r["correct_appeared"])
        a3_vote = sum(1 for r in a3 if (m := mode_answer(r)) is not None and r["gold"] is not None and m == r["gold"])
        c_settle_n = sum(1 for r in c if r["settled_ans"] is not None)
        c_settle_c = sum(1 for r in c if r["settled_ans"] is not None and r["gold"] is not None and r["settled_ans"] == r["gold"])
        a3_head = sum(1 for r in a3 if r["correct_appeared"] and not r["final_correct"])
        c_head = sum(1 for r in c if r["correct_appeared"] and not r["final_correct"])
        print(f"{block:30} {n:4} {pct(a3_act, n):>12} {pct(c_act, n):>12} "
              f"{pct(a3_vote, n):>12} "
              f"{c_settle_n/n:8.1%} "
              f"{pct(c_settle_c, c_settle_n):>11} "
              f"{a3_head:>8} {c_head:>8}")
    print()

    print("=" * 112)
    print("GPQA C settle diagnostics (gpqa_051-198, n=%d)" % len(c_gpqa_recs))
    print("=" * 112)
    settle_ok = [r for r in c_gpqa_recs if r["settled_ans"] is not None and r["settled_ans"] == r["gold"]]
    settle_wrong = [r for r in c_gpqa_recs if r["settled_ans"] is not None and r["settled_ans"] != r["gold"]]
    non_settle = [r for r in c_gpqa_recs if r["settled_ans"] is None]
    print(f"settle-correct : {len(settle_ok)}")
    print(f"settle-WRONG   : {len(settle_wrong)}")
    print(f"non-settle     : {len(non_settle)} (of which activated: "
          f"{sum(1 for r in non_settle if r['correct_appeared'])})")
    print()

    print("=" * 112)
    print("SETTLE-WRONG chains  (Stage A optimization targets)")
    print("=" * 112)
    for r in sorted(settle_wrong, key=lambda x: x["task_id"]):
        dump_chain(r, "settle-WRONG")

    print("=" * 112)
    print("NON-SETTLE chains  (Stage B / meta-cognition targets)")
    print("=" * 112)
    for r in sorted(non_settle, key=lambda x: x["task_id"]):
        activated = "activated" if r["correct_appeared"] else "NEVER"
        dump_chain(r, f"non-settle[{activated}]")


if __name__ == "__main__":
    main()
