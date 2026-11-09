#!/usr/bin/env python3
# SUPERSEDED — lock-rule signal study, not reported in the paper. Relocated to
# docs/_deprecated/ during closeout — do not revive.
"""Candidate-level signal study on C3 HLE-400 trajectories (gold-free features vs sidecar-v2 truth).
Which answer should the lock pick? Features per candidate, AUROC for 'candidate correct', and task-level
accuracy of a few FIXED scoring rules vs plain mode. Reported on all 400 and on even/odd halves."""
import json, sys, statistics
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, ".")
from src.score_hle_arms import load_index, read_traj, _key, _mode_idx
ARM = sys.argv[1] if len(sys.argv) > 1 else "C3"
idx = load_index(Path("data/raw/hle/hle_400_new.jsonl"))
side = json.load(open("experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))["arms"][ARM]
tr = read_traj(Path(f"experiments/hle400_{ARM}/deepseek-v4-flash/loop_trajectories.jsonl"))

def auroc(pos, neg):
    if not pos or not neg: return float("nan")
    return sum(1 if p > n else 0.5 if p == n else 0 for p in pos for n in neg) / (len(pos) * len(neg))

rows = []  # (task, cand, features dict, correct)
tasks = {}
for t, task in tr.items():
    rs = task["rounds"]; sl = side[t]; keys = [_key(idx[t], r) for r in rs]
    valid = [i for i, k in enumerate(keys) if k is not None and sl[i]["s"] != "trunc"]
    cnt = Counter(keys[i] for i in valid)
    if not cnt: continue
    n = len(rs)
    feats = {}
    for a in cnt:
        occ = [i for i in valid if keys[i] == a]
        # runs
        runs = []; prev = None
        for i in occ:
            if prev is not None and i == prev + 1: runs[-1] += 1
            else: runs.append(1)
            prev = i
        entries = sum(1 for i in occ if i == 0 or keys[i - 1] != a)
        # critic archetype on this candidate's rounds (critic judges the committed answer of round i)
        arch = Counter((s.get("archetype_name") or "") for i in occ for s in (rs[i].get("critic_direction") or [])[:1])
        f = {
            "count": cnt[a],
            "last": max(occ) / max(1, n - 1),
            "first": min(occ) / max(1, n - 1),
            "max_streak": max(runs),
            "entries": entries,
            "reentries": entries - 1,
            "is_final": 1 if keys[valid[-1]] == a else 0,
            "is_init": 1 if (0 in occ) else 0,
            "held_after_challenge": cnt[a] - entries,         # rounds where it was re-committed right after the critic objected to it
            "mean_reasoning_tok": statistics.mean(rs[i].get("reasoning_tokens", 0) for i in occ),
            "recency_sum": sum(0.8 ** (n - 1 - i) for i in occ),
            "frac_retrieval_abort": arch.get("retrieval-abort", 0) / max(1, sum(arch.values())),
            "frac_truncation": arch.get("procedure truncation / omission", 0) / max(1, sum(arch.values())),
            "carried_any": 1 if any(rs[i].get("carried") for i in occ) else 0,
            "ans_len": len(str(rs[occ[0]]["final_answer"])),
        }
        c = any(sl[i]["c"] for i in occ)
        rows.append((t, a, f, c)); feats[a] = (f, c)
    tasks[t] = feats

multi = [r for r in rows if len(tasks[r[0]]) >= 2]
print(f"{ARM}: tasks {len(tasks)}, multi-candidate tasks {sum(1 for t in tasks if len(tasks[t])>=2)}, candidates in them {len(multi)}, correct candidates {sum(1 for r in multi if r[3])}")
print("\nCandidate-level AUROC (candidate is correct), multi-candidate tasks:")
for k in multi[0][2]:
    pos = [r[2][k] for r in multi if r[3]]; neg = [r[2][k] for r in multi if not r[3]]
    print(f"  {k:24s} {auroc(pos,neg):.3f}")

RULES = {
    "mode (count, tie latest)": lambda f: (f["count"], f["last"]),
    "count + is_final":          lambda f: (f["count"] + f["is_final"], f["last"]),
    "count + reentries":         lambda f: (f["count"] + f["reentries"], f["last"]),
    "count + max_streak":        lambda f: (f["count"] + f["max_streak"], f["last"]),
    "recency_sum":               lambda f: (f["recency_sum"], f["last"]),
    "count - 1*is_init":         lambda f: (f["count"] - f["is_init"], f["last"]),
    "max_streak (tie latest)":   lambda f: (f["max_streak"], f["last"]),
    "last (final answer)":       lambda f: (f["last"],),
    "count + held_after_chal":   lambda f: (f["count"] + f["held_after_challenge"], f["last"]),
    "count, tie -> longest streak": lambda f: (f["count"], f["max_streak"], f["last"]),
    "count, tie -> earliest":    lambda f: (f["count"], -f["first"]),
}
def evaluate(rule, tset):
    ok = 0
    for t in tset:
        feats = tasks[t]
        best = max(feats, key=lambda a: rule(feats[a][0]))
        ok += feats[best][1]
    return ok
allt = list(tasks); even = [t for t in allt if int(t[4:]) % 2 == 0]; odd = [t for t in allt if int(t[4:]) % 2 == 1]
print("\nTask-level accuracy of fixed lock rules (all / even / odd):")
for name, rule in RULES.items():
    print(f"  {name:30s} {evaluate(rule, allt):4d}   {evaluate(rule, even):3d} / {evaluate(rule, odd):3d}")
