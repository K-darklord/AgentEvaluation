# 三模型稿件的修改记录（2026-11-14）

流程：初稿 v0 → 10 轮「独立审稿 agent 批评 → 按批评修改」（v1–v10）→ 对 v1–v10 的结论性文字做 universal self-consistency（USC）选择 → 定稿。
每轮审稿 agent 都是新建的、互不知情的，只读当时的 `main.tex`，提示词见 `reviewer_prompt.txt`（ACL/ARR 审稿人 + 不了解实验的读者；每轮恰好三条批评；不得要求新实验）。

| 轮 | 评分（Soundness / Overall） | 三条批评的要点 | 主要修改 |
|---|---|---|---|
| 1 | 3 / 2.5 | "不提升选择"说过头；安慰性循环并不单独隔离"再问一次"；judge 一节以偏概全、grader 与 judge 混名、MiniMax 上质疑条数不匹配 | 改为"选中数的提升未被确立"；承认循环与采样有多处差异；grader/judge 分名；剂量不匹配写入正文与局限 |
| 2 | 3 / 2.5 | 到达率只是相对无 critic 的循环，采样到达一样多；"reach 能解释"没有操作化、合并估计单位不一；预注册、交出答案、judge 数字等与后文矛盾 | 摘要补"并不稳定多于采样"；合并估计统一为每模型平均；"内部记录、未外部注册"；交出答案改为如实表述 |
| 3 | 3 / 2.5 | "选择"一词多义；安慰剂阶梯并非"每次只加一样"；重复概率之比受度量影响 | 术语表区分 selected（计数）与 conversion（比例）；正文列出 critic 作为"整包"的未匹配项；加入绝对差与 odds ratio |
| 4 | 3 / 2.5 | 对照未隔离"具体性"；选中数依赖 grader 且未用精确匹配复核；人工审计未完成、计数对不上 | 新增分析：仅精确匹配下的选中数（`scripts/selected_exact_only.py`）；审计改称 partial 并对账 |
| 5 | 3 / 3 | "小"没有参照；增益来自"再问"而不是投票；精确匹配下与采样的比较变化未报告 | 给出"首答 → 再问 → critic"两步的数字；报告精确匹配下对采样的到达与选中 |
| 6 | 3 / 2.5 | 到达率可能只是"换答案更多"；21–32 的基线不稳；次要检验与审计计数不一致 | 新增分析：第二个候选的正确率、非选择题子集（`scripts/reach_quality_checks.py`）；计数对齐 |
| 7 | 3 / 2.5 | 同上（MiniMax 上是"更多"不是"更好"）；judge 一节与术语对外行难读 | 术语表加入角色与 votes；Final 改为 Last；judge 细节移入附录 |
| 8 | 3 / 2.5 | 局限一节仍把到达归因于"具体批评"；两步比较基线；证据标准不统一 | 归因改为"critic 整包"；§3 写明 confirmatory / secondary / exploratory 三类及统一规则 |
| 9 | 3 / 2.5 | 摘要一句话里四个区间、指代不清；三处无检验的陈述；采样比较应单列 | 重写摘要（每句一个数字）；采样比较单列一节；补区间；DeepSeek 截断题的影响给出数字（32.0 → 28.0） |
| 10 | 3 / 3 | 到达结论的措辞；"未确立"的标准要一致并说明检验功效；21–32 需说明与九样本投票相当 | 统一规则并说明确证检验功效不足；摘要与结论补充对照 |

## USC 选择
- 做法：把 v1–v10 各自的摘要、引言中的主要结果、结论抽出来，打乱顺序、去掉版本号，交给一个独立 agent，用 Chen et al. (2023) 的 USC 提示词（"Select the most consistent response based on majority consensus"）。文件：`usc_candidates.txt`，对照表 `usc_key.json`。
- 结果：选中 Response 7 = **v5**（第 5 轮之后的版本），不是最后一版 v10。
- 该 agent 同时指出 v5 中两处不属于多数版本的说法：把 critic 的增量写成既定事实（多数版本写作"估计增量"），以及稳健性列表较短。

