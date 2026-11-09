# Evaluator 结果汇总（论文 §evaluator 的唯一数据源）

> 口径：全部 freeze-key 身份（`score_hle_arms._key`）+ sidecar v2 逐轮正误；dev = 偶数题，test = 奇数题。
> 自动生成的 judge 审计表：`docs/_judge_audit_autogen.md`（由 `scripts/judge_conditional_test.py` 重跑生成，勿手改）。
> 设计与预注册：`docs/EVALUATOR_FINAL_DESIGN.md`；Q-CUT 原设计：`docs/EVALUATOR_FINAL_QCUT.md`。

## 0. 命名

| 论文名 | 内容 | 判决 | 数据 |
|---|---|---|---|
| **Judge-R** | rubric_ce：三维评分（disconnection / contradiction / error），max≥8→CUT，全 0→KEEP | CUT / KEEP / UNSURE | `c3_rubric_ce.jsonl` per_switch（1185/1201 边有判决） |
| **Judge-R+** | Q-CUT：Judge-R 的加强版——judge 看题面、须引用原文（line-ID + 片段）、给证伪类 | CUT / NO_CUT | `qcut_result.jsonl`（覆盖 130/253 多答案题，766 次调用） |
| **Judge-C** | 回收版：判 critic 对 OLD 轮的 suspicion/check 是否过度（不看 NEW） | OVER / WARRANTED / UNSURE | `judge_c_verdicts_dashscope.jsonl`（1201 边 × N=2，同权重 deepseek-v4-flash-0731 按量别名；135 次解析失败=5.6%） |
| mode | 冻结多数票，tie→最新 | — | `t3_final_scores_v2.json` |

## 1. 空间：上限分解（信息存在）

| arm | 上限（可选上限：所选规则投票范围内，存在最后出现轮判对的候选；A3 = 9 个样本，A2/C3 = 全部轮） | mode | 差 | 多答案题数 |
|---|---|---|---|---|
| A2 | 154 | 145 | 9 | 161 |
| A3 | 190 | 136 | 54 | 319 |
| C3 | 191 | 154 | 37 | 253 |

C3 可回收 37 题构成：平局 8（多为 11 轮 11 答案的自由文本题）/ 正确答案被放弃 27（含 `MRMMM` 型 9）/ 晚收敛 2。C3.mode = A2 上限。

## 2. oracle：信息对称（任何聚合的边界）

| 策略（C3） | 正确 | vs mode |
|---|---|---|
| mode | 154 | — |
| oracle 撤销所有 R→W switch | 173 | +19 |
| oracle 只撤销 solver 引用了反馈的 R→W | 165 | +11 |
| oracle 只撤销 premise 类 archetype 的 R→W | 165 | +11 |
| 盲撤所有引用了反馈的 switch | 149 | +6 −11 |
| 盲撤所有 switch | 125 | — |

全部 1201 条 switch：W→R 159、R→W 142、W→W 801、R→R 99。

## 3. 三个 judge：边级、任务级、条件信息（见 `_judge_audit_autogen.md` 全表）

**摘要表（论文主表）**

| judge | 边级 E1（全集） | LR CI 含 1？ | 预注册 E3：dev 估→test（vs mode 76） | E4：test 估→dev（vs mode 78） | 与计数相左时判对率 | 聚合穷举 in-sample 最大（81 配置） |
|---|---|---|---|---|---|---|
| Judge-R | 56/97 = 0.577 | 是（dev） | 76（+2 −2） | 73（+5 −10） | 18/36 = **0.500** | 154（无配置 ≥155） |
| Judge-R+ | 72/126 = 0.571 | 是 | 77（+3 −2） | 76（+4 −6） | 38/80 = **0.475** | 156（31 配置 ≥155；跨半归零） |
| Judge-C | 120/181 = 0.663 | **否**（OVER 0.51 [0.32,0.80]，WARRANTED 1.87 [1.24,2.81]） | 71（+3 −8，p=0.23） | 77（+8 −9） | 32/66 = **0.485** | 155（6 配置；跨半归零） |

**只用计数**在同一批决定性边上的判对率：Judge-R 边 0.577、Judge-R+ 边 0.603、Judge-C 边 0.674——三个 judge 都不高于计数。

