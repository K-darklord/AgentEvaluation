# A2′ = 扰动型安慰剂：执行规格（预注册）

> 目的：判定 critic arm（C2/C3）相对安慰剂 A2 的上限增益（+37/+44）来自**批评的具体内容**，还是来自**任何结构化、每轮必发的扰动**。
> A2 是"安抚"（告诉 solver 没发现问题），不是扰动；A3 用温度噪声达到同样上限（190）已暗示非特定扰动可能足够。A2′ 把这个假设变成可检验的 arm。
> 规则：先写本文件，再跑；§5 判读在看数前写死，不改。模板与约束沿用 `C2_BANK_FREE_CRITIC_SPEC.md`。

## 1. 切口（A2′ 与 C2 的全部差异）

| | C2 | A2′ |
|---|---|---|
| critic 输入 | 题面 + 当前答案 + CoT 尾部 | **无**（不读题、不读答案、不读 CoT） |
| critic 产出 | LLM 生成 1–3 条针对该答案的具体 suspicion + check | **模板**生成 k 条（k 分布匹配 C2：P(3)=.86 / P(2)=.11 / P(1)=.03），从 5 个 archetype 名中**不放回**抽 k 个，填入 C3 多条格式 |
| LLM 调用 | 每轮 1 次 | **0 次**（纯模板） |
| 其余 | — | 完全相同：solver prompt、`_feedback_message` 包装、never silent、max_rounds 10、early_stop 3、预算、T=0、rationale off、A-seeding |

**模板**（固定，不随题变；k 条按 C3 多条格式渲染，k∈{1,2,3}）：
```
A few possible error directions were inferred for this answer:

1. {ARCHETYPE_1} -- you may have {GENERIC_SUSPICION[ARCHETYPE_1]}.
   To check: {GENERIC_CHECK[ARCHETYPE_1]}.

2. {ARCHETYPE_2} -- you may have {GENERIC_SUSPICION[ARCHETYPE_2]}.
   To check: {GENERIC_CHECK[ARCHETYPE_2]}.
   …（共 k 条，逐条同式）
```
`GENERIC_SUSPICION` / `GENERIC_CHECK` 为每个 archetype 一句**与题无关**的通用描述（写入代码常量，附录 B 原文发布），例如
constraint-blind decimation → "discounted a constraint or condition stated in the problem" / "re-read the problem statement and list every stated constraint, then confirm the answer satisfies each"。五条句子在跑前写死，不得含任何题目、答案或领域词。

随机源：`random.Random(zlib.crc32(task_id) ^ round_index)`，可复现；每题每轮独立抽样（不放回抽 k 个，故同一轮内不重复；跨轮可重复）。

### §1 跑前修订（2026-11-08，预注册最终版）

在预注册原文基础上，跑前修订如下（未跑任何题、未看任何数）：

1. **archetype 数 = 5（不是 7）**：A2′ 匹配 critic 实际看到的词汇。C3 的 prompt 里只有去重后的 5 条（7-archetype 词汇里的 `memory_substitution`、`sign_normalization_slip` 在 deepseek 的 bank 中**没有实例**，从未进入任何 critic 调用）。抽 7 个会让安慰剂使用两个 C3 从未用过的名字，反而引入差异；故只用 5 个有实例、且是 C3 实际看到的去重词汇。
2. **archetype 名 = bank 原文**（`docs/ERROR_BANK_PROVENANCE.md` §3 表，逐字）：
   - `constraint-blind decimation`
   - `descriptor/label conflation`
   - `procedure truncation / omission`
   - `retrieval-abort`
   - `format / precision non-conformance`
   五句通用 suspicion/check 句沿用已通过版本（见附录 B），仅名改为上述原文；不同时扩到 7。
3. **随机源 = `zlib.crc32(task_id) ^ round_index`**（替代 `hash(task_id)`；Python `hash(str)` 受 `PYTHONHASHSEED` 盐化不可复现，crc32 跨进程/跨平台确定）。
4. **端点 + A-seeding**：`deepseek-v4-flash-payg`（payg，`DASHSCOPE_BASE_URL`；token-plan 配额已 429 耗尽）+ `A_SOURCE_TRAJ` 指向 `experiments/hle400_A/deepseek-v4-flash/loop_trajectories.jsonl`（与 C2 同法，round-0 复用 A 臂）。
5. **方向数匹配 C2（跑前修订）**：每轮先抽 k，`P(k=3)=.86`、`P(k=2)=.11`、`P(k=1)=.03`，再从 5 个名中**不放回**抽 k 个；模板按 C3 的多条格式（`1. … To check … 2. …`），包装器沿用 `_feedback_message`；summary 记 `k_draw_counts` 与 `archetype_draw_counts`。

## 2. 不动的（与 C2/C3 逐项一致）
模型 deepseek-v4-flash（端点与 C2 同为 payg，或与 C3 同为 token-plan——**先确认哪个可用，记录在 summary**）；thinking 16384 / margin 8192 / max_tokens 24576；max_rounds 10；early_stop_n 3；rationale_mode off；同 400 题；`--out-dir hle400_A2PRIME`。

## 3. 实现
1. `src/run_feedback_loop.py`：arm `"A2P"`；分支生成模板反馈（不构造 critic 对象）；`critic_direction` 记录 `{archetype_name: <抽到的名>, suspicion: <通用句>, check: <通用句>, template: true}`，保证 `switch_contrast.py` 等分析脚本可直接用。
2. summary 增加 `"template_critic": true`、`"archetype_draw_counts"`。
3. smoke：5 题，dump 反馈文本，确认不含题面/答案片段、五句通用句逐字一致。

## 4. 计分
T1 → T2 → T3 K=1 → 争议 K=3，规则复用 `t3_k3_adjudicate_and_recompute.py`（含 hle_201）；新变体按 `HLE_SCORER.md` §1.2 人工裁决并追加规则；三件套新增 `A2P`。

## 5. 预注册终点与判读

| 终点 | 定义 | 检验 |
|---|---|---|
| **主：上限** | 可选上限（freeze-key，最后出现轮判对） | A2′ vs C2、A2′ vs A2，配对 McNemar |
| 次 1 | mode（对称约定：A2′ 平局随机化与 A3 同法；另报 recency） | vs A3（随机）、vs C2、vs A2 |
| 次 2 | stay 不对称 + bootstrap CI；run-3 | 同 `persistence_analysis.py` 口径 |
| 次 3 | 每题 switch 数、R→W / W→R、均轮数、候选数 | 描述 |
| 次 4 | solver token（无 critic 成本） | 描述 |

**判读（写死）**
- **内容无作用**：A2′ 上限 ≥ C2 − 5 且 A2′ vs C2 的 mode 差 n.s. → 论文主语改为"结构化扰动 + 序列计数"；C2/C3 的"批评"降为扰动的一种实现；§1 贡献 2 相应改写。
- **内容有作用**：A2′ 上限 ≤ C2 − 15 且 p < 0.05 → 具体、有根据的批评是有效成分；§7 H1 的"结构"残差得以分解。
- **灰区**：其余 → 如实报告三臂（A2 / A2′ / C2），不下强结论。
- A2′ vs A2：无论如何都报（它回答"扰动 vs 安抚"），不作判读依据。

## 6. 禁止
不读结果后调模板或抽样分布；不用 HLE 内容写通用句；不改任何冻结文件的规则；INVALID 的 429 运行隔离不进统计。

## 7. 交付
代码 diff；`experiments/hle400_A2PRIME/...` + smoke dump；三件套 `A2P`；`docs/A2PRIME_RESULTS.md`（§5 全表 + 判读句，只填数）。
