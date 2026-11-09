#!/usr/bin/env python3
"""Verifier-regime simulation (§5.6) on frozen trajectories.
A verifier accepts each candidate independently (sensitivity s for correct, specificity p for wrong); selection =
count among accepted (recency tie), fallback mode. Rows: symmetric q, asymmetric (s,p), and a correlated-error
variant where per-item accuracy falls with the number of candidates (q_item = q - 0.05*(n_cand-2), floored at 0.5)
and with difficulty (items the greedy solver got wrong at round 0 get q-0.05)."""
import json,sys,importlib.util,random
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('reco',ROOT/'scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(ROOT/'experiments/hle400/t3/is_correct_t3_sidecar_v2.json'))['arms']
ARMS=[('A2','hle400_A2/deepseek-v4-flash'),('A3','hle400_A3/deepseek-v4-flash'),('C3','hle400_C3/deepseek-v4-flash'),('C2','hle400_C2/deepseek-v4-flash-payg')]
T={}
for arm,d in ARMS:
    loop=reco.load_jsonl(ROOT/'experiments'/d/'loop_trajectories.jsonl'); L=[]
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]
        hard=not sl[0]['c']
        if arm=='A3': keys=keys[1:]; sl=sl[1:]
        cnt=Counter(k for k in keys if k is not None)
        if not cnt: L.append(([],None,hard)); continue
        last={}
        for i,k in enumerate(keys):
            if k is not None: last[k]=i
        cands=[(k,cnt[k],last[k],reco.last_key_correct(keys,sl,k)) for k in cnt]
        L.append((cands,max(cands,key=lambda c:(c[1],c[2])),hard))
    T[arm]=L
random.seed(0)
def realized(arm,s,p,correlated=False,draws=120):
    tot=0.0
    for cands,mode,hard in T[arm]:
        if not cands: continue
        if len(cands)==1: tot+=cands[0][3]; continue
        ss,pp=s,p
        if correlated:
            adj=0.05*(len(cands)-2)+(0.05 if hard else 0); ss=max(0.5,s-adj); pp=max(0.5,p-adj)
        acc=0
        for _ in range(draws):
            accepted=[c for c in cands if (random.random()<ss if c[3] else random.random()<(1-pp))]
            pick=max(accepted,key=lambda c:(c[1],c[2])) if accepted else mode
            acc+=pick[3]
        tot+=acc/draws
    return tot
print("| regime | q / (s,p) | "+" | ".join(a for a,_ in ARMS)+" | C3−A2 | C3−A3 | C2−A3 |"); print("|---"*8+"|")
for q in (0.5,0.6,0.7,0.8,0.9,0.95,1.0):
    r={a:realized(a,q,q) for a,_ in ARMS}
    print(f"| symmetric | {q} | "+" | ".join(f"{r[a]:.1f}" for a,_ in ARMS)+f" | {r['C3']-r['A2']:+.1f} | {r['C3']-r['A3']:+.1f} | {r['C2']-r['A3']:+.1f} |")
for s,p in ((0.7,0.95),(0.8,0.95),(0.9,0.99)):
    r={a:realized(a,s,p) for a,_ in ARMS}
    print(f"| asymmetric | ({s},{p}) | "+" | ".join(f"{r[a]:.1f}" for a,_ in ARMS)+f" | {r['C3']-r['A2']:+.1f} | {r['C3']-r['A3']:+.1f} | {r['C2']-r['A3']:+.1f} |")
for q in (0.7,0.9):
    r={a:realized(a,q,q,correlated=True) for a,_ in ARMS}
    print(f"| correlated | {q} | "+" | ".join(f"{r[a]:.1f}" for a,_ in ARMS)+f" | {r['C3']-r['A2']:+.1f} | {r['C3']-r['A3']:+.1f} | {r['C2']-r['A3']:+.1f} |")
