"""
mode_bimodality.py
==================
Test the "over-guided critic reshapes the sampling distribution" intuition:
  - is the correct answer the MODE (top-1 frequency) of the n-round answer
    value histogram, rather than just a random draw (H2 mechanism)?
  - when the mode-selector is WRONG, is it because the distribution is BIMODAL
    and the correct answer sits at the ~2nd mode (wrong peak got marginally more)?
  - is mode CONCENTRATION (top1 share) correlated with lock-in (final correct)?
  - do stationary-argmax and frequency-argmax AGREE (稳态 vs freq 正相关)?
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _norm_ans(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower()).strip(".,;:!?")


def _steady(P):
    n = len(P)
    pi = [1.0 / n] * n
    for _ in range(300):
        npi = [0.0] * n
        for i in range(n):
            row, s = P[i], pi[i]
            for j in range(n):
                npi[j] += s * row[j]
        if max(abs(a - b) for a, b in zip(npi, pi)) < 1e-12:
            pi = npi; break
        pi = npi
    return pi


def analyze(path: Path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    n = 0
    rank = Counter()                 # rank of the correct value in freq ordering
    conc_correct, conc_wrong = [], []
    bimodal_second = 0               # mode wrong BUT correct is top-2
    mode_wrong_total = 0
    agree_freq_pi = 0
    conc_locked, conc_unlocked = [], []
    final_correct = 0

    for t in rows:
        if not t.get("family"):
            continue
        rounds = t["rounds"]
        if len(rounds) < 2:
            continue
        seq = [_norm_ans(r.get("final_answer")) for r in rounds]
        corr = [bool(r.get("is_correct")) for r in rounds]
        good_of = {}
        for a, c in zip(seq, corr):
            good_of[a] = good_of.get(a, False) or c
        # correct VALUES (may be >1 if two different strings both scored true; rare)
        good_vals = [a for a, g in good_of.items() if g]
        if not good_vals:
            continue
        n += 1
        if corr[-1]:
            final_correct += 1

        last_idx = {a: i for i, a in enumerate(seq)}
        counts = Counter(seq)
        # order by count desc, tie -> larger last index
        ordered = sorted(set(seq), key=lambda a: (-counts[a], last_idx[a]))
        c1 = counts[ordered[0]]
        # best rank (lowest) among correct values
        best_rank = min(ordered.index(g) + 1 for g in good_vals)
        rank[best_rank] += 1

        conc = c1 / len(seq)
        top1_good = good_of[ordered[0]]
        (conc_correct if top1_good else conc_wrong).append(conc)
        (conc_locked if corr[-1] else conc_unlocked).append(conc)

        # is a correct value the mode?
        if not top1_good:
            mode_wrong_total += 1
            if len(ordered) >= 2 and good_of[ordered[1]]:
                bimodal_second += 1

        # freq-argmax vs stationary-argmax agreement
        states = list(set(seq))
        idx = {a: i for i, a in enumerate(states)}
        cnt = [[0] * len(states) for _ in states]
        out = [0] * len(states)
        for i in range(len(seq) - 1):
            a, b = idx[seq[i]], idx[seq[i + 1]]
            cnt[a][b] += 1
            out[a] += 1
        P = [[cnt[i][j] / out[i] if out[i] else 0.0 for j in range(len(states))]
             for i in range(len(states))]
        pi = _steady(P)
        pi_argmax = max(states, key=lambda a: (pi[idx[a]], last_idx[a]))
        if pi_argmax == ordered[0]:
            agree_freq_pi += 1

    def mean(x): return sum(x) / len(x) if x else 0.0
    print(f"\n===== {path.relative_to(ROOT)} =====")
    print(f"  tasks(with correct value appeared)={n}   final-correct(锁定)={final_correct/n:.1%}")
    print(f"  [正确值在频率直方图里的排名] (R1=就是众数/mode)")
    for r in (1, 2, 3):
        if rank[r]:
            print(f"    rank={r} : {rank[r]/n:6.2%}  ({rank[r]})")
    print(f"    rank>=4  : {sum(v for k,v in rank.items() if k>=4)/n:6.2%}")
    print(f"  [mode 选错的题目：正确值是否就在第2峰(双mode)]")
    if mode_wrong_total:
        print(f"    mode错误里, 正确值=top2 : {bimodal_second}/{mode_wrong_total} = {bimodal_second/mode_wrong_total:.1%}")
    print(f"  [众数集中度 vs 正确性 / 锁定]  (top1 份额)")
    print(f"    mode 正确时   : {mean(conc_correct):.3f}  (n={len(conc_correct)})")
    print(f"    mode 错误时   : {mean(conc_wrong):.3f}  (n={len(conc_wrong)})")
    print(f"    末轮正确时    : {mean(conc_locked):.3f}  (n={len(conc_locked)})")
    print(f"    末轮错误时    : {mean(conc_unlocked):.3f}  (n={len(conc_unlocked)})")
    print(f"  [稳态 vs 众数 正相关]  freq-argmax == pi-argmax : {agree_freq_pi/n:.1%}")


def main():
    targets = [
        ROOT / "experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/glm-5.3/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/qwen3.8-flash/loop_trajectories.jsonl",
    ]
    for p in targets:
        if p.exists():
            analyze(p)


if __name__ == "__main__":
    main()
