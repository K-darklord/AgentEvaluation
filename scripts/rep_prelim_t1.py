#!/usr/bin/env python3
"""Preliminary read of the second-model replication using ONLY the in-loop exact-match score (T1, `is_correct`)
and gold-free descriptives. NOT the pre-registered read-out (which needs the full T1-T3 sidecar).
Usage: python3 scripts/rep_prelim_t1.py [model_dir_suffix]"""
import json,sys,importlib.util,random
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
M=sys.argv[1] if len(sys.argv)>1 else 'qwen3.8-flash-payg'
def tr(v): return v is True or str(v) in ('True','true','1')
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
D={}
for arm in ('A2','A2P','A3','C2'):
    loop=reco.load_jsonl(Path(f'experiments/rep200_{arm}_{M}/{M}/loop_trajectories.jsonl'))
    st=1 if arm=='A3' else 0; T={}
    for t,lp in loop.items():
        rs=lp['rounds'][st:]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]
        c=[tr(r.get('is_correct')) and r.get('finish_reason')!='length' for r in rs]
        tok=sum(int(r.get('prompt_tokens') or 0)+int(r.get('completion_tokens') or 0) for r in lp['rounds'])
        T[t]=(keys,c,tok,tr(lp['rounds'][0].get('is_correct')))
    D[arm]=T
tasks=sorted(D['C2'])
def lastc(keys,c,k):
    for i in range(len(keys)-1,-1,-1):
        if keys[i]==k: return c[i]
    return False
def sel(keys,c):
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: return 0.0
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; return sum(lastc(keys,c,k) for k in tied)/len(tied)
def ceil(keys,c): return float(any(lastc(keys,c,k) for k in set(keys) if k is not None))
def stay(arm):
    a=[0,0,0,0]
    for t in tasks:
        keys,c,_,_=D[arm][t]
        if arm=='A3':
            for i in range(len(keys)):
                for j in range(len(keys)):
                    if i!=j and keys[i] is not None: a[0 if c[i] else 2]+=1; a[1 if c[i] else 3]+=keys[j]==keys[i]
        else:
            for i in range(len(keys)-1):
                if keys[i] is not None: a[0 if c[i] else 2]+=1; a[1 if c[i] else 3]+=keys[i+1]==keys[i]
    return a[1]/max(a[0],1),a[3]/max(a[2],1)
print(f"model {M}; n={len(tasks)}; greedy exact-match correct {sum(D['A2'][t][3] for t in tasks)}")
S={}
for arm in D:
    S[arm]={'sel':[sel(*D[arm][t][:2]) for t in tasks],'ceil':[ceil(*D[arm][t][:2]) for t in tasks],'fin':[float(D[arm][t][1][-1]) for t in tasks]}
    sc,sw=stay(arm)
    nc=sum(len(set(k for k in D[arm][t][0] if k is not None)) for t in tasks)/len(tasks); nr=sum(len(D[arm][t][0]) for t in tasks)/len(tasks)
    print(f"{arm:4s} exact-only: final {sum(S[arm]['fin']):.0f} selected {sum(S[arm]['sel']):.1f} ceiling {sum(S[arm]['ceil']):.0f} | cand/item {nc:.2f} rounds/item {nr:.2f} tokens {sum(D[arm][t][2] for t in tasks)/1e6:.1f}M | stay|c {sc:.2f} stay|w {sw:.2f} ratio {sc/max(sw,1e-9):.2f}")
def perm(x,y,n=10000):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.4f}"
for a,b in (('C2','A3'),('C2','A2'),('C2','A2P'),('A2','A3'),('A2P','A2')):
    x,y=S[a]['ceil'],S[b]['ceil']; B=sum(1 for i in range(len(tasks)) if x[i] and not y[i]); C=sum(1 for i in range(len(tasks)) if y[i] and not x[i])
    print(f"  {a} vs {b}: selected {perm(S[a]['sel'],S[b]['sel'])} | ceiling {B}/{C} p={mcn(B,C):.4f}")
