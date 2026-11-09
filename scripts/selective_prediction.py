#!/usr/bin/env python3
"""Selective prediction (§5.5): vote margin as abstention signal, per arm, frozen vote/mode semantics.
Loop arms (A2, C3, C2, A2P if present): mode over all rounds, recency tie-break (method as specified) AND
random ties; A3: vote over samples r1..9 with ties randomized (300 draws). Also AUROC (margin -> pick correct)
with bootstrap CI. Reads frozen files only."""
import json,sys,importlib.util,random,statistics
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('reco',ROOT/'scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(ROOT/'experiments/hle400/t3/is_correct_t3_sidecar_v2.json'))['arms']
ARMS=[('A2','hle400_A2/deepseek-v4-flash'),('A3','hle400_A3/deepseek-v4-flash'),('C3','hle400_C3/deepseek-v4-flash'),('C2','hle400_C2/deepseek-v4-flash-payg'),('A2P','hle400_A2PRIME/deepseek-v4-flash-payg')]
_CACHE={}
def _load(arm,d):
    if arm not in _CACHE:
        p=ROOT/'experiments'/d/'loop_trajectories.jsonl'
        if not p.exists() or arm not in side: _CACHE[arm]=None
        else:
            loop=reco.load_jsonl(p); _CACHE[arm]=[(reco.freeze_keys(lp.get('gold_answer',''),lp),side[arm][t]) for t,lp in loop.items()]
    return _CACHE[arm]
def items(arm,d,rng=None,rule='latest'):
    L=_load(arm,d)
    if L is None: return None
    out=[]
    for keys,sl in L:
        if arm=='A3': keys=keys[1:]; sl=sl[1:]
        cnt=Counter(k for k in keys if k is not None)
        if not cnt: out.append((-1,0.0,False)); continue
        last={};first={}
        for i,k in enumerate(keys):
            if k is None: continue
            last[k]=i; first.setdefault(k,i)
        top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
        if rule=='latest': k=max(tied,key=lambda k:last[k])
        elif rule=='earliest': k=min(tied,key=lambda k:first[k])
        else: k=rng.choice(tied)
        c=sorted(cnt.values(),reverse=True); margin=c[0]-(c[1] if len(c)>1 else 0)
        out.append((margin,c[0]/sum(c),reco.last_key_correct(keys,sl,k)))
    return out
def auroc(rows):
    pos=[r[0]+1e-3*r[1] for r in rows if r[2]]; neg=[r[0]+1e-3*r[1] for r in rows if not r[2]]
    return sum(1 if p>q else 0.5 if p==q else 0 for p in pos for q in neg)/max(1,len(pos)*len(neg))
def acc_at(rows,cov):
    rows=sorted(rows,key=lambda r:(r[0],r[1]),reverse=True); k=int(round(cov*len(rows))); return sum(r[2] for r in rows[:k])/k
print("| coverage | "+" | ".join(a for a,_ in ARMS)+" |"); print("|---"*(len(ARMS)+1)+"|")
data={}
for arm,d in ARMS:
    if arm=='A3':
        rng=random.Random(0); draws=[items(arm,d,rng,'random') for _ in range(100)]; data[arm]=draws
    else:
        r=items(arm,d); data[arm]=[r] if r else None
for cov in (1.0,0.8,0.67,0.5,0.33):
    cells=[]
    for arm,_ in ARMS:
        dr=data.get(arm)
        if not dr: cells.append('—'); continue
        cells.append(f"{statistics.mean(acc_at(x,cov) for x in dr):.3f}")
    print(f"| {cov:.2f} | "+" | ".join(cells)+" |")
print("\nAUROC(margin -> selected answer correct), bootstrap 95% CI over items (1000 resamples):")
rng=random.Random(1)
for arm,_ in ARMS:
    dr=data.get(arm)
    if not dr: continue
    base=dr[0]; n=len(base); bs=[]
    for _ in range(1000):
        idx=[rng.randrange(n) for _ in range(n)]; bs.append(auroc([base[i] for i in idx]))
    bs.sort(); print(f"  {arm}: {auroc(base):.3f} [{bs[25]:.3f}, {bs[975]:.3f}]"+("  (A3: first random-tie draw)" if arm=='A3' else ""))
