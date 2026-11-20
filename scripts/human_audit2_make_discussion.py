"""Second human audit, path P3 (docs/HUMAN_AUDIT2_PLAN.md): build the discussion workbook. Reads items.csv, triage.json and
the P1 sheet (annotator and reviewer labels). Does not read key.json. The notes are an assistant's reading, offered as
arguments; the adjudicators decide, after each has written an initial judgement.
Usage: python3 scripts/human_audit2_make_discussion.py"""
import csv,json
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
D='audit/selection_audit_20261117/'
R={r['audit_id']:r for r in csv.DictReader(open(D+'items.csv',encoding='utf-8'))}; tri=json.load(open(D+'triage.json'))
P1={}
for r in load_workbook(D+'selection_audit_P1.xlsx',data_only=True)['Items'].iter_rows(min_row=2,values_only=True):
    if r[0]: P1[r[0]]=((str(r[4]).strip().lower() if r[4] else ''),(str(r[6]).strip().lower() if r[6] else ''))
norm=lambda x:{'c':'correct','yes':None}.get(x,x)
disagree=[i for i,(a,b) in P1.items() if 'unsure' in (a,norm(b)) or (norm(b) not in (None,a))]
# (id, group, point to settle, assistant's reading, suggested label or '')
N=[
('S002','记号','参考 countable；模型 ω。','题目问的是 weight（一个基数）。ω 作为基数就是 ℵ₀，即可数。','correct'),
('S060','记号','参考 countable；模型 ℵ₀。','ℵ₀ 即可数无穷基数。','correct'),
('S046','记号','参考 2^(2^ω)；模型 2^𝔠。','𝔠 = 2^ω（=2^ℵ₀），两式是同一个基数。','correct'),
('S051','选项字母对内容','参考 I；模型 8。','题目选项 I 的内容是 8。模型给出的是该选项的内容。','correct'),
('S054','命名法','2-(3-oxopentyl)cyclohexanone 对 …cyclohexan-1-one。','同一化合物的两种 IUPAC 写法（位次 1 可省）。','correct'),
('S043','变量名','参考 p(1-p)/(1+N-p)；模型 p(1-p)/(n+1-p)。','题目里伞的数目记作 n；参考答案写成 N。式子相同。','correct'),
('S077','变量名','同 S043（同一题的另一条答案）。','同上。','correct'),
('S012','变量名','八个小问；公式里 L, L0 对 L\', L 等。','前五问逐项相同；三条公式只是记号不同（L=L0√(1+v²)；Δt=Δt0/√(1+v²)；(u+v)/(1−uv)）。','correct'),
('S065','变量名','同 S012（同一题的另一条答案）。','同上。','correct'),
('S005','长答案','参考：Bacillus subtilis was non-viable。模型给出一段解释。','解释的核心是质控菌株经多次传代已无活性，"无生长"是假阴性——即参考答案；同时提到抗生素被高压灭菌破坏（题目背景）。','correct'),
('S025','长答案','同一题的另一条答案。','先讲氯霉素被破坏，再明确说质控的 B. subtilis 已无活性、无生长是假阴性，并把实验室的错误归于此。包含参考答案；是否因先讲了另一原因而算"多个答案"，请裁决。','correct'),
('S023','答案不完整','参考：Edges are preserved and become sharper；模型：They are preserved。','只给出一半（保留），没有"变锐"。按说明第 4 条，只给出所要求答案的一部分算 incorrect。','incorrect'),
('S040','渐近类','参考 Θ(min{15n, M+12n}·n)；模型 Θ(n²)。','min{15n, M+12n} 介于 12n 与 15n 之间，所以参考式恒为 Θ(n²)，两者在渐近意义上相同。但题目要的是"exact time complexity"，参考答案保留了 M；是否接受化简后的写法，请裁决。',''),
('S089','等值但不同的填法','参考 a: n+1−m, b: m−1；模型 a = n−m, b = m。','对参考式作代换 m→m+1，Σ_{m=1}^{n}(n+1−m)²(m−1) = Σ_{m=1}^{n}(n−m)²·m（m=n 项为零），两种填法给出同一个和。题目问"a、b 应填什么"，填法不唯一；是否接受，请裁决。',''),
('S074','答案不唯一','左互质分解；模型给出另一组 D、N。','代数系统核验：D⁻¹N = H 成立，且 [D N] 的 2×2 子式无公共根（左互质）。左互质分解不唯一（可左乘单模矩阵）。参考答案本身也通过同样的核验。','correct'),
('S076','答案不唯一','同一题的另一条答案。','同上，核验通过。','correct'),
('S010','数值','参考 4(10²⁰−0.5)/(10⁴⁰+1)；模型 4×10⁻²⁰。','参考值 = 4×10⁻²⁰·(1−5×10⁻²¹)/(1+10⁻⁴⁰)，与 4×10⁻²⁰ 的相对差约 5×10⁻²¹。按数值规则（答案等于参考值按答案自身有效位数四舍五入）相符；但题目可能要精确式，请裁决。',''),
('S013','数值与单位','参考 0.175 m；模型 14+2√3 cm。','14+2√3 = 17.464 cm = 0.17464 m，四舍五入到三位是 0.175 m。模型给的是精确式，参考是其三位近似。','correct'),
('S028','数值','参考 1.384；模型 a₃ ≈ 1.38 m/s²。','1.384 按答案的三位有效数字四舍五入为 1.38。按数值规则相符。','correct'),
('S075','数值','参考 1.384；模型 1.38。','同上。','correct'),
('S090','数值','参考 0.481769；模型 0.481。','0.481769 四舍五入到三位是 0.482，模型写 0.481（截断）。按数值规则不符。','incorrect'),
('S008','REF：参考答案被截断','参考在数据集中止于 "a = 4.7 Å b = 3"；模型：CuO, monoclinic, C2/c, a = 4.6837, b = 3.4226, c = 5.1288, β = 99.54°。','物相、晶系、空间群一致；a 四舍五入为 4.7，b 以 3 开头。可比对的部分全部相符。Note 请以 REF 开头。','correct'),
('S099','REF：参考答案被截断','参考止于 "n·m^{k−1} − m^{k−2}·(k−1)·"；模型 M^{K−1}(N − (K−1)(M+1)/2)。','模型式展开为 N·M^{K−1} − M^{K−2}·(K−1)·M(M+1)/2，前两个因子与参考可见部分一致，被截掉的因子无法核对。Note 请以 REF 开头。',''),
('S100','P1 中 unsure','参考 [1/3, √2/4)；模型 1/3 ≤ k < √2/4。','区间与不等式是同一集合。','correct'),
('S061','P1 中两人不同','参考 y² = a x² + a² + a + 9（a 任意实数）；模型 y² = C x² + C² + C + 9。','任意常数的名字不同（a 对 C），式子相同。','correct'),
('S035','P1 中两人不同','参考 Z+Z+Z+Z+Z；模型 …= Z⁵。','五个 Z 的直和即 Z⁵。','correct'),
]
ids=[n[0] for n in N]; want=sorted([i for i,p in tri['paths'].items() if p=='P3']+disagree)
assert sorted(ids)==want,(set(want)-set(ids),set(ids)-set(want))
wb=Workbook(); ws=wb.active; ws.title='裁决表'
ws.append(['ID','类别','Question','Reference answer','Model answer','P1 标注人','P1 复核人','要裁决的点','助手的阅读（仅供参考）','助手建议','标注人初判（必填，先于讨论）','复核人初判（必填，先于讨论）','讨论后的最终裁决','备注（参考答案有问题以 REF 开头）'])
for i,g,q,a,s in N:
    r=R[i]; p=P1.get(i,('','')); ws.append([i,g,r['question'],r['reference_answer'],r['model_answer'],p[0],norm(p[1]) or '',q,a,s,None,None,None,None])
