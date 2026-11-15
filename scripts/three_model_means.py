#!/usr/bin/env python3
"""Mean over the three models of the difference in selected questions (Table "Paired comparisons", last column;
forest figure, "mean of three"). Exploratory summary, not a pre-specified test.
For each question the three per-model differences are summed; the sum is tested with a sign-flip permutation
(10,000 draws) and a question-level bootstrap (2,000 draws); totals are divided by three.
Same vote, tie rule and frozen files as two_model_tables.py / third_model_readout.py.
Usage: python3 scripts/three_model_means.py   (writes experiments/hle400/t3/three_model_means.json)"""
import json,importlib.util,random,glob
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','A3','C2')})}
def selected(side,arm,d):
    """Expected score per question under uniformly random ties; independent samples use samples 1-9."""
    loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if arm=='A3' else 0; v=[]
    for t in sorted(loop):
        lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        if arm=='A3': keys,sl=keys[:9],sl[:9]
        cnt=Counter(k for k in keys if k is not None)
        if not cnt: v.append(0.0); continue
        ok=lambda k: bool(sl[max(j for j,x in enumerate(keys) if x==k)]['c'])
        top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; v.append(sum(ok(k) for k in tied)/len(tied))
    return v
S={m:{a:selected(json.load(open(sp))['arms'],a,d) for a,d in arms.items()} for m,(sp,arms) in CFG.items()}
OUT={'per_model_selected':{m:{a:round(sum(S[m][a]),1) for a in S[m]} for m in S},'mean_of_three':{}}
for m in S: print(m,OUT['per_model_selected'][m])
for x,y in (('C2','A2'),('C2','A2P'),('A2P','A2'),('C2','A3')):
    v=[sum(S[m][x][i]-S[m][y][i] for m in S) for i in range(400)]
    r=random.Random(1); nz=[q for q in v if q]; obs=sum(v)
    ge=sum(abs(sum(q if r.random()<.5 else -q for q in nz))>=abs(obs)-1e-9 for _ in range(10000))
    bs=sorted(sum(v[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    res={'diff':round(obs/3,1),'lo':round(bs[50]/3,1),'hi':round(bs[1949]/3,1),'p':round((ge+1)/10001,4)}
    OUT['mean_of_three'][f'{x}-{y}']=res
    print('mean of three',x,'-',y,'%+.1f [%+.1f,%+.1f] p=%.4f'%(res['diff'],res['lo'],res['hi'],res['p']))
json.dump(OUT,open('experiments/hle400/t3/three_model_means.json','w'),indent=1)
