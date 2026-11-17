# 规格：token 对齐的 generic-doubt loop（预先写定，2026-11-15）

> 状态：**作者已确认（2026-11-15 21:47），可下达**。本文件写于任何相关运行之前；确认后不再修改判据。名称对照见 `INDEX.md` 第 2 节（A2P = generic-doubt loop，C2 = critique loop）。

## 1. 要回答的问题

critique loop 比两种安慰剂 loop 到达更多题，但它用的 token 是后者的 1.9–2.5 倍。事后分析（`REVIEW_RESPONSE_PLAN.md` A 项，`scripts/budget_matched_reach.py`）显示：把 critique loop 截断到安慰剂 loop 的 token 预算，它不再到达更多。但截断是单向的：安慰剂 loop 按"连续三次相同即停"的规则早早停止，从未用过那么多 token。

本实验做反方向的对照：**让 generic-doubt loop 一直跑到花掉与 critique loop 同样多的 token，它能到达同样多的题吗？**
- 能：critic 对 reach 的贡献可以由"让 loop 多跑、多花 token"解释，批评的内容不是必要的。
- 不能：在相同 token 下，批评仍带来通用怀疑带不来的正确答案。

## 2. 条件定义（代号 `A2PY`）

与 A2P 完全相同，只改停止规则：
- 模型：`qwen3.8-flash-payg`。选它的理由（先于运行写定）：三个模型中成本最低（约 36M token）、没有截断问题、critique loop 对 generic-doubt loop 的 reach 差距最大（49/16），检验效力最高；同时事后分析里它是"同预算下 critique loop 反而到达更少"（13/32）的模型，两个方向都有可能。
- 题目：同一 400 题。首答沿用 `experiments/rep200_A_qwen3.8-flash-payg/` 的第 0 轮（`A_SOURCE_TRAJ`），与其他条件相同。
- 反馈：A2P 的五句模板、条数分布（3/2/1 条的概率 .86/.11/.03）、随机种子规则全部不变；不读答案，不调用模型。
- solver 设置不变：温度 0，thinking 预算 16,384，输出上限 8,192，提示词一字不改。
- **停止规则**：取消"连续三次相同即停"。每道题的预算 B 取自 `experiments/hle400/t3/yoke_budget_qwen.json`（由 `scripts/make_yoke_budget.py` 从冻结的 critique loop 轨迹生成：各轮 solver 的 prompt + completion token，加每个反馈轮一次 critic 调用，critic 按回放均值 4,816 token 计；400 题合计 36.2M，中位数 7.4 万）。每轮结束后累计本题 solver 的 prompt + completion token（含第 0 轮）；**累计值达到或超过 B 即停**。上限 30 个反馈轮，触顶的题记录在案。
- 预算文件只含 token 数，不含任何对错信息。

## 3. 运行规则（与此前各规格相同）

1. 含接口失败轮的轨迹无效，整题重跑；报错文本不算答案。
2. 先跑 16 题健康度检查（沿用第三模型选型时的 16 题），**只回报运行健康度**：完成/超时、截断率、每题轮数、实际 token 与预算之比、触顶题数。不回报、不查看任何对错。健康度正常再跑全量。
3. 不改提示词、不调参数、不看中间对错。
4. 输出目录：`experiments/yoke_A2PY_qwen3.8-flash-payg/`。

## 4. 判分

与 qwen 其余条件相同的冻结流程（`scripts/gen_t3_sidecar_rep.py` 的口径）：截断轮为错 → 精确匹配 → grader（gpt-6-astra，K1）→ 已有裁决规则（同一实质答案在各条件下同判）。不新开争议复判。输出 `experiments/hle400/t3/is_correct_t3_sidecar_yoke.json`。

## 5. 读出（判据在此写定）

读出脚本 `scripts/yoked_readout.py` 在数据到齐后由分析方编写，只实现本节。

**两种口径。** 最后一轮通常会越过预算。
- 主口径（含越界轮）：计入 A2PY 实际跑的全部轮次。此时 A2PY 花的 token 不少于 critique loop，对"critic 有额外贡献"的结论偏保守。
- 辅口径（预算内）：只计累计 token 不超过 B 的轮次。

**检验。**
- **Y1（主检验）**：reached，critique loop 对 A2PY，精确 McNemar，双侧。
- Y2：reached，A2PY 对原 A2P（多跑本身是否提高 reach）。
- Y3：selected，critique loop − A2PY，符号翻转置换检验（10,000 次）与题目级 bootstrap 95% 区间。描述性。
- 描述量：每题轮数与候选数、实际 token、重复概率、触顶题数。

**判定。**
| 结果 | 结论 | 论文处理 |
|---|---|---|
| Y1 两个口径下 critique loop 都到达更多且 p < .05 | 在相同 token 下，critic 仍带来通用怀疑带不来的 reach（在该模型上） | §4.1 "Is it only more tokens?" 一段补一句，附录给全表 |
| Y1 主口径下不显著或方向相反 | 该模型上 critic 的 reach 增益可由多花的 token 解释 | 同一段如实写明；摘要第一条结果保持"at about twice the tokens … reaches no more"的现有措辞，并去掉任何暗示内容起作用的句子 |
| 两个口径结论不一致 | 没有定论 | 两个口径都报告，不下结论 |

无论哪种结果都写入论文。只有一个模型，结论限定在该模型上。Y2、Y3 不改变上述判定。

## 6. 成本与范围

约 36M token 的 solver 调用（与 qwen 的 critique loop 相当），加判分调用。不做第二个模型；若作者在看到结果后想在 MiniMax-M2.5 上重复，须另写一页规格，沿用本文件的判据。

## 7. 给执行 agent 的指令（确认后原样转发）

```
任务 Y1（规格：docs/COMPUTE_MATCHED_PLACEBO_SPEC.md，判据已冻结，只执行、不改判读）

1. 代码：在 src/run_feedback_loop.py 给 A2P 增加可选的"预算停止"模式。
   - 环境变量 YOKE_BUDGET_FILE 指向 experiments/hle400/t3/yoke_budget_qwen.json 时启用，读取其中 budget[task_id]。
   - 启用时：不使用"连续三次相同即停"；每轮结束后累计该题各轮 prompt_tokens + completion_tokens（含第 0 轮），累计 >= 预算即停；--max-rounds 30。
   - 其余（模板、条数抽样与种子、A 首答 seeding、solver 参数、提示词）与现有 A2P 完全一致。未设置该环境变量时行为不变。
   - 每条轨迹记录 yoke_budget、实际累计 token、是否触顶。
2. 先跑 16 题健康度检查（scripts/gate_16_candidates.py 用的同一组题），只回报：完成/超时、finish_reason=length 的比例、每题轮数、实际 token / 预算、触顶题数。不要计算或查看对错。回报后等待确认。
3. 确认后跑全量 400 题：MODEL=qwen3.8-flash-payg，--arm A2P --temperature 0，输出目录 experiments/yoke_A2PY_qwen3.8-flash-payg/，A_SOURCE_TRAJ 指向 experiments/rep200_A_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl。
4. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。
5. 判分：按 scripts/gen_t3_sidecar_rep.py 的冻结口径（截断为错 → 精确匹配 → astra K1 → 已有裁决规则），输出 experiments/hle400/t3/is_correct_t3_sidecar_yoke.json；不新开 K3 争议。
6. 完成后回报：轮数与 token 的描述统计、失败与重跑清单、文件路径。不要自行做 reach / selected 的比较，读出由分析方按规格第 5 节完成。
7. 不提交 audit/ 下的标注表与 key.json；提交信息沿用 [P2.x] 编号。
```