## 定稿的构成
- 摘要、引言中的主要结果、结论：取 USC 选中的 v5 的表述，并把上面两处改为多数版本的说法。
- 正文其余部分：取 v10，因为第 6–10 轮的改动里有事实性更正（计数对账、新增的稳健性分析、术语表与角色表、judge 一节的设定说明），这些不随"哪一版的表述更一致"而改变。
- 正文 8 页以内（Limitations 从第 8 页末开始），共 15 页。

## 过程中的观察（与论文结论的对照）
- 十轮里审稿评分没有上升（Overall 在 2.5 与 3 之间波动），而每一轮都找到了新的可改之处：批评扩大了被检查到的问题范围，但没有让"最后一版"成为最被认可的一版。
- USC 选的是中间版本；最后一版的摘要在第 6–8 轮曾因不断叠加限定语而变得难读，第 9 轮审稿人明确指出了这一点。

## 仍需作者处理
1. 人工审计只完成 65/100；附录 D 如实写为 partial。剩余 35 条在 `audit/human_audit_20261111/discussion_adjudication.xlsx`，裁决后需更新附录 D 与 Limitations 中的一句。
2. 符号核验的两处转写（H042、H088）待确认。
3. 新增引文两条已核对题目与作者（Song et al. 2024；Jain 2026，ICML 2026 workshop）。检索中出现的 arXiv 2604.22273 因抓取受限未能核实，未引用。
4. 作者单位未填。

## 2026-11-15 定稿后的四处文字修改（独立 EMNLP 审计之后）
1. 相关工作补引并区分五篇（均已核对题目与作者）：Ning et al. 2026（arXiv 2604.01029）、Wang et al. 2025（arXiv 2504.14047）、Mirzaei 2026（arXiv 2607.28576）、Zhang et al. 2024（arXiv 2412.14959）、Ryu et al. 2026（NeurIPS 2026 workshop）。讨论一节说明与"投票优于顺序修正"的结果为何不同。
2. §3 给出确证检验的功效：区间半宽约 12 题；对合并估计（13.6 题）的功效约 57%，80% 功效需约 18 题（正态近似）。
3. Limitations 开头新增 Scope 一段。
4. 附录 E 说明预先写定的检验文档随材料公开（投稿前需把这些文档放入补充材料并做匿名化检查）。
为保持正文 8 页，judge 一节进一步压缩，细节在附录 G。

## 2026-11-15 与"投票优于顺序修正"文献的对账（探索性分析，`scripts/reconcile_with_voting_literature.py`）
- 按那些研究的读法（取最后一次修改）：critique loop 的最后答案对九样本投票为 +11.3 [−2.1, 24.2]、+21.0 [6.7, 36.5]、+4.3 [−9.2, 17.4]，只在一个模型上领先。
- 按答案形式：参考答案为单个字母的 86 题上优势消失（0.0、+6.2、+4.4）；其余 314 题上为 +20.7、+16.9、+7.8。
- 按难度（用另外两个模型的首答定义）：优势不随难度增大。原稿里"因为题目难"的解释与数据不符，已删去。
- 正文讨论一节与附录 F 已据此改写。

## 2026-11-15 判分审计完成（v10）
- 100 条全部处理：直接比对 53、符号核验 12、讨论裁决 35（`scripts/human_audit_final.py`）。
- 与自动判分一致 93/100。自动判对的 71 条中 6 条被判为错（grader 接受的 62 条中 4 条，裁决层 4 条中 2 条，精确匹配 5 条中 0 条）；自动判错的 29 条中 1 条被判为对。
- 6 条误收中有 3 条落在 qwen 的 critique loop（该处共审 4 条）。
- 讨论裁决的 35 条：最终裁决与模型写的讨论要点在 32 条有明确建议的题上全部一致，3 条无建议的判为错；初判只记录了 13 条。附录 D 已如实写明这一部分是模型辅助的。
- 附录 D 重写；Limitations 与 §3 的相应句子更新；标题由 Human Audit 改为 Audit of the Scoring。

