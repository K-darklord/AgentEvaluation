#!/usr/bin/env python3
"""Sample and annotator workbooks for the second human audit (docs/HUMAN_AUDIT2_PLAN.md): grader verdicts behind the
selected counts on the 800 new questions, qwen3.8-flash. Same mode as the first audit (human_audit_sample.py,
human_audit_make_sheets.py): blind to condition, two annotators, independent order, 'unsure' goes to discussion.
Unit: a candidate answer that is the plurality answer of its question (or tied for it) in one loop and was scored by the
grader (not by exact match), taken at its last occurrence. Reads frozen files only.
Writes audit/selection_audit_20261117/{items.csv,key.json,selection_audit_annotator_{A,B}.xlsx}.
Usage: python3 scripts/human_audit2_sample.py"""
import json,importlib.util,random,csv,re
from pathlib import Path
from collections import Counter,defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
SEED=20261117; Q='qwen3.8-flash-payg'; OUT=Path('audit/selection_audit_20261117'); OUT.mkdir(parents=True,exist_ok=True)
side=json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_confirm.json'))['arms']
QUOTA={('C2','astra_true'):34,('A2PY','astra_true'):25,('A2','astra_true'):25,('C2','astra_false'):6,('A2PY','astra_false'):5,('A2','astra_false'):5}
pool=defaultdict(list); QA={}
for arm in ('C2','A2PY','A2'):
    L=reco.load_jsonl(Path(f'experiments/conf_{arm}_{Q}/{Q}')/'loop_trajectories.jsonl')
    for t,lp in L.items():
        QA[t]=(str(lp.get('prompt') or ''),str(lp.get('gold_answer') or ''))
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]; cnt=Counter(k for k in keys if k is not None)
        if not cnt: continue
        top=max(cnt.values())
        for k in [k for k in cnt if cnt[k]==top]:
            i=max(j for j,x in enumerate(keys) if x==k); tier=sl[i].get('s')
            if tier not in ('astra_true','astra_false'): continue
            ans=str(lp['rounds'][i].get('final_answer') or '').strip()
            if ans: pool[(arm,tier)].append(dict(arm=arm,task=t,round=i,tier=tier,machine_correct=bool(sl[i]['c']),answer=ans,n_tied=sum(1 for x in cnt if cnt[x]==top)))
print('pool sizes',{k:len(v) for k,v in sorted(pool.items())})
rng=random.Random(SEED); chosen=[]; seen=set()
for (arm,tier),n in QUOTA.items():
    c=list(pool[(arm,tier)]); rng.shuffle(c); got=0
    for x in c:
        u=(x['task'],re.sub(r'\s+','',x['answer'].lower()))
        if u in seen: continue
        seen.add(u); x=dict(x); x['stratum']=f'{arm}/{tier}'; chosen.append(x); got+=1
        if got==n: break
    assert got==n,(arm,tier,got)
rng.shuffle(chosen); key={}; rows=[]
for n,c in enumerate(chosen,1):
    aid=f'S{n:03d}'; q,g=QA[c['task']]; ans=c['answer'] if len(c['answer'])<=3000 else c['answer'][:3000]+' [... truncated for display]'
    rows.append(dict(audit_id=aid,question=q,reference_answer=g,model_answer=ans)); key[aid]={k:c[k] for k in ('arm','task','round','tier','machine_correct','stratum','n_tied')}
with open(OUT/'items.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['audit_id','question','reference_answer','model_answer']); w.writeheader(); w.writerows(rows)
json.dump({'seed':SEED,'n':len(chosen),'quota':{f'{a}/{t}':n for (a,t),n in QUOTA.items()},'pool':{f'{a}/{t}':len(v) for (a,t),v in pool.items()},'items':key},open(OUT/'key.json','w'),ensure_ascii=False,indent=1)
INSTR=['Human audit of answer correctness (second audit) — instructions','',
'1. For each row, decide whether the MODEL ANSWER gives the same final answer as the REFERENCE ANSWER. Read the QUESTION as far as needed',
'   to know what form of answer it asks for. You are not asked to solve the question.',
'2. Fill the yellow "Judgement" column with one of: correct / incorrect / unsure (use the dropdown).',
'3. "correct" = same final answer. Different notation, formatting, units written differently, or extra explanation are fine.',
'   A numeric answer must agree to the precision the reference gives.',
'4. "incorrect" = a different final answer, only part of the required answer, several alternatives without committing to one, or no answer.',
'5. "unsure" = you cannot decide by direct comparison. This is a normal outcome: the item then goes to the discussion round. Say why in "Note".',
'6. If you think the question or the reference answer itself is flawed, still give your judgement and start the Note with REF.',
'7. Allowed: calculator, computer algebra system, looking up a definition. Not allowed: any large language model / AI assistant.',
'8. Work independently. Do not discuss items with the other annotator before both sheets are finished.',
'9. Do not change the ID column or the row order. Save as .xlsx and send the file back.']
for who,seed in (('A',1),('B',2)):
    r=list(rows); random.Random(SEED+seed).shuffle(r)
    wb=Workbook(); ws=wb.active; ws.title='Items'
    ws.append(['ID','Question','Reference answer','Model answer','Judgement','Note'])
    for x in r: ws.append([x['audit_id'],x['question'],x['reference_answer'],x['model_answer'],None,None])
    f=Font(name='Arial',size=10)
    for row in ws.iter_rows():
        for c in row: c.font=f; c.alignment=Alignment(wrap_text=True,vertical='top')
    for c in ws[1]: c.font=Font(name='Arial',size=10,bold=True); c.fill=PatternFill('solid',fgColor='D9D9D9')
    for i in range(2,len(r)+2): ws.cell(i,5).fill=PatternFill('solid',fgColor='FFFF00')
    for col,w in zip('ABCDEF',(8,90,35,45,14,30)): ws.column_dimensions[col].width=w
    dv=DataValidation(type='list',formula1='"correct,incorrect,unsure"',allow_blank=True); ws.add_data_validation(dv); dv.add(f'E2:E{len(r)+1}')
    ws.freeze_panes='B2'
    wi=wb.create_sheet('Instructions',0)
    for line in INSTR: wi.append([line])
    for row in wi.iter_rows():
        for c in row: c.font=f
    wi['A1'].font=Font(name='Arial',size=12,bold=True); wi.column_dimensions['A'].width=140
    wb.save(OUT/f'selection_audit_annotator_{who}.xlsx'); print(who,len(r),'items')
