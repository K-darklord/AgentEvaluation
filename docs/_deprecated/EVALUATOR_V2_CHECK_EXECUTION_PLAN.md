> **SUPERSEDED** — intermediate evaluator scheme (CEL / MPC / threshold sweep / `lock_rule_study`), not
> reported in the paper. Relocated to `docs/_deprecated/` during closeout; see `../EVALUATOR_RESULTS.md`.
> Do not revive.

# Evaluator v2 — Check-Execution Lock (CEL) · 方案

**日期**：2026-11-03 · **状态**：方案，未实现 · **前置**：`HLE400_EVALUATOR_AUDIT.md`（rubric_ce 诊断）、`MOVE_PAIRWISE_CUT_PLAN.md`（MPC，对照方案）

**一句话**：默认信 persistence（mode）；只在 mode 没把握的题上介入；介入时只问一个可核对的二值问题——solver 改答案的那一轮，有没有执行 critic 要求的那条 check。固定规则、零拟合参数、判官全不确定时自动退化为 mode。

---

## 0. 为什么不是调阈值、也不是 MPC

来自 HLE-400 C3 轨迹（sidecar v2 标签）的四个事实：

| 事实 | 数 | 含义 |
|---|---|---|
| 正确答案在循环中出现过的题 | 193 | 任何 excluder 的天花板 |
| plain mode 锁对 | 154 | 缺口 39 题 |
| rubric_ce 的 `max(contradiction, error)` 在同题内边上的 AUROC | 0.57（信息边 0.59） | judge 分数几乎分不开对错转换 |
| `cut_bar` 从 3 扫到 11 | 146 → 154，单调逼近 mode | 没有阈值能超过 mode |

gold-free 信号在 273 条信息边上的区分力：新答案的出现次数 **0.64** > 保持长度 0.61 > judge 分数 0.59 > critic suspicion 条数 0.47。**persistence 是现有最强的排除信号**；judge 想加分，必须带来 persistence 之外的信息。MPC 把"绝对分数+阈值"换成"同题内两两比较"，消的是题目级偏移和阈值，但判官读的证据没变（§8 自认 error/contradiction 都弱），信息量不变。

critic **不**判断上一轮 check 是否被执行：3541 条 `critic_direction` 每轮都对当前答案重新给 1–3 条 suspicion + check，无空轮；"archetype 是否延续"AUROC 0.52。所以"check 是否被执行"必须是一次新的独立判断。

39 题缺口的构成：正确答案只出现 1 次 20 题；是少数但 >1 次 14 题；平局判错 3 题；key 提取不到 2 题。

---

## 1. 命题（可证伪）

> 在 mode 没把握的题（候选计数 margin ≤ 1）上，用"入口 move 是否执行了 critic 的 check"作为 ±1 的修正项，锁定准确率高于 plain mode，且不降低 margin ≥ 2 题的准确率（按设计不碰）。

**失败判据**（任一成立即放弃）：dev 集信息边上 P(新答案正确 | executed) < 0.8；`cannot_tell` 率 > 60%；HLE-400 上 CEL ≤ plain mode。

---

## 2. 规则（顺序固定）

记一题的有效轮次 V = 排除 `None` key 和 `finish_reason == length` 的轮次；候选答案 a 的出现次数 c(a)（与 scorer `_mode_idx` 同一 key、同一 None 规则）。

### 规则 1 — persistence 锁定
margin = c(第一) − c(第二)。**margin ≥ 2 → 锁定第一，不调用 evaluator。**
HLE-400 C3：此类题 mode 错 70，其中正确答案出现过 16——按设计放弃（推翻 ≥2 票多数需要 96% 精度，做不到）。

### 规则 2 — 介入集合
margin ≤ 1 的题（C3：132 题；mode 在其中错 95，正确答案出现过 21 = CEL 的全部目标）。
候选集 K = 计数并列最高的答案 ∪ {最终轮答案，若它只出现 1 次}。

