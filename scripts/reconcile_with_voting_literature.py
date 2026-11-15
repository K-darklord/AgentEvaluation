#!/usr/bin/env python3
"""Exploratory: why does the critique loop out-select a vote over samples here, when other studies find voting ahead of
sequential revision? (a) difficulty strata defined by the OTHER two models' first answers; (b) answer format;
(c) the protocol of those studies replayed on our data: last answer after 3 critique rounds vs a vote over 5 samples.
Reads frozen files only. Usage: python3 scripts/reconcile_with_voting_literature.py"""
import json,importlib.util,glob,random,re
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A3':'experiments/hle400_A3/deepseek-v4-flash','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A3','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A3','C2')})}
def vote(keys,sl):
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: return 0.0
    last={k:i for i,k in enumerate(keys) if k is not None}; top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return sum(bool(sl[last[k]]['c']) for k in tied)/len(tied)
V={}; R0={}; MC={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; V[m]={}
    for a,d in arms.items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl')
        for t in sorted(loop):
            lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[a][t]
            MC[t]=bool(re.fullmatch(r'[A-Z]',str(lp.get('gold_answer','')).strip()))
            if a=='A3':
                K,S=keys[1:],sl[1:]; V[m].setdefault('sc9',{})[t]=vote(K,S); V[m].setdefault('sc5',{})[t]=vote(K[:5],S[:5]); V[m].setdefault('sc3',{})[t]=vote(K[:3],S[:3])
                V[m].setdefault('single',{})[t]=sum(bool(x['c']) for x in S)/len(S)
            else:
                V[m].setdefault(a+'_sel',{})[t]=vote(keys,sl); V[m].setdefault(a+'_last',{})[t]=float(bool(sl[-1]['c']))
                i=min(3,len(sl)-1); V[m].setdefault(a+'_last3',{})[t]=float(bool(sl[i]['c'])); V[m].setdefault(a+'_sel3',{})[t]=vote(keys[:4],sl[:4])
                if a=='A2': R0.setdefault(m,{})[t]=bool(sl[0]['c'])
T=sorted(MC)
def perm(d,n=10000):
    obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(n))
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000)) if d else [0]*2000
    return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.3f}"
print('== whole set (400): critique loop vs samples under different read-outs')
for m in CFG:
    v=V[m]; f=lambda x,y: perm([v[x][t]-v[y][t] for t in T])
    print(m,'| first',sum(R0[m].values()),'single-sample %.1f'%sum(v['single'].values()),'| FC majority - SC9',f('C2_sel','sc9'),'| FC LAST - SC9',f('C2_last','sc9'),'| FC last after 3 rounds - SC5',f('C2_last3','sc5'),'| FC last@3 - SC3',f('C2_last3','sc3'),'| RP last - SC9',f('A2_last','sc9'))
print('\n== by difficulty for the model under test, defined by the other two models: number of them whose FIRST answer is correct')
pool={0:[],1:[],2:[]}; pool_last={0:[],1:[],2:[]}
for m in CFG:
    others=[o for o in CFG if o!=m]; v=V[m]
    for k in (0,1,2):
        S=[t for t in T if sum(R0[o][t] for o in others)==k]
        acc=sum(v['single'][t] for t in S)/len(S)
        d=[v['C2_sel'][t]-v['sc9'][t] for t in S]; dl=[v['C2_last'][t]-v['sc9'][t] for t in S]; pool[k]+=d; pool_last[k]+=dl
        print(f"{m} others-correct={k}: n={len(S)} single-sample acc {acc:.2f} | SC9 {sum(v['sc9'][t] for t in S):.1f} FC majority {sum(v['C2_sel'][t] for t in S):.1f} FC last {sum(v['C2_last'][t] for t in S):.0f} | FC maj - SC9 {perm(d)} | FC last - SC9 {perm(dl)}")
for k in (0,1,2): print(f"POOLED others-correct={k}: n={len(pool[k])} FC maj - SC9 {perm(pool[k])} (per question {sum(pool[k])/len(pool[k]):+.3f}) | FC last - SC9 {perm(pool_last[k])} (per question {sum(pool_last[k])/len(pool_last[k]):+.3f})")
print('\n== by answer format')
for m in CFG:
    v=V[m]
    for name,S in (('single-letter reference',[t for t in T if MC[t]]),('other',[t for t in T if not MC[t]])):
        print(m,name,'n',len(S),'acc %.2f'%(sum(v['single'][t] for t in S)/len(S)),'| FC maj - SC9',perm([v['C2_sel'][t]-v['sc9'][t] for t in S]),'| FC last - SC9',perm([v['C2_last'][t]-v['sc9'][t] for t in S]))
