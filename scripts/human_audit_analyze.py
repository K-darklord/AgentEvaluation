#!/usr/bin/env python3
"""Analysis for docs/HUMAN_AUDIT_PLAN.md. Needs openpyxl (run where it is installed) or CSV exports of the
two 'Items' sheets (columns: ID, ..., Judgement) passed as arguments.
Usage: python3 scripts/human_audit_analyze.py [A.xlsx|A.csv] [B.xlsx|B.csv]"""
import json,sys,csv,math
from collections import Counter,defaultdict
D='audit/human_audit_20261111/'
def load(p):
    out={}
    if p.endswith('.csv'):
        for r in csv.DictReader(open(p,encoding='utf-8')): out[r['ID']]=(r.get('Judgement') or '').strip().lower()
    else:
        from openpyxl import load_workbook
        s=load_workbook(p,data_only=True)['Items']
        for row in s.iter_rows(min_row=2,values_only=True):
            if row[0]: out[row[0]]=(str(row[4]) if row[4] else '').strip().lower()
    return out
A=load(sys.argv[1] if len(sys.argv)>1 else D+'human_audit_annotator_A.xlsx'); B=load(sys.argv[2] if len(sys.argv)>2 else D+'human_audit_annotator_B.xlsx')
key=json.load(open(D+'key.json'))['items']
ids=sorted(key); miss=[i for i in ids if not A.get(i) or not B.get(i)]
print('items',len(ids),'unfilled',len(miss))
def kappa(x,y,labels):
    n=len(x); po=sum(a==b for a,b in zip(x,y))/n; pe=sum((x.count(l)/n)*(y.count(l)/n) for l in labels); return po,(po-pe)/(1-pe) if pe<1 else float('nan')
done=[i for i in ids if i not in miss]
a=[A[i] for i in done]; b=[B[i] for i in done]
print('labels A',Counter(a),'B',Counter(b)); print('inter-annotator agreement %.3f kappa %.3f (three labels)'%kappa(a,b,['correct','incorrect','unsure']))
both=[i for i in done if A[i]==B[i] and A[i] in('correct','incorrect')]
print('agreed and decided:',len(both),'of',len(done),'-> remaining need discussion; put resolved labels in',D+'resolved.json as {id: correct|incorrect}')
try: res=json.load(open(D+'resolved.json'))
except Exception: res={}
gold={i:(A[i] if i in both else res.get(i)) for i in done}; gold={i:v for i,v in gold.items() if v in('correct','incorrect')}
def wilson(k,n,z=1.96):
    if n==0: return (float('nan'),)*2
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return (c-h)/d,(c+h)/d
m=[('correct' if key[i]['machine_correct'] else 'incorrect') for i in gold]; h=[gold[i] for i in gold]
print('machine vs human gold: agreement %.3f kappa %.3f (n=%d)'%(*kappa(m,h,['correct','incorrect']),len(gold)))
st=defaultdict(lambda:[0,0])
for i,g in gold.items():
    k=key[i]; s=k['stratum']; st[s][1]+=1; st[s][0]+= (g!=('correct' if k['machine_correct'] else 'incorrect'))
for s in sorted(st):
    e,n=st[s]; lo,hi=wilson(e,n); print(f'  {s:28s} machine errors {e}/{n} = {e/n:.2f}  Wilson95 [{lo:.2f},{hi:.2f}]')