### 规则 3 — 入口 move 的 check 执行裁决
对每个 a ∈ K，取 a **最近一次进入**的转换 (r−1 → r)。判官输入（不含题目、不含 gold、不含并排答案）：

```
Round r-1 critic asked the solver to check:   <check_{r-1}>        # critic_direction[*].check
Round r visible reasoning (excerpt):          <reasoning_r>
Round r committed answer:                     <answer_r>

Question: Does round r actually carry out that check and state its outcome?
Answer: executed | not_executed | cannot_tell
Quote: one sentence from round r that shows the check being done (required for executed/not_executed)
```

同一 move 用第二种表述再问一次；两次不一致 → `cannot_tell`。`Quote` 必须能在第 r 轮文本中逐字找到（自动回链），找不到 → `cannot_tell`。

critic 一轮给出 1–3 条 check 时，取第一条（critic 的排序即优先级）；其余作消融。

### 规则 4 — 分数与锁定

```
score(a) = c(a) + 1·[executed] − 1·[not_executed]      # cannot_tell 记 0
lock     = argmax score ; 仍平局 → 最后出现者（与 mode 同规则）
```

全部候选 `cannot_tell` → 退化为 plain mode（设计自检项）。权重固定为 1：一次有证据的"执行了核对"= 多出现一次，刚好翻转 margin ≤ 1，永远翻不动 margin ≥ 2。

### 与 EIR / ECR 的对应
- 错误答案的入口 move `not_executed` → 该答案 −1 → **压 EIR**（critic 带来的误导转换被撤销）
- 单次出现的正确答案入口 move `executed` → +1 → **保住 ECR**（mode 本会丢掉的激活被锁住）

---

## 3. 开发 / 评估协议（事先写死）

| 阶段 | 数据 | 做什么 | 调用 |
|---|---|---|---|
| **S0 上限模拟** | HLE-400 C3 轨迹 + sidecar v2 | 用完美判官（executed ⇔ 新答案正确）跑规则 1–4，得 CEL 上限；同时跑"随机判官（AUROC 0.5）"得下限 | 0 |
| **S1 证据卡定稿** | in-family C3 轨迹（GPQA 等，有 `critic_direction.check` + T3 级标签）20 题 | 人工看 check 文本是否可执行、摘录长度够不够 | 人 |
| **S2 dev 验收** | in-family C3 轨迹全部 margin ≤ 1 题 | 跑规则 3，算 P(正确 \| executed)、P(正确 \| not_executed)、cannot_tell 率、换述一致率 | ≈ 2 × 候选 move 数 |
| **S3 一次性测试** | HLE-400 C3 | 只评一次；CEL vs plain mode 配对 McNemar；按 margin 分层报 | ≈ 1 150（574 move × 2），收窄 K 后更少 |

**门槛**：S0 上限 − 154 ≥ 15 才做 S1（否则规则 2 的集合定义本身不够）；S2 达标（§1）才做 S3。HLE-400 上**不做任何迭代**。

---

## 3.1 S0 结果（2026-11-03，`scripts/cel_simulate.py`，零调用）

规则 1–4 原样执行；模拟判官对候选入口 move 回答 `executed` ⇔ 新答案正确（完美），或以给定准确率翻转。

| 判官 | C3（mode = 154） | 变化 (+/−) | A2（mode = 145） |
|---|---|---|---|
| 完美 | **170** | +16 / −0 | 148 |
| acc 0.9 | 165.4 | +12.4 / −1.0 | 146.8 |
| acc 0.8 | 161.4 | +9.5 / −2.1 | 145.9 |
| acc 0.7 | 157.6 | +7.7 / −4.1 | 145.1 |
| acc 0.6 | 152.6 | +5.5 / −7.0 | 144.4 |
| 随机 | 150.7 | | 143.6 |
| 完美，K 只取平局 + 最终单例 | 164 | | 147 |

介入 132 题（C3），完美判官不损失任何 mode 已对的题（−0），上限 +16，达到 §3 的门槛（≥15）。**盈亏平衡点在判官准确率 ≈ 0.63**；要有意义的增益（≥ +7）需要 ≥ 0.7，稳妥需要 0.8。