## 2026-11-15 披露与措辞（v11）
- 附录 D：讨论裁决改为"人工裁决人在看到讨论要点的情况下判断"，写明撰写讨论要点的模型（Claude，claude-fable-5-2）；32 条有建议的题裁决与建议一致，3 条无建议的由裁决人判为错。
- 新增 "Use of AI Assistants" 一节：实验规划与规格起草、分析代码、统计、文字起草与修改（含模拟审稿）使用了 AI 助手；实验运行由另一个 AI 编码代理执行；作者确定研究问题、设计、协议与主张并对内容负责。

## 2026-11-15 根据外部 AI 审计笔记（针对 v10）的修改（v12）
采纳：摘要重写为三条结果并区分两个比较对象（对安慰剂循环 / 对独立采样）；majority answer 全文改为 plurality answer；正文说明受限 critic 是最初设计、现用 critic 是其对照；说明安慰剂"剂量匹配、计算量不匹配"；正文说明第三模型的替换；Holm 校正一句；表 4 标出确证检验、表 5 与图 1 的说明；模型名不再用小型大写；"reach 在有外部检查时才重要"改为未检验的预期；语法一处。
未采纳及原因见给作者的回复（需要新实验的三条；PDF 文本抽取造成的假错字；数值舍入）。

## 2026-11-15 文档对齐时的数值复核（v13）
逐项用仓库脚本复算论文数字时发现两处与冻结数据不一致，已改正文并重新编译（`v13_*.pdf`；v12 移入 `_old/`）：
- 附录 F 重复概率表与 §4.3 正文：MiniMax-M2.5 critique loop 的比值 1.452，按四舍五入应为 1.5（原写 1.4，是把 1.45 截断所致）。预先确定的次要检验（比值下界高于 reassuring loop 的估计）不受影响。
- 附录 F "Does the critic hand over answers?"：MiniMax-M2.5 的计数应为 13/115（变好）与 16/98（变坏），原写 12/115 与 9/89，与现行 sidecar（rep3）不符；结论句由 "about 10%" 改为 "between 10% and 16%"，"变好一侧没有更多" 的结论不变。
- 同一张表：qwen critique loop 的两个概率为 .45 与 .28（原写 .46 与 .29，舍入方向有误），比值 1.6 不变。
- §4.3：两个概率之差按未舍入的数值重算，为 0.23→0.28、0.11→0.17、0.13→0.17（原写 0.12→0.17、0.14→0.16，是用舍入后的概率相减）；MiniMax-M2.5 的 odds ratio 为 1.8→2.0（原写"不变（1.9）"，同样来自舍入后的概率）。句子改为 "grows by about 0.05 … barely moves (1.8 to 2.0)"。**这句的判断（"比值上升只是弱证据"）未改，但依据略有削弱，请作者通读时留意。**
- 正文仍在 8 页内（Limitations 从第 9 页顶开始）。

新增两个只读脚本，补上此前只在会话中算过、仓库里没有脚本的数字：`scripts/three_model_means.py`（表 4 末列与图 3 的三模型均值）、`scripts/three_model_appendix.py`（三模型的重复概率及其差与 odds ratio、首轮修复/损伤、critic 文本是否含下一答案、被截断的首答数）。`docs/consistency_manifest.json` 重建为 v3（272 条），`scripts/check_manifest.py` 逐条对照脚本输出与 `main.tex`，当前 0 处不符。

## 2026-11-15 针对三个审稿问题的修复（v14）
问题：只有一个 benchmark；安慰剂 loop 的计算量未对齐；确认性检验不显著。规则先于计算写在 `docs/REVIEW_RESPONSE_PLAN.md`。

