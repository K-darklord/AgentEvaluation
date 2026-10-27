"""Merge flip19 (19 tasks across 3 slices) and compare arms on the EIR/ECR loop.

Answers three questions (2026-10-24):
  1. Is strong critic effective — with vs without CoT (lever-1)?
  2. Does the loop show net gain (final vs init), i.e. is ECR > EIR in aggregate?
  3. Whole-19 aggregate (no per-slice split).

EIR/ECR are per-round transition rates on the two-state chain {Correct, Incorrect}:
  EIR = P(c_{k+1}=wrong | c_k=correct)   = correct->wrong events / correct rounds
  ECR = P(c_{k+1}=correct | c_k=wrong)   = wrong->correct events / wrong rounds
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"

ARMS = {
    "A3C3_cotfix(CoT)": [
        "feedback_loop_A3C3_flip19_phase1_20261024_cotfix",
        "feedback_loop_A3C3_flip19_new_20261024_cotfix",
        "feedback_loop_A3C3_flip19_gpqa_20261024_cotfix",
        "feedback_loop_A3C3_flip19_gpqa_20261024_cotfix_retry",
    ],
    "A3C3_buggy(noCoT)": [
        "feedback_loop_A3C3_flip19_phase1_20261023",
        "feedback_loop_A3C3_flip19_new_20261023",
        "feedback_loop_A3C3_flip19_gpqa_20261023",
    ],
    "C3_cotfix(CoT)": [
        "feedback_loop_C3_flip19_phase1_20261024_cotfix",
        "feedback_loop_C3_flip19_new_20261024_cotfix",
        "feedback_loop_C3_flip19_gpqa_20261024_cotfix",
    ],
    "C3v2_old": [
        "feedback_loop_C3v2_flip19_phase1_20261023",
        "feedback_loop_C3v2_flip19_new_20261023",
        "feedback_loop_C3v2_flip19_gpqa_20261023",
    ],
}


def load(arm_dirs):
    tasks = {}
    for d in arm_dirs:
        p = EXP / d / "deepseek-v4-flash" / "loop_trajectories.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            t = json.loads(line)
            tasks[t["task_id"]] = t
    return tasks


def transitions(t):
    """(eir_n, ecr_n, correct_rounds, wrong_rounds) from the per-round is_correct vector."""
    cs = [r["is_correct"] for r in t["rounds"]]
    eir_n = ecr_n = 0
    for k in range(len(cs) - 1):
        if cs[k] and not cs[k + 1]:
            eir_n += 1
        elif not cs[k] and cs[k + 1]:
            ecr_n += 1
    cor = sum(1 for c in cs if c)
    wrg = sum(1 for c in cs if not c)
    return eir_n, ecr_n, cor, wrg


print(f"{'arm':22s} {'n':>2s} {'init':>5s} {'final':>6s} {'EIR':>6s} {'ECR':>6s}  EIRn/ECRn  states")
for arm, dirs in ARMS.items():
    tasks = load(dirs)
    n = len(tasks)
    if n == 0:
        print(f"{arm:22s}  (no data)")
        continue
    init_n = sum(1 for t in tasks.values() if t.get("start_correct"))
    fin_n = sum(1 for t in tasks.values() if t.get("final_correct"))
    states = Counter(t.get("end_state") for t in tasks.values())
    eir_n = ecr_n = cor = wrg = 0
    for t in tasks.values():
        e, c, cr, wr = transitions(t)
        eir_n += e
        ecr_n += c
        cor += cr
        wrg += wr
    eir = eir_n / cor if cor else float("nan")
    ecr = ecr_n / wrg if wrg else float("nan")
    init = init_n / n
    fin = fin_n / n
    st = ",".join(f"{k}:{v}" for k, v in sorted(states.items(), key=lambda x: x[0]))
    print(f"{arm:22s} {n:2d} {init:5.3f} {fin:6.3f} {eir:6.3f} {ecr:6.3f}  "
          f"{eir_n:2d}/{ecr_n:2d}   {{{st}}}")