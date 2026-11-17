#!/usr/bin/env python3
"""Reach of the critique loop against the two placebo loops by subject area (docs/REVIEW_RESPONSE_PLAN.md, part B).
Post hoc, descriptive; no test within a subject. Subject = the `category` field of the benchmark.
For each subject and model: questions reached only by the critique loop / only by the comparison loop.
Reads frozen files only. Usage: python3 scripts/reach_by_subject.py  (writes experiments/hle400/t3/reach_by_subject.json)"""
import json,importlib.util,glob
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','C2')})}
rows=[json.loads(l) for l in open('data/raw/hle/hle_400_new.jsonl')]
order=[c for c,_ in Counter(r['category'] for r in rows).most_common()]
R={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; R[m]={}
    for a,d in arms.items():
        L=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); ts=sorted(L); assert len(ts)==400
        if m=='deepseek' and a=='A2': TS=ts
        R[m][a]=[]
        for t in ts:
            keys=reco.freeze_keys(L[t].get('gold_answer',''),L[t]); R[m][a].append(any(reco.last_key_correct(keys,side[a][t],k) for k in {k for k in keys if k is not None}))
    assert ts==TS
# map task order to subject: tasks are hle_001..hle_400 in the order of the question file
cat=[r['category'] for r in rows]; assert len(cat)==400
OUT={'n':dict(Counter(cat)),'by_subject':{}}
for y in ('A2','A2P'):
    print(f"\ncritique loop vs {y}: reached only by critique / only by {y}   (deepseek, qwen, minimax | sum of three)")
    pos={m:0 for m in R}
    for c in order:
        idx=[i for i in range(400) if cat[i]==c]; cells=[]; sb=sc=0
        for m in R:
            b=sum(R[m]['C2'][i] and not R[m][y][i] for i in idx); k=sum(R[m][y][i] and not R[m]['C2'][i] for i in idx); cells.append([b,k]); sb+=b; sc+=k; pos[m]+= b>k
        OUT['by_subject'].setdefault(c,{})[y]={'per_model':cells,'sum':[sb,sc]}
        print(f"  {c:28s} n={len(idx):3d}  "+"  ".join(f"{b}/{k}" for b,k in cells)+f"  | {sb}/{sc}")
    OUT.setdefault('subjects_with_more_for_critique',{})[y]=pos; print('  subjects (of 8) in which the critique loop reaches more:',pos)
json.dump(OUT,open('experiments/hle400/t3/reach_by_subject.json','w'),indent=1)
