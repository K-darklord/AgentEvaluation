#!/usr/bin/env python3
"""Exploratory: is the lower share of reached questions that are selected under critique a matter of which questions are
reached, or of what the critique does on the same questions? Questions with a wrong first answer (800 new questions),
split by which of the two loops (reassuring, critique) reaches them.
Usage: python3 scripts/conversion_composition.py (writes experiments/hle400/t3/conversion_composition.json)"""
import json,sys
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,J,T
OUT={}
for model,sf in (('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json'),('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json')):
    side=J(sf)['arms']; R={}
    for arm in ('A2','C2'):
        R[arm]={}
        for l in open(f'experiments/conf_{arm}_{model}/{model}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); t=d['task_id']; k=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[arm][t]
            if sl[0]['c'] or d['rounds'][0].get('finish_reason')=='length': continue
            cnt=Counter(x for x in k if x is not None); reached=0; sel=0.0
            if cnt:
                ok={x:reco.last_key_correct(k,sl,x) for x in cnt}; top=max(cnt.values()); tied=[x for x in cnt if cnt[x]==top]; reached=int(any(ok.values())); sel=sum(ok[x] for x in tied)/len(tied)
            R[arm][t]=(reached,sel)
    ts=[t for t in R['A2'] if t in R['C2']]; g={'reached by both':[t for t in ts if R['A2'][t][0] and R['C2'][t][0]],'reached only under critique':[t for t in ts if R['C2'][t][0] and not R['A2'][t][0]],'reached only under reassurance':[t for t in ts if R['A2'][t][0] and not R['C2'][t][0]]}
    OUT[model]={k:{'n':len(v),'selected under reassurance':round(sum(R['A2'][t][1] for t in v),1),'selected under critique':round(sum(R['C2'][t][1] for t in v),1)} for k,v in g.items()}
    print(model); [print('  ',k,v) for k,v in OUT[model].items()]
json.dump(OUT,open(T+'conversion_composition.json','w'),indent=1)
