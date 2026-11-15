"""Build the two annotator workbooks from audit/human_audit_20261111/items.csv.
Same items, independent random order per annotator. key.json is never copied into the sheets.
Usage: python3 scripts/human_audit_make_sheets.py"""
import csv, random
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
D='audit/human_audit_20261111/'
import json
TRI=json.load(open(D+'triage.json'))['paths']
rows=[r for r in csv.DictReader(open(D+'items.csv',encoding='utf-8')) if TRI[r['audit_id']]=='P1']  # P1 = direct comparison only
INSTR=['Human audit of answer correctness (path P1: direct comparison) — instructions','',
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
    r=list(rows); random.Random(20261111+seed).shuffle(r)
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
    wb.save(D+f'human_audit_annotator_{who}.xlsx'); print(who,len(r),'items')
