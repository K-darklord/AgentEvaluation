# Evaluator 最终方案 — Q-CUT（question-visible, cited, subtractive cut）

**日期**：2026-11-03 · **状态**：定稿待执行 · **取代**：rubric_ce（v1）、MPC、CEL、COV、QV-MPC 的各自草案
**超参数**：**0 个可调，且方法内不存在任何实数阈值。** 唯一的"数"是调用次数 N（预算）和减票权重 1（推导所得）。
**不做消融。** 只有一次 dev、一次 test，结果无论正负都进论文。

---

## 0. 一句话

**Q-CUT 是 mode 的优化版本，不是新方法。**

它在 mode 之上加一个减法算子：对每个候选答案的入口 move，判官**看着题目**只做一件事——指出一处使新答案必定错误的步骤并逐字引用；指不出就不动。**全不动 = mode。**

三个不变式：

| 不变式 | 含义 |
|---|---|
| 无引文不动 | 判官全 NONE 时，输出**逐题等于** mode |
| 一票 = 一次出现 | 权重固定为 1，永远翻不动 margin ≥ 2（见 §2 证明） |
| 减法只作用于有入口 move 的候选 | round-0 独有答案被结构性保护 |

---

## 1. 为什么是这个形态（每条都有实测）

| 设计选择 | 依据 |
|---|---|
| 默认 mode | 轨迹内 gold-free 信号候选级 AUROC ≤ 0.58；11 条固定锁定规则全落在 mode ± 2；mode 是现有信息的上限 |
| 只减不加 | 减法对判官宽容：误删率 10% / 召回 30% 时约 +2 题；误删率超过 ~25% 转为负。收益区间有明确边界，不是无条件更优 |
| 判官看题 | 不看题时最自信的 CUT（score=10 且带引文）精度只有 73%，越自信越错——判官在读表面特征；看题是唯一未试过的信息增量 |
| **维度只做隐式权衡** | `max(contradiction,error) ≥ 8` 里的 8 无法推导；让三维只参与判官的内部权衡、不落成可输出的分数，门槛就不再是一个数 |
| **单次判定而非过线** | 阈值原来在做"压噪声"；单次判定把"够不够错"变成"错没错"，这枚逻辑常数不需要知道噪声分布 |
| **逐字回链而非"可信度"** | 把"说得像不像真的"换成"这句话在不在文本里"——机械判定，也是唯一能挡住编造的东西 |
| 单 move 绝对判断，不做 pairwise | m=2 时 pairwise 强迫产生 loser；两候选皆错时拿不到信息。"都不动"是成本不对称下的必要选项 |

---

## 2. 规则（三条，全部固定）

记 V = 有效轮次（排除 `None` key 与 `finish_reason == length`），c(a) = 候选 a 在 V 中的出现次数（与 scorer `_mode_idx` 同 key、同规则）。排序一律：**计数降序，同计数按最后出现靠后者优先**（与 mode 的 tie-break 一致）。

```
R1  对每个有入口 move 的候选 a：
      取 a 最近一次进入的 move (r−1 → r)，调用判官 1 次（不重复、不换序）
      判官内部权衡三个维度（contradiction / error / disconnection），但不输出任何分数
      只返回：verdict = CUT | NO_CUT；dimension = 命中的那一维；quote
      命中 iff  verdict = CUT  且  quote 在第 r 轮 reasoning 中逐字回链
    cut(a) = 1 iff 命中
    例外：只出现在 round 0 的候选没有入口 move → cut(a) = 0，不调用判官

R2  score(a) = c(a) − cut(a)
    pick = argmax score；平局取最后出现者（与 mode 同规则）

R3  所有候选都未命中 → 结果 = mode（逐题恒等）
```

**没有 margin 规则，也没有候选集 K。** 理由：

- margin ≥ 2 的题**可以跳过调用**，这是可证的优化而非规则：若 `c(W) ≥ c(x)+2`，则 `c'(W) = c(W)−1 ≥ c(x)+1 > c'(x)`，任何单次减票都改不了胜者；
- 不设 K，每个候选都被审查，因此不存在"未被审查却靠平局胜出"的路径——`argmax` 直接在全体候选上取。

