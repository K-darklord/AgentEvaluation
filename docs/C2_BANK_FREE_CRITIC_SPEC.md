# C2 = bank-free critic：执行规格（给执行 agent）

> 状态：预注册。本文件写定后不得因结果修改 §5 判据。
> 目的：判定 C3 相对 A2 的效果（上限 191 vs 154，stay 不对称 1.5 vs 1.25）来自 error bank 的内容，还是来自"结构化批评"本身。
> 读者须先读：`docs/HLE400_FROZEN_DATA.md`（C3 冻结设置与数字）、`docs/HLE_SCORER.md` §1.2（计分协议）、`src/strong_critic.py`、`src/run_feedback_loop.py`。

## 0. 命名冲突（先处理）

`run_feedback_loop.py` 里已有一个历史 arm `"C2"`（TF-IDF top-3 critic，`Level3Critic.topk`），从未在 HLE 上跑过，论文不报。
- 把该分支改名为 `"C2TFIDF"`（`--arm` choices、第 848 行 `if arm == "C2"`、第 1053 行 `if arm in ("C","C2")`、help 文本）。
- 新 arm 取名 `"C2"` = bank-free strong critic。全库 grep `"C2"` 确认没有其他引用（`analyze_hle_activation.py --arms` 默认值等）。

## 1. bank 在测试时的足迹（事实，已核）

`StrongCritic._vocab()` 把 `experiments/l0_distill_v1/level3_bank_deepseek-v4-flash.json`（24 条）按 `id` 去重为 **5 条**，以
"Wrong-execution vocabulary (pick from THESE only)" 注入 user prompt，每条 = 名称 + 实例级定义 + 实例级 check_procedure。
其余 19 条测试时不出现。C3 的输出结构（1–3 条 `{id, suspicion, check}`、never silent、answer-free 铁律）由 SYSTEM 与格式段规定，与 bank 无关。
critic 失败时 C3 回退到 `Level3Critic.topk`（TF-IDF，也读 bank）。

## 2. 切口：C2 与 C3 的全部差异（只有以下四处）

| # | 位置 | C3 | C2 |
|---|---|---|---|
| 1 | `_build_user` vocabulary 块 | 5 条词汇 + "pick from THESE only" | **整块删除** |
| 2 | `_build_user` 输出格式 `"id"` 行 | `the vocabulary name you invoke, verbatim from the list above` | `a short label (at most 4 words) naming the kind of shortcoming` |
| 3 | `SYSTEM` | `...using ONLY the answer-free wrong-execution vocabulary supplied below, identify...` | `...using your own judgement of where answers to such questions typically go wrong, identify...`（其余逐字相同） |
| 4 | `feedback()` 的 except 回退 | `Level3Critic.topk`（读 bank） | **重试 1 次**；仍失败 → 返回 `(A2_PLACEBO_FEEDBACK, [], None)`，并把 `critic_fallback=True` 写进该轮记录 |

其余一切（铁律四条、"Speak only in possible"、JSON only、CoT tail 与 `CRITIC_REASONING_BUDGET=6000`、`STRONG_CONTENT_MARGIN`、T=0、同模型）逐字不动。

## 3. 代码改动清单

1. `src/strong_critic.py`
   - 新增 `SYSTEM_BANK_FREE`（按 §2-3）。
   - `StrongCritic.__init__(self, entries, model_entry, bank_free: bool=False)`；`load(cls, model, bank_dir=None, bank_free=False)`。`bank_free=True` 时 `entries=[]`、`self._weak=None`。
   - `_build_user`：`if not self.bank_free:` 包住 vocabulary 块；`"id"` 行按 §2-2 二选一。
   - `feedback()`：`bank_free` 时 except 分支按 §2-4；计数器 `self.fallback_count`。
2. `src/run_feedback_loop.py`
   - §0 改名。
   - `--arm` choices 加 `"C2"`；分支 `arm in ("C3","A3C3","C2")` 走 strong critic 路径（含 CoT tail）；critic 构造 `StrongCritic.load(name, bank_free=(arm=="C2"))`。
   - 轨迹每轮记录新增 `critic_fallback: bool`（C3 可为 None）。`critic_direction` 结构不变（`archetype_name` = 自拟标签，`archetype_id` = None）。
   - `loop_summary.json` 增加 `"bank_free": true` 与 `"critic_fallback_rounds"`。
3. 不改：`_early_stop_key`、`_carries_forward`、`_feedback_message`、early-stop、任何计分代码。

## 4. 运行

