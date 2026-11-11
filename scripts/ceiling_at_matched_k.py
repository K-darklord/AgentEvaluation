#!/usr/bin/env python3
"""Ceiling at matched candidate count (pass@k over distinct candidates in order of first appearance),
ceiling at matched round, and per-new-candidate hit rate. Reads frozen files only.
Usage: python3 scripts/ceiling_at_matched_k.py"""
import json,sys,importlib.util,random
sys.path.insert(0,'.')
from pathlib import Path
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(__import__('os').environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
ARM={}
for arm,d in (('A2','deepseek-v4-flash'),('A2P','deepseek-v4-flash-payg'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    T={}
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]
        st=1 if arm=='A3' else 0
        keys=keys[st:]; sl=sl[st:]
        cands=[]; 
        for k in keys:
            if k is not None and k not in cands: cands.append(k)
        T[t]=dict(keys=keys,sl=sl,cands=cands,corr=[bool(reco.last_key_correct(keys,sl,k)) for k in cands])
    ARM[arm]=T
tasks=sorted(ARM['C3'])
print("sidecar entry example:",side['C2'][tasks[0]][0])
print("\n=== pass@k over distinct candidates (first-appearance order) ===")
P={}
for arm,T in ARM.items():
    P[arm]={k:[any(T[t]['corr'][:k]) for t in tasks] for k in range(1,11)}
    nc=sum(len(T[t]['cands']) for t in tasks)/400
    print(f"{arm:4s} cand/item {nc:.2f}  "+" ".join(f"k{k}:{sum(P[arm][k])}" for k in range(1,9)))
for k in (2,3,4):
    for a,b in (('C2','A2P'),('C3','A2P'),('C2','A2'),('A2P','A2'),('C2','A3'),('C2','C3')):
        x,y=P[a][k],P[b][k]; B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i])
        print(f"  k={k} {a} vs {b}: {sum(x)} vs {sum(y)}  {B}/{C} p={mcn(B,C):.4f}")
print("\n=== items with >=k distinct candidates ===")
for arm,T in ARM.items(): print(arm," ".join(f">={k}:{sum(len(T[t]['cands'])>=k for t in tasks)}" for k in range(1,8)))
print("\n=== per-candidate hit rate by rank (correct / candidates at that rank) ; and given all earlier candidates wrong ===")
for arm,T in ARM.items():
    out=[]
    for r in range(0,6):
        n=sum(len(T[t]['cands'])>r for t in tasks); c=sum(len(T[t]['cands'])>r and T[t]['corr'][r] for t in tasks)
        n2=sum(len(T[t]['cands'])>r and not any(T[t]['corr'][:r]) for t in tasks); c2=sum(len(T[t]['cands'])>r and not any(T[t]['corr'][:r]) and T[t]['corr'][r] for t in tasks)
        out.append(f"r{r+1}: {c}/{n}={c/max(n,1):.2f} | prevwrong {c2}/{n2}={c2/max(n2,1):.2f}")
    print(arm,"; ".join(out))
print("\n=== restricted to items whose first candidate is wrong: P(new candidate produced), P(correct | rank>=2 candidate), new cands/item ===")
for arm,T in ARM.items():
    W=[t for t in tasks if T[t]['cands'] and not T[t]['corr'][0]]
    ncand=sum(len(T[t]['cands'])-1 for t in W); ncorr=sum(sum(T[t]['corr'][1:]) for t in W); reach=sum(any(T[t]['corr'][1:]) for t in W)
    print(f"{arm}: first-wrong items {len(W)}; extra cands {ncand} ({ncand/len(W):.2f}/item); correct among them {ncorr} ({ncorr/max(ncand,1):.3f}); items reached {reach} ({reach/len(W):.3f}); reached per extra cand {reach/max(ncand,1):.3f}")
print("\n=== ceiling by round (matched number of solver calls) ===")
for arm,T in ARM.items():
    print(arm,[sum(any(x['c'] for x in T[t]['sl'][:r+1]) for t in tasks) for r in range(0,10)])
print("\n=== subsample: draw m distinct candidates uniformly without replacement per item (200 draws) ===")
rng=random.Random(0)
for m in (2,3):
    for arm,T in ARM.items():
        s=0
        for _ in range(200):
            for t in tasks:
                c=T[t]['corr']; idx=rng.sample(range(len(c)),min(m,len(c))) if c else []
                s+=any(c[i] for i in idx)
        print(f"m={m} {arm}: {s/200:.1f}")
print("\n=== M3: ceiling by scoring tier (candidate-level; a candidate counts only if its last occurrence is correct AND accepted by an allowed tier) ===")
from collections import Counter
tiers=Counter(x.get('s') for a in side for t in side[a] for x in side[a][t] if x['c']); print("tiers among correct rounds:",dict(tiers))
def ceil(arm,allowed):
    T=ARM[arm]; out=[]
    for t in tasks:
        keys,sl=T[t]['keys'],T[t]['sl']; ok=False
        for k in T[t]['cands']:
            i=max(j for j,kk in enumerate(keys) if kk==k)
            if sl[i]['c'] and (allowed is None or sl[i].get('s') in allowed): ok=True
        out.append(ok)
    return out
for name,allowed in (('all tiers',None),('t1 exact only',{'t1'})):
    R={a:ceil(a,allowed) for a in ARM}
    print(name," ".join(f"{a}:{sum(R[a])}" for a in ARM))
    for a,b in (('C2','A2P'),('C2','A2'),('C3','A2'),('A2P','A2'),('C2','A3')):
        x,y=R[a],R[b]; B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i])
        print(f"   {a} vs {b}: {B}/{C} p={mcn(B,C):.4f}")