**事后分析一：同 token 预算下的 reach（`scripts/budget_matched_reach.py`）。结果对论文不利，按预先写定的规则如实写入并收窄措辞。**
- 逐题把 critique loop 截断到安慰剂 loop 在该题上花的 token：对 reassuring loop 18/16、15/25、13/19，对 generic-doubt loop 17/23、13/32（p=.007，更少）、19/23。三个模型上都不再到达更多。
- 统一轮数上限（总 token 对齐）：对 reassuring loop 30/15（p=.04）、38/19（p=.02）、23/18；对 generic-doubt loop 27/21、33/30、31/19，均不显著。
- 论文改动：摘要第一条结果加"用约两倍 token，截断到安慰剂 loop 的预算后不再到达更多"；引言第一条同样；§4.1 新增一段 "Is it only more tokens?"；Discussion 与 Conclusion 各改一句；附录 F 给出全部数字与两种口径各自的偏向；附录 E 注明这是评审后追加的分析。
- 为保持正文 8 页，以下内容移到附录 F：不含选择题的 reach、第二候选的计数、精确匹配下对独立样本的 reach、每题轮数、MiniMax 复述通用怀疑的比例（88%）。

**更正：MiniMax-M2.5 的 critique loop token。** 原写 45M（其中 critic 15.4M），实际为 40M（critic 10.6M）。原数把 reasoning token 在 completion 之外又加了一次（`docs/THIRD_MODEL_RESULTS.md` 的合计口径是 prompt + completion + reasoning）。相应地"2.1 到 2.5 倍"改为"1.9 到 2.5 倍"。

**事后分析二：按学科的 reach（`scripts/reach_by_subject.py`）。** 三模型合计，critique loop 对 reassuring loop 在 8 个学科中 7 个领先、1 个持平（工程 1/1），无反向。写入附录 F。

**选题说明。** 附录 F 新增 "Choice of benchmark"：此前六个 benchmark 上首答正确率 89%（261/294），修改没有空间；33 个错答只用于 restricted critic 的词表。Limitations 加一句指向。

**确认性检验的表述。** 检查了摘要、引言、§4.2、结论、Limitations 五处，均为"未确立 / inconclusive"，§3 已写明需要约 18 题的增益才能检出；未改。

**新实验规格。** `docs/TOKEN_YOKED_CONTROL_SPEC.md`（token 对齐的 generic-doubt loop，qwen，一个条件），待作者确认，未运行。

manifest 更新为 344 条，`scripts/check_manifest.py` 0 处不符。v13 移入 `_old/`。

**同日补充（作者指出）。** 截断分析没有跑新实验，只是把已有的 critique loop 轨迹按 token 截短；它是单向的，不能说明安慰剂 loop 多花 token 就有效。据此改了两句话，去掉了超出证据的表述：§4.1 末句改为 "These cuts run one way only: they show that the gain needs the extra tokens, not that tokens alone would produce it …"；Discussion 里 "at a cost in tokens that accounts for much of its gain in reach" 改为 "…spends about twice the tokens; whether a placebo loop given those tokens would reach as much is untested"。

**同日第二次补充（作者意见：截断方法不合理，安慰剂 loop 在扰动低时未必能产生更多答案；附录必须让人看出不是 p-hacking）。**
- 截断分析从摘要和引言中撤下，只保留"约两倍 token"的事实陈述。§4.1 "Is it only more tokens?" 一段改写：先说明安慰剂 loop 自行停止、本文没有跑 token 对齐的安慰剂；再给两个单侧证据——前两个反馈轮里 critique loop 每轮首次出现正确答案的比例更高（11%、12%、8% 对 5%–9%），以及截断结果（附带"这种截断偏严"的说明）；结论句为"增益离不开额外 token；只靠 token 能否产生它，现有运行不能判定"。截断分析留在附录 F "Reach and tokens"，并新增一小节 "What these cuts can and cannot show"。保留而不删除的理由：规则先于计算写定且承诺不论方向都报告，删掉一个不利的分析正是需要避免的做法。
- 附录 F "Choice of benchmark" 扩写为 "Choice of benchmark, earlier runs, and how the questions were drawn"，列出研究开始前跑过的全部内容。**核对旧运行时发现：reassuring loop 和早期 critic loop 此前在 GPQA-Diamond 等 benchmark 上跑过**（见 `docs/CLAIMS_REGISTRY.md` 的披露一节）；原先的草稿只写了"测过首答"，现已如实补上数字和不可比的原因。
- 400 题分三次抽取（50、150、200）如实写明；新增分半检查（`scripts/reach_by_draw.py`）：只看协议冻结前没跑过任何东西的后 200 题，结论相同（对 reassuring loop 27/2、35/5、20/3）。
- manifest 399 条，0 处不符。正文仍在 8 页内。

