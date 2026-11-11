#!/usr/bin/env python3
"""Compute §5 R1-R4 + §8 descriptives for BOTH models (deepseek, qwen) under the
FROZEN scoring protocol, using the frozen sidecars only.

deepseek: experiments/hle400/t3/is_correct_t3_sidecar_v3.json
qwen:     experiments/hle400/t3/is_correct_t3_sidecar_rep.json

Outputs a printed report + experiments/hle400/t3/replication_results.json.
"""
from __future__ import annotations

import json
import sys
import random
from pathlib import Path
from collections import Counter
from math import comb

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))

from scripts.recompute_evaluator_offline import load_jsonl, freeze_keys  # noqa: E402

# arm -> (exp_dir, model_subdir, start_idx)
# start_idx=1 for A3 (round 0 is the greedy seeding, skipped for sample metrics)
MODELS = {
    "deepseek": {
        "sidecar": ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v3.json",
        "arms": {
            "A":   ("hle400_A",       "deepseek-v4-flash",      0),
            "A2":  ("hle400_A2",      "deepseek-v4-flash",      0),
            "A2P": ("hle400_A2PRIME", "deepseek-v4-flash-payg", 0),
            "A3":  ("hle400_A3",      "deepseek-v4-flash",      1),
            "C2":  ("hle400_C2",      "deepseek-v4-flash-payg", 0),
        },
    },
    "qwen": {
        "sidecar": ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_rep.json",
        "arms": {
            "A":   ("rep200_A_qwen3.8-flash-payg",       "qwen3.8-flash-payg", 0),
            "A2":  ("rep200_A2_qwen3.8-flash-payg",      "qwen3.8-flash-payg", 0),
            "A2P": ("rep200_A2P_qwen3.8-flash-payg",     "qwen3.8-flash-payg", 0),
            "A3":  ("rep200_A3_qwen3.8-flash-payg",      "qwen3.8-flash-payg", 1),
            "C2":  ("rep200_C2_qwen3.8-flash-payg",      "qwen3.8-flash-payg", 0),
        },
    },
}


def mcn(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, sum(comb(n, i) for i in range(0, min(b, c) + 1)) * 2 / 2 ** n)


def last_correct(keys, corr, k):
    for i in range(len(keys) - 1, -1, -1):
        if keys[i] == k:
            return bool(corr[i])
    return False


def ceiling(keys, corr):
    seen = set(k for k in keys if k is not None)
    return float(any(last_correct(keys, corr, k) for k in seen))


def selected(keys, corr):
    cnt = Counter(k for k in keys if k is not None)
    if not cnt:
        return 0.0
    top = max(cnt.values())
    tied = [k for k in cnt if cnt[k] == top]
    return sum(last_correct(keys, corr, k) for k in tied) / len(tied)


def distinct_cands(keys):
    return len(set(k for k in keys if k is not None))


def change_rate(keys):
    num = den = 0
    for i in range(len(keys) - 1):
        if keys[i] is not None and keys[i + 1] is not None:
            den += 1
            num += keys[i] != keys[i + 1]
    return (num, den)


def stay_counts(keys, corr, is_a3):
    # per-item: (n_c, n_cc, n_w, n_ww)  -- committed current, and next==current
    a = [0, 0, 0, 0]
    if is_a3:
        for i in range(len(keys)):
            if keys[i] is None:
                continue
            for j in range(len(keys)):
                if i != j:
                    if corr[i]:
                        a[0] += 1; a[1] += keys[j] == keys[i]
                    else:
                        a[2] += 1; a[3] += keys[j] == keys[i]
    else:
        for i in range(len(keys) - 1):
            if keys[i] is None:
                continue
            if corr[i]:
                a[0] += 1; a[1] += keys[i + 1] == keys[i]
            else:
                a[2] += 1; a[3] += keys[i + 1] == keys[i]
    return a


def a3_agreement_counts(keys):
    num = den = 0
    for i in range(len(keys)):
        for j in range(len(keys)):
            if i != j and keys[i] is not None and keys[j] is not None:
                den += 1
                num += keys[i] == keys[j]
    return (num, den)


def permutation_test(x, y, tasks, rng, n=10000):
    d = [x[t] - y[t] for t in tasks]
    obs = sum(d)
    nz = [v for v in d if v != 0]
    ge = 0
    for _ in range(n):
        s = sum(v if rng.random() < 0.5 else -v for v in nz)
        if abs(s) >= abs(obs) - 1e-9:
            ge += 1
    bs = []
    for _ in range(2000):
        bs.append(sum(d[rng.randrange(len(d))] for _ in range(len(d))))
    bs.sort()
    return obs, (ge + 1) / (n + 1), bs[50], bs[1949]


