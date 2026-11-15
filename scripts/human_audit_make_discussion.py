"""Path P3 (docs/HUMAN_AUDIT_PLAN.md): build the discussion workbook. Reads items.csv, the annotator-A sheet (initial P1 labels)
and the notes below. Does not read key.json. The notes are an assistant's reading, offered as arguments; the adjudicator decides.
Usage: python3 scripts/human_audit_make_discussion.py"""
import csv
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
D='audit/human_audit_20261111/'
R={r['audit_id']:r for r in csv.DictReader(open(D+'items.csv',encoding='utf-8'))}
A={r[0]:(str(r[4]).strip().lower() if r[4] else '') for r in load_workbook(D+'human_audit_annotator_A.xlsx',data_only=True)['Items'].iter_rows(min_row=2,values_only=True) if r[0]}
# (id, group, question to settle, assistant's reading, suggested label)
N=[
('H008','写法/题目规则','模型写"I. <式子>"，参考答案是选项 I。','式子与题目选项 I 逐字相同，选的就是 I。','correct'),
('H049','写法/题目规则','参考 ULDL；模型给出逐格路径 UULLLL…DDLLLL…。','题目写明"连续同向只写一个字母"。把模型答案折叠后是 U-L-D-L，与参考相同。模型没有按要求折叠，属格式不符、内容相同。','correct'),
('H071','写法/题目规则','同 H049（同一题，另一条答案）。','折叠后同为 ULDL。','correct'),
('H073','写法/题目规则','{n | n≥4} 对 {4,5,6,…}。','顶点数是整数，两种写法是同一个集合。','correct'),
('H018','写法/题目规则','参考写 c；模型写 𝔠。','此题没有选项，c 不是选项字母；参考答案指连续统的基数，𝔠 是它的标准记号。','correct'),
('H056','写法/题目规则','同一题：参考 c；模型 2^ℵ0。','连续统的基数按定义等于 2^ℵ0。','correct'),
('H087','答案不够具体','同一题：参考 c；模型只说 uncountable。','"不可数"没有给出具体基数（不可数集的基数不一定是 𝔠），比参考答案弱。','incorrect'),
('H013','数值容差','参考 3.92×10⁻⁶；模型 3.87×10⁻⁶ Gy。','相差 1.3%，不是参考值的四舍五入。建议统一规则：答案须等于参考值按答案自身有效位数四舍五入后的值。按此规则不符。','incorrect'),
('H097','数值容差','同一题：参考 3.92×10⁻⁶；模型 3.9 μGy。','3.9 μGy = 3.9×10⁻⁶ Gy，是 3.92 保留两位的结果；按上面的规则相符。','correct'),
('H059','数值容差','参考 1.776×10⁻³；模型 1.8×10⁻³ mol/L。','1.776 保留两位是 1.8；按上面的规则相符。','correct'),
('H003','写法/题目规则','参考 Y[1.10]；模型 Y1.10。','题目格式是"Y[e]"，方括号是占位写法，数值相同。','correct'),
('H064','写法/题目规则','参考 O(1)；模型 O(1)（或 Θ(1)）。','给出的就是 O(1)，括号里是同义补充，不是另一个答案。','correct'),
('H031','答案更具体','参考"三溴代产物"；模型给出三溴代物及一个具体结构。','模型明确说是 tribromide；参考答案没有指定结构，无法据参考否定它。','correct'),
('H034','答案更具体','同一题：模型说是三溴代的过度溴化产物，给了另一个具体结构。','同上，结论是三溴代产物。两条答案的具体结构互不相同，但参考答案不涉及结构。','correct'),
('H092','答案不同','参考 DDSSDS；模型 D D S D D S。','去掉空格是 DDSDDS，第四音步不同。','incorrect'),
('H062','答案不完整','参考 I-II-VI；模型只答 I。','题目要求列出全部适用项，模型只给一项。','incorrect'),
('H084','答案不同','参考 F（能编译）；模型说不能编译。','结论相反。','incorrect'),
('H060','答案更简略','问"引用了谁的讲义"；参考"基尔霍夫的力学讲义"；模型"Gustav Kirchhoff"。','问题问的是"谁的"，人名即答案。','correct'),
('H044','读题','参考 (1260n³+21n+10)/(2520n)；模型 n²/2+1/120+1/(252n)+O(n⁻²)，并说明误差恰为 n⁻² 阶。','三项通分后等于参考答案；题目要求误差为 O(n⁻²) 且不更好，模型说明了这一点。','correct'),
('H054','读题','同一题：模型写三项 + Eₙ，Eₙ=1/(480n²)+O(n⁻³)。','近似公式是前三项，与参考相同；Eₙ 是对误差的说明，没有并入公式。标注人初判 incorrect，讨论后倾向 correct。','correct'),
('H047','题目歧义','参考 b=αP₁；模型：若 X₂=U₂+bZ₁ 则 −αP₁，若 X₂=U₂−bZ₁ 则 αP₁。','题目没有定义 b 的符号约定。按"须给出单一最终答案"可判错；按"题目有歧义且答案覆盖了参考答案"可判对。标注人倾向 correct。两种都说得通，请裁决并标 REF。','correct (REF)'),
('H058','渐近阶','参考 max(√(BL), L/log(L/B))；模型 L/log(2+L/B)+√(BL)。','题目问 Θ 量级。max 与和只差常数倍；L≥2B 时两个对数同阶；L≤B 时 √(BL) 主导，模型第一项不超过 L/log2≤√(BL)/log2。B<L<2B 之间参考答案的第二项在 L→B 时发散，是参考写法的缺陷，模型的写法在该处有定义。我认为同阶。','correct (REF)'),
('H036','答案包含更多','参考只给修正因子 r^{A(1−cosθ)+B sinθ}；模型给出完整渐近式，其中含同一个因子。','修正因子逐字相同，多出的是题目已给的 A=B=0 部分。','correct'),
('H069','不同的式子','参考 exp(Δ/2)Σexp(Δ/2)ᵀ；模型 J_ℓ(δ)ΣJ_ℓ(δ)ᵀ（左雅可比）。','J_ℓ(δ)=I+½[δ]×+⅙[δ]×²+…，exp(δ/2)=I+½[δ]×+⅛[δ]×²+…，二阶项不同；题目要求不做近似的精确式。','incorrect'),
('H080','不同的构造','参考 f(w)=⊥⊸⊥^{1+w}，C=f(b)^m；模型用递归 f(0)=1, f(n+1)=⊥⊸f(n)，C 为 m 个 f(b) 的张量积。','C 的写法相同；f 的构造不同（一个是 ⊥ 的幂，一个是嵌套蕴涵）。模型的编码是否也成立需要证明，无法通过比对确认。建议 unsure，或按"与参考不同"判 incorrect。','unsure'),
('H028','不同的表述','参考 Z=Tr exp(−βH)；模型给出反周期边界条件下的 Grassmann 路径积分。','两者是同一个量的两种表示；题目问的恰是"路径积分形式"，模型答的更贴题，参考答案反而没有写路径积分。','correct (REF)'),
('H040','不同的表述','同一题：模型给出路径积分并注明反周期边界条件。','同上。','correct (REF)'),
('H038','答案更具体','参考 ∞；模型"可数无穷多（ℵ₀）"。','模型给的是一种无穷，与参考不矛盾且更具体；参考答案没有区分可数与否。','correct (REF)'),
('H076','答案更具体','同一题：模型"可数无穷多"。','同上。','correct (REF)'),
('H025','专业命名','参考"linalool (p-tolyl) thiocarbonate"；模型"O-(p-tolyl) S-linalyl carbonothioate"。','两者都是芳樟基（linalyl）与对甲苯基的硫代碳酸酯，即烯丙位重排后的产物；模型多写了 O/S 的位置。需要化学背景确认，我认为是同一化合物。','correct'),
('H079','未化简','参考 q^240；模型给出 |E₈(q)|/|W|·Σ_w 1/det(q−w)，未化简。','这个求和式按 Steinberg 定理等于 q^{2N}=q^240，所以数值上是对的；但题目问"确切数目"，模型没有算出来。是否算"给出了最终答案"需要裁决。','unsure'),
('H095','未化简','同一题：模型给出按共轭类求和的等价式，未化简。','同上。','unsure'),
('H006','可计算核验','参考 y≥b·l, y≥x+b−1；模型 y≥x−u+ub−ua, y≥−u+ub−ua。','用穷举核验（scripts/human_audit_milp_check.py，先验证参考答案通过）：模型的约束组不是 f(x) 的精确编码，x 接近 l 时 y 的可行域是一个区间而不是单点。','incorrect'),
('H053','可计算核验','同一题：模型 y≥x−u+l+ub−lb, y≥−ub+lb。','穷举核验：在 5 组 (l,u) 上都是 f(x) 的精确编码。形式与参考不同，但题目的正确答案不唯一。','correct'),
('H065','可计算核验','同一题：模型 y≥x−M+Mb, y≥−Mb，M=u−l+max(0,−u)。','穷举核验：精确编码。用了大 M 常数而不是直接用 l、u，仍对 x,y,a,b 线性。','correct'),
]
assert len(N)==35 and len({n[0] for n in N})==35
wb=Workbook(); ws=wb.active; ws.title='裁决表'
ws.append(['ID','类别','题目','参考答案','模型答案','初判（讨论前）','要判断的问题','讨论要点（助手的看法，仅供参考）','建议','最终裁决','备注（题目或参考答案有缺陷的以 REF 开头）'])
for i,g,qn,note,sug in N:
    r=R[i]; q=r['question']; q=q if len(q)<=6000 else q[:3500]+'\n…[中间省略，完整题目见 items.csv]…\n'+q[-2000:]
    ws.append([i,g,q,r['reference_answer'],r['model_answer'],A.get(i,''),qn,note,sug,None,None])