**同日第三次补充（作者决定）。** 论文中不保留任何截断分析：§4.1 "Is it only more tokens?" 缩为三句（token 成本；安慰剂 loop 自行停止、本文没有 token 对齐的安慰剂；因此不能说增益在这样的对照下还剩多少，独立采样花相近的 token 到达同样多或更多），附录 F "Reach and tokens" 整节删除，其中有利于 critique loop 的"每轮首次出现正确答案的比例"也一并删除，避免只留一半。Limitations 加一句 "Neither placebo loop is matched to the critique loop in tokens"。附录 F 的披露一节补一句：此前在其他 benchmark 上也试过早期的同模型 judge。记录见 `docs/REVIEW_RESPONSE_PLAN.md` 末节。待 token 对齐的安慰剂实验完成后，§4.1 这一段按实验结果重写。

**对照实验规格修订（v2，下达前）。** 根据外部意见：改名为 token-yoked generic-doubt control（它匹配总 token，不匹配 critic 调用，不能把批评内容与额外调用分开）；Y1 与 Y2 联合解释；写明 token 对齐的判据（95%–120%，触顶题不超过 20 道）、越界与触顶的处理、Y1 的功效（差距保留四分之三时 88%，保留一半时 45%）。规格：`docs/TOKEN_YOKED_CONTROL_SPEC.md`。

**对照实验计划（2026-11-15 22:25，作者决定先把安慰剂相关实验做完，再考虑新 400 题）。** qwen 上三个条件：token-yoked generic-doubt control（`docs/TOKEN_YOKED_CONTROL_SPEC.md`）、错配批评、只读题目的批评（`docs/CONTENT_CONTROLS_SPEC.md`）。判据均先于运行写定，五个条件的结果不论方向全部报告。

**内容对照规格修订（v2，下达前）。** 根据外部意见：五个条件不再称阶梯，改为性质表加成对比较；错配批评的供体按批评长度匹配（平均 1,650 对 1,645 字符，条数 2.96 对 2.96）；写明错配批评可能有害时 X1 不能归因于"针对本题有益"；C2Q 增加长度报告、"与长度混淆"的标记规则和 30 条人工抽查；解释表改为"可以说 / 不能说"。未采纳：现场生成供体批评（C2X-live），理由写在规格 2.3。

**叙事调整（2026-11-15 22:50，作者意见：reach 可能是通用收益，selection 可能取决于模型，可作为假设提出）。**
- 摘要末尾加一句：selected 的估计在模型间为 5 到 23 题，"我们假设 reach 的增益是通用的、selection 的增益取决于模型"。第二条结果仍是"未确立"。
- Discussion 新增一段 "A hypothesis on models"，明确写"假设而非结论"，并写明三个模型分不清"效应因模型而异"与"同一效应加噪声"，模型间差别都不显著。
- 附录 F 新增 "An arithmetic split of the gain in selected questions"：恒等式拆分（reach 部分 +42.6/+43.6/+22.0，conversion 部分 −30.2/−20.3/−16.7）与模型间差别的三个区间。
- 对外部文章《selection 是 model-specific》的核对：分解式与数字成立；但它把 MiniMax 归因于"conversion 下降"与数据不符（MiniMax 的 conversion 损失是三者中最小的，不同之处在 reach 增益只有一半）；"clear on two models"不成立（deepseek 的区间含零）；"MiniMax 答案更分散"与数据相反（每题候选数 3.2，最少）。未采纳这些表述。
- 为保持正文 8 页删去的句子：Discussion 中"critic 也许主要是恢复多样性"的猜测、§4.2 两句重复的限定语、"Is it the scoring?" 的段落标题、引言与 §4.1 各一处从句。

