# Evaluator 最终设计：两个 judge、一个聚合器、一条验收线

> 目的：给 Stage B evaluator 一个**非 ad hoc 的最终形态**，并用它严格检验"同模型 evaluator 是否坍缩到 mode"。
> 约束：judge = deepseek-v4-flash（与 solver/critic 同模型）；无 gold；无答案；零手工阈值；不重跑 solver。
> 相关：`docs/EVALUATOR_FINAL_QCUT.md`（Q-CUT 原设计）、`docs/HLE400_EVALUATOR_AUDIT.md`、`scripts/switch_contrast.py`、`experiments/hle400/t3/r2w_w2r_switches_freezekey.jsonl`。

## 0. 结构一句话

```
轨迹（freeze-key 候选 + switch 边）
   ├─ judge-R（rubric 版）：对每条 switch 边给三维评分 → 边级判决 v ∈ {CUT, KEEP, UNSURE}
   └─ judge-C（回收版）：对每条 switch 边判 critic 的反馈是否过度 → 边级判决 v ∈ {OVER, WARRANTED, UNSURE}
                      ↓
   聚合器（共用）：score(c) = log count(c) + Σ ±log LR(v)   —— LR 在 dev 估，test 用
                      ↓
   验收：LR 的 95% CI 是否包含 1；test 上相对 mode 的净变化
```

两个 judge 只是**判决来源**；聚合器、身份、计分、验收完全相同。mode 是所有 LR = 1 的特例。

## 1. 共同基础（不可改）

| 项 | 规定 | 出处 |
|---|---|---|
| 候选身份 | `score_hle_arms._key`（= `_early_stop_key`），两段式截断规则 | `HLE_SCORER.md` §1.2 |
| switch 边 | 相邻非 None 轮 key 不同：(a→b)，共 1201 条 | `recompute_evaluator_offline.freeze_switches` |
| 边的真值（仅用于 dev 估计与报告） | sidecar v2：修复 = W→R，破坏 = R→W，其余非决定性 | `is_correct_t3_sidecar_v2.json` |
| 计分 | 选中候选最后出现轮的 sidecar 判定；截断赢家判错 | 同 mode |
| 划分 | dev = 偶数题，test = 奇数题 | 预注册 |
| judge 调用 | N=2 顺序对换；两次一致才取非 UNSURE 判决 | Q-CUT 原规定 |
| 平局 | 分数相等 → 最新出现 | 同 mode |

## 2. judge-R（rubric 版 = rubric_ce 最终版）

- **输入**：题面；OLD 轮提交尾部；NEW 轮提交尾部（各 ≤ `char_cap`，头尾保留）；critic 给 NEW 轮的 check 一条。
- **三维评分**（0–10，整数）：
  1. `disconnection`：NEW 是否脱离了 OLD 已建立且未被推翻的步骤；
  2. `contradiction`：NEW 内部或与题面给定条件是否矛盾；
  3. `error`：NEW 中可定位的具体错误（须引用 ≤40 字原文）。
- **判决**：`score = max(三维)`；三维全 0 → KEEP；`score ≥ 8` → CUT；否则 UNSURE。（8 是 rubric_ce 冻结值，不再扫；三值化只是给 LR 估计用的分箱，LR 本身不含阈值。）
- **已有数据**：`experiments/hle400/t3/c3_rubric_ce.jsonl` 的 `per_switch`（1310 条边，映射到 freeze 边后 1185 条有判决、16 条 UNSURE）。**不需要重跑**。

## 3. judge-C（回收版 = 判 critic 是否过度反馈）

- **输入**：题面；critic 对 OLD 轮的 suspicion + check（一条）；OLD 轮提交尾部（被批评的对象）。**不给 NEW 轮**——这是它与 judge-R 的本质区别：它评价的是反馈，不是改动。
- **问题**：这条反馈所指控的缺陷，在 OLD 轮中是否**实际存在且足以推翻 OLD 答案**？
- **输出**：`OVER`（缺陷不存在 / 存在但不影响答案 / 指控的是题面未要求的东西）；`WARRANTED`（缺陷存在且推翻 OLD）；`UNSURE`。须引用 OLD 轮 ≤40 字原文作为依据，引不出则 UNSURE。
- **聚合语义**：OVER → 这次 switch 被视为 critic 误伤：NEW 侧 −log LR、OLD 侧 +log LR（方向由 LR 符号自动决定，不手工设）。
- **已有数据**：`qcut_mislead_mech.jsonl`（0–10 分，方案 A）可做预估；最终版按本节三值输出重跑一次：对象 = 全部 1201 条 switch 边 × N=2 ≈ 2400 次 flash 调用。
- **已知先验**（来自审计，仅作报告，不进聚合）：premise probe 75/81 NOT-ABOUT；mislead 0–10 评分 AUC 0.56。

## 4. 聚合器（共用，Bayes 加权投票）

