#!/usr/bin/env python3
"""Sensitivity of E-SC (docs/EQUAL_TOKEN_SAMPLES_SPEC.md) to one property of the frozen scoring: the grader judges the
raw answer text, while votes are counted by answer key, so two spellings of the same key can receive different verdicts.
For every (question, key) with conflicting verdicts across the critique, reassuring, token-yoked and equal-token-sample
runs, the verdict is unified by three rules (majority; correct if any; correct only if all) and E-SC is recomputed.
Descriptive only; the confirmatory result stands as read out. Usage: python3 scripts/grading_key_sensitivity.py
(writes experiments/hle400/t3/grading_key_sensitivity.json)"""
import json,copy,sys
from collections import defaultdict,Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,T,arm,perm,order
OUT={}
for M,files in (('qwen3.8-flash-payg',('is_correct_t3_sidecar_confirm.json','is_correct_t3_sidecar_confirm3.json')),('deepseek-v4-flash-payg',('is_correct_t3_sidecar_confirm_ds.json','is_correct_t3_sidecar_confirm_ds2.json'))):
    L=json.load(open(T+files[0]))['arms']; N=json.load(open(T+files[1]))['arms']
    src={'C2':L['C2'],'A2':L['A2'],'A2PY':L['A2PY'],'A3Y':N['A3Y']}; occ=defaultdict(list); K={}
    for a,side in src.items():
        for l in open(f'experiments/conf_{a}_{M}/{M}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); K[(a,t)]=keys
            for i,k in enumerate(keys):
                if k is not None and not (a=='A3Y' and i==0): occ[(t,k)].append(bool(side[t][i]['c']))
    bad={tk for tk,v in occ.items() if len(set(v))>1}
    def unified(rule):
        out={}
        for a,side in src.items():
            s=copy.deepcopy(side)
            for (aa,t),keys in K.items():
                if aa!=a: continue
                for i,k in enumerate(keys):
                    if (t,k) in bad:
                        v=occ[(t,k)]; s[t][i]['c']=(sum(v)*2>len(v)) if rule=='majority' else any(v) if rule=='correct if any' else all(v)
            out[a]=s
        return out
    def samples_selected(s):
        res={}
        for (aa,t),keys in K.items():
            if aa!='A3Y': continue
            cnt=Counter(k for k in keys[1:] if k is not None)
            def ok(k): return bool(s[t][max(j for j,x in enumerate(keys) if x==k)]['c'])
            if cnt: top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; res[t]=sum(ok(k) for k in tied)/len(tied)
            else: res[t]=0.0
        return res
    o={'answer_keys':len(occ),'keys_with_conflicting_verdicts':len(bad),'questions_affected':len({t for t,_ in bad}),'E-SC':{}}
    for rule in ('as scored','majority','correct if any','correct only if all'):
        s=src if rule=='as scored' else unified(rule)
        C=arm(f'experiments/conf_C2_{M}/{M}',s['C2'],critic=True); Y=samples_selected(s['A3Y']); ts=order(C)
        p=perm([C[t]['selected'] for t in ts],[Y[t] for t in ts])
        o['E-SC'][rule]={'critique':round(sum(C[t]['selected'] for t in ts),1),'equal_token_samples':round(sum(Y.values()),1),**p}
    OUT[M]=o
    print(M,{k:o[k] for k in ('answer_keys','keys_with_conflicting_verdicts','questions_affected')})
    for r,v in o['E-SC'].items(): print(f"   {r:20s} critique {v['critique']:6.1f} samples {v['equal_token_samples']:6.1f} E-SC {v['diff']:+.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
json.dump(OUT,open(T+'grading_key_sensitivity.json','w'),indent=1)
