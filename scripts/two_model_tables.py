#!/usr/bin/env python3
"""Main tables for both models from frozen sidecars: final / selected (expected score, random ties) / pooled bound /
ceiling / matched-k ceiling / exact-only ceiling / tokens, with paired tests. Reads frozen files only.
Usage: python3 scripts/two_model_tables.py"""
import json,sys,importlib.util,random
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
CFG={'deepseek':dict(side='experiments/hle400/t3/is_correct_t3_sidecar_v3.json',
        arms={'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C3':'experiments/hle400_C3/deepseek-v4-flash','C2':'experiments/hle400_C2/deepseek-v4-flash-payg'}),
     'qwen':dict(side='experiments/hle400/t3/is_correct_t3_sidecar_rep.json',
        arms={a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')})}
def lastc(keys,sl,k): return bool(reco.last_key_correct(keys,sl,k))
def perm(x,y,n=10000):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.4f}"
OUT={}
for model,cfg in CFG.items():
    side=json.load(open(cfg['side']))['arms']; S={}; info={}
    for arm,d in cfg['arms'].items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if arm=='A3' else 0
        tasks=sorted(loop); R={k:[] for k in ('sel','pool','ceil','fin','k2','k3','k4','t1ceil','r0')}; tok=0; nc=0; nr=0; trunc=0
        for t in tasks:
            lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
            assert len(keys)==len(sl),(model,arm,t)
            cnt=Counter(k for k in keys if k is not None)
            if cnt:
                top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; R['sel'].append(sum(lastc(keys,sl,k) for k in tied)/len(tied))
            else: R['sel'].append(0.0)
            m=Counter()
            for k,s in zip(keys,sl):
                if k is not None: m['__C__' if s['c'] else k]+=1
            if m:
                top=max(m.values()); tied=[k for k in m if m[k]==top]; R['pool'].append(('__C__' in tied)/len(tied))
            else: R['pool'].append(0.0)
            cands=[]
            for k in keys:
                if k is not None and k not in cands: cands.append(k)
            cc=[lastc(keys,sl,k) for k in cands]; nc+=len(cands); nr+=len(keys)
            R['ceil'].append(float(any(cc)))
            for kk in (2,3,4): R[f'k{kk}'].append(float(any(cc[:kk])))
            def t1ok(k):
                i=max(j for j,x in enumerate(keys) if x==k); return sl[i]['c'] and sl[i].get('s')=='t1'
            R['t1ceil'].append(float(any(t1ok(k) for k in cands)))
            R['fin'].append(float(bool(sl[-1]['c']))); R['r0'].append(float(bool(side[arm][t][0]['c'])))
            tok+=sum(int(r.get('prompt_tokens') or 0)+int(r.get('completion_tokens') or 0) for r in lp['rounds'])
            trunc+=sum(r.get('finish_reason')=='length' for r in lp['rounds'][st:])
        S[arm]=R; info[arm]=(tok/1e6,nc/len(tasks),nr/len(tasks),trunc)
    OUT[model]=S
    print(f"\n===== {model} (n={len(tasks)}) greedy correct {sum(S['A2']['r0']):.0f}")
    for arm in S:
        R=S[arm]; tk,nc,nr,tr=info[arm]
        print(f"{arm:4s} final {sum(R['fin']):.0f} selected {sum(R['sel']):.1f} pooled {sum(R['pool']):.1f} ceiling {sum(R['ceil']):.0f} | k2 {sum(R['k2']):.0f} k3 {sum(R['k3']):.0f} k4 {sum(R['k4']):.0f} exact-only {sum(R['t1ceil']):.0f} | cand {nc:.2f} rounds {nr:.2f} trunc {tr} solver tokens {tk:.1f}M")
    pairs=[('C2','A3'),('C2','A2'),('C2','A2P'),('A2','A3'),('A2P','A3'),('A2P','A2')]+([('C3','A3'),('C3','A2'),('C2','C3')] if 'C3' in S else [])
    for a,b in pairs:
        def mc(key):
            x,y=S[a][key],S[b][key]; B=sum(1 for i in range(len(x)) if x[i] and not y[i]); C=sum(1 for i in range(len(x)) if y[i] and not x[i]); return f"{B}/{C} p={mcn(B,C):.2g}"
        print(f"  {a} vs {b}: selected {perm(S[a]['sel'],S[b]['sel'])} | pooled {perm(S[a]['pool'],S[b]['pool'])} | ceiling {mc('ceil')} | k2 {mc('k2')} k3 {mc('k3')} | exact-only {mc('t1ceil')} | final {mc('fin')}")
json.dump(OUT,open('experiments/hle400/t3/two_model_scores.json','w'))
