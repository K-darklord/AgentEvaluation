#!/usr/bin/env python3
"""Exploratory: how well does a model's agreement with itself separate correct from incorrect first answers?
For each question, agreement = number of the nine independent samples (T=0.7) whose answer equals the T=0 first answer.
M1 = area under the ROC curve of agreement as a score for 'the first answer is correct' (0.5 = no information), with a
question-level bootstrap interval (2,000 resamples), and the share of correct first answers by agreement stratum.
Cells: qwen and deepseek on HLE-800, qwen on BBEH-800. A first answer without an answer key has agreement 0.
Usage: python3 scripts/first_answer_confidence.py  (writes experiments/hle400/t3/first_answer_confidence.json)"""
import json,random,sys
sys.path.insert(0,'scripts')
from confirm_common import reco,T,J
def auc(pos,neg):
    if not pos or not neg: return None
    c=sum((p>n)+0.5*(p==n) for p in pos for n in neg); return c/(len(pos)*len(neg))
def cell(path,side,keyf):
    rows=[]
    for l in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); sl=side[d['task_id']]; k=keyf(d,sl); assert len(k)>=10
        rows.append((0 if k[0] is None else sum(x==k[0] for x in k[1:10]),bool(sl[0]['c'])))
    a=auc([s for s,c in rows if c],[s for s,c in rows if not c]); r=random.Random(1); bs=[]
    for _ in range(2000):
        smp=[rows[r.randrange(len(rows))] for _ in rows]; v=auc([s for s,c in smp if c],[s for s,c in smp if not c])
        if v is not None: bs.append(v)
    bs.sort(); out={'n':len(rows),'first_answer_correct':sum(c for _,c in rows),'M1_auroc':round(a,3),'M1_interval':[round(bs[int(.025*len(bs))],3),round(bs[int(.975*len(bs))-1],3)],'strata':{}}
    for lab,lo,hi in (('0-3',0,3),('4-6',4,6),('7-9',7,9)):
        g=[c for s,c in rows if lo<=s<=hi]; out['strata'][lab]={'questions':len(g),'first_answer_correct':sum(g),'share':round(sum(g)/max(1,len(g)),3)}
    return out
hk=lambda d,sl:reco.freeze_keys(d.get('gold_answer',''),d); bk=lambda d,sl:[None if x['k'] is None else json.dumps(x['k'],sort_keys=True) for x in sl]
Q='qwen3.8-flash-payg'; D='deepseek-v4-flash-payg'
O={'qwen, HLE-800':cell(f'experiments/conf_A3_{Q}/{Q}',J('is_correct_t3_sidecar_confirm2.json')['arms']['A3'],hk),
   'deepseek, HLE-800':cell(f'experiments/conf_A3_{D}/{D}',J('is_correct_t3_sidecar_confirm_ds.json')['arms']['A3'],hk),
   'qwen, BBEH-800':cell(f'experiments/b1_A3_hard_{Q}/{Q}',J('bbeh_sidecar.json')['arms']['A3'],bk)}
json.dump(O,open(T+'first_answer_confidence.json','w'),indent=1)
for k,v in O.items(): print(k,v)