def load_model(name, cfg):
    side = json.load(open(cfg["sidecar"]))["arms"]
    arms = {}
    for arm, (exp_dir, subdir, st) in cfg["arms"].items():
        traj = load_jsonl(ROOT / "experiments" / exp_dir / subdir / "loop_trajectories.jsonl")
        arms[arm] = {"exp_dir": exp_dir, "st": st, "tasks": {}}
        srows = side.get(arm, {})
        for tid in sorted(traj):
            lp = traj[tid]
            gold = lp.get("gold_answer", "")
            keys = freeze_keys(gold, lp)
            sr = srows.get(tid, [])
            corr = [bool(sr[i].get("c")) if i < len(sr) else False for i in range(len(keys))]
            arms[arm]["tasks"][tid] = {"keys": keys, "corr": corr}
    return arms


def main():
    rng = random.Random(0)
    models = {}
    for name, cfg in MODELS.items():
        models[name] = load_model(name, cfg)

    out = {"models": {}}
    for name in MODELS:
        arms = models[name]
        tasks = sorted(arms["C2"]["tasks"])
        res = {"tasks": tasks, "arms": {}}
        # first-answer accuracy from the A arm (round 0)
        a_arm = arms["A"]["tasks"]
        first_acc = sum(bool(a_arm[t]["corr"][0]) for t in tasks) / len(tasks)
        res["first_acc"] = first_acc

        for arm in ("A2", "A2P", "A3", "C2"):
            st = arms[arm]["st"]
            per = {}
            per_ceil = {}
            per_sel = {}
            per_stay = {}  # tuple
            per_agr = {}   # A3 only
            per_change = {} # (num,den)
            per_distinct = {}
            for t in tasks:
                keys = arms[arm]["tasks"][t]["keys"][st:]
                corr = arms[arm]["tasks"][t]["corr"][st:]
                per_ceil[t] = ceiling(keys, corr)
                per_sel[t] = selected(keys, corr)
                per_distinct[t] = distinct_cands(keys)
                per_change[t] = change_rate(keys)
                per_stay[t] = tuple(stay_counts(keys, corr, is_a3=(arm == "A3")))
                if arm == "A3":
                    per_agr[t] = a3_agreement_counts(keys)
            res["arms"][arm] = {
                "ceil_sum": sum(per_ceil.values()),
                "sel_sum": sum(per_sel.values()),
                "distinct_mean": sum(per_distinct.values()) / len(tasks),
                "change": (sum(a for a, b in per_change.values()), sum(b for a, b in per_change.values())),
                "stay_items": [per_stay[t] for t in tasks],
                "agr": (sum(a for a, b in per_agr.values()), sum(b for a, b in per_agr.values())) if arm == "A3" else None,
                "per_ceil": per_ceil,
                "per_sel": per_sel,
            }

        # repair/damage (§5.3) for loop arms A2/A2P/C2 using round 0 -> round 1
        for arm in ("A2", "A2P", "C2"):
            repair = damage = wrong0 = correct0 = 0
            for t in tasks:
                c0 = arms[arm]["tasks"][t]["corr"][0]
                c1 = arms[arm]["tasks"][t]["corr"][1]
                if not c0:
                    wrong0 += 1
                    if c1:
                        repair += 1
                else:
                    correct0 += 1
                    if not c1:
                        damage += 1
            rr = repair / wrong0 if wrong0 else 0.0
            dr = damage / correct0 if correct0 else 0.0
            ratio = rr / dr if dr else float('inf')
            a_val = first_acc
            thr = a_val / (1 - a_val) if a_val < 1 else float('inf')
            res["arms"][arm]["repair_damage"] = {
                "a": a_val, "repair": repair, "damage": damage,
                "wrong0": wrong0, "correct0": correct0,
                "repair_rate": rr, "damage_rate": dr,
                "ratio": ratio, "threshold": thr,
            }

        out["models"][name] = res

    # ---------------- §5 R1-R4 (qwen replication read-out) ----------------
    # R1: C2 mode vs A3 vote (paired expected score)
    # R2: ceiling C2 vs A2 (exact McNemar)
    # R3: stay ratio C2 vs A2
    # R4: ceiling A2P vs C2
    rep = {}
    for name in MODELS:
        r = out["models"][name]
        tasks = r["tasks"]
        c2m = r["arms"]["C2"]["per_sel"]
        a3v = r["arms"]["A3"]["per_sel"]
        obs, p, lo, hi = permutation_test(c2m, a3v, tasks, rng)
        c2c = r["arms"]["C2"]["per_ceil"]
        a2c = r["arms"]["A2"]["per_ceil"]
        B = sum(1 for t in tasks if c2c[t] and not a2c[t])
        C = sum(1 for t in tasks if a2c[t] and not c2c[t])
        a2pc = r["arms"]["A2P"]["per_ceil"]
        B4 = sum(1 for t in tasks if a2pc[t] and not c2c[t])
        C4 = sum(1 for t in tasks if c2c[t] and not a2pc[t])
        # stay ratios
        def pooled_ratio(items):
            a = [0, 0, 0, 0]
            for it in items:
                for k in range(4):
                    a[k] += it[k]
            sc = a[1] / a[0] if a[0] else 0.0
            sw = a[3] / a[2] if a[2] else 0.0
            return sc / sw if sw else float('inf')
        c2_stay_ratio = pooled_ratio(r["arms"]["C2"]["stay_items"])
        a2_stay_ratio = pooled_ratio(r["arms"]["A2"]["stay_items"])
        rep[name] = {
            "R1": {"c2_mode": sum(c2m.values()), "a3_vote": sum(a3v.values()),
                   "diff": obs, "p": p, "ci": (lo, hi)},
            "R2": {"c2_ceil": sum(c2c.values()), "a2_ceil": sum(a2c.values()), "B": B, "C": C, "p": mcn(B, C)},
            "R3": {"c2_stay_ratio": c2_stay_ratio, "a2_stay_ratio": a2_stay_ratio},
            "R4": {"a2p_ceil": sum(a2pc.values()), "c2_ceil": sum(c2c.values()), "B": B4, "C": C4, "p": mcn(B4, C4)},
        }
    out["R1_R4"] = rep

    json.dump(out, open(ROOT / "experiments/hle400/t3/replication_results.json", "w"), indent=1)

    # ---------------- print ----------------
    for name in MODELS:
        r = out["models"][name]
        print(f"\n===== {name} =====")
        print(f"first-answer acc = {r['first_acc']*400:.1f}/400 ({r['first_acc']:.3f})")
        for arm in ("A2", "A2P", "A3", "C2"):
            a = r["arms"][arm]
            cn, cd = a["change"]
            print(f"  {arm:4s} ceil={a['ceil_sum']:.0f} sel={a['sel_sum']:.1f} "
                  f"distinct={a['distinct_mean']:.2f} change={cn}/{cd} ({cn/max(cd,1):.3f})")
            sc, sw, ratio, lo, hi = pooled_stay(r, arm)
            print(f"        stay_c={sc:.3f} stay_w={sw:.3f} ratio={ratio:.3f} [{lo:.3f},{hi:.3f}]")
            if arm == "A3":
                an, ad = a["agr"]
                print(f"        A3 agreement={an}/{ad} ({an/max(ad,1):.3f})")
            if arm in ("A2", "A2P", "C2"):
                rd = a["repair_damage"]
                print(f"        repair={rd['repair']} damage={rd['damage']} "
                      f"rate_rr={rd['repair_rate']:.3f} rate_dr={rd['damage_rate']:.3f} "
                      f"ratio={rd['ratio']:.3f} thr={rd['threshold']:.3f}")

    print("\n===== R1-R4 =====")
    for name in MODELS:
        r = rep[name]
        print(f"  {name}: R1 C2.mode={r['R1']['c2_mode']:.1f} A3.vote={r['R1']['a3_vote']:.1f} "
              f"diff={r['R1']['diff']:+.1f} p={r['R1']['p']:.4f} CI=[{r['R1']['ci'][0]:+.1f},{r['R1']['ci'][1]:+.1f}]")
        print(f"         R2 C2.ceil={r['R2']['c2_ceil']:.0f} A2.ceil={r['R2']['a2_ceil']:.0f} "
              f"({r['R2']['B']}/{r['R2']['C']}) p={r['R2']['p']:.2g}")
        print(f"         R3 C2.stay={r['R3']['c2_stay_ratio']:.3f} A2.stay={r['R3']['a2_stay_ratio']:.3f}")
        print(f"         R4 A2P.ceil={r['R4']['a2p_ceil']:.0f} C2.ceil={r['R4']['c2_ceil']:.0f} "
              f"({r['R4']['B']}/{r['R4']['C']}) p={r['R4']['p']:.2g}")


def pooled_stay(r, arm):
    items = r["arms"][arm]["stay_items"]
    a = [0, 0, 0, 0]
    for it in items:
        for k in range(4):
            a[k] += it[k]
    sc = a[1] / a[0] if a[0] else 0.0
    sw = a[3] / a[2] if a[2] else 0.0
    obs = sc / sw if sw else float('inf')
    rng = random.Random(1)
    N = len(items)
    bs = []
    for _ in range(2000):
        samp = [items[rng.randrange(N)] for _ in range(N)]
        aa = [0, 0, 0, 0]
        for it in samp:
            for k in range(4):
                aa[k] += it[k]
        ssc = aa[1] / aa[0] if aa[0] else 0.0
        ssw = aa[3] / aa[2] if aa[2] else 0.0
        bs.append(ssc / ssw if ssw else float('inf'))
    bs.sort()
    return sc, sw, obs, bs[50], bs[1949]


if __name__ == "__main__":
    main()
