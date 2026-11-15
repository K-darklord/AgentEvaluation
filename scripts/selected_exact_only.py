#!/usr/bin/env python3
"""Robustness: selected questions when only exact matches count as correct (grader and adjudication ignored).
Same vote and tie rule as two_model_tables.py. Reads frozen files only. Usage: python3 scripts/selected_exact_only.py"""
import json,sys,importlib.util,random,glob
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','A3','C2')})}
def perm(x,y,n=10000):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(n))
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000)); return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.3f}"
OUT={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; S={}
    for a,d in arms.items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if a=='A3' else 0; v=[]; r0=[]
        for t in sorted(loop):
            lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[a][t][st:]
            cnt=Counter(k for k in keys if k is not None)
            def ok(k):
                i=max(j for j,x in enumerate(keys) if x==k); return bool(sl[i]['c']) and sl[i].get('s')=='t1'
            if cnt:
                top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; v.append(sum(ok(k) for k in tied)/len(tied))
            else: v.append(0.0)
            s0=side[a][t][0]; r0.append(float(bool(s0['c']) and s0.get('s')=='t1'))
        S[a]=v; S['first']=r0
    OUT[m]={a:round(sum(S[a]),1) for a in S}
    print(m,'exact-only: first',sum(S['first']),'selected',{a:round(sum(S[a]),1) for a in arms})
    for x,y in (('C2','A2'),('C2','A2P'),('C2','A3'),('A2','A3')): print('   ',x,'-',y,perm(S[x],S[y]))
    OUT[m]['vec']={a:S[a] for a in arms}
d={}
for x,y in (('C2','A2'),('C2','A2P'),('C2','A3')):
    v=[sum(OUT[m]['vec'][x][i]-OUT[m]['vec'][y][i] for m in OUT) for i in range(400)]
    r=random.Random(1); nz=[q for q in v if q]; obs=sum(v); ge=sum(abs(sum(q if r.random()<.5 else -q for q in nz))>=abs(obs)-1e-9 for _ in range(10000)); bs=sorted(sum(v[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    print('mean per model',x,'-',y,'%+.1f [%+.1f,%+.1f] p=%.4f'%(obs/3,bs[50]/3,bs[1949]/3,(ge+1)/10001))
for m in OUT: OUT[m].pop('vec')
json.dump(OUT,open('experiments/hle400/t3/selected_exact_only.json','w'),indent=1)