对照：现有 rubric_ce 在同类边上的 AUROC 0.57–0.59，若 CEL 判官只有这个水平，结果 ≈ 151–152，低于 mode。因此 S2 的门槛（P(正确 | executed) ≥ 0.8）不是保守，是必要条件；"check 是否被执行"这个问题必须比"这条 move 弱不弱"好答得多，方案才成立。这也是 S1 人工看 20 张证据卡要回答的核心问题。

A2 的介入题只有 65 道、上限 +3：placebo 臂几乎没有可裁决的转换，符合预期。

## 3.2 S1 结果（2026-11-03，12 张证据卡，审计 agent 人工判读）—— **不通过**

从 HLE-400 C3 的 margin ≤ 1 题中抽 12 条入口 move（6 条新答案正确、6 条错误，打乱后盲判），每张卡 = 第 r−1 轮 critic 的 `check` + 第 r 轮推理尾部 1500 字 + 第 r 轮答案。判读结果：

| 判读 | 新答案正确 | 新答案错误 |
|---|---|---|
| executed | 3（hle_388 r10, hle_388 r6, hle_386） | **5**（hle_036, hle_318, hle_152, hle_239, hle_115） |
| not_executed / cannot_tell | **3**（hle_225, hle_162, hle_077） | 1（hle_163） |

P(正确 \| executed) = 3/8，判官准确率 4/12——不高于随机，远低于 §3.1 要求的 0.7。

**"check 是否被执行"本身是可读的**（12 张卡里 9 张能明确判断），但它**不预测正确性**，原因有两个，都是结构性的：

1. 执行了核对 ≠ 核对解决了错误。hle_036 按 check 重推了"first quarter"条件、hle_115 显式测试了 p=2 的可除性、hle_239 推出了 Gale–Ryser 条件——都认真执行了，答案仍错。
2. critic 的 check 本身有一半是对正确答案发的（critic 每轮必发 1–3 条，不区分对错）。hle_152 的 check 要求"没给 g 就只给符号式"，solver 照做，答案从对变错；hle_386 的 check 要求计算光稳态混合物，是在把正确答案往错的方向推。顺着 critic 走，继承的是 critic 的噪声。

**结论**：CEL 在 S1 终止。"入口 move 的 check 执行"不能提供 persistence 之外的信息；+16 的上限需要轨迹里不存在的信息（更强的判官模型或外部验证工具），超出本文范围。

**对论文的含义**：
- Stage B 以诊断性负结果呈现：rubric_ce 151 ≤ mode 154，judge AUROC 0.57，阈值扫描单调逼近 mode，check-执行判读 4/12。
- Stage A 是正结果：critic 驱动的循环 + persistence 锁定（C3.mode 154）对 self-consistency（A3.vote 136）配对 McNemar p = 0.0175，solver 成本为 A3 的 72%。
- H1 的分析必须同时报告 critic 在**正确**轮次上的误报率，不能只报错误轮次上的命中率——S1 的卡片直接显示 critic 对正确答案照样开火。

## 4. 消融（S3 同批数据，离线可得）

| 消融 | 回答 |
|---|---|
| A. 去掉 check，只给 reasoning_r（问"这一轮有没有做任何核对"） | 增益来自 critic 的 check 内容，还是来自"有没有核对"本身 |
| B. 只用第一步（纯 mode，K 不介入） | = 154，基线 |
| C. 权重 w = 2 | 规则是否对 w 敏感（应几乎不变，因只在 margin ≤ 1 介入） |
| D. 完美判官 vs 实际判官 | 判官离上限多远，即 Stage B 剩余 headroom |

---

## 5. 主表里怎么呈现

Tab 4（消融）加一行：`C3 + CEL`，列 acc / 与 mode 的配对差 / 介入题数 / executed 精度 / cannot_tell 率。
无论成败，`rubric_ce` 那一行（151，AUROC 0.57）保留为诊断结果；CEL 成功则主文说"persistence 先验 + 可核对的 check 执行判断"，失败则写入 discussion："在 margin ≤ 1 的题上，check 执行判断也未能提供 persistence 之外的信息"。