**页数（作者决定，22:45）。** 新实验未跑完前暂不为页数删内容：上一条里为压到 8 页而删的句子已恢复，正文目前超出 8 页若干行，留待实验结果写入后整体压缩。

**确认性实验草案（2026-11-15 23:00，未下达）。** `docs/MODEL_DEPENDENCE_SPEC.md`：qwen 与 MiniMax 在新抽的题上，两阶段各 400 题；主检验 P1（qwen 上 critique 对 reassuring 的 selected 增益）与 P2（该增益在两个模型间的差）；显著性水平按 Bonferroni 与并集界分配。待三个对照实验完成后由作者决定是否实施。

## 2026-11-16 对照实验读出
三个对照在 qwen 上跑完并判分，结果见 `docs/CONTROLS_RESULTS.md`。要点：token-yoked 通用怀疑到达 181 题（critique 182，Y1 不显著，32/31）；错配批评到达 120 题，与 reassuring loop 无差别；只读题目的批评到达 161 题（Q1 校正后 p=.041）；四个对照的 selected 都在 91–96，critique 为 114.1。论文尚未改写，待作者确认叙事。

## 2026-11-16 稳妥版（v15）
对照结果写入论文，主叙事不翻转：三模型的结果照旧，新解释写成假设。
- 摘要：四条结果。第一条补"在做了对照的那个模型上，通用怀疑花同样多的 token 到达同样多，为别的题写的批评不起作用，reach 的增益可由多花的计算解释"；新增第四条（该模型上 critique 的 selected 比每个对照多 18–22 题，描述性）；末句改为两个假设（reach 由计算换来；selection 的增益来自读了答案的批评，并取决于模型）。
- §4.1："Is it only more tokens?" 改写为 token-yoked 的结果；新增 "Must the feedback be about the question, and about the answer?" 与 "The controls and selection" 两段；新增表 5（六个条件的 reached / selected / conversion / token）。
- Discussion："A hypothesis on models" 改为 "Two hypotheses"。Conclusion、Limitations 各改一两句。
- 附录 E 增列对照的三个主检验；新增附录 "Token-Yoked and Content Controls"（条件定义、性质表、操纵检查、三个主检验与预先写定的读法、selected、健康度检查后改动的两个设置、截断分析为何被替换）。
- 未写入：只读题目批评的 30 条人工抽查（待作者填写）。
- 正文超出 8 页约 0.7 页，按作者意见暂不压缩。manifest 420 条，0 处不符。v14 移入 `_old/`。
- 同日写定并下达：`docs/SELECTION_CONFIRMATION_SPEC.md`（qwen，800 新题，五个条件；确认性检验 S1、S2 与 reach 的等价性检验 R1）。待定：`docs/TOKEN_YOKED_MINIMAX_ADDENDUM.md`。

