#!/usr/bin/env python3
"""Results on the questions drawn first and last (docs/REVIEW_RESPONSE_PLAN.md, part F). Post hoc, descriptive.
The 400 questions were drawn in three steps by one rule: 50, then 150 (hle_001-hle_200), then 200 (hle_201-hle_400).
Early versions of the loop were run on the first 200 before the protocol was frozen; nothing was run on the
last 200 before that. For each half and model: reached only by the critique loop / only by the comparison loop,
and the difference in selected questions (expected score under random ties).
Reads frozen files only. Usage: python3 scripts/reach_by_draw.py  (writes experiments/hle400/t3/reach_by_draw.json)"""
import json,importlib.util,glob
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','C2')})}
OUT={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; R={}; S={}
    for a,d in arms.items():
        L=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); ts=sorted(L); assert ts[0]=='hle_001' and ts[-1]=='hle_400' and len(ts)==400
        R[a]=[]; S[a]=[]
        for t in ts:
            keys=reco.freeze_keys(L[t].get('gold_answer',''),L[t]); s=side[a][t]; ok={k:reco.last_key_correct(keys,s,k) for k in set(keys) if k is not None}
            R[a].append(any(ok.values())); cnt=Counter(k for k in keys if k is not None)
            if cnt:
                top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; S[a].append(sum(ok[k] for k in tied)/len(tied))
            else: S[a].append(0.0)
    OUT[m]={}
    for name,idx in (('first_200',range(0,200)),('last_200',range(200,400))):
        o={}
        for y in ('A2','A2P'):
            b=sum(R['C2'][i] and not R[y][i] for i in idx); c=sum(R[y][i] and not R['C2'][i] for i in idx)
            o[y]={'reached_only_critique':b,'reached_only_comparison':c,'selected_diff':round(sum(S['C2'][i]-S[y][i] for i in idx),1)}
        o['reached']={a:sum(R[a][i] for i in idx) for a in R}; OUT[m][name]=o
        print(f"{m:8s} {name}: reached {o['reached']} | critique vs A2 {o['A2']['reached_only_critique']}/{o['A2']['reached_only_comparison']} selected {o['A2']['selected_diff']:+.1f} | vs A2P {o['A2P']['reached_only_critique']}/{o['A2P']['reached_only_comparison']} selected {o['A2P']['selected_diff']:+.1f}")
json.dump(OUT,open('experiments/hle400/t3/reach_by_draw.json','w'),indent=1)