---

## 6. 交付物

1. `scripts/cel_simulate.py` — S0：完美/随机判官下的 CEL 上限与下限（零调用）
2. `scripts/cel_probe.py` — 规则 2–4 + 证据卡构造 + 换述双问 + 回链检查
3. S2 验收表（四个数）
4. S3 结果：主表行 + McNemar + 按 margin 分层 + 消融 A/C/D

---

## 附录 A · 锁定规则全面检验（2026-11-03，`scripts/lock_rule_study.py`，零调用）

问题：在 C3 的 250 道多候选题（1126 个候选，250 个正确）上，轨迹里**任何** gold-free 信号能否比"出现次数"更好地指出正确候选？

**候选级 AUROC（候选正确 vs 错误）**

| 特征 | AUROC | 特征 | AUROC |
|---|---|---|---|
| 出现次数 count | **0.578** | 是否最终答案 | 0.555 |
| 最长连续保持 | 0.575 | 最后出现位置（recency） | 0.551 |
| 被 critic 反对后仍保持的轮数 | 0.575 | 衰减加权次数 | 0.556 |
| 进入次数 / 重入次数 | 0.532 | 答案长度 | 0.540 |
| critic 标 retrieval-abort 的比例 | 0.476 | critic 标 truncation 的比例 | 0.514 |
| 是否 round-0 答案 | 0.500 | carried 标记 | 0.498 |
| **该候选各轮的平均 CoT 长度** | **0.430**（越长越错） | 首次出现位置 | 0.467 |

`rationale` 字段在冻结运行中为空（`rationale_mode=off`），没有可用的自述。

**任务级：11 条事先固定的锁定规则（全 400 / 偶数题 / 奇数题）**

| 规则 | 全 | 偶 | 奇 |
|---|---|---|---|
| mode（count，平局取最新） | 155 | 78 | 77 |
| count + 最长连续 | 156 | 79 | 77 |
| count + 被反对后保持 | 155 | 78 | 77 |
| count，平局取最长连续 | 155 | 78 | 77 |
| 最长连续（平局取最新） | 154 | 77 | 77 |
| count + 重入次数 | 153 | 78 | 75 |
| count − 是否 round-0 | 153 | 78 | 75 |
| 衰减加权次数 | 151 | 76 | 75 |
| count + 是否最终 | 150 | 78 | 72 |
| count，平局取最早 | 149 | 78 | 71 |
| 最终答案 | 146 | 75 | 71 |

**与独立采样合并**：C3 轮次 + A3 的 10 个样本合并投票 150；C3 + A2 150；三臂合并 151 —— 都低于 C3 mode 单独的 155。外部样本稀释了循环内的 persistence。

**结论**：轨迹里记录下来的所有 gold-free 信号，在候选级没有一个超过 0.58，11 条规则都落在 mode ± 2 以内、奇偶两半一致。**以现有运行记录的信息，mode 已经是上限**；再做任何后验聚合都只是在噪声里挑。

超过 mode 需要的信号必须在**运行时**产生，这与"evaluator 有空间"并不矛盾，但空间在上游：

1. **可弃权的 critic。** 现在 critic 每轮必发 1–3 条 suspicion，对正确答案也发（S1 的 12 张卡里 6 张如此），所以"critic 有没有反对"这个最自然的 Stage-B 信号恒为真、信息量为零。让 critic 在找不到可落地的 check 时输出"无异议"，"被 critic 放行的答案"就成了锁定依据——这是 exclusion 机制本身，不是后处理。
2. **转换自述。** `rationale_mode=transition` 本来就是为 Stage B 设计的（flip19 的证据链用过），冻结运行关掉了。
3. 可执行的 check（能用代码/工具核的那类）——超出本文。

这三条都是新的运行，不是离线分析。在现有数据上，Stage B 的结论就是 §3.2。