f=Font(name='Arial',size=10)
for row in ws.iter_rows():
    for c in row: c.font=f; c.alignment=Alignment(wrap_text=True,vertical='top')
for c in ws[1]: c.font=Font(name='Arial',size=10,bold=True); c.fill=PatternFill('solid',fgColor='D9D9D9')
for k in range(2,len(N)+2):
    ws.cell(k,10).fill=PatternFill('solid',fgColor='FFFF00')
    if not ws.cell(k,6).value: ws.cell(k,6).fill=PatternFill('solid',fgColor='FFFF00')
for col,w in zip('ABCDEFGHIJK',(7,13,60,26,36,13,34,60,13,13,28)): ws.column_dimensions[col].width=w
dv=DataValidation(type='list',formula1='"correct,incorrect,unsure"',allow_blank=True); ws.add_data_validation(dv); dv.add(f'F2:F{len(N)+1}'); dv.add(f'J2:J{len(N)+1}')
ws.freeze_panes='C2'
wi=wb.create_sheet('说明',0)
for line in ['讨论裁决（路径 P3）— 说明','',
 '1. 黄色的"初判"格：请在读"讨论要点"之前先填你自己的第一判断（可以把 H、I 两列先隐藏）。已有内容的是你在直接比对阶段的原始判断，不要改。',
 '2. 然后读"要判断的问题"和"讨论要点"。讨论要点是助手的看法，可能有错；它没有参考机器判分（H006、H047、H054、H058、H062、H084 以及直接比对阶段的 13 条除外，这些的机器判分此前已知）。',
 '3. 在黄色的"最终裁决"格填 correct / incorrect / unsure。不同意讨论要点时照你的判断填，并在备注里写一句理由。',
 '4. 认为题目或参考答案本身有缺陷的，备注以 REF 开头。',
 '5. 数值容差的三条（H013、H097、H059）请用同一条规则裁决，并把规则写在其中一条的备注里。',
 '6. 论文中这一部分称为"模型辅助的讨论裁决"，与人工直接比对分开报告；初判与最终裁决都会报告。']: wi.append([line])
for row in wi.iter_rows():
    for c in row: c.font=f
wi['A1'].font=Font(name='Arial',size=12,bold=True); wi.column_dimensions['A'].width=150
wb.save(D+'discussion_adjudication.xlsx'); print('rows',len(N),'initial prefilled',sum(bool(A.get(n[0])) for n in N))
