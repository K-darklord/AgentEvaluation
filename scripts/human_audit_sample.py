#!/usr/bin/env python3
"""Stratified sample of scored answers for the human audit (docs/HUMAN_AUDIT_PLAN.md). Reads frozen files only.
Unit: a distinct candidate answer (model, condition, item, answer key), scored by its last occurrence.
Writes audit/human_audit_20261111/{items.csv, key.json}. Usage: python3 scripts/human_audit_sample.py"""
import json,sys,importlib.util,random,csv,re
sys.path.insert(0,'.')
from pathlib import Path
from collections import defaultdict,Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
SEED=20261111
CFG={'ds':dict(side='experiments/hle400/t3/is_correct_t3_sidecar_v3.json',arms={'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C3':'experiments/hle400_C3/deepseek-v4-flash','C2':'experiments/hle400_C2/deepseek-v4-flash-payg'}),
     'qw':dict(side='experiments/hle400/t3/is_correct_t3_sidecar_rep.json',arms={a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')})}
pool=defaultdict(list); Q={}
for m,cfg in CFG.items():
    side=json.load(open(cfg['side']))['arms']
    for arm,d in cfg['arms'].items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if arm=='A3' else 0
        for t,lp in loop.items():
            Q[t]=(str(lp.get('prompt') or ''),str(lp.get('gold_answer') or ''))
            keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]
            last={}
            for i in range(st,len(keys)):
                if keys[i] is not None: last[keys[i]]=i
            for k,i in last.items():
                s=sl[i]; tier=s.get('s')
                if tier=='trunc': continue
                ans=str(lp['rounds'][i].get('final_answer') or '').strip()
                if not ans: continue
                pool[(m,arm,tier)].append(dict(model=m,arm=arm,task=t,round=i,tier=tier,machine_correct=bool(s['c']),answer=ans,key=json.dumps(k,ensure_ascii=False)))
print({k:len(v) for k,v in sorted(pool.items())})
rng=random.Random(SEED); chosen=[]; seen=set(); per_task=Counter()
def draw(cands,n,stratum):
    cands=list(cands); rng.shuffle(cands); got=0
    for c in cands:
        u=(c['model'],c['task'],re.sub(r'\s+','',c['answer'].lower()))
        if u in seen or per_task[(c['model'],c['task'])]>=2: continue
        seen.add(u); per_task[(c['model'],c['task'])]+=1; c=dict(c); c['stratum']=stratum; chosen.append(c); got+=1
        if got==n: break
    if got<n: print('WARNING short stratum',stratum,got,n)
    return got
for arm in ('A2','A2P','A3','C3','C2'): draw(pool[('ds',arm,'astra_true')],20,f'ds/{arm}/model_accepted')
for arm in ('A2','A2P','A3','C3','C2'): draw(pool[('ds',arm,'astra_false')],8,f'ds/{arm}/model_rejected')
g=draw([c for a in ('A2','A2P','A3','C3','C2') for c in pool[('ds',a,'adjudicated')]],15,'ds/any/adjudicated')
PENDING_ADJ=15-g
draw([c for a in ('A2','A2P','A3','C3','C2') for c in pool[('ds',a,'t1')]],10,'ds/any/exact_match')
for arm in ('A2','A2P','A3','C2'): draw(pool[('qw',arm,'astra_true')],5,f'qw/{arm}/model_accepted')
draw([c for a in ('A2','A2P','A3','C2') for c in pool[('qw',a,'astra_false')]],15,'qw/any/model_rejected')
if PENDING_ADJ: draw([c for a in ('A2','A2P','A3','C2') for c in pool[('qw',a,'adjudicated')]],PENDING_ADJ,'qw/any/adjudicated')
rng.shuffle(chosen)
out=Path('audit/human_audit_20261111'); key={}
with open(out/'items.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['audit_id','question','reference_answer','model_answer'])
    for n,c in enumerate(chosen,1):
        aid=f'H{n:03d}'; q,g=Q[c['task']]
        ans=c['answer'] if len(c['answer'])<=3000 else c['answer'][:3000]+' [... truncated for display]'
        w.writerow([aid,q,g,ans]); key[aid]={k:c[k] for k in ('model','arm','task','round','tier','machine_correct','stratum','key')}
json.dump({'seed':SEED,'n':len(chosen),'items':key},open(out/'key.json','w'),ensure_ascii=False,indent=1)
print(len(chosen),'items;',Counter(c['stratum'] for c in chosen)); print('longest question chars',max(len(Q[c['task']][0]) for c in chosen),'longest answer',max(len(c['answer']) for c in chosen))
