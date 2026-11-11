# Paper Outline v2 — EGTE (精炼版, 2026-10-31)

> 以 `paper_ppt.md` 为核心思路；`paper_outline.md` / `docs/PAPER_DRAFT.md` 降为过程资料。
> 单一故事：**EGTE 作为 train-free 的 test-time 排除方法**。其他线全部删除或下沉。

---

## 0. 一句话 claim（全文只守这一句）

> 从模型自己在普通题集上的错误中离线蒸馏出一组**答案无关的错误机制**，用它驱动一个
> **不需要 gold、不需要训练、同一模型**的 test-time 循环（critic 激活 + evaluator 排除），
> 能在**bank 从未见过的更难题集（HLE）**上找回 self-consistency 采样找不到的正确答案。

**Falsification**：HLE-400 上 C3 的准确率不系统性高于 A3（paired McNemar 不显著且 Δ ≤ 0）→ claim 不成立。

---

## 1. Introduction（1 页）

1. 现状：test-time scaling 的主流是采样 + 投票（self-consistency）；正确答案往往"出现过但没被保住"。
2. 问题：内在自我纠错不可靠（Huang 2023），需要外部信号；但 PRM / verifier 需要训练和标注。
3. 本文：外部信号 = **error bank**（模型自己的历史错误，离线蒸馏成答案无关的机制），运行时**只排除错的，不给正确方向打分**。
4. 三个 contribution：
   - **C1 中间对象**：答案无关的 error mechanism（class-level `mechanism` + `check_procedure`），跨题、跨 family 可迁移，gold 只在离线蒸馏时可见。
   - **C2 机制**：三角色 train-free 循环（distiller 离线 / critic 在环 / evaluator 事后），用 EIR/ECR 两态链解释"为什么有效、何时有效"。
   - **C3 证据**：HLE-400 上 C3 > A3（out-of-family + 更难）；eliminator on/off 隔离 evaluator 贡献；跨 family 的 in-domain 题集作 sanity。
5. 删除：26 pp FAB 伪缺口、capability curve、RSI/递归自改进（移到 §7）。

## 2. Related Work（≤ 1 页，三条线，每条以 "unlike X, we …" 收尾）

- Test-time scaling / self-consistency / best-of-N + verifier → 它们需要正向打分或大量采样。
- Self-correction 与外部反馈（Huang 2023, Reflexion, Self-Refine, LLM-as-judge）→ 反馈来源不是模型自身历史错误。
- Learn-from-mistakes（Mistake Notebook, PRISM, Cliff, LANPO, Agent-R/TAPO/LEMMA; EIR/ECR 词汇源自 Liu & Meng）→ 它们记忆实例或做蒸馏训练；我们**不训练**、**答案无关**、**只排除**、**仅在答案发生 transition 时介入**。

## 3. Method: EGTE

### 3.1 概览与角色（Fig 2）
solver（生成）/ scorer（冻结、唯一的最终 gold 读者）之外，三个策略角色、各自一次独立调用、**同一基础模型**：

| 角色 | 时态 | 读 gold? | 产出 | 优化量 |
|---|---|---|---|---|
| distiller | 离线 | 是 | 答案无关 `mechanism` + `check_procedure` + `trigger` | 可复用的排除规则 |
| critic | 在环 | 否 | 1–3 条 suspicion + 需复核的步骤 | 激活 `P_act` ↑（代价：带来 EIR） |
| evaluator | 事后、仅在 transition | 否 | CUT / KEEP / UNSURE → elimination + mode 锁定 | 压制 EIR，保留 ECR |

### 3.2 Error-mechanism distillation（C1）
- 正文只讲：实例错误 → 按"错误动词"聚类 → 跨 benchmark archetype（当前 7 个），每条带 gold-free `check_procedure`。
- 铁律：per-model bank；永不写具体数值/分子/选项。
- L1/L2/L3 的构建细节 → Appendix A。

### 3.3 Critic（Stage A, activation）
读题、已提交答案、隐藏 CoT、archetype 词表 → 判定最可能违反的机制 → 发出 suspicion。永不读 gold、永不给概率、永不给答案。

### 3.4 Evaluator（Stage B, elimination + lock）
- 只看答案 **切换边**；三维判分（contradiction / error / disconnection），`error` 必须回链到 bank；用 `max(contradiction, error)` 决定 CUT。
- 裁决：CUT（回退旧答案）/ KEEP（接受新答案）/ UNSURE（两者保留）；聚合 = elimination + mode，全 UNSURE 退回 mode。
- 最终固定 `rubric_ce`；rubric_v5、knob 扫描不进正文。

