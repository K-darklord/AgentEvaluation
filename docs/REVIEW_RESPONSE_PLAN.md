# 针对三个审稿问题的修复计划（2026-11-15 21:30 写定，先于任何计算）

三个问题：(Q1) 为什么只有一个 benchmark；(Q2) 安慰剂 loop 的计算量没有与 critique loop 对齐；(Q3) 关于 selected 的确认性检验不显著。
本文件先写规则，再算数。A、B 两项只读冻结文件，属于**事后追加的探索性分析**，论文中照此标明；无论结果方向如何都写入附录。C 项是新实验，规格另见 `TOKEN_YOKED_CONTROL_SPEC.md`。
名称用论文叫法；代号对照见 `INDEX.md` 第 2 节。

## A. 同 token 预算下的 reach（Q2，现有数据）

**问题。** critique loop 用的 token 是 reassuring loop 的 2.1–2.5 倍。它多到达的题，是否只是多花计算的结果？

**定义。**
- 一道题上一个 loop 的成本 = 各轮 solver 的 prompt + completion token 之和，加上各次 critic 调用的 prompt + completion token。
- critic token：MiniMax-M2.5 用轨迹里逐轮记录的值；deepseek、qwen 的轨迹没有逐轮记录，用回放实测的每次调用均值（`token_replay_summary.json` 的 `per_call_means`，prompt + completion），每个有 critic 调用的轮次记一次。
- 首答（第 0 轮）计入成本，并且总是保留。
- **主口径（逐题预算）**：对每道题，预算 = 对照 loop（reassuring 或 generic-doubt）在该题上的总成本。critique loop 保留从第 0 轮起、累计成本不超过预算的最长前缀；第 j 轮的累计成本包含产生第 j 轮所需的那次 critic 调用。
- **辅口径（统一轮数上限）**：取最大的 R，使 critique loop 只保留第 0..R 轮时 400 题总成本不超过对照 loop 的总成本。
- reached：保留的轮次里出现过判分为正确的答案。

**读出。** 截断后的 critique loop 对完整的对照 loop，配对比较 reached（精确 McNemar，双侧）。每个模型、两个对照、两个口径都报告。
- 在某个模型上"同预算下仍成立" = 主口径下截断后的 critique loop 到达更多，且 p < .05。
- 三个模型都成立：§4.1 加一句"在相同 token 预算下仍成立"。
- 任一模型不成立：如实写明在该模型上 reach 优势不能与多花的计算分开，§4.1 与摘要第一条结果的措辞相应收窄为"在更高的计算量下到达更多"。
- 同时报告截断后保留的平均轮数与实际用掉的预算比例，供读者判断。

**已知局限（写入论文）。** deepseek、qwen 的 critic 成本是均值近似；逐题预算使简单题（对照 loop 很快停止）上的 critique loop 几乎只剩首答，这对 critique loop 不利，是偏保守的比较。

## B. 按学科分层的 reach（Q1，现有数据）

**定义。** 400 题按 HLE 的 `category` 字段分 8 层（Math 175、Computer Science/AI 44、Biology/Medicine 41、Physics 40、Humanities/Social Science 36、Other 31、Chemistry 20、Engineering 13）。每层、每个模型报告：只有 critique loop 到达的题数 / 只有 reassuring loop 到达的题数；对 generic-doubt loop 同样报告。

**读出。** 纯描述，不做逐层检验（层内题数小）。报告每个模型上方向为正（前者多于后者）的层数，以及三模型合计后各层的两个计数。若某一层三模型合计方向为负，点名写出。

## C. 选题说明（Q1，已有记录）

附录加一段说明为什么用 HLE：此前在六个 benchmark 上各取约 50 题测过首答（deepseek-v4-flash，温度 0）：AIME 47/50、GPQA-Diamond 41/50、BBH 40/44、MMLU-Pro 43/50、MATH-500 45/50、BFCL 45/50，合计 261/294（89%）。按 break-even 条件，正确率 0.89 时一轮修改要修好的比例达到改坏比例的 8 倍才有净收益。因此选首答正确率低的题集；这一选择先于任何 HLE 运行（error bank 冻结于 2026-10-21，HLE 首次运行于 2026-10-31）。这六个 benchmark 上的 33 个错答只用于构造 restricted critic 的词表（附录 B 已写明），不作为本文任何结论的证据。来源：`experiments/_deprecated/{new_set_20261008_full,mmlu_pro_int16_full,d1_baseline_20260928_201128}/summary.json`、`docs/ERROR_BANK_PROVENANCE.md`。

## D. 确认性检验的表述（Q3，只改文字）

不追加任何检验。检查摘要、引言、§4.2、结论、Limitations 五处对该结果的表述是否一致为"未确立（inconclusive）"，没有一处读成"无效果"或"有效果"。若正文尚无，则在 §4.2 写明该区间排除了什么（上界 18.0）。

## E. 新实验：计算量匹配的安慰剂 loop（Q2）

见 `TOKEN_YOKED_CONTROL_SPEC.md`。一个模型、一个条件；判据预先写定；结果不论方向都报告。

## F. 题集分三次抽取的披露与分半检查（Q1，2026-11-15 21:55 写定，先于计算）

**事实（写入附录）。** 400 题分三次按同一规则（纯文本、按学科分层、种子 42）抽取：50 题试点、再 150 题、最后 200 题（2026-10-31 冻结）。前两次抽取的 200 题上，在最终协议冻结之前跑过早期版本的 loop；最后 200 题在冻结之前没有跑过任何东西。没有任何题目被剔除。论文的全部数字来自冻结协议下对全部 400 题的运行。

**检查。** 把 400 题分成"先抽的 200 题"与"后抽的 200 题"（依据 `data/raw/hle/hle_400_new_selection.json` 与 `hle_50_pilot.jsonl`、`hle_150_new.jsonl`），每个模型分别报告：critique loop 对 reassuring loop、对 generic-doubt loop 的 reached 配对计数（只有前者 / 只有后者），以及 selected 之差。纯描述，不做检验的判定；不论两半是否一致都写入附录。若后 200 题上三模型合计的 reached 方向与前 200 题相反，在 Limitations 点名写出。


## 执行结果与作者决定（2026-11-15 22:00）
- A 项已按规则算出（`experiments/hle400/t3/budget_matched_reach.json`）：主口径下三个模型都"不成立"。作者审阅后判断这一方法不成立——安慰剂 loop 按规则自行停止，截断只缩短 critique loop，不能回答"安慰剂 loop 花同样多的 token 会怎样"——决定**不把任何截断分析写入论文**，改做 E 项实验。本节"不论方向都写入附录"的承诺因此对 A 项不再执行；这一改变及其理由记录在此与 `CLAIMS_REGISTRY.md`，脚本和输出保留。E 项实验的结果不论方向都写入论文，这一承诺不变。
- B、C、F 项已写入附录 F；D 项检查无需改动。