**round-0 的结构性保护（写进论文）**：round 0 的答案没有入口 move，永远不可能被 cut。113 道 init 正确的题里 C3.mode 丢了 10 道，这条规则对它们无害；但对"init 错、且后来一直没被改掉"的题也无能为力——这是 evaluator 只审 transition 的固有边界，不是缺陷。

**调用量**：C3-400 共 ≈ 574 条候选 move，**每个候选 1 次调用**；跳过 margin ≥ 2 的题后 ≈ 300 次。约为 A3 的 1/7（A3 = 10 次 solver × 400 题）。

---

## 3. 为什么这里没有阈值

| 原来 | 现在 | 为什么不再是可调参数 |
|---|---|---|
| `cut_bar = 8` | 不存在 | 没有分数 |
| 三个 0–10 维度 | 三维只做**隐式权衡**，不输出分数 | 没有可输出的"程度"，也就没有可调的数 |
| 分数 ≥ bar | 单次判断 + 逐字回链 | 输出是二值，门槛不再是数 |
| 分数可信度 | 逐字回链 | 机械判定 |
| 加权求和 | 权重 1 | 来自"一次有引证的否定 = 少出现一次" |

唯一残留的隐式阈值是判官心里的"definitely wrong"——它删不掉，只能**测而不调**：D 阶段报 precision / recall 作为**结果**，不拿它回来改提示词。这与"在 test 上挑操作点"是两件事。

---

## 4. 判官契约

**输入**（每个候选 move 一张卡）

```
QUESTION:
<题目原文>

The solver changed its committed answer at round r:
  previous answer (round r-1, committed key): <old>
  new answer (round r, committed key):        <new>
Before this change, a reviewer asked the solver to check:
  <critic_direction[0].check at round r>
Round r reasoning:
  <reasoning_content_r —— 全量，直到 CHAR_CAP（默认 24k 字）；超出才取 head 60% + tail 40%>

Weigh these three dimensions in your head — do NOT print scores for them:
  contradiction  the trace, or the self-report, contradicts itself; or the conclusion disagrees
                 with the NEW answer
  error          a substantive mistake located in the derivation (computation, sign, mechanism)
  disconnection  the reasoning never actually reaches the NEW answer

Then make ONE decision: is there a single step in round r that makes the NEW answer
definitely wrong? Do not solve the problem. Do not judge the previous answer.

Output exactly:
  verdict: CUT | NO_CUT
  dimension: contradiction | error | disconnection | none     (which one decided it)
  quote: <verbatim sentence from round r reasoning; required when CUT>
  because: <one sentence>
```

**窗口策略（这是最大的实际风险，必须先解决）**：C3 的 reasoning 中位数在 3–6 万字，而 `head 1500 + tail 2500` 只覆盖不到 10%。`error`（计算错）与 `contradiction`（前后矛盾）恰恰发生在推导中段——**recall 会被窗口卡死，而不是被判断力卡死**。所以：

- 默认给**全量 reasoning**，上限 `CHAR_CAP = 24k 字`（若判官模型上下文允许，调到能让 ≥80% 的轨迹整篇放下的位置）；
- 超出才截断，且按 **head 60% + tail 40%** 的固定比例，不做动态选择；
- 回链一律对**原文全文**校验（不是对截断后的片段），因此引文必须真实存在于原文；
- D 阶段必须报 **full-coverage rate**（整篇放下的轨迹占比）——它直接决定 recall 的上限。

**不输出分数、不重复调用。** "命中"由流水线机械判定：`verdict = CUT` 且 `quote` 回链成功。
**不给**：gold、其他候选、任何分数、self-report（HLE-400 为空）。
**回链**：`quote` 必须在第 r 轮 `reasoning_content` 中逐字出现（空白归一化后），否则记 NO_CUT。
**old/new 口径**：`old`、`new` 一律取 **committed key**（与 scorer `_mode_idx` 同口径），不是原始可见文本；`quote` 的逐字回链仍对第 r 轮 `reasoning_content` 原文做。`old` 缺 committed key 时该 move 跳过判官调用（与 round-0 保护同原则）。
**check 索引约定**：`critic_direction[0]` 是第 r 轮 record 里的第 1 条 check，它在第 r 轮 solve 之前针对 `prev_answer`（= 第 r−1 轮答案）发出，故卡上记 `at round r`，不是 r−1。
**判官模型**：与 solver 相同（deepseek-v4-flash），T=0。

