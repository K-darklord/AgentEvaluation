#!/usr/bin/env python3
"""lr_vote.py — Bayes weighted-vote aggregator (EVALUATOR_FINAL_DESIGN.md sec.4).

Per candidate c over FROZEN keys:
    s(c) = log n(c)  +  sum_{edges a->b with verdict v} ( [b==c]*log LR(v) - [a==c]*log LR(v) )
    pick = argmax s(c), tie -> latest occurrence.

LR(v) = P(v|fix) / P(v|break), Laplace(+1) smoothing over the 3 verdict labels,
estimated on dev (even tasks) decisive edges, applied (frozen) on test (odd tasks).

No model call: it consumes the edge-level verdict file produced by judge-C / judge-R
(JSONL, one record per switch edge: {task_id, from_r, to_r, label, final}).

Usage (run from this dir; ROOT points at AgentEvaluation):
  python3 lr_vote.py --verdicts <abs>/experiments/hle400/t3/judge_c_verdicts.jsonl \
      --loop <abs>/experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl \
      --sidecar <abs>/experiments/hle400/t3/is_correct_t3_sidecar_v2.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))

from src.score_hle_arms import _key  # noqa: E402


# ------------------------------------------------------------------ helpers
def _task_num(tid: str) -> int:
    m = re.search(r"(\d+)$", tid)
    return int(m.group(1)) if m else 0


def _is_dev(tid: str) -> bool:
    return _task_num(tid) % 2 == 0


def sidecar_correct(slist, i: int) -> bool:
    return bool(slist[i].get("c")) if 0 <= i < len(slist) else False


def freeze_keys(gold, loop_rec):
    meta = {"gold": gold}
    return [_key(meta, r) for r in loop_rec.get("rounds", [])]


def freeze_votes(keys):
    votes, latest = {}, {}
    for i, k in enumerate(keys):
        if k is None:
            continue
        votes[k] = votes.get(k, 0) + 1
        latest[k] = i
    return votes, latest


def freeze_mode_key(keys):
    votes, latest = freeze_votes(keys)
    if not votes:
        return None
    return max(votes, key=lambda k: (votes[k], latest[k]))


def last_key_correct(keys, slist, k) -> bool:
    for i in range(len(keys) - 1, -1, -1):
        if keys[i] == k:
            return sidecar_correct(slist, i)
    return False


# ------------------------------------------------------------------ LR fit / apply
VERDICTS = ("OVER", "WARRANTED", "UNSURE")


def fit_lr(vedges):
    """Laplace(+1) LR over dev decisive edges. Returns (lr_tab, Nf, Nb)."""
    n_fix = Counter()
    n_break = Counter()
    for r in vedges:
        if not _is_dev(r["task_id"]):
            continue
        if r["label"] == "fix":
            n_fix[r["final"]] += 1
        elif r["label"] == "break":
            n_break[r["final"]] += 1
    Nf = sum(n_fix.values())
    Nb = sum(n_break.values())
    out = {}
    for v in VERDICTS:
        a, b = n_fix[v], n_break[v]
        pf = (a + 1) / (Nf + 3)
        pb = (b + 1) / (Nb + 3)
        lr = pf / pb
        se = math.sqrt(1.0 / (a + 1) + 1.0 / (b + 1))
        out[v] = {"lr": lr,
                  "lo": math.exp(math.log(lr) - 1.96 * se),
                  "hi": math.exp(math.log(lr) + 1.96 * se),
                  "n_fix": a, "n_break": b}
    return out, Nf, Nb


def apply_lr(keys, votes, latest, edges_info, lr_tab):
    cands = list(votes.keys())
    if len(cands) < 2:
        return cands[0] if cands else None
    s = {c: math.log(votes[c]) for c in cands}
    for (from_r, to_r, v) in edges_info:
        w = math.log(lr_tab[v]["lr"])
        a = keys[from_r]
        b = keys[to_r]
        if a in s:
            s[a] -= w
        if b in s:
            s[b] += w
    return max(cands, key=lambda c: (s[c], latest.get(c, -1)))


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    p = min(b, c)
    acc = 0.0
    for k in range(p + 1):
        acc += math.comb(n, k) * (0.5 ** n)
    return min(2 * acc, 1.0)


def _rev_signs(vedges, pred):
    n_fix = Counter()
    n_break = Counter()
    for r in vedges:
        if not pred(r["task_id"]):
            continue
        if r["label"] == "fix":
            n_fix[r["final"]] += 1
        elif r["label"] == "break":
            n_break[r["final"]] += 1
    Nfr = sum(n_fix.values())
    Nbr = sum(n_break.values())
    out = {}
    for v in VERDICTS:
        pf = (n_fix[v] + 1) / (Nfr + 3)
        pb = (n_break[v] + 1) / (Nbr + 3)
        out[v] = pf / pb
    return out


def _sign(x):
    return "+" if x > 1 else ("-" if x < 1 else "0")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--loop", default=str(ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    args = ap.parse_args()

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    c3 = side["arms"]["C3"]
    loop = {}
    for line in Path(args.loop).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            loop[r["task_id"]] = r

    vedges = []
    for line in Path(args.verdicts).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            vedges.append(json.loads(line))

    edges_by_tid = defaultdict(list)
    for r in vedges:
        edges_by_tid[r["task_id"]].append((r["from_r"], r["to_r"], r["final"]))

    tasks = {}
    for tid in sorted(loop):
        lp = loop[tid]
        sl = c3.get(tid, [])
        keys = freeze_keys(lp.get("gold_answer", "") or "", lp)
        votes, latest = freeze_votes(keys)
        tasks[tid] = {"keys": keys, "votes": votes, "latest": latest,
                      "mode": freeze_mode_key(keys), "sl": sl}

    # E1
    dev_dec = [r for r in vedges if _is_dev(r["task_id"]) and r["label"] != "other"]
    n_correct = sum(
        1 for r in dev_dec
        if (r["final"] == "OVER" and r["label"] == "break")
        or (r["final"] == "WARRANTED" and r["label"] == "fix"))
    e1 = (n_correct / len(dev_dec)) if dev_dec else 0.0

    # E2
    lr_tab, Nf, Nb = fit_lr(vedges)

    # mode headline (all tasks)
    mode_correct_all = sum(
        1 for t in tasks.values()
        if last_key_correct(t["keys"], t["sl"], t["mode"]))

    # E3
    test_tids = [tid for tid in sorted(tasks) if not _is_dev(tid)]
    test_mode_correct = 0
    test_final_correct = 0
    b = c = 0
    flips = []
    for tid in test_tids:
        t = tasks[tid]
        m_ok = last_key_correct(t["keys"], t["sl"], t["mode"])
        pick = apply_lr(t["keys"], t["votes"], t["latest"],
                        edges_by_tid.get(tid, []), lr_tab)
        f_ok = last_key_correct(t["keys"], t["sl"], pick)
        test_mode_correct += 1 if m_ok else 0
        test_final_correct += 1 if f_ok else 0
        if m_ok and not f_ok:
            b += 1
            flips.append((tid, "R->W"))
        elif (not m_ok) and f_ok:
            c += 1
            flips.append((tid, "W->R"))
    net = test_final_correct - test_mode_correct

    # E4
    fwd_sign = {v: _sign(lr_tab[v]["lr"]) for v in VERDICTS}
    rev_lr = _rev_signs(vedges, lambda tid: not _is_dev(tid))
    rev_sign = {v: _sign(rev_lr[v]) for v in VERDICTS}

    print("=" * 78)
    print("lr_vote — Bayes weighted-vote (judge-C edge verdicts)")
    print("=" * 78)
    print(f"edge verdicts loaded = {len(vedges)}")
    print(f"verdict dist       = {dict(Counter(r['final'] for r in vedges))}")
    print(f"label dist         = {dict(Counter(r['label'] for r in vedges))}")
    print()
    print(f"[E1] dev edge-level accuracy = {e1:.3f}  ({n_correct}/{len(dev_dec)})  baseline 0.5")
    print()
    print(f"[E2] Laplace(+1) LR on dev (fix={Nf}, break={Nb}):")
    print(f"  {'verdict':<10} {'n_fix':>6} {'n_break':>8} {'LR':>8}  95% CI")
    for v in VERDICTS:
        d = lr_tab[v]
        print(f"  {v:<10} {d['n_fix']:>6} {d['n_break']:>8} {d['lr']:>8.3f}  "
              f"[{d['lo']:.3f}, {d['hi']:.3f}]")
    ci_all = all(lr_tab[v]["lo"] <= 1 <= lr_tab[v]["hi"] for v in VERDICTS)
    print(f"  -> all 95% CI contain 1: {ci_all}")
    print()
    print(f"[E3] test (odd) net effect, fit dev -> apply test:")
    print(f"  mode (frozen)   = {test_mode_correct}/{len(test_tids)} test-correct")
    print(f"  final (LR-vote) = {test_final_correct}/{len(test_tids)} test-correct")
    print(f"  net = {net:+d}  (McNemar b={b} R->W, c={c} W->R, p={mcnemar_p(b,c):.4f})")
    print(f"  flips = {flips}")
    print()
    print(f"[E4] reverse-fit LR sign (test -> dev) vs forward (dev -> test):")
    print(f"  forward: {fwd_sign}   reverse: {rev_sign}")
    print()
    print("=" * 78)
    print(f"[HEADLINE] frozen mode accuracy (all 400) = {mode_correct_all}/400 "
          f"= {mode_correct_all / 400 * 100:.1f}%")
    print(f"[HEADLINE] test-only: mode = {test_mode_correct}/200, LR-vote = "
          f"{test_final_correct}/200 (delta {net:+d})")
    print("=" * 78)


if __name__ == "__main__":
    main()