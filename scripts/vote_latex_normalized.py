#!/usr/bin/env python3
"""Sensitivity analysis (gold-free, deterministic, zero-LLM): vote after stripping LaTeX display wrappers,
\\boxed, spacing macros and whitespace from open-form keys, applied to correct AND incorrect answers in every arm.
Does not change the frozen key. Expected score under random ties; paired sign-flip permutation tests.
Usage: python3 scripts/vote_latex_normalized.py"""
import json,sys,importlib.util,random,re
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(__import__('os').environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
def canon(k):
    if k is None or k[0]!='raw': return k
    s=str(k[1])
    s=re.sub(r'\\boxed\s*\{(.*)\}',r'\1',s,flags=re.S)
    s=re.sub(r'\\(left|right|displaystyle|,|!|;|:|quad|qquad)(?![a-zA-Z])','',s)
    s=re.sub(r'\\text\s*\{([^{}]*)\}',r'\1',s)
    s=s.replace('\\[','').replace('\\]','').replace('\\(','').replace('\\)','').replace('$','')
    s=s.replace('×','\\times').replace('∈','\\in').replace('−','-')
    s=re.sub(r'\s+','',s).strip('.,;:!?')
    return ('raw',s)
def score(keys,sl):
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: return 0.0
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return sum(bool(reco.last_key_correct(keys,sl,k)) for k in tied)/len(tied)
S={}; nmerge={}; mixed={}
for arm,d in (('A2','deepseek-v4-flash'),('A2P','deepseek-v4-flash-payg'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    st=1 if arm=='A3' else 0; S[arm]={'raw':{},'canon':{}}; nm=0; mx=0
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        ck=[canon(k) for k in keys]
        S[arm]['raw'][t]=score(keys,sl); S[arm]['canon'][t]=score(ck,sl)
        a=len(set(k for k in keys if k)); b=len(set(k for k in ck if k)); nm+=a-b
        by={}
        for k,s in zip(ck,sl):
            if k is not None: by.setdefault(k,set()).add(bool(s['c']))
        mx+=sum(len(v)>1 for v in by.values())
    nmerge[arm]=nm; mixed[arm]=mx
tasks=sorted(S['C3']['raw'])
print("distinct keys merged away:",nmerge); print("merged clusters containing both correct and incorrect rounds:",mixed)
print("raw  :"," ".join(f"{a}:{sum(S[a]['raw'].values()):.1f}" for a in S))
print("canon:"," ".join(f"{a}:{sum(S[a]['canon'].values()):.1f}" for a in S))
def test(x,y,n=10000):
    d=[x[t]-y[t] for t in tasks]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    return obs,(ge+1)/(n+1),bs[50],bs[1949]
for a,b in (('C2','A3'),('C3','A3'),('A2','A3'),('C2','A2'),('C3','A2'),('C2','A2P'),('C2','C3')):
    o,p,lo,hi=test(S[a]['canon'],S[b]['canon']); print(f"  canon {a} vs {b}: {o:+.1f} [{lo:+.1f},{hi:+.1f}] p={p:.4f}")
