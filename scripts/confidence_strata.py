#!/usr/bin/env python3
"""Exploratory: does the hold of the first answer depend on how strongly the model favours that answer?
Confidence proxy, measured outside the loops: how many of the nine independent samples give the same answer as the T=0
first answer. Strata fixed before computing: 0-3, 4-6, 7-9 samples in agreement. For each loop and stratum, split by
whether the first answer is correct: share of questions on which the loop's plurality answer is still the first answer,
and selected questions. 800 new questions, qwen and deepseek.
Usage: python3 scripts/confidence_strata.py (writes experiments/hle400/t3/confidence_strata.json)"""
import json,sys
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,J,T
OUT={}
for model,sf,a3 in (('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json',J('is_correct_t3_sidecar_confirm2.json')['arms']['A3']),('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json',None)):
    side=J(sf)['arms']; agree={}
    for l in open(f'experiments/conf_A3_{model}/{model}/loop_trajectories.jsonl'):
        if not l.strip(): continue
        d=json.loads(l); k=reco.freeze_keys(d.get('gold_answer',''),d)
        if k[0] is not None and d['rounds'][0].get('finish_reason')!='length': agree[d['task_id']]=sum(x==k[0] for x in k[1:10])
    OUT[model]={'questions with a parsed first answer':len(agree)}
    print(f"\n{model}: agreement of nine samples with the first answer -> n questions per stratum")
    for arm in ('A2','A2PY','C2'):
        g=Counter()
        for l in open(f'experiments/conf_{arm}_{model}/{model}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); t=d['task_id']
            if t not in agree: continue
            k=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[arm][t]; cnt=Counter(x for x in k if x is not None); top=max(cnt.values()); tied=[x for x in cnt if cnt[x]==top]
            ok={x:reco.last_key_correct(k,sl,x) for x in cnt}; sel=sum(ok[x] for x in tied)/len(tied); st='0-3' if agree[t]<=3 else ('4-6' if agree[t]<=6 else '7-9'); fc='first correct' if ok[k[0]] else 'first wrong'
            g[st,fc,'n']+=1; g[st,fc,'kept']+=(k[0] in tied)/len(tied) if k[0] in tied else 0; g[st,fc,'sel']+=sel; g[st,fc,'changed']+=sum(1 for i in range(1,len(k)) if k[i] is not None and k[i-1] is not None and k[i]!=k[i-1]); g[st,fc,'rounds']+=len(k)-1
        OUT[model][arm]={}
        for st in ('0-3','4-6','7-9'):
            for fc in ('first correct','first wrong'):
                n=g[st,fc,'n']; OUT[model][arm][f'{st} | {fc}']={'n':n,'plurality_is_first_answer':round(g[st,fc,'kept']/max(1,n),3),'selected':round(g[st,fc,'sel'],1),'answer_changes_per_round':round(g[st,fc,'changed']/max(1,g[st,fc,'rounds']),3)}
        print(' ',arm,' | '.join(f"{k}: n={v['n']} kept {v['plurality_is_first_answer']:.2f} sel {v['selected']}" for k,v in OUT[model][arm].items()))
json.dump(OUT,open(T+'confidence_strata.json','w'),indent=1)