**模拟 ARR 审稿（2026-11-16，独立子代理，只给匿名稿）。** 评分：Soundness 3，Overall 3（Findings），主会约 10%，Findings 约 35%–40%。主要意见：没有单一的、已确立的主结论；对照只在一个模型上；qwen 上 selected 的结果最依赖 grader，且对照的比较没有报告精确匹配口径；"accounted for by computation" 说得过强（按 token 相等，按候选 critique 仍领先）；单一 benchmark、每格一次运行。
据此当场做的修改（都不需要新实验）：
- 补算并写入对照在"只计精确匹配"下的 selected（`controls_readout.py` 新增一节）：critique 68.1，对照 55.5–59.0；领先 9.1–12.6 题，区间多数含零（对 token-yoked +10.7 [−0.8, 21.8]）。摘要第四条与 §4.1 相应加注，附录 G 给全表。
- "accounted for by additional computation" 三处改写，并在 §4.1 写明两种对齐方式结论不同：按候选 critique 领先，按 token 不领先。
- "The four loops" 改为 "The five loops"；§4.2 "The picture is the same" 改为注明 qwen 的区间在精确匹配下含零；错配批评一句限定为"在这个模型上被无视"。
尚未处理、留待整体改稿：叙事聚焦到一个主结论并压回 8 页；审稿人列出的其余措辞与定义问题（round 的定义、316/314、表 8 的舍入位数、附录 H 的过期数字等）。

**2026-11-16 晚：第二份模拟审稿（作者转来）与两份意见的综合。** 作者决定：MiniMax 上做 token-yoked；qwen 800 新题照做；benchmark 暂不加；补齐"各种反馈在相同 token 下"一列并重跑一次 critique loop（`docs/EQUAL_TOKEN_CONTROLS_SPEC.md`）。稿面：摘要两处措辞收窄；同模型 judge 一节移到附录（正文留一段指引）；conversion 等是否移到附录，待实验结束、主叙事确定后再定。

**相同 token 对照改为续跑（v2）。** 作者意见：续跑合理，重跑不合理。三个条件都从已有轨迹接着跑到预算；critique loop 的重复运行取消。对齐判据按续跑的性质在运行前重写（每题不少于预算；总量如实报告，C2QY 预计为 critique loop 的 120%–125%，因为已有运行里 135 题已超出预算）。

**相同 token 对照 v3。** 只读题目的批评改为按总量对齐（f = 0.391，补约 4.2M），避免总量超出两成；另两行仍按每题对齐。

**相同 token 对照 v4（外部审阅后）。** 三个条件统一按题对齐：不足预算的题续跑到预算；已超出预算的题读出时只计到预算为止的轮次（即从头按预算跑会停下的位置）。v3 的按比例补法取消。另报"自然停止"与"全部轮次"两种口径。

## 2026-11-17 — v16 draft (new narrative; results pending marked in the text)

Trigger: read-outs of the equal-token continuation (qwen), token-yoked generic doubt (MiniMax) and the confirmation on 800 new questions (qwen): S1, S2 passed, R1 equivalent (`docs/CONTROLS_RESULTS.md`). Author decision: one core conclusion, "reach is bought with tokens; a critique of the answer raises what is selected".

