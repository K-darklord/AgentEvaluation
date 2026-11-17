# 规格：token-yoked generic-doubt control（v2.1，2026-11-15 23:55，先于任何全量运行）

> 状态：**作者已确认要跑；本版为下达前的最终版**。v1（同日 21:40，文件名 `COMPUTE_MATCHED_PLACEBO_SPEC.md`，现存 `docs/_deprecated/20261115_v13_alignment/`）在外部意见后修订：改名、写明它匹配的是什么、Y1 与 Y2 联合解释、上限与越界的处理、统计功效。修订时没有任何相关运行存在（`experiments/` 下无 `yoke_*` 目录）。下达后判据不再修改。
> 名称对照见 `INDEX.md` 第 2 节（A2P = generic-doubt loop，C2 = critique loop）。

## 1. 这个对照回答什么，不回答什么

critique loop 比 generic-doubt loop 到达更多题，但花的 token 是安慰剂 loop 的 1.9–2.5 倍。generic-doubt loop 按"连续三次相同即停"自行停止，从未花过那么多 token。

**回答的问题**：让 generic-doubt loop 一直跑到花掉与 critique loop 同样多的 token，它能到达同样多的题吗？也就是，critique loop 的 reach 优势是否只是"多跑、多花 token"。

**它匹配的是总 token，不是 critic 调用。** 本条件没有 critic 调用，多出来的 token 全部花在 solver 的通用怀疑轮次上。因此：
- 它能排除的解释："只要让 loop 带着通用怀疑多跑同样多的 token，就能到达同样多"。
- 它不能排除的解释："一次读了题目和推理过程的额外模型调用"本身起作用，而与批评的内容无关。把内容与调用分开需要另一种对照（例如调用照常但内容被替换），本规格不做。
- 它不涉及 selected 的确认性检验的功效，也不涉及单一 benchmark 的外推问题。

论文里称它为 **token-yoked generic-doubt control**，不称 compute-matched placebo。

## 2. 条件定义（代号 `A2PY`）

与 A2P 完全相同，只改停止规则：
- 模型：`qwen3.8-flash-payg`。理由（先于运行写定）：三个模型中成本最低（约 36M token）、没有截断问题、critique loop 对 generic-doubt loop 的 reach 差距最大（49/16），功效最高。
- 题目：同一 400 题。首答沿用 `experiments/rep200_A_qwen3.8-flash-payg/` 的第 0 轮（`A_SOURCE_TRAJ`）。
- 反馈：A2P 的五句模板、条数分布（3/2/1 条的概率 .86/.11/.03）、随机种子规则不变；不读答案，不调用模型。
- solver 设置不变：温度 0，thinking 预算 16,384，输出上限 8,192，提示词一字不改。
- **停止规则**：取消"连续三次相同即停"。每道题的预算 B 取自 `experiments/hle400/t3/yoke_budget_qwen.json`（`scripts/make_yoke_budget.py` 从冻结的 critique loop 轨迹生成：各轮 solver 的 prompt + completion token，加每个反馈轮一次 critic 调用，critic 按回放均值 4,816 token 计；400 题合计 36.2M，每题中位数 7.4 万）。每轮结束后累计本题 solver 的 prompt + completion token（含第 0 轮）；**累计值达到或超过 B 即停**。
- **轮数上限**：100 个反馈轮（v2.1 更正，见文末；v2 为 30）。触顶的题照常计入，逐题记录。
- 预算文件只含 token 数，不含任何对错信息。

## 3. 运行规则

1. 含接口失败轮的轨迹无效，整题重跑；报错文本不算答案。
2. 先跑 16 题健康度检查（沿用第三模型选型时的 16 题），**只回报运行健康度**：完成/超时、截断率、每题轮数、实际 token 与预算之比、触顶题数。不回报、不查看任何对错。健康度正常再跑全量。
3. 不改提示词、不调参数、不看中间对错。
4. 输出目录：`experiments/yoke_A2PY_qwen3.8-flash-payg/`。

## 4. 判分

与 qwen 其余条件相同的冻结流程（`scripts/gen_t3_sidecar_rep.py` 的口径）：截断轮为错 → 精确匹配 → grader（gpt-6-astra，K1）→ 已有裁决规则。不新开争议复判。输出 `experiments/hle400/t3/is_correct_t3_sidecar_yoke.json`。

## 5. 读出（判据在此写定）

读出脚本 `scripts/yoked_readout.py` 在数据到齐后由分析方编写，只实现本节。

### 5.1 token 是否对齐（先于任何对错读出检查）
- 报告 A2PY 的总 token 与 critique loop 总 token（36.2M）之比，以及触顶题数。
- **对齐成立** = 含越界轮的总 token 在 critique loop 总量的 95%–120% 之间，且触顶题不超过 20 道。
- 对齐不成立时仍按下文读出，但结论一律标为"token 未对齐，不作判定"，并在论文里照此写。

### 5.2 两种口径（越界的处理）
最后一轮通常会越过预算。
- 主口径（含越界轮）：计入 A2PY 实际跑的全部轮次。A2PY 花的 token 不少于 critique loop，对"critique loop 仍领先"偏保守。
- 辅口径（预算内）：只计累计 token 不超过 B 的轮次。
- 敏感性：去掉触顶的题后重复 Y1。

