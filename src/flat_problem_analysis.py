"""flat_problem_analysis.py — profile the "no-stable-state" (flat) wrong answers.

Answers point 4 of the causal design: (a) what is COMMON to the flat (no-mode)
wrong questions, and (b) once the correct answer IS in the sampled set, can a
gold-free signal identify it (so a cheap verifier only breaks ties, not ranks all).

Per task over the stored C-arm rounds:
  - distinct answer values, each tagged GOOD (correct in >=1 of its rounds)
  - concentration (modal share)
  - for the FLAT-WRONG subset (final wrong AND concentration <= 0.5):
      * does a correct value appear at all?
      * which picker finds it: freq / self-loop / first / last / pi-argmax
      * is the good value in the top-2 by frequency? (=> verifier break-ties only)
      * common features: family, n_uniq, prompt word-count, critic evidence, entropy
"""
from __future__ import annotations
import json, re, math, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

def _norm(s):
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")

def _steady(P):
    n = len(P); pi = [1.0/n]*n
    for _ in range(300):
        npi = [0.0]*n
        for i in range(n):
            for j in range(n):
                npi[j] += pi[i]*P[i][j]
        if max(abs(a-b) for a,b in zip(npi,pi)) < 1e-12: return npi
        pi = npi
    return pi

FILES = [
    ROOT/"experiments/feedback_loop_20261006_173715/deepseek-v4-flash/loop_trajectories.jsonl",
    ROOT/"experiments/feedback_loop_20261006_173715/glm-5.3/loop_trajectories.jsonl",
    ROOT/"experiments/feedback_loop_20261006_173715/qwen3.8-flash/loop_trajectories.jsonl",
    ROOT/"experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
]

def analyze(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    flat = []          # flat-wrong task records
    fam_cnt = defaultdict(lambda: {"flat":0, "flat_good":0})
    for t in rows:
        fam = t.get("family") or "unknown"
        rounds = t.get("rounds", [])
        if not rounds: continue
        seq = [_norm(r.get("final_answer")) for r in rounds]
        corr = [bool(r.get("is_correct")) for r in rounds]
        n = len(seq)
        cnt = Counter(seq)
        conc = cnt.most_common(1)[0][1]/n
        if corr[-1] or conc > 0.5:
            continue
        # flat-wrong
        good_of = {}
        for a,c in zip(seq,corr): good_of[a] = good_of.get(a,False) or c
        good_vals = [a for a,v in good_of.items() if v]
        states = list(cnt.keys())
        idx = {a:i for i,a in enumerate(states)}
        # self-loop rate per state
        M = [[0]*len(states) for _ in states]; out=[0]*len(states)
        for i in range(n-1):
            a,b = idx[seq[i]], idx[seq[i+1]]; M[a][b]+=1; out[a]+=1
        sl = {a: (M[i][i]/out[i] if out[i] else 0) for i,a in enumerate(states)}
        pi = _steady([[M[i][j]/out[i] if out[i] else 0 for j in range(len(states))] for i in range(len(states))])
        pimap = {a: pi[i] for i,a in enumerate(states)}
        # last index per value
        lastidx = {a: max(i for i,x in enumerate(seq) if x==a) for a in states}
        firstidx = {a: min(i for i,x in enumerate(seq) if x==a) for a in states}
        # entropy
        H = -sum((c/n)*math.log2(c/n) for c in cnt.values())
        evs = [r.get("evidence") for r in rounds]
        ev = max((x for x in evs if x is not None), default=None)

        rec = {"family":fam, "n_uniq":len(states), "n":n, "conc":conc, "entropy":H,
               "n_good":len(good_vals),
               "wlen": len(re.findall(r"\S+", t.get("prompt") or "")),
               "evidence": ev}
        if good_vals:
            fam_cnt[fam]["flat_good"] += 1
            freq_pick = cnt.most_common(1)[0][0]
            sl_pick = max(states, key=lambda a: sl[a])
            pi_pick = max(states, key=lambda a: pimap[a])
            rec["freq_hit"] = good_of.get(freq_pick, False)
            rec["selfloop_hit"] = good_of.get(sl_pick, False)
            rec["pi_hit"] = good_of.get(pi_pick, False)
            rec["last_hit"] = good_of.get(seq[-1], False)
            rec["first_hit"] = good_of.get(seq[0], False)
            # is good in top-2 by freq?
            ranked = [a for a,_ in cnt.most_common()]
            rec["good_in_top2"] = any(good_of[a] for a in ranked[:2])
            rec["good_in_top3"] = any(good_of[a] for a in ranked[:3])
            # rank of the first good value by freq
            goodr = [ (i+1) for i,a in enumerate(ranked) if good_of.get(a) ]
            rec["good_freq_rank_min"] = min(goodr) if goodr else None
        else:
            fam_cnt[fam]["flat_good"] += 0
        fam_cnt[fam]["flat"] += 1
        flat.append(rec)

    def mean(x): return sum(x)/len(x) if x else 0.0
    print(f"\n{'='*72}\n{path.relative_to(ROOT)}\n{'='*72}")
    nf = len(flat)
    ng = sum(1 for r in flat if r["n_good"]>0)
    print(f"  flat-wrong tasks = {nf};  with a correct value in the sampled set = {ng} ({ng/nf:.1%})")
    if ng:
        hits = {k: sum(1 for r in flat if r["n_good"]>0 and r[k]) for k in
                ["freq_hit","selfloop_hit","pi_hit","last_hit","first_hit"]}
        print(f"\n  [picker hit-rate on the RESCUABLE flat subset (n={ng})]")
        for k in ["freq_hit","selfloop_hit","pi_hit","last_hit","first_hit"]:
            print(f"    {k:<14} {hits[k]}/{ng} = {hits[k]/ng:.1%}")
        top2 = sum(1 for r in flat if r["n_good"]>0 and r["good_in_top2"])
        top3 = sum(1 for r in flat if r["n_good"]>0 and r["good_in_top3"])
        print(f"    good-value IN top-2 by freq : {top2}/{ng} = {top2/ng:.1%}")
        print(f"    good-value IN top-3 by freq : {top3}/{ng} = {top3/ng:.1%}")
    print(f"\n  [flat-wrong common features: mean]")
    for k in ["n_uniq","n","conc","entropy","wlen","evidence"]:
        vals=[r[k] for r in flat if r[k] is not None]
        print(f"    {k:<10} {mean(vals):.3f}")
    print(f"\n  [flat-wrong by family]")
    for fam in sorted(fam_cnt, key=lambda x:-fam_cnt[x]["flat"]):
        f=fam_cnt[fam]
        print(f"    {fam:<10} flat={f['flat']:>3}  flat_good={f['flat_good']:>3} "
              f"(rescued-good {f['flat_good']/f['flat']:.1%})" if f['flat'] else
              f"    {fam:<10} flat=0")

for p in FILES:
    if p.exists(): analyze(p)