- Abstract and the results part of the Introduction rewritten around two results (was four results and two hypotheses).
- §4.1 retitled "Reach: the critique loop reaches more, and tokens account for it"; "Is it only more tokens?" now reports the token-yoked control on two models; Table `tab:controls` now shows five kinds of feedback at natural stop and at equal tokens; content paragraph rewritten for equal tokens.
- New §4.2 "Confirmation on new questions" (`sec:confirm`, Table `tab:confirm`).
- Former §4.2 retitled "Selected questions in the first study"; first paragraph reworded (first study's confirmatory test inconclusive; gain confirmed on qwen with new questions, unestablished on the other two).
- §4.3: paragraph with repeat probabilities, first revision and last answer on the new questions (`scripts/confirmation_mechanism.py`). §4.4: note that samples on new questions are pending.
- Discussion: "Two hypotheses" replaced by "What is established and what is not" and "Does the gain in selection depend on the model?"; "Use" and Conclusion rewritten; Limitations updated (one model; R1 met by one question; uneven across draws; samples added after the read-out).
- Appendix: new section "Confirmation on New Questions" (`app:confirm`: design, criteria, results, secondary, by subject, by draw [not in plan], runs added after the read-out); `app:controls` gains "Continuation to equal tokens" and "Token-yoked generic doubt on MiniMax".
- Manifest: 636 facts (195 added), paper_version "v16 draft"; `check_manifest.py` 0 problems.
- Not yet done: body is about two pages over eight; conversion/split material not yet moved; Figure 1 still shows the first study only; Appendix E list not yet extended with the new tests; pending results (samples and question-only on new questions, deepseek on new questions, second benchmark).
- Files: `v16_draft_anonymous.pdf`, `v16_draft_preprint.pdf` (23 pages); v15 sources kept as `_old/main_v15.tex`, `_old/main_preprint_v15.tex`.

### 2026-11-17 (later) — v16 draft, fixes after an external audit (`AUDIT_v16_20261117.md`)
- Correction: last answer of the critique loop on the 800 new questions is 207 (verdict of the last round, the definition of Table 1), not 211 (an earlier figure used a different definition); `scripts/confirmation_mechanism.py` now uses the paper's definition and reports last minus plurality with interval. "Last" column added to Table `tab:confirm`; the last-answer paragraph states that last and plurality do not differ on qwen in either question set.
- Reason for choosing qwen for the confirmation stated in §4.2 and Appendix; "as many or more" for samples made precise (intro, abstract); sensitivity of the equivalence bound and pre-run power added to the appendix.

### 2026-11-17 (night) — v16 draft, rewrite after the simulated ARR review
- Headline of the second result changed from "a critique of the answer raises what is selected" to "the critique raises what is selected" (abstract, introduction); abstract and introduction state that the need to read the answer rests on descriptive comparisons.
- Reach wording calibrated: "reaches no more, possibly fewer"; first-400 token-yoked comparisons now carry the difference with 90% interval (qwen +1, -11 to 14; MiniMax -4, -15 to 7; `equal_token_readout.py`), and are described as tests of a difference, not equivalence.
- §3: statistics and "What was fixed in advance" rewritten (no more "reach is our headline"; confirmatory = first-study test plus the three tests of the confirmation; Holm within families). Table 2 "counted over the questions".
- New Figure 1 (`figs/tokens_select.pdf`, `make_figs.py`): reached and selected on qwen at equal tokens (first 400) and on the 800 new questions; the three-model figure moved to the start of Results as `fig:first`.
- Clarifications: change rates in §4.1 are over the equal-token runs; Table 10 rounding note (total 36.2); Table 9 note on unrounded ratios; 86 one-letter references = 84 multiple-choice questions and two others; samples claim in the abstract hedged ("narrowly on one model").
- Body now ends on page 11 (about 2.3 pages over); cuts postponed until the pending results are in.
- New: `scripts/human_audit2_sample.py`, `docs/HUMAN_AUDIT2_PLAN.md` (sheets in `audit/selection_audit_20261117/`), `docs/RUN_VARIANCE_SPEC.md`.
- Still open from the review: related-work additions (to verify before citing), section order, page cuts, merge bound for the token-yoked loop, cross-check of the main tests with a standard statistics library.

### 2026-11-17 (late night) — v16 draft, narrative focused on one finding (author's instruction)
- Abstract and Introduction rewritten around one sentence: the critique does not help the model find correct answers; it helps the model settle on them. Introduction now runs: claim; a narrow question (one model, 157 vs 145); two outcomes and one change at a time; the finding ("reach follows the tokens", "selection follows the critique"); what is verified and what is not; why it matters (a rule of use). Relative gains (13%, 22%) added.
- Results reordered: 4.1 The observation (first study); 4.2 Tokens account for what the critique loop reaches; 4.3 Tokens do not account for what it selects (first 400 at equal tokens, then the confirmation); 4.4 How the critique changes what is selected (repeat probabilities, last answer); 4.5 independent samples.
- Conversion and the split by reach (Table `tab:split`) moved to Appendix F. Body now ends on page 10.
- Previous state kept as `_old/main_v16a.tex`.
