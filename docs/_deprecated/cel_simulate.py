#!/usr/bin/env python3
# SUPERSEDED — CEL simulation (S0 of the check-execution plan), not reported in the
# paper. Relocated to docs/_deprecated/ during closeout — do not revive.
"""S0 of docs/EVALUATOR_V2_CHECK_EXECUTION_PLAN.md: zero-call simulation of the
Check-Execution Lock (CEL) under perfect / noisy / random judges.

Rules 1-4 are applied exactly as in the plan. The simulated judge returns
`executed` for a candidate's entry move iff the new side is correct (perfect judge),
with accuracy p for noisy judges (verdict flipped with prob 1-p), or coin-flip (random).
Correctness labels come from is_correct_t3_sidecar_v2.json; answer identity from the
scorer's _early_stop_key with the None/truncation rule (same as _mode_idx).
"""
import json, random, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, ".")
from src.score_hle_arms import load_index, read_traj, _key, _mode_idx

ARM = sys.argv[1] if len(sys.argv) > 1 else "C3"
idx = load_index(Path("data/raw/hle/hle_400_new.jsonl"))
side = json.load(open("experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))["arms"][ARM]
tr = read_traj(Path(f"experiments/hle400_{ARM}/deepseek-v4-flash/loop_trajectories.jsonl"))

def task_view(t, task):
    rs = task["rounds"]; sl = side[t]
    keys = [_key(idx[t], r) for r in rs]
    valid = [i for i, k in enumerate(keys) if k is not None and sl[i]["s"] != "trunc"]
    cnt = Counter(keys[i] for i in valid)
    cor = {i: sl[i]["c"] for i in range(len(rs))}
    return keys, valid, cnt, cor

def entry_move(keys, valid, a):
    """last transition into a: (r-1, r) with keys[r]==a and keys[r-1]!=a (r in valid)."""
    for r in reversed(valid):
        if keys[r] == a and r > 0 and keys[r - 1] != a:
            return r
    return None  # a only at round 0 (no entry move)

def run(judge, seed=0, k_rule="plan"):
    rng = random.Random(seed)
    tot = mode_tot = 0; interv = 0; flips_good = flips_bad = 0
    for t, task in tr.items():
        keys, valid, cnt, cor = task_view(t, task)
        mi = _mode_idx(idx[t], task); mode_c = cor.get(mi, False) if mi >= 0 else False; mode_tot += mode_c
        if len(cnt) < 2:
            tot += mode_c; continue
        top = cnt.most_common(); margin = top[0][1] - (top[1][1] if len(top) > 1 else 0)
        if margin >= 2:
            tot += mode_c; continue
        interv += 1
        second = top[1][1]
        K = [a for a, c in cnt.items() if c >= second] if k_rule == "plan" else [a for a, c in cnt.items() if c == top[0][1]]
        last = keys[valid[-1]]
        if cnt[last] == 1 and last not in K: K.append(last)
        score = {}
        for a in K:
            r = entry_move(keys, valid, a)
            adj = 0
            if r is not None:
                truth = cor[r]
                if judge == "perfect": v = truth
                elif judge == "random": v = rng.random() < 0.5
                else: v = truth if rng.random() < judge else (not truth)
                adj = 1 if v else -1
            score[a] = cnt[a] + adj
        best = max(score.values())
        tied = [a for a in K if score[a] == best]
        if len(tied) == 1: lock = tied[0]
        else:
            lock = max(tied, key=lambda a: max(i for i in valid if keys[i] == a))  # latest
        # correctness of the locked answer = correctness of any non-trunc round with that key
        lc = any(cor[i] for i in valid if keys[i] == lock)
        tot += lc
        if lc and not mode_c: flips_good += 1
        if mode_c and not lc: flips_bad += 1
    return tot, mode_tot, interv, flips_good, flips_bad

print(f"arm={ARM}")
tot, mode_tot, interv, g, b = run("perfect")
print(f"  plain mode            = {mode_tot}")
print(f"  CEL perfect judge     = {tot}   (intervened {interv} tasks; +{g} / -{b})")
for p in (0.9, 0.8, 0.7, 0.6):
    vals = [run(p, seed=s) for s in range(20)]
    m = sum(v[0] for v in vals) / len(vals); g = sum(v[3] for v in vals) / len(vals); b = sum(v[4] for v in vals) / len(vals)
    print(f"  CEL judge acc={p:.1f}     = {m:6.1f}  (mean of 20 seeds; +{g:.1f} / -{b:.1f})")
vals = [run("random", seed=s) for s in range(20)]
print(f"  CEL random judge      = {sum(v[0] for v in vals)/len(vals):6.1f}")
tot2, _, interv2, g2, b2 = run("perfect", k_rule="ties_only")
print(f"  CEL perfect, K=ties+final-singleton only = {tot2} (intervened {interv2})")