---

## 5. 协议（事先写死，不改）

| 阶段 | 数据 | 做什么 | 报什么 |
|---|---|---|---|
| **D（dev）** | 偶数题中 margin ≤ 1 的题（≈ 66 题、≈ 290 条 move） | 跑 R1–R3 | 砍的 **precision**（1 − 误删率）、**recall**、回链失败率、**dimension 分布**、**full-coverage rate**（整篇放下的轨迹占比）、**命中引文在原文中的相对位置**（`index/len`，报中位数与四分位）、**分维度的误删率**，各带二项 CI |
| **T（test）** | 奇数题中 margin ≤ 1 的题 | 同一套提示词、同一套常数，**只跑一次** | Q-CUT vs mode 配对 McNemar（奇数半） |
| **合并** | 全 400 | 两半合并 | 主表一行：acc / 与 mode 的配对差 / 介入题数 / precision / 回链失败率 |

**D 的定位与唯一外部决策线**：

- **误删率（对正确候选的命中比例）点估计 > 25% → 停。** 25% 是减法形态的盈亏平衡点（召回 30–50% 时），来自模拟；
- 回链失败率 > 50% → 提示词或抽取坏了，修提示词不算改方案；
- 其余情况直接进 T，D 不设"召回"门槛——召回低只是少赚，不会亏。

这条 25% 是**实验的外部决策线**，不进入运行时、不影响任何一题的输出；方法内部仍然零阈值。

**两条预注册规则（写在跑之前，不是调参）**：

1. **若某一维度的误删率显著高于其他两维（Fisher p < .05），T 阶段在流水线层过滤该维度的命中**（`dimension == X` 的 CUT 记作 0，不改提示词）。理由：sidecar v2 里有 60 多条 `missed_rescue` 是 `24/25 vs 0.96`、`arcsin(1/5) vs arccos(2√6/5)` 这种形式等价——scorer 判对，而判官很可能把"写法不同"当 contradiction 或 error 判掉。过滤在流水线层做，提示词全程不变。
2. **若命中引文的位置分布显著集中在中段**（而 `full-coverage rate` 偏低），说明 recall 被窗口卡住而不是被判断力卡住：此时先扩 `CHAR_CAP`，不得通过改提示词"提高召回"。

D 不承担精确验收：290 条 move 上 10% 误删只有 29 次事件，CI 约 ±5pp，写成窄区间会被一次抽样波动卡死。**真正的证据是 T 那一半。**

T 的结果无论正负都进论文：正 → 主表 `C3 + Q-CUT` 一行；负 → discussion 一段，附 D/T 两半的 precision 表。

**"没有变成解题者"的核对**（T 同批，离线可得）：CUT 集合里"新答案其实正确"的比例就是误删率，它直接度量判官在找错还是在解题，不另做基线实验。

---

## 6. 对论文的措辞

> The evaluator reads the question but never produces an answer. It may only *remove* a candidate by
> quoting a specific erroneous step in the derivation that produced it; the quotation is verified
> mechanically against the trace, and a removal requires a single call per entry move. When it
> cannot, the lock is the persistence majority.

`answer-free` 保留给 error bank（蒸馏物不含答案）和 critic（不给答案）；evaluator 的描述改为 **answer-producing-free**。

主表脚注写一句：`Q-CUT reduces to mode on the items where no quotation passes the backlink check (x%).`

---

## 7. 交付物

1. `experiments/hle400/t3/qcut_dev_moves.jsonl` / `qcut_test_moves.jsonl` — 两半的候选 move 清单（task_id、round、old、new、check、reasoning 摘录范围、c(a)）
2. `scripts/qcut_run.py` — 构卡、单次调用、verdict/dimension/quote 解析、逐字回链、R1–R3（sidecar v2 评分）
3. D 报告（precision / recall / 回链失败率 / 类别分布 + CI）
4. T 结果 + 主表行 / discussion 段
