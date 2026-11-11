"""
markov_behavior_study.py
========================
Study the n-round answer sequence as a Markov chain over ANSWER VALUES, and ask
whether the CORRECT answer has any special stationary/absorbing status there —
or whether the model wanders near-uniformly (a pure random walk).

Per task we:
  - build the 1st-order transition matrix over normalized answer values,
  - mark each value GOOD (rounds where it scored correct) or BAD,
  - compute:
      * self-loop rate of GOOD vs BAD values (stickiness),
      * stationary distribution pi; the GOOD mass ratio = pi(GOOD) / (n_good/n_uniq),
        i.e. how much MORE (ratio>1) or LESS (ratio<1) the chain dwells on the
        correct value than uniform would predict. ratio ~ 1 => pure random walk.
      * which value is the pi-argmax, and how often that is the GOOD value,
      * return probability P(a_{t+2}=a_t) and entropy rate,
      * value-space EIR = P(GOOD->BAD), ECR = P(BAD->GOOD),
  - also relate entropy rate to lock-in (does high-entropy => lower final acc).

Gold-free features only; correctness labels come from the already-stored
is_correct flag. Deterministic, zero-API.
"""
from __future__ import annotations
import json, math, re, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _norm_ans(s) -> str:
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")


def _steady(P):
    n = len(P)
    pi = [1.0 / n] * n
    for _ in range(300):
        npi = [0.0] * n
        for i in range(n):
            row = P[i]
            s = pi[i]
            for j in range(n):
                npi[j] += s * row[j]
        if max(abs(a - b) for a, b in zip(npi, pi)) < 1e-12:
            pi = npi; break
        pi = npi
    return pi


def _entropy_rate(P, pi):
    rate = 0.0
    for i, row in enumerate(P):
        for p in row:
            if p > 0.0:
                rate += pi[i] * p * math.log2(p)
    return -rate


def analyze(path: Path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

    good_self, bad_self = [], []
    mass_ratios = []
    argmax_is_good = 0
    n_with_good = 0
    n_tasks = 0
    ret_rates = []
    entropies = []
    eir_tot = ecr_tot = 0
    entropy_by_lock = defaultdict(list)  # 'locked'|'not' -> [entropy...]

    for t in rows:
        fam = t.get("family")
        if not fam:
            continue
        rounds = t["rounds"]
        if len(rounds) < 2:
            continue
        n_tasks += 1
        seq = [_norm_ans(r.get("final_answer")) for r in rounds]
        corr = [bool(r.get("is_correct")) for r in rounds]

        # value -> is_good (a value is GOOD iff it ever scored correct)
        good_of = {}
        for a, c in zip(seq, corr):
            good_of[a] = good_of.get(a, False) or c
        n_good = sum(1 for v in good_of.values() if v)
        n_uniq = len(set(seq))

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

        # self-loop of GOOD vs BAD
        for si, a in enumerate(states):
            sl = P[si][si]
            (good_self if good_of[a] else bad_self).append(sl)

        pi = _steady(P)
        if n_good:
            n_with_good += 1
            pi_good = sum(pi[si] for si, a in enumerate(states) if good_of[a])
            uniform = n_good / n_uniq if n_uniq else 0.0
            mass_ratios.append(pi_good / uniform if uniform > 0 else 0.0)
            if good_of[states[max(range(len(states)), key=lambda i: pi[i])]]:
                argmax_is_good += 1

        # value-space EIR / ECR
        for i in range(len(seq) - 1):
            a, b = good_of[seq[i]], good_of[seq[i + 1]]
            if a and not b:
                eir_tot += 1
            elif (not a) and b:
                ecr_tot += 1

        # return probability P(a_{t+2}=a_t)
        if len(seq) >= 3:
            ret = sum(1 for i in range(len(seq) - 2) if seq[i] == seq[i + 2])
            ret_rates.append(ret / (len(seq) - 2))

        # entropy rate
        H = _entropy_rate(P, pi)
        entropies.append(H)
        # lock-in: final answer correct (not just appeared)
        entropy_by_lock['locked' if corr[-1] else 'not'].append(H)

    def mean(x): return sum(x) / len(x) if x else 0.0
    print(f"\n===== {path.relative_to(ROOT)} =====")
    print(f"  tasks={n_tasks}  (with a correct value: {n_with_good})")
    print(f"\n  [Q3a 正确值是否更'粘']")
    print(f"    self-loop rate  GOOD value : {mean(good_self):.3f}  (n={len(good_self)})")
    print(f"    self-loop rate  BAD  value : {mean(bad_self):.3f}  (n={len(bad_self)})")
    print(f"\n  [Q3b 平稳分布里正确值是否被高估]  ratio = pi(GOOD)/uniform; 1=纯随机")
    if mass_ratios:
        mr = sorted(mass_ratios)
        q = lambda p: mr[min(len(mr)-1, int(p*len(mr)))]
        print(f"    GOOD mass ratio  mean={mean(mr):.3f}  med={q(.5):.3f}  "
              f"p25={q(.25):.3f}  p75={q(.75):.3f}")
        print(f"    pi-argmax IS the correct value : {argmax_is_good}/{n_with_good} = "
              f"{argmax_is_good/n_with_good:.1%}")
    print(f"\n  [随机游走 vs 方向]")
    print(f"    value-space EIR (GOOD->BAD) : {eir_tot}")
    print(f"    value-space ECR (BAD->GOOD) : {ecr_tot}")
    print(f"\n  [摇摆量]")
    print(f"    return prob P(a_{{t+2}}=a_t) : {mean(ret_rates):.3f}")
    print(f"    entropy rate (bits/step)    : {mean(entropies):.3f}")
    lo = entropy_by_lock.get('locked', [])
    no = entropy_by_lock.get('not', [])
    print(f"\n  [衍生: 熵率 vs 锁定]")
    print(f"    entropy when FINAL correct : {mean(lo):.3f}  (n={len(lo)})")
    print(f"    entropy when FINAL wrong   : {mean(no):.3f}  (n={len(no)})")


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