1. **复现 C3 的全部设置**：以 `experiments/hle400_C3/loop_summary.json` 和 `docs/HLE400_FROZEN_DATA.md` 为准——`--task-set hle`、`--models deepseek-v4-flash`、`--max-rounds 10`、`--early-stop 3`、`--temperature 0`、`--rationale-mode off`、`--tier C`、并发 6、`CRITIC_HOLD_ON_REPEAT=0`、思考预算 16384 / margin 8192 / max_tokens 24576（按 C3 当时的 config/env，先核再跑）。`--out-dir hle400_C2`。
2. **Smoke（必做）**：`--tasks hle_001,hle_002,hle_003,hle_004,hle_005`；dump 一次 critic 的完整 user+system prompt；`grep` 五个 bank 名称（constraint-blind decimation / descriptor/label conflation / procedure truncation / retrieval-abort / format / precision non-conformance）与 "vocabulary"，**必须零命中**；确认 JSON 解析成功、`archetype_name` 为自拟标签。
3. 全量 400 题。断点续跑用 `--out-dir hle400_C2`。
4. 跑完对比 `loop_summary.json` 与 C3 的除 `run_id/arm/bank_free` 外逐字段相同；不同即作废重跑。

## 5. 计分（与 C3 同协议，不得简化）

- `src/hle_t3_stage.py` 同参数跑 T1 → T2（deepseek-v4-pro FN 救回）→ T3 astra K=1；争议 K=3。
- K=3 裁决规则复用 `scripts/t3_k3_adjudicate_and_recompute.py` 的逐题规则表；**新答案变体**按 `HLE_SCORER.md` §1.2 协议逐条人工裁决，追加到规则表并记录于 `docs/HLE400_T3_SECOND_AUDIT.md` 新一节 "C2"。
- 截断规则、两段式投票、`_mode_idx/_settle_idx` 完全一致；输出追加 `arms.C2` 到 `is_correct_t3_sidecar_v2.json`、`t3_final_scores_v2.json`、`transition_metrics_v2.json`（备份旧文件）。
- 这一步是本实验最大的人工成本（C3 当时 ~70 条逐条复核），不可跳过。

## 6. 预注册终点与判据

| 终点 | 定义 | 检验 |
|---|---|---|
| **主：上限 pass@trajectory** | 轨迹中出现过正确 key 的题数（= activation；C3 191、A2 154） | C2 vs C3 配对 McNemar |
| 次 1 | stay 不对称（正确/错误答案逐步 stay 率之比；C3 1.5、A2 1.25） | `scripts/persistence_analysis.py` 的 bootstrap CI |
| 次 2 | mode / settle / final / init | McNemar，仅报告 |
| 次 3 | R→W / W→R / W→W 计数、每题 switch 数、run-3 复合 | 描述 |
| 次 4 | solver + critic tokens | 描述 |
| 次 5 | 回退率；自拟标签分布（事后映射到 5 个 bank 名称，仅描述，不进任何判据） | 描述 |

**判读（写死）**
- **bank 有效**：C2 上限 ≤ C3 − 15 且 p < 0.05，或不对称 CI 与 C3 不重叠且更低 → 标题保留 error-guided；§机制加"内容来源"一段。
- **bank 无效**：C2 上限 ≥ C3 − 5 且不对称 CI 重叠 → 效果来自结构化批评本身；标题主语改 critique-induced persistence；§3.2 bank 降为实现细节。
- **灰区**：其余情况 → 加跑 C3GV（保留 5 个名称，定义/check 换为不看 bank 实例的抽象一句话）；仍灰则三臂如实报告，不下强结论。
- mode 差异不作判据（400 题功效不足已在 evaluator 分析中证明）。
- 回退率 > 5% → 结果标注 "critic 可用性受限"，并报告剔除回退轮后的敏感性分析。

## 7. 交付物

1. 代码 diff（§3），含 §0 改名。
2. `experiments/hle400_C2/deepseek-v4-flash/loop_trajectories.jsonl` + `loop_summary.json` + smoke 的 prompt dump。
3. 计分三件套中新增的 `arms.C2`，及 K=3 新规则与审计记录。
4. `docs/C2_RESULTS.md`：§6 全表 + 判读结论（只填数，不改判据）。
5. `docs/HLE400_FROZEN_DATA.md` 新增 C2 行；`docs/ERROR_BANK_PROVENANCE.md` 补一句"测试时 critic 实际看到去重后 5 条词汇"。

## 8. 禁止事项

- 不得改 C3 的任何冻结文件；不得重跑 C3/A2/A3。
- 不得在看过 C2 结果后调整 prompt、回退策略或判据。
- 不得用 HLE 题或 HLE 轨迹生成任何词汇/示例进 critic prompt（bank 永不含 HLE 的约束同样适用于 C2）。
- 不得把 C2 的自拟标签回填到 bank。
