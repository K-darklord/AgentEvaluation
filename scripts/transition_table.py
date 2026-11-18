#!/usr/bin/env python3
"""Exploratory: round-to-round transitions on the 800 new questions. For consecutive answered rounds: from a correct
answer (kept / changed to an incorrect one), from an incorrect answer (kept / changed to a correct one / changed to
another incorrect one). Usage: python3 scripts/transition_table.py (writes experiments/hle400/t3/transition_table.json)"""
import json,sys
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,J,T
OUT={}
for model,sf in (('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json'),('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json')):
    side=J(sf)['arms']; OUT[model]={}
    print(f"\n{model}\n{'loop':8s} from correct: n  kept  ->wrong | from incorrect: n  kept  ->correct  ->other wrong | per question: correct->wrong events, wrong->correct events")
    for arm in ('A2','A2P','A2PY','C2'):
        c=Counter()
        for l in open(f'experiments/conf_{arm}_{model}/{model}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); k=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[arm][d['task_id']]
            for i in range(len(k)-1):
                if k[i] is None or k[i+1] is None: continue
                a=bool(sl[i]['c']); b=bool(sl[i+1]['c']); same=k[i+1]==k[i]
                c[('C' if a else 'W')+'n']+=1
                if a: c['Ckept' if (same or b) else 'Cwrong']+=1
                else: c['Wkept' if same else ('Wright' if b else 'Wother')]+=1
        o={'from_correct_n':c['Cn'],'correct_kept':round(c['Ckept']/c['Cn'],3),'correct_to_wrong':round(c['Cwrong']/c['Cn'],3),'from_incorrect_n':c['Wn'],'incorrect_kept':round(c['Wkept']/c['Wn'],3),'incorrect_to_correct':round(c['Wright']/c['Wn'],3),'incorrect_to_other_incorrect':round(c['Wother']/c['Wn'],3),'events_correct_to_wrong':c['Cwrong'],'events_wrong_to_correct':c['Wright']}
        OUT[model][arm]=o
        print(f"{arm:8s} {o['from_correct_n']:5d} {o['correct_kept']:.2f} {o['correct_to_wrong']:.2f} | {o['from_incorrect_n']:5d} {o['incorrect_kept']:.2f} {o['incorrect_to_correct']:.3f} {o['incorrect_to_other_incorrect']:.2f} | {c['Cwrong']/800:.2f} {c['Wright']/800:.2f}")
json.dump(OUT,open(T+'transition_table.json','w'),indent=1)
