#!/usr/bin/env python3
"""Descriptive sensitivity analysis for the 300 s wall-clock timeout (docs: WALL_TIMEOUT_AUDIT_20261120).
A question is 'flagged' in a condition if experiments/hle400/t3/wall_timeout_flags.json marks at least one of its solver
calls as impossible in a single attempt (spec: slowest-5% speed; med: median speed). For each contrast of selected
questions, the difference is recomputed (a) on all 800, (b) on questions unflagged in both conditions, (c) on the rest,
for both definitions. Definitions of selected as in confirm_common.arm / the read-out scripts. Writes
experiments/hle400/t3/wall_timeout_sensitivity.json. Usage: python3 scripts/wall_timeout_sensitivity.py"""
import json,gc,sys
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import *
F=J('wall_timeout_flags.json'); OUT={}
def samplesY(path,sl_all):
    out={}
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=sl_all[t]
        ok=lambda k: bool(sl[max(j for j,x in enumerate(keys) if x==k)]['c'])
        cnt=Counter(k for k in keys[1:] if k is not None); s=0.0
        if cnt: top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; s=sum(ok(k) for k in tied)/len(tied)
        out[t]={'selected':s}
    return out
def bb(a,side,samples):
    Q='qwen3.8-flash-payg'; out={}
    for l in open(f'experiments/b1_{a}_hard_{Q}/{Q}/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); t=d['task_id']; sl=side[t]; keys=[None if x['k'] is None else json.dumps(x['k'],sort_keys=True,ensure_ascii=False) for x in sl]
        ok=lambda k: bool(sl[max(j for j,x in enumerate(keys) if x==k)]['c'])
        cnt=Counter(k for k in keys[(1 if samples else 0):] if k is not None); s=0.0
        if cnt: top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; s=sum(ok(k) for k in tied)/len(tied)
        out[t]={'selected':s}
    return out
def contrast(name,scope,X,Y,ax,ay,ts):
    o={}
    for lab,fk in (('spec','impossible'),('median','impossible_med')):
        fl=lambda t: F[f'{scope}|{ax}'][t][fk] or F[f'{scope}|{ay}'][t][fk]
        clean=[t for t in ts if not fl(t)]; rest=[t for t in ts if fl(t)]
        o[lab]={}
        for sub,q in (('unflagged in both',clean),('flagged in either',rest)):
            if len(q)<20: o[lab][sub]={'questions':len(q)}; continue
            p=perm([X[t]['selected'] for t in q],[Y[t]['selected'] for t in q]); o[lab][sub]={'questions':len(q),'diff':p['diff'],'interval':[p['lo'],p['hi']],'per_100_questions':round(100*p['diff']/len(q),2)}
    p=perm([X[t]['selected'] for t in ts],[Y[t]['selected'] for t in ts]); o['all']={'questions':len(ts),'diff':p['diff'],'interval':[p['lo'],p['hi']],'per_100_questions':round(100*p['diff']/len(ts),2)}
    OUT[name]=o; print(name); print('  all',o['all'])
    for lab in ('spec','median'):
        for sub in o[lab]: print('  ',lab,sub,o[lab][sub])
for key,M,sides in (('qwen','qwen3.8-flash-payg',{'loops':'is_correct_t3_sidecar_confirm.json','new':'is_correct_t3_sidecar_confirm3.json'}),
                    ('deepseek','deepseek-v4-flash-payg',{'loops':'is_correct_t3_sidecar_confirm_ds.json','new':'is_correct_t3_sidecar_confirm_ds2.json'})):
    L=J(sides['loops'])['arms']; N=J(sides['new'])['arms']
    R={'C2':arm(f'experiments/conf_C2_{M}/{M}',L['C2'],critic=True),'A2':arm(f'experiments/conf_A2_{M}/{M}',L['A2']),'A2PY':arm(f'experiments/conf_A2PY_{M}/{M}',L['A2PY'])}; gc.collect()
    Y=samplesY(f'experiments/conf_A3Y_{M}/{M}',N['A3Y']); ts=order(R['C2']); sc=f'HLE-800|{key}'
    contrast(f'{key} HLE-800: critique - equal-token samples',sc,R['C2'],Y,'C2','A3Y',ts)
    contrast(f'{key} HLE-800: critique - token-matched placebo',sc,R['C2'],R['A2PY'],'C2','A2PY',ts)
    contrast(f'{key} HLE-800: critique - reassuring',sc,R['C2'],R['A2'],'C2','A2',ts)
    del R,Y,L,N; gc.collect()
bs=J('bbeh_sidecar.json')['arms']; bn=J('bbeh_sidecar_et.json')['arms']
C=bb('C2',bs['C2'],False); Y=bb('A3Y',bn['A3Y'],True); A2=bb('A2',bs['A2'],False); PY=bb('A2PY',bs['A2PY'],False); ts=sorted(C); sc='BBEH-800|qwen'
contrast('qwen BBEH-800: critique - equal-token samples',sc,C,Y,'C2','A3Y',ts)
contrast('qwen BBEH-800: critique - token-matched placebo',sc,C,PY,'C2','A2PY',ts)
contrast('qwen BBEH-800: critique - reassuring',sc,C,A2,'C2','A2',ts)
json.dump(OUT,open(T+'wall_timeout_sensitivity.json','w'),indent=1)
