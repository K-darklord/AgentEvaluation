# 第二模型复现规格（预注册）

> 目的：把 §5 的三条主结果从"一模型"变成"两模型"，或诚实地给出边界。只复现 §5；不跑 judge（§6 的结论是边界性陈述，不复现）。
> 规则：本文件写定后再抽题、再跑；判读在看数前写死。

## 1. 模型与数据
- 模型：`qwen3.8-flash`（config 已注册）；若其 thinking/预算配置无法与 deepseek 对齐则改 `glm-5.3`，二选一，跑前定并记录原因。
- 题目：**全部 400 题为主方案**。功效：主实验的 C2 vs A3 不一致对约 33/15，200 题时约 16/8（McNemar 功效 ≈ 50%），400 题 ≈ 85–90%；上限与持久性检验在 200 题已足够。执行分两段：先跑 `data/raw/hle/hle_replication_200.json`（四格分层抽样，种子 20261108），再跑其补集 `hle_replication_rest200.json`；**扩到 400 是现在预先决定的，与第一段结果无关，R1–R3 只在最终 n 上检验一次**。预算不足时 200 为回退，并在 §6 注明功效。
- 不用 deepseek 的任何轨迹、判决或 bank；该模型的 round 0 = 其自身 T=0 答案（A-seeding 用它自己的 A 臂）。

## 2. 臂
A（round 0）、A2（安慰剂）、A3（9 样本 T=0.7）、C2（自由批评，bank-free；critic = 同模型）、A2P（扰动安慰剂，模板，零 LLM）。不跑 C3（bank 是为 deepseek 蒸馏的，跨模型无意义）。

## 3. 常量
与主实验一致：max_rounds 10、early_stop 3、rationale off、T=0（A3 样本 0.7）。

thinking 预算对齐：`qwen3.8-flash-payg` 设 `thinking_budget = 16384`（与 deepseek 冻结预算一致），agent 侧 `max_tokens = 16384 + REASONING_CONTENT_MARGIN(8192) = 24576`。缺失该字段时 qwen 落到 `REASONING_BENCH_MAX_TOKENS = 8192`（推理+可见输出总量）；qwen 在 HLE 每轮 hidden CoT 均值 ~12.5k，会大面积 finish_reason=length 截断并判错，压低所有臂，故必须对齐。

预算对齐已核（A 臂前 16 题，2026-11-08）：reasoning_tokens ≤ 16384（max=9378）、completion_tokens ≤ 24576（max=9393）、finish_reason 全 stop（16/16）；reasoning_content 非空（16/16），确认 dashscope 的 qwen thinking 字段名 `reasoning_content` 被 agent.py 正确解析。

## 4. 计分
同协议：T1 → T2（deepseek-v4-pro）→ T3 astra K=1 → 争议 K=3；规则表复用并追加；sidecar 新文件 `is_correct_t3_sidecar_rep.json`。

## 5. 预注册检验（三条，都用对称约定：A3 平局随机化 300 次）
| # | 检验 | 主实验对应 | 复现成立 |
|---|---|---|---|
| R1 | C2.mode vs A3.vote 配对 McNemar | 157.4 vs 137.3，p=0.004 | 方向相同且 p<0.05（或 200 题功效不足时：方向相同且 95% CI 排除 0 的 Δ≥5%） |
| R2 | 上限 C2 vs A2 | 198 vs 154，p=4e-9 | 方向相同且 p<0.05 |
| R3 | stay 不对称 C2 > A2 | 1.9 vs 1.25 | C2 的 CI 下界 > A2 的点估计 |
| R4（若 A2P 已跑） | 上限 A2P vs C2 | 主实验判读 | 与主实验同一判读规则 |

判读：R1–R3 全成立 → "两模型复现"；部分成立 → 如实列表，§8 写明哪条未复现；全不成立 → 结论限定为 deepseek，标题加模型限定。
不以 200 题的结果反过来修改主实验的任何判读。

## 6. 成本
200 题 × (1 + ~4.9 + 9 + ~6.9 + ~6.9) ≈ 5 700 次 solver 调用 + ~1 400 次 critic 调用 + 计分。人工裁决量级 ≈ 主实验 K=3 的一半。

## 7. 交付
题单文件；五臂轨迹；sidecar/scores；`docs/REPLICATION_RESULTS.md`（§5 表，只填数）。