```
对每个候选 c：
  s(c) = log n(c)                                  # n(c) = 候选出现轮数（= mode 的信息）
  对每条 switch 边 (a→b) 及其判决 v：
      s(key_b) += log LR(v);  s(key_a) -= log LR(v)
  pick = argmax s(c)，平局 → 最新出现
LR(v) = P(v | 修复边) / P(v | 破坏边)，Laplace(+1) 平滑，在 dev 的决定性边上估计
```

- 条件独立下 Bayes 最优；参数 = 每种判决一个 LR（judge-R 3 个，judge-C 3 个）；全部在 dev 估、test 冻结。
- 退化：所有 LR = 1 ⇔ mode。rubric_ce 的 elimination、node 投票、Q-CUT 的 CUT 规则、margin 门控，都是手工给 LR 赋值的特例。
- 实现：`scripts/lr_vote.py --verdicts <edge-verdict.jsonl> --fit even --apply odd`，边级判决文件统一格式 `{task_id, from_r, to_r, verdict}`。

## 5. 验收（预注册；每个 judge 分别报）

| 指标 | 定义 | "坍缩到 mode"的判据 |
|---|---|---|
| E1 边级准确率 | dev 决定性边上：CUT/OVER 落在破坏边 + KEEP/WARRANTED 落在修复边 的比例 | ≤ 0.65（基准 0.5；rubric_ce 实测 0.58，Q-CUT 0.58） |
| E2 LR | 每种判决的 LR 及 95% CI（dev） | 所有 CI 包含 1 |
| E3 test 净效 | dev 估 LR → test 应用，相对 mode 的 +/− 题数与 McNemar | \|净\| ≤ 3 或 p > 0.1 |
| E4 稳定性 | 反向（test 估 → dev 用）LR 符号是否与正向一致 | 任一符号翻转即判不稳 |

三条同时满足（E1 ≤ 0.65、E2 全含 1、E3 不显著）→ 该 judge 坍缩到 mode。两个 judge 都坍缩 → 结论"同模型 evaluator = mode"。任一 judge 过线 → 以 test 的 E3 为正式结果，不回头调 prompt。

## 6. 已有结果（judge-R 用冻结判决；judge-C 用方案 A 预估）

| judge | 判决 | 修复 | 破坏 | LR | 95% CI |
|---|---|---|---|---|---|
| judge-R (dev) | CUT | 12 | 12 | 0.90 | [0.42, 1.94] |
| | KEEP | 14 | 14 | 0.90 | [0.44, 1.84] |
| | UNSURE | 62 | 53 | 1.05 | [0.73, 1.51] |
| Q-CUT (all) | CUT | 44 | 50 | 0.78 | [0.52, 1.17] |
| | NO_CUT | 25 | 11 | 1.92 | [0.97, 3.81] |

judge-R：E1 = 0.58；E3 test = +2 −2；E4 反向 CUT LR 0.90 → 0.30，不稳。已满足坍缩判据。
judge-C：待最终版重跑后填表（预估 AUC 0.56 → 预期同样坍缩）。

## 7. 报告模板（论文 evaluator 一节）

1. 上限分解：A2 154/145、A3 195/136、C3 191/154；C3 可回收 37 题（平局 8 / 放弃 27 / 晚收敛 2）。
2. oracle：撤销全部 R→W = 173；只撤引用反馈的 = 165；盲撤 = 149 → 信息存在、对称。
3. 两个 judge 的边级混淆表 + LR 表（§6）。
4. 轨迹级对照（附录）：26 个无 gold 特征 AUC ≤ 0.59、dev/test 无一稳定（`scripts/switch_contrast.py`）。
5. 结论：switch 是修复还是破坏仅取决于旧答案对错；同模型 judge 两种框架均 58%；Bayes 最优加权退化为 mode。回收需要信息不对称（预防侧：abstaining critic；判断侧：非同模型 judge），列为 future work。

## 8. 待办

- [ ] `scripts/lr_vote.py`（§4），输入统一边级判决格式。
- [ ] judge-R：把 `c3_rubric_ce.jsonl` 的 per_switch 导出为边级判决文件；跑 lr_vote，填 §6。
- [ ] judge-C：按 §3 跑最终版（1201 边 × N=2），导出边级判决；跑 lr_vote，填 §6。
- [ ] 冻结表 evaluator 行：148 → "judge-R（freeze-key）：elimination 149 / node 152 / LR 加权 = mode"，注明旧值口径。
- [ ] `EVALUATOR_FINAL_QCUT.md` 顶部加一行：Q-CUT 作为 judge-R 的变体纳入本框架，不再单独报。

## 9. 修订历史

- **2026-11-06 核验器修正**：长度阈值由否决改为报告；归一化加 LaTeX 间距；原因：74 条一致判决被否中 54% 为真 verbatim 超长、3% 归一化伪影。prompt 未改、judge 输出未改。
