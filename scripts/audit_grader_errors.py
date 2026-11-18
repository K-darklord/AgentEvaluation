#!/usr/bin/env python3
"""Audit of the grader step behind a score file: every round scored by the grader must have a real verdict in the
verdict cache. A cache entry whose served_model starts with 'ERR' is a failed judge call that was stored as 'incorrect';
such rounds were never judged. Exits with status 1 if any are found.
Usage: python3 scripts/audit_grader_errors.py   (checks the score files of the 800 new questions)"""
import json,sys
from collections import Counter
T='experiments/hle400/t3/'; Q='qwen3.8-flash-payg'; D='deepseek-v4-flash-payg'
cache={}
for l in open(T+'astra_verdicts_confirm.jsonl'):
    d=json.loads(l); cache[(d['task_id'],d['final_answer'])]=(str(d.get('served_model')),str(d.get('c')))
JOBS=[('is_correct_t3_sidecar_confirm.json',{a:f'experiments/conf_{a}_{Q}/{Q}' for a in ('A','A2','A2P','C2','A2PY')}),
      ('is_correct_t3_sidecar_confirm_rerun.json',{'C2':f'experiments/conf_C2r_{Q}/{Q}','A2PY':f'experiments/conf_A2PYr_{Q}/{Q}'}),
      ('is_correct_t3_sidecar_confirm2.json',{'A3':f'experiments/conf_A3_{Q}/{Q}','C2Q':f'experiments/conf_C2Q_{Q}/{Q}','C2QY':f'experiments/yoke_C2QY_confirm_{Q}/{Q}'}),
      ('is_correct_t3_sidecar_confirm_ds.json',{a:f'experiments/conf_{a}_{D}/{D}' for a in ('A','A2','A2P','C2','A3','A2PY')})]
bad=0
for f,arms in JOBS:
    try: side=json.load(open(T+f))['arms']
    except FileNotFoundError: continue
    print(f)
    for a,p in arms.items():
        c=Counter(); qs=set()
        for l in open(p+'/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); t=d['task_id']
            for i,r in enumerate(d['rounds']):
                s=side[a][t][i]
                if s.get('s') in ('astra_true','astra_false'):
                    v=cache.get((t,r.get('final_answer'))); k='missing' if v is None else ('error' if v[0].startswith('ERR') else 'judged'); c[k]+=1
                    if k!='judged': qs.add(t)
                    elif (v[1]=='True')!=bool(s['c']): c['mismatch']+=1
        n=c['error']+c['missing']+c['mismatch']; bad+=n
        print(f"   {a:5s} grader rounds {c['judged']+c['error']+c['missing']:6d}: judged {c['judged']}, never judged {c['error']}, missing {c['missing']}, verdict differs from cache {c['mismatch']}; questions affected {len(qs)}")
print('OK: every grader round has a verdict' if not bad else f'PROBLEM: {bad} grader rounds without a valid verdict')
sys.exit(1 if bad else 0)