f=Font(name='Arial',size=10)
for row in ws.iter_rows():
    for c in row: c.font=f; c.alignment=Alignment(wrap_text=True,vertical='top')
for c in ws[1]: c.font=Font(name='Arial',size=10,bold=True); c.fill=PatternFill('solid',fgColor='D9D9D9')
n=len(N)
for i in range(2,n+2):
    for col in (11,12,13): ws.cell(i,col).fill=PatternFill('solid',fgColor='FFFF00')
for col,w in zip('ABCDEFGHIJKLMN',(7,14,70,30,40,10,10,34,48,10,14,14,14,28)): ws.column_dimensions[col].width=w
dv=DataValidation(type='list',formula1='"correct,incorrect"',allow_blank=True); ws.add_data_validation(dv)
for col in 'KLM': dv.add(f'{col}2:{col}{n+1}')
ws.freeze_panes='C2'
wi=wb.create_sheet('说明',0)
for line in ['第二次人工核对：讨论裁决（P3）——说明','',
 '1. 每一行先由标注人、复核人各自填写"初判"（correct / incorrect），互不商量，也不要先看"助手的阅读"与"助手建议"两栏（可先把这两列隐藏）。',
 '2. 两人都填完初判后，再一起讨论，可以参考助手的阅读；在"讨论后的最终裁决"一栏填 correct 或 incorrect。',
 '3. 助手的阅读由 AI 助手在不知道自动判分的情况下写成（未打开 key.json），只是论据，不是结论；不同意就按你们的判断填。',
 '4. 数值题统一规则：答案须等于参考值按答案自身有效位数四舍五入后的值。',
 '5. 认为题目或参考答案本身有问题的，备注以 REF 开头。',
 '6. 另请确认 P2 的七处转写（见 docs/HUMAN_AUDIT2_PLAN.md"分流结果与文件"一节），在本页下方写"已确认"或指出问题。','',
 'P2 转写确认：']: wi.append([line])
for row in wi.iter_rows():
    for c in row: c.font=f
wi['A1'].font=Font(name='Arial',size=12,bold=True); wi.column_dimensions['A'].width=150
wb.save(D+'selection_audit_P3_discussion.xlsx'); print('P3 items',n,'| from P1:',disagree)
