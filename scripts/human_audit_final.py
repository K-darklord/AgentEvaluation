#!/usr/bin/env python3
"""Final read-out of the audit of the automatic scoring (docs/HUMAN_AUDIT_PLAN.md): direct comparison (P1),
symbolic check (P2), discussed adjudication (P3). Usage: python3 scripts/human_audit_final.py"""
import json
from openpyxl import load_workbook
from collections import Counter
D='audit/human_audit_20261111/'
key=json.load(open(D+'key.json'))['items']; tri=json.load(open(D+'triage.json'))['paths']; cas={c['id']:c for c in json.load(open(D+'cas_results.json'))}
norm=lambda x:(str(x).strip().lower() if x else '')
def sheet(f,name,col): return {r[0]:norm(r[col]) for r in load_workbook(D+f,data_only=True)[name].iter_rows(min_row=2,values_only=True) if r[0]}
A=sheet('human_audit_annotator_A.xlsx','Items',4); B=sheet('human_audit_annotator_B.xlsx','Items',4); Fd=sheet('discussion_adjudication.xlsx','裁决表',9); Fi=sheet('discussion_adjudication.xlsx','裁决表',5); Sg=sheet('discussion_adjudication.xlsx','裁决表',8)
mach=lambda i:'correct' if key[i]['machine_correct'] else 'incorrect'
final={}; how={}
for i in key:
    if i in Fd: final[i]=Fd[i]; how[i]='discussion'
    elif tri[i]=='P2': final[i]='correct' if cas[i]['equivalent'] else 'incorrect'; how[i]='symbolic'
    else: final[i]=A[i]; how[i]='direct'
assert all(v in ('correct','incorrect') for v in final.values()),Counter(final.values())
print('resolved by',Counter(how.values()))
agree=[i for i in key if final[i]==mach(i)]; print('agree with automatic',len(agree),'/',len(key))
for h in ('direct','symbolic','discussion'): S=[i for i in key if how[i]==h]; print(' ',h,len(S),'agree',sum(final[i]==mach(i) for i in S))
fp=[i for i in key if mach(i)=='correct' and final[i]=='incorrect']; fn=[i for i in key if mach(i)=='incorrect' and final[i]=='correct']
print('automatic accepted, audit incorrect:',len(fp),fp,'| automatic rejected, audit correct:',len(fn),fn)
print('\nby scoring step: (n, automatic accepted, of which audit incorrect, automatic rejected, of which audit correct)')
for tier in ('t1','astra_true','astra_false','adjudicated'):
    S=[i for i in key if key[i]['tier']==tier]; acc=[i for i in S if mach(i)=='correct']; rej=[i for i in S if mach(i)=='incorrect']
    print(' ',tier,len(S),len(acc),sum(i in fp for i in acc),len(rej),sum(i in fn for i in rej))
print('\nautomatic acceptances audited, by model and method (n, audit incorrect)')
c=Counter((key[i]['model'],key[i]['arm']) for i in key if mach(i)=='correct'); f=Counter((key[i]['model'],key[i]['arm']) for i in fp)
for k in sorted(c): print(' ',k,c[k],f[k])
cm=Counter(key[i]['arm'] for i in key if mach(i)=='correct'); fm=Counter(key[i]['arm'] for i in fp); print('  by method',{a:(cm[a],fm[a]) for a in sorted(cm)})
dis=[i for i in Fd]; print('\ndiscussion round: n',len(dis),'| initial judgement recorded',sum(bool(Fi[i]) for i in dis),'| final equals suggestion where suggestion definite',sum(Fd[i]==Sg[i].split()[0] for i in dis if Sg[i].split()[0] in ('correct','incorrect')),'/',sum(Sg[i].split()[0] in ('correct','incorrect') for i in dis),'| suggestion unsure',sum(Sg[i].startswith('unsure') for i in dis))
json.dump({'final':final,'how':how,'false_accept':fp,'false_reject':fn},open(D+'audit_final.json','w'),indent=1)
