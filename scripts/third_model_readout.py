#!/usr/bin/env python3
"""Pre-registered read-out for the third model (docs/THIRD_MODEL_SPEC.md sections 6-7): P1, P2, S1-S5 and descriptives.
Same definitions as two_model_tables.py / persistence_and_settle.py. Reads frozen files only; run once after scoring.
Usage: python3 scripts/third_model_readout.py   (writes experiments/hle400/t3/third_model_readout.json)"""
import json,sys,importlib.util,random,re
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
M='minimax-m2.5'; ARMS=('A2','A2P','A3','C2')
side=json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json'))['arms']
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
def perm(x,y,n=10000):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return dict(diff=round(obs,1),lo=round(bs[50],1),hi=round(bs[1949],1),p=round((ge+1)/(n+1),4))
lastc=lambda keys,sl,k: bool(reco.last_key_correct(keys,sl,k))
S={};D={};PER={}
for arm in ARMS:
    loop=reco.load_jsonl(Path(f'experiments/rep3_{arm}_{M}/{M}/loop_trajectories.jsonl')); st=1 if arm=='A3' else 0
    tasks=sorted(loop); assert len(tasks)==400
    R={k:[] for k in ('sel','pool','ceil','fin','k2','k3','t1ceil','r0','single')}; tok=nc=nr=trunc=bad=0; per=[]; latest=0
    for t in tasks:
        lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        assert len(keys)==len(sl),(arm,t)
        for r in lp['rounds']:
            bad+=bool(r.get('api_failure')) or bool(re.search(r'LLM error|Connection error|timed out|Traceback',r.get('final_answer') or '',re.I))
        cnt=Counter(k for k in keys if k is not None)
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; R['sel'].append(sum(lastc(keys,sl,k) for k in tied)/len(tied))
            last={k:i for i,k in enumerate(keys) if k is not None}; latest+=lastc(keys,sl,max(tied,key=lambda k:last[k]))
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
        for kk in (2,3): R[f'k{kk}'].append(float(any(cc[:kk])))
        def t1ok(k):
            i=max(j for j,x in enumerate(keys) if x==k); return sl[i]['c'] and sl[i].get('s')=='t1'
        R['t1ceil'].append(float(any(t1ok(k) for k in cands)))
        R['fin'].append(float(bool(sl[-1]['c']))); R['r0'].append(float(bool(side[arm][t][0]['c'])))
        R['single'].append(sum(bool(s['c']) for s in sl)/len(sl))
        tok+=sum(int(r.get('prompt_tokens') or 0)+int(r.get('completion_tokens') or 0) for r in lp['rounds'])
        trunc+=sum(r.get('finish_reason')=='length' for r in lp['rounds'][st:])
        a=[0,0,0,0]
        if arm=='A3':
            for i in range(len(keys)):
                for j in range(len(keys)):
                    if i!=j and keys[i] is not None:
                        c=bool(sl[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= keys[j]==keys[i]
        else:
            for i in range(len(keys)-1):
                if keys[i] is None: continue
                c=bool(sl[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= keys[i+1]==keys[i]
        per.append(a)
    S[arm]=R; PER[arm]=per
    D[arm]=dict(final=sum(R['fin']),selected=round(sum(R['sel']),1),pooled=round(sum(R['pool']),1),reach=sum(R['ceil']),reach_k2=sum(R['k2']),reach_k3=sum(R['k3']),reach_exact_only=sum(R['t1ceil']),
                mode_recency=latest,cand_per_q=round(nc/400,2),rounds_per_q=round(nr/400,2),truncated_rounds=trunc,solver_tokens_M=round(tok/1e6,1),failure_rounds=bad,greedy=sum(R['r0']))
rng=random.Random(0)
def ratio(P):
    A=[sum(x[i] for x in P) for i in range(4)]; return (A[1]/A[0])/(A[3]/A[2])
for arm in ARMS:
    bs=sorted(ratio([PER[arm][rng.randrange(400)] for _ in range(400)]) for _ in range(1000)); D[arm]['stay_ratio']=round(ratio(PER[arm]),2); D[arm]['stay_ratio_ci']=[round(bs[25],2),round(bs[974],2)]
def mc(a,b,key):
    x,y=S[a][key],S[b][key]; B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); return dict(b=B,c=C,p=round(mcn(B,C),4))
T={}
T['P1 selected FC-RP']=perm(S['C2']['sel'],S['A2']['sel']);   T['P1 selected FC-RP']['holds']=T['P1 selected FC-RP']['diff']>0 and T['P1 selected FC-RP']['lo']>0
T['P2 selected FC-PP']=perm(S['C2']['sel'],S['A2P']['sel']);  T['P2 selected FC-PP']['holds']=T['P2 selected FC-PP']['diff']>0 and T['P2 selected FC-PP']['lo']>0
x=mc('C2','A2','ceil');  x['holds']=x['b']>x['c'] and x['p']<0.05; T['S1 reach FC vs RP']=x
x=mc('C2','A2P','ceil'); x['holds']=(D['C2']['reach']-D['A2P']['reach']>=15) and x['p']<0.05; T['S2 reach FC vs PP (>=15, p<.05)']=x
x=mc('A2P','A2','ceil'); x['holds']=x['b']>x['c'] and x['p']<0.05; T['S3 reach PP vs RP']=x
T['S4 selected FC-SC9']=perm(S['C2']['sel'],S['A3']['sel']);  T['S4 selected FC-SC9']['holds']=T['S4 selected FC-SC9']['diff']>0 and T['S4 selected FC-SC9']['lo']>0
T['S5 stay ratio FC lower bound > RP estimate']=dict(fc=D['C2']['stay_ratio'],fc_ci=D['C2']['stay_ratio_ci'],rp=D['A2']['stay_ratio'],holds=D['C2']['stay_ratio_ci'][0]>D['A2']['stay_ratio'])
X={}
X['selected PP-RP']=perm(S['A2P']['sel'],S['A2']['sel']); X['selected RP-SC9']=perm(S['A2']['sel'],S['A3']['sel']); X['pooled FC-SC9']=perm(S['C2']['pool'],S['A3']['pool'])
X['reach FC vs SC9']=mc('C2','A3','ceil'); X['final FC vs RP']=mc('C2','A2','fin'); X['final FC vs PP']=mc('C2','A2P','fin')
for k in ('k2','k3','t1ceil'):
    X[f'{k} FC vs RP']=mc('C2','A2',k); X[f'{k} FC vs PP']=mc('C2','A2P',k); X[f'{k} PP vs RP']=mc('A2P','A2',k)
X['single_sample_accuracy_SC']=round(sum(S['A3']['single']),1)
out=dict(model=M,descriptives=D,preregistered=T,other=X); json.dump(out,open('experiments/hle400/t3/third_model_readout.json','w'),indent=1)
print('greedy',D['A2']['greedy'])
for a in ARMS: print(a,D[a])
print(); [print(k,v) for k,v in T.items()]; print(); [print(k,v) for k,v in X.items()]