### 5.3 检验
- **Y1（主检验）**：reached，critique loop 对 A2PY，精确 McNemar，双侧，α = .05。
- **Y2**：reached，A2PY 对原 A2P，同上。它回答"多跑通用怀疑轮次本身是否提高 reach"，与 Y1 一起解释。
- Y3：selected，critique loop − A2PY，符号翻转置换检验（10,000 次）与题目级 bootstrap 95% 区间。描述性，不参与判定。
- 描述量：每题轮数与候选数、实际 token、重复概率、新增轮次里首次出现正确答案的比例。

### 5.4 功效（Y1）
现有数据里 critique loop 对 A2P 的不一致对是 49/16（差 33）。若 A2PY 追回一部分差距：

| 剩余差距 | 预期不一致对 | Y1 检出概率 |
|---|---|---|
| 全部保留 | 49/16 | 99% |
| 保留四分之三 | 46/21 | 88% |
| 保留一半 | 43/27 | 45% |
| 保留三分之一 | 42/31 | 20% |

所以 Y1 能可靠检出"差距大部分保留"，对"差距减半"只有约一半把握。**Y1 不显著不等于差距消失**；此时必须同时报告不一致对与 A2PY 的 reached 数，由读者判断。

### 5.5 判定（Y1 与 Y2 联合）

| Y1：critique 对 A2PY | Y2：A2PY 对 A2P | 结论（限 qwen） | 论文措辞 |
|---|---|---|---|
| 两个口径都显著领先 | 任意 | reach 优势不只是多花 token | "not merely more tokens"：通用怀疑花同样多的 token 到达不了同样多。同时写明这不区分批评内容与 critic 调用 |
| 主口径不显著 | A2PY 显著多于 A2P | 多花 token 的通用怀疑追回了差距（全部或一部分） | "consistent with computation"：reach 优势与多花的 token 相容。不写成"内容不重要"；给出不一致对与功效 |
| 主口径不显著 | A2PY 不多于 A2P | 没有定论：多跑并未提高 reach，却也检不出与 critique loop 的差别 | 两项都报告，不下结论 |
| 两个口径结论不一致 | 任意 | 没有定论 | 两个口径都报告，不下结论 |
| 主口径下 A2PY 显著多于 critique | 任意 | 同样的 token 花在通用怀疑上到达更多 | 如实写明，并把 §4.1 关于 critic 的表述相应收窄 |

Y1 不显著时报告不一致对与区间，不写"无效果"。无论哪种结果都写入论文（§4.1 "Is it only more tokens?" 一段与附录 "Token-Yoked and Content Controls"）。只有一个模型，结论限定在该模型上。

## 6. 成本与范围

约 36M token 的 solver 调用，加判分调用。不做第二个模型；若作者看到结果后想在 MiniMax-M2.5 上重复，另写一页规格，沿用本文件的判据。

## 7. 给执行 agent 的指令（原样转发）

```
任务 Y1（规格：docs/TOKEN_YOKED_CONTROL_SPEC.md v2，判据已冻结，只执行、不改判读）

1. 代码：在 src/run_feedback_loop.py 给 A2P 增加可选的"预算停止"模式。
   - 环境变量 YOKE_BUDGET_FILE 指向 experiments/hle400/t3/yoke_budget_qwen.json 时启用，读取其中 budget[task_id]。
   - 启用时：不使用"连续三次相同即停"；每轮结束后累计该题各轮 prompt_tokens + completion_tokens（含第 0 轮），累计 >= 预算即停；--max-rounds 100。
   - 其余（模板、条数抽样与种子、A 首答 seeding、solver 参数、提示词）与现有 A2P 完全一致。未设置该环境变量时行为不变。
   - 每条轨迹记录 yoke_budget、实际累计 token、是否触顶（跑满 100 个反馈轮仍未达到预算）。
2. 先跑 16 题健康度检查（scripts/gate_16_candidates.py 用的同一组题），只回报：完成/超时、finish_reason=length 的比例、每题轮数、实际 token / 预算、触顶题数。不要计算或查看对错。回报后等待确认。
3. 确认后跑全量 400 题：MODEL=qwen3.8-flash-payg，--arm A2P --temperature 0，输出目录 experiments/yoke_A2PY_qwen3.8-flash-payg/，A_SOURCE_TRAJ 指向 experiments/rep200_A_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl。
4. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。
5. 判分：按 scripts/gen_t3_sidecar_rep.py 的冻结口径（截断为错 → 精确匹配 → astra K1 → 已有裁决规则），输出 experiments/hle400/t3/is_correct_t3_sidecar_yoke.json；不新开 K3 争议。
6. 完成后回报：轮数与 token 的描述统计（总 token、与 36.2M 之比、触顶题数）、失败与重跑清单、文件路径。不要自行做 reach / selected 的比较，读出由分析方按规格第 5 节完成。
7. 不提交 audit/ 下的标注表与 key.json；提交信息沿用 [P2.x] 编号。
```

## 更正记录

**v2.1（2026-11-15 23:55）：轮数上限由 30 改为 100。** 依据只有 16 题健康度检查的运行统计，没有查看任何对错。检查中已有一题跑满 30 轮只花掉预算的 56%：答案稳定后每轮的 token 很少，要花完预算需要更多轮。用冻结的 generic-doubt 运行里逐题的每轮 token 重新估计，上限 30 时约 18% 的题（约 70 道）会触顶，远超 5.1 节"触顶题不超过 20 道"的对齐判据，实验将因 token 未对齐而无法判定；上限 60 时约 5%，上限 100 时约 0.5%。v2 第 2 节里"中位数约 9 轮、第 90 百分位约 23 轮"的估计用的是全体平均的每轮 token，低估了尾部。上限改动不增加 token 总量（总量由预算决定），只延长少数题的运行时间。5.1 节的对齐判据不变。