### 3.5 EIR/ECR 两态链（机制解释，半页）
- `final = init + ECR − EIR`；迭代有益当且仅当 `ECR/EIR > Acc/(1−Acc)`；稳态 `ECR/(EIR+ECR)`（标准两态马尔可夫链，引文即可，不作为本文 proposition）。
- 映射：critic 同时抬高 ECR 与 EIR；evaluator 只压 EIR。这是"为什么两段都需要"的全部论证。
- 删除 Prop 1（排除 vs 打分不等式）：降级为 §6 一句 motivation。

## 4. Experimental Setup

- **模型**：deepseek-v4-flash（solver = critic = evaluator）。
- **Bank 来源 vs 评测目标**（必须一张表写清，这是 reviewer 第一个会查的）：
  - bank：GSM8K / MATH-500 / MMLU-Pro / BFCL / AIME / BBH / GPQA 上的历史错误 → L3 bank；
  - 主评测：**HLE-400**（bank 从未包含 HLE 任何题）；
  - in-family 题集：仅作 sanity / 天花板说明，不作主证据。
- **Arms**（Tab 1）：A（bare T=0）/ A2（neutral placebo loop）/ A3（SC, T=0.7, N=10）/ C3（critic + evaluator）/ A3C3（A3 种子 + C3 循环）。删除 C（weak critic）。
- **冻结运行标准**：max_tokens 8192、max_rounds 10、early_stop 3、除 A3 round-0 外全部 T=0。
- **指标**：accuracy（scorer 判定）；tokens-per-correct（**含 critic + evaluator 所有调用**）；EIR / ECR（按全样本所有 round 的 transition 机会估计）；paired McNemar。
- **两个假设**：H1 激活——C3 的 `P_act ≥ A3`；H2 锁定——eliminator on − off > 0。

## 5. Results（主表 = HLE-400）

- 5.1 主表：HLE-400 × {A, A2, A3, C3, A3C3} × {acc, tokens/correct, EIR, ECR, McNemar}。
- 5.2 H1：激活率 C3 vs A3（correct appeared ≥1 次）。
- 5.3 H2：eliminator on/off（Stage B 单独贡献）；elimination+mode vs 纯 mode。
- 5.4 In-family 题集一张小表（含天花板说明；无区分度的 benchmark 删）。
- 5.5 两三个 transition 案例（Fig 3）：轨迹 + critic suspicion + evaluator 裁决，说明排除可归因于真实机制。
- 删除：flip19、knob ablation、rubric_v5、settle-vs-final（如需保留，Appendix 一句）。

## 6. Discussion / Limitations

- 单模型；HLE-400 的 n 与显著性；evaluator 不能可靠 abstain；按题型的差异（MCQ vs 开放答案）。
- "排除比打分便宜"只作为设计动机陈述，不作为已验证结论。
- 更强模型对照未完成 → 明确列为 limitation。

## 7. Future Work：outer loop（递归 bank 精炼）

- 本文展示了**一个 cycle**：失败 → 蒸馏 → bank → test-time 排除。
- 延展：每轮评测后把新错误蒸馏回 bank（distiller 仍是唯一 gold 读者；评测集永不入 bank）；作为 agent 中的一种持续运行模式。
- 只描述，不作 claim；S1–S3 可作为未来验收标准列出。

## Appendices

- A：L1→L2→L3 蒸馏流程、7 个 archetype 定义、prompt。
- B：critic / evaluator 完整 rubric 与 prompt；CUT/KEEP/UNSURE 形式定义。
- C：冻结标准、seed、代码 tag（REPRODUCIBILITY）。
- D：更多 transition 案例。

## 图表清单

- Fig 1：EGTE 一个 cycle 的总览（离线蒸馏 → 在线排除）。
- Fig 2：三角色流水线叠在 EIR/ECR 两态链上。
- Fig 3：一条 HLE 轨迹的 transition 证据链。
- Tab 1：arms。Tab 2：bank 来源 vs 评测目标。Tab 3：HLE-400 主表。Tab 4：eliminator on/off + in-family 小表。

---

## 术语取舍

| 保留（正文） | 下沉（Appendix / 一句带过） | 删除 |
|---|---|---|
| EGTE, distiller / critic / evaluator, error bank, archetype, EIR / ECR, CUT / KEEP / UNSURE, A/A2/A3/C3/A3C3, eliminator on/off | L1/L2/L3, settle / mode, `check_procedure` / `trigger`, rubric 三维, P_act | hard slice（改为 HLE 本身）, flip19, knob (`keep`/`vote_mode`/`weight_by`), rubric_v5, C arm, astra, 26 pp FAB, RSI, Prop 1/2, metacognition |
