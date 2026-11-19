"""Second human audit (docs/HUMAN_AUDIT2_PLAN.md, revision 2026-11-19): triage of the 100 items into P1 direct comparison,
P2 symbolic check, P3 discussed adjudication, from items.csv only (key.json not read), and the P1 annotator sheets.
Writes audit/selection_audit_20261117/triage.json and selection_audit_P1_annotator_{A,B}.xlsx (P1 items only, each in its
own random order). Usage: python3 scripts/human_audit2_make_sheets.py"""
import csv,json,random
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
D=Path('audit/selection_audit_20261117'); SEED=20261119
rows=list(csv.DictReader(open(D/'items.csv',encoding='utf-8')))
P2={i:'both sides are mathematical expressions (or Boolean formulas); equality decided by computer algebra / truth table'
    for i in ('S006','S009','S024','S027','S036','S037','S050','S052','S055','S056','S058','S062','S083','S084','S092','S093','S095')}
P3={'S002':'notation: "countable" against omega (cardinal vs ordinal notation)','S060':'notation: "countable" against aleph_0',
    'S046':'notation: 2^(2^omega) against 2^c (cardinal arithmetic)','S051':'option letter (I) against option content (8)',
    'S054':'chemical nomenclature: cyclohexanone against cyclohexan-1-one','S043':'reference writes N, the question and the model write n',
    'S077':'reference writes N, the question and the model write n','S005':'long explanation; must read the question to decide whether its final answer is the reference',
    'S025':'long explanation; must read the question to decide whether its final answer is the reference','S023':'possibly partial answer (preserved, without "become sharper")',
    'S012':'multi-part; formula variables named differently (L, L0 against L, L\')','S065':'multi-part; formula variables named differently (L, L0 against L, L\')',
    'S040':'asymptotic class: Theta(min{15n, M+12n} n) against Theta(n^2) depends on M','S089':'different a, b that give the same sum after an index shift; must read the question',
    'S074':'non-unique answer: a different left coprime factorization (computer algebra: valid; see cas_results.json); must read the question',
    'S076':'non-unique answer: a different left coprime factorization (computer algebra: valid; see cas_results.json); must read the question',
    'S010':'exact expression against a decimal approximation','S013':'numeric tolerance and units: 0.175 m against 14+2sqrt3 cm (=0.1746 m)',
    'S028':'numeric tolerance: 1.384 against 1.38','S075':'numeric tolerance: 1.384 against 1.38','S090':'numeric tolerance: 0.481769 against 0.481',
    'S008':'REF: reference answer is cut off in the dataset ("b = 3"); numeric precision','S099':'REF: reference answer is cut off in the dataset ("\\cdo")'}
paths={r['audit_id']:('P2' if r['audit_id'] in P2 else 'P3' if r['audit_id'] in P3 else 'P1') for r in rows}
json.dump({'decided':'2026-11-19, from items.csv only (key.json not read), before any annotation','counts':{p:sum(v==p for v in paths.values()) for p in ('P1','P2','P3')},
           'paths':paths,'p2_reason':P2,'p3_reason':P3},open(D/'triage.json','w'),ensure_ascii=False,indent=1)
INSTR=['Human audit of answer correctness (second audit, path P1: direct comparison) — instructions','',
'1. For each row, decide whether the MODEL ANSWER gives the same final answer as the REFERENCE ANSWER. Read the QUESTION as far as needed',
'   to know what form of answer it asks for. You are not asked to solve the question.',
'2. Fill the yellow "Judgement" column with one of: correct / incorrect / unsure (use the dropdown).',
'3. "correct" = same final answer. Different notation, formatting, units written differently, or extra explanation are fine.',
'   A numeric answer must equal the reference rounded to the number of significant digits the model answer gives.',
'4. "incorrect" = a different final answer, only part of the required answer, several alternatives without committing to one, or no answer.',
'5. "unsure" = you cannot decide by direct comparison. This is a normal outcome: the item then goes to the discussion round. Say why in "Note".',
'6. If you think the question or the reference answer itself is flawed, still give your judgement and start the Note with REF.',
'7. Allowed: calculator, computer algebra system, looking up a definition. Not allowed: any large language model / AI assistant.',
'8. Work independently. Do not discuss items with the other annotator before both sheets are finished.',
'9. Do not change the ID column or the row order. Save as .xlsx and send the file back.',
'10. This sheet holds only the items that can be compared directly. Other items are checked by computer algebra or in the discussion round.']
p1=[r for r in rows if paths[r['audit_id']]=='P1']
for who,k in (('A',1),('B',2)):
    r=list(p1); random.Random(SEED+k).shuffle(r)
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
    wb.save(D/f'selection_audit_P1_annotator_{who}.xlsx'); print(who,len(r),'items')
print(json.load(open(D/'triage.json'))['counts'])
