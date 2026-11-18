#!/usr/bin/env python3
"""Five checks that must pass before any BBEH read-out is computed.
Usage: python3 scripts/audit_bbeh_before_readout.py
Reads the b1 runs and the (possibly regenerated) bbeh_sidecar.json. Prints PASS/FAIL per check.
"""
import json, os, glob, statistics as st
from collections import Counter

BASE='experiments'; SIDE='experiments/hle400/t3/bbeh_sidecar.json'
ARMS=['A','A2','A2P','C2','A3','A2PY']; SPLITS=['hard','easy']
EXPECT={'hard':800,'easy':240}
def tpath(a,s): return f'{BASE}/b1_{a}_{s}_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl'
def toks(r): return (r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0)
def ctoks(r): return (r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0)
def load(p):
    out={}
    for line in open(p,encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); out[d['task_id']]=d
    return out

print('='*72); print('BBEH pre-read-out audit'); print('='*72)
runs={}
for a in ARMS:
    for s in SPLITS:
        p=tpath(a,s)
        if os.path.exists(p): runs[(a,s)]=load(p)
        else: print(f'  [missing run] {a:5} {s:5}  {p}')

print('\n[1] item coverage (expected hard=800, easy=240)')
ok1=True
for s in SPLITS:
    for a in ARMS:
        n=len(runs.get((a,s),{}))
        flag='OK ' if n==EXPECT[s] else 'FAIL'
        if n!=EXPECT[s]: ok1=False
        print(f'  {flag} {a:5} {s:5} {n:4d}/{EXPECT[s]}')

print('\n[2] rounds per item (mean / max), vs HLE reference 4.6-7.3 mean')
ok2=True
for s in SPLITS:
    for a in ARMS:
        if (a,s) not in runs: continue
        r=[len(d['rounds']) for d in runs[(a,s)].values()]
        print(f'  {a:5} {s:5} mean={st.mean(r):5.2f} max={max(r):3d} min={min(r)}')

print('\n[3] token alignment: A2PY / C2 total tokens per item (target 0.9-1.1)')
ok3=True
for s in SPLITS:
    C=runs.get(('C2',s)); Y=runs.get(('A2PY',s))
    if not C or not Y: print(f'  {s}: missing arm'); ok3=False; continue
    ratios=[]
    for t in set(C)&set(Y):
        c=sum(toks(r)+ctoks(r) for r in C[t]['rounds']); y=sum(toks(r)+ctoks(r) for r in Y[t]['rounds'])
        if c: ratios.append(y/c)
    if not ratios: print(f'  {s}: no overlap'); continue
    med=st.median(ratios); frac=sum(0.9<=x<=1.1 for x in ratios)/len(ratios)
    flag='OK ' if 0.85<=med<=1.15 else 'FAIL'
    if flag=='FAIL': ok3=False
    print(f'  {flag} {s:5} median={med:.3f} share_in_[0.9,1.1]={frac:.2f} n={len(ratios)}')

print('\n[4] shared first answer across arms (round 0 identical per item)')
ok4=True
for s in SPLITS:
    base={}
    for a in ARMS:
        if (a,s) not in runs: continue
        for t,d in runs[(a,s)].items():
            k=str(d['rounds'][0].get('committed_answer') or '').strip()
            base.setdefault(t,set()).add(k)
    bad=[t for t,ks in base.items() if len(ks)>1]
    print(f"  {'OK ' if not bad else 'FAIL'} {s:5} items={len(base)} mismatched={len(bad)}" + (f' e.g. {bad[:3]}' if bad else ''))
    if bad: ok4=False

print('\n[5] label coverage in sidecar')
ok5=True
try:
    side=json.load(open(SIDE,encoding='utf-8'))['arms']
    for a in ARMS:
        if a not in side: print(f'  FAIL {a:5} absent from sidecar'); ok5=False; continue
        n=len(side[a]); miss=sum(1 for v in side[a].values() for r in v if r.get('c') is None)
        print(f'  {"OK " if n>0 and miss==0 else "FAIL"} {a:5} items={n:4d} missing_labels={miss}')
        if n!=1040 or miss: ok5=False
except Exception as e:
    print('  FAIL cannot read sidecar:',e); ok5=False

print('\n'+'='*72)
print('RESULT:', 'ALL PASS — a single read-out may proceed' if all([ok1,ok2,ok3,ok4,ok5]) else 'NOT READY — do not read out')
print('='*72)
