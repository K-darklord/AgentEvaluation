#!/usr/bin/env python3
"""Paired tests on per-item expected score (ties randomized analytically -> fractional credit), sign-flip
permutation test (10k) + bootstrap 95% CI of the difference; plain vote and merged-correct vote; ceilings with
exact McNemar; split by answer form. Reads frozen files only. Usage: python3 scripts/paired_expected_score_tests.py"""
import json,sys,importlib.util,random
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(__import__('os').environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
def plain(keys,sl):
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: return 0.0
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return sum(bool(reco.last_key_correct(keys,sl,k)) for k in tied)/len(tied)
def merged(keys,sl):
    m=Counter()
    for k,s in zip(keys,sl):
        if k is not None: m['__C__' if s['c'] else k]+=1
    if not m: return 0.0
    top=max(m.values()); tied=[k for k in m if m[k]==top]
    return ('__C__' in tied)/len(tied)
def ceil(keys,sl):
    seen=set(k for k in keys if k is not None)
    return float(any(reco.last_key_correct(keys,sl,k) for k in seen))
S={}; form={}
rng=random.Random(0)
for arm,d in (('A2','deepseek-v4-flash'),('A2P','deepseek-v4-flash-payg'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    st=1 if arm=='A3' else 0
    S[arm]={'plain':{},'merged':{},'ceil':{},'final':{}}
    if arm=='A3': S['A3ad']={'plain':{},'merged':{}}
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        S[arm]['plain'][t]=plain(keys,sl); S[arm]['merged'][t]=merged(keys,sl); S[arm]['ceil'][t]=ceil(keys,sl); S[arm]['final'][t]=float(bool(sl[-1]['c']))
        g=str(lp.get('gold_answer','')).strip(); form[t]='mc' if (len(g)==1 and g.isalpha()) else 'open'
        if arm=='A3':
            p=m=0.0; idx=list(range(len(keys)))
            for _ in range(200):
                rng.shuffle(idx); cnt=Counter(); stop=len(idx)
                for j,i in enumerate(idx):
                    if keys[i] is not None: cnt[keys[i]]+=1
                    if cnt and max(cnt.values())>=3: stop=j+1; break
                kk=[keys[i] for i in idx[:stop]]; ss=[sl[i] for i in idx[:stop]]
                # correctness of a key judged on full sample set (last occurrence in original order)
                c2=Counter(k for k in kk if k is not None)
                if c2:
                    top=max(c2.values()); tied=[k for k in c2 if c2[k]==top]
                    p+=sum(bool(reco.last_key_correct(keys,sl,k)) for k in tied)/len(tied)
                m+=merged(kk,ss)
            S['A3ad']['plain'][t]=p/200; S['A3ad']['merged'][t]=m/200
tasks=sorted(S['C3']['plain'])
print("answer form:",Counter(form[t] for t in tasks))
def test(x,y,n=10000,seed=1):
    d=[x[t]-y[t] for t in tasks]; obs=sum(d); r=random.Random(seed); ge=0
    nz=[v for v in d if v!=0]
    for _ in range(n):
        s=sum(v if r.random()<0.5 else -v for v in nz)
        if abs(s)>=abs(obs)-1e-9: ge+=1
    bs=[]
    for _ in range(2000):
        bs.append(sum(d[r.randrange(400)] for _ in range(400)))
    bs.sort()
    return obs,(ge+1)/(n+1),bs[50],bs[1949]
for metric in ('plain','merged'):
    print(f"\n=== selected answer, {metric} vote, expected score under random ties ===")
    print("  totals:"," ".join(f"{a}:{sum(S[a][metric].values()):.1f}" for a in ('A2','A2P','A3','A3ad','C3','C2')))
    for a,b in (('C2','A3'),('C2','A3ad'),('C3','A3'),('A2','A3'),('A2P','A3'),('C2','A2'),('C3','A2'),('C2','A2P'),('C2','C3'),('A2P','A2')):
        o,p,lo,hi=test(S[a][metric],S[b][metric]); print(f"  {a} vs {b}: diff {o:+.1f}  perm p={p:.4f}  95% CI [{lo:+.1f},{hi:+.1f}]")
    for f in ('open','mc'):
        print(f"  [{f}] "+" ".join(f"{a}:{sum(v for t,v in S[a][metric].items() if form[t]==f):.1f}" for a in ('A2','A2P','A3','C3','C2')))
print("\n=== ceiling (candidate whose last occurrence is correct), exact McNemar ===")
print("  totals:"," ".join(f"{a}:{int(sum(S[a]['ceil'].values()))}" for a in ('A2','A2P','A3','C3','C2')))
for a,b in (('C3','A2'),('C2','A2'),('C2','C3'),('C3','A3'),('C2','A3'),('C2','A2P'),('C3','A2P'),('A2P','A2')):
    x,y=S[a]['ceil'],S[b]['ceil']; B=sum(1 for t in tasks if x[t] and not y[t]); C=sum(1 for t in tasks if y[t] and not x[t]); print(f"  {a} vs {b}: {B}/{C} p={mcn(B,C):.2g}")
print("\n=== final answer, exact McNemar ===")
print("  totals:"," ".join(f"{a}:{int(sum(S[a]['final'].values()))}" for a in ('A2','A2P','C3','C2')))
for a,b in (('C2','A2'),('C3','A2'),('A2P','A2'),('C2','A2P')):
    x,y=S[a]['final'],S[b]['final']; B=sum(1 for t in tasks if x[t] and not y[t]); C=sum(1 for t in tasks if y[t] and not x[t]); print(f"  {a} vs {b}: {B}/{C} p={mcn(B,C):.3f}")
for a in ('C2','C3','A2','A2P'):
    o,p,lo,hi=test(S[a]['final'],S['A3']['plain']); print(f"  final {a} vs A3 vote: diff {o:+.1f} perm p={p:.4f} CI [{lo:+.1f},{hi:+.1f}]")
json.dump({a:{m:[S[a][m][t] for t in tasks] for m in S[a]} for a in S},open('experiments/hle400/t3/paired_expected_scores_v3.json','w'))
