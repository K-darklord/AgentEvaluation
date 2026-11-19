#!/usr/bin/env python3
"""Descriptive: does the critic doubt correct and incorrect answers alike? For every critique-loop round i>=1 whose
critique is a parsed list (no fallback) and whose criticized answer (round i-1) has an answer key, the number of doubts
raised, split by the correctness of the criticized answer. Same definition as scripts/critic_path_diagnostics.py.
Cells: qwen and deepseek on the 800 new HLE questions, qwen on BBEH-hard (800).
Usage: python3 scripts/critic_doubts_by_correctness.py   (writes experiments/hle400/t3/critic_doubts_by_correctness.json)"""
import json,statistics,sys
sys.path.insert(0,'scripts')
from confirm_common import reco,J,T
def cell(path,keyf,side):
    nd={True:[],False:[]}
    for l in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); k=keyf(d); sl=side[d['task_id']]; assert len(sl)==len(d['rounds'])
        for i in range(1,len(k)):
            r=d['rounds'][i]; cd=r.get('critic_direction')
            if isinstance(cd,list) and not r.get('critic_fallback') and k[i-1] is not None: nd[bool(sl[i-1]['c'])].append(len(cd))
    out={}
    for ok in (True,False):
        x=nd[ok]; out['criticized answer correct' if ok else 'criticized answer incorrect']={'rounds':len(x),'mean_doubts':round(statistics.mean(x),2),'share_with_three_or_more':round(sum(v>=3 for v in x)/len(x),3)}
    return out
OUT={}
for m,sf in (('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json'),('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json')):
    OUT[f'{m}, HLE new 800']=cell(f'experiments/conf_C2_{m}/{m}',lambda d:reco.freeze_keys(d.get('gold_answer',''),d),J(sf)['arms']['C2'])
bs=J('bbeh_sidecar.json')['arms']['C2']; Q='qwen3.8-flash-payg'
OUT['qwen3.8-flash-payg, BBEH-hard 800']=cell(f'experiments/b1_C2_hard_{Q}/{Q}',lambda d:[None if x['k'] is None else json.dumps(x['k'],sort_keys=True) for x in bs[d['task_id']]],bs)
json.dump(OUT,open(T+'critic_doubts_by_correctness.json','w'),indent=1)
for k,v in OUT.items(): print(k,v)