结论：三个 judge 的边级信息都是计数的边际重述；**条件于投票结构，残余信息为零**。mode 是同模型可提取信息的充分统计量。

## 4. 为什么边级 66% 也不够（Judge-C）

- 基率：推翻 mode 只在"mode 错且有对的候选"（37）与"mode 对"（86 多答案题）上发生，先验 30%。边级判对率 p 的推翻精度 = 0.3p/(0.3p+0.7(1−p))；p=0.66→45%<50%；净正需 p>0.70。
- 在可回收 37 题的 R→W 边上，Judge-C 判 OVER 14 / WARRANTED 18——在 critic 恰好错的地方更多站在 critic 一边。
- 候选级 logistic（计数 4 特征 + 判决 8 特征）在全 400 题上拟合并评估（in-sample 上界）：150 < 154。

## 5. 鲁棒性 / 事后分析（标注为 post-hoc）

- 三角色 naive Bayes（正确规格的 Bayes 聚合，修正预注册 ± 版的双计与未校准 W→W 边）：Judge-C dev→test 73 vs 76，test→dev 79 vs 78。
- 聚合穷举：作用位置 {node, fragment, candidate} × break 权重 {0,.5,1} × fix 权重 {0,.5,1} × 门控 {无, margin≤1, margin=0}；见主表最后一列。
- 轨迹级对照（`scripts/switch_contrast.py`，`r2w_w2r_switches_freezekey.jsonl`）：26 个无 gold 特征在 R→W vs W→R 上 AUC 0.43–0.59，dev/test 无一稳定。
- premise probe（judge 只看题面 + critic 断言）：81 条 switch 中 75 NOT-ABOUT-QUESTION、0 UNSUPPORTED——critic 的断言是关于推导的，不是关于题面的。

## 6. 修订记录

- 2026-11-03 evaluator 行口径：旧 148 为 transitions 字串空间；freeze-key 下 elimination 149 / node 152 / node+tie→mode 154。
- 2026-11-06 Judge-C 核验器 v2：引用长度由否决改为报告；归一化加 LaTeX 间距。原因：74 条一致判决被否中 54% 为真 verbatim 超长。prompt 与 judge 输出未改。首次运行 77% 调用 429，作废；全量重跑于 dashscope（同权重）。
- 2026-11-07 预注册 ± logLR 聚合器规格错误记录（双计、W→W 边未校准）；正式数仍用预注册版，三角色 NB 作鲁棒性。

## 7. 收口前还缺的

- [ ] **Judge-R+ 覆盖**：Q-CUT 只跑了 130/253 多答案题（dev moves + 部分 test）。要么补齐剩余 123 题（≈700 次调用），要么论文明说 Judge-R+ 为 130 题子集上的鲁棒性行。建议：补齐，否则主表里它是唯一不全覆盖的行。
- [ ] `HLE400_FROZEN_DATA.md` evaluator 行替换为本文件 §3 的口径（148 → freeze-key 数 + 指向本文件）。
- [ ] `EVALUATOR_FINAL_DESIGN.md` §6 填入 `_judge_audit_autogen.md` 的数；§4 加规格错误修订。
- [ ] `EVALUATOR_FINAL_QCUT.md` 顶部加一行：Q-CUT = Judge-R+，纳入本框架。
- [ ] critic / evaluator token 成本：Judge-R（rubric_ce prompt/completion tokens 在 `c3_rubric_ce.jsonl`）、Judge-C（`pt/ct/rt` 字段）、Judge-R+（`pt/ct/rt`）汇总一行，进成本表。
- [ ] 论文 §evaluator 文字：按 §1→§2→§3→§4→结论 的顺序写；主文只放 §3 摘要表 + §4 基率一句；全表与 §5 进附录。
- [ ] 与 evaluator 无关但影响标题：C2（bank-free）结果与判读（`docs/C2_BANK_FREE_CRITIC_SPEC.md` §6）。
- [ ] 删除不再报告的中间方案文档或在顶部标注 superseded：CEL / MPC / COV / QV-MPC / lock_rule_study / 阈值 sweep。
