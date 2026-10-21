"""
stable_state_estimator.py
=========================
Test H2: can a gold-free "most-stable-state" selector over n feedback rounds
recover the correct answer better than naively taking the last round's answer?

Per task we build the 1st-order transition matrix over normalized answer values
(same as markov_behavior_study.py), then compare several FINAL-ANSWER SELECTORS:
  first     : round-0 answer
  last      : final round answer   (= current lock-in / early-stop output)
  freq      : most-frequent value (direct from data, no simulation)
  selfloop  : highest self-loop P(a->a) (direct from data)
  pi_argmax : stationary-distribution argmax (power iteration = "simulate long-run")

Tie-break for freq/selfloop/pi: last occurrence index (deterministic).

Also relates the stable-state selector to lock-in:
  - lock-in rate = accuracy of `last`
  - does the stability SELECTION agree with `last`, and when they disagree,
    does the stable state rescue `last` failures?
  - stability margin (pi of the selected state) for locked-correct vs locked-wrong.
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
    selectors = ["first", "last", "freq", "selfloop", "pi_argmax"]
    hit = {s: 0 for s in selectors}
    n = 0
    n_act = 0              # tasks where a correct value appeared
    agree_last_pi = 0      # pi_argmax == last value
    rescue = 0             # pi correct while last wrong
    sabotage = 0           # pi wrong while last correct
    margin_locked = []     # pi(argmax) for tasks whose FINAL answer is correct
    margin_unlocked = []   # pi(argmax) for tasks whose FINAL answer is wrong

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
        if not any(good_of.values()):
            continue  # no correct value ever appeared -> cannot test decorrection

        n += 1
        n_act += 1 if any(corr) else 0

        states = list(set(seq))
        idx = {a: i for i, a in enumerate(states)}
        last_idx = {a: i for i, a in enumerate(seq)}
        cnt = [[0] * len(states) for _ in states]
        out = [0] * len(states)
        for i in range(len(seq) - 1):
            a, b = idx[seq[i]], idx[seq[i + 1]]
            cnt[a][b] += 1
            out[a] += 1
        P = [[cnt[i][j] / out[i] if out[i] else 0.0 for j in range(len(states))]
             for i in range(len(states))]
        pi = _steady(P)

        picks = {
            "first":     seq[0],
            "last":      seq[-1],
            "freq":      max(states, key=lambda a: (seq.count(a), last_idx[a])),
            "selfloop":  max(states, key=lambda a: (P[idx[a]][idx[a]], last_idx[a])),
            "pi_argmax": max(states, key=lambda a: (pi[idx[a]], last_idx[a])),
        }
        for s in selectors:
            hit[s] += 1 if good_of[picks[s]] else 0

        # agreement with lock-in (last)
        if picks["pi_argmax"] == picks["last"]:
            agree_last_pi += 1
        gc, gl = good_of[picks["pi_argmax"]], good_of[picks["last"]]
        if gc and not gl:
            rescue += 1
        if (not gc) and gl:
            sabotage += 1

        m = pi[idx[picks["pi_argmax"]]]
        (margin_locked if corr[-1] else margin_unlocked).append(m)

    def mean(x): return sum(x) / len(x) if x else 0.0
    print(f"\n===== {path.relative_to(ROOT)} =====")
    print(f"  tasks(with a correct value appeared)={n}   P_act={n_act}/{n}={n_act/n:.1%}")
    print(f"  [H2 选择器准确率 vs 记录 is_correct]")
    for s in selectors:
        print(f"    {s:>9} : {hit[s]/n:6.2%}  ({hit[s]}/{n})")
    print(f"  [稳定态 vs 锁定(末轮)]")
    print(f"    pi_argmax 与 last 取值一致 : {agree_last_pi/n:.1%}")
    print(f"    rescue  (pi对 / last错   ) : {rescue}  ({rescue/n:.1%})")
    print(f"    sabotage(pi错 / last对   ) : {sabotage}  ({sabotage/n:.1%})")
    print(f"  [稳定态置信度边际 vs 锁定]")
    print(f"    pi(argmax) 当末轮正确 : {mean(margin_locked):.3f}  (n={len(margin_locked)})")
    print(f"    pi(argmax) 当末轮错误 : {mean(margin_unlocked):.3f}  (n={len(margin_unlocked)})")


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
