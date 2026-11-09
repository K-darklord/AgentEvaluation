# Experiment: INT-07 T2 Judge Self-Evaluation Bias Test

## Experiment ID
INT-07-judge_bias

## Date
2026-09-16

## Hypothesis
Using DeepSeek-V4-Flash as both agent AND T2 judge creates self-evaluation bias.
The judge may be systematically more lenient (favoring its own outputs) or more
harsh (over-critiquing) compared to an independent judge model.

Switching T2 judge to DeepSeek-V4-Pro (different, more capable model) will
either:
- Reveal over-scoring (accuracy drops with independent judge)
- Reveal under-scoring (accuracy rises with more capable judge)
- Show no bias (accuracy unchanged)

## Evidence (Baseline)
- Same INT-05 trajectories.jsonl (50 tasks)
- Baseline (V4-Flash judge + 4000 chars): 54% (27/50) [from INT-05 eval]

## Method
- Control: T2_JUDGE_MODEL=deepseek-ai/DeepSeek-V4-Flash (baseline, 54%)
- Treatment: T2_JUDGE_MODEL=deepseek-ai/DeepSeek-V4-Pro (single variable change)
- T2_MAX_TRAJECTORY_CHARS=4000 (default, held constant)
- Same trajectories.jsonl (from INT-05 run)
- Same agent (V4-Flash)
- Same T1/T2 2-tier scoring logic

## Variables
| Variable | Control (baseline) | Treatment |
|---|---|---|
| T2_JUDGE_MODEL | deepseek-ai/DeepSeek-V4-Flash | deepseek-ai/DeepSeek-V4-Pro |
| T2_MAX_TRAJECTORY_CHARS | 4000 | 4000 (same) |
| Trajectories source | INT-05 (50 tasks) | INT-05 (50 tasks, same) |
| Agent model | V4-Flash | V4-Flash (same) |

## Expected Outcome
- If +5pp or more: V4-Flash was under-scoring (self too harsh)
- If -5pp or more: V4-Flash was over-scoring (self too lenient) - this would be the strongest interference signal
- If within +/-2pp: no significant self-eval bias
- Most likely: -3 to -5pp if self-eval bias exists (leniency is common in LLM self-eval)

## Status
RUNNING

## Status Update (2026-09-16 19:15)
**PAUSED** — V4-Pro 作为 judge 的推理成本约为 V4-Flash 的 10 倍以上，单次全量评测 (50 tasks × 3 轮 T2 voting) 成本过高。

### Resume Strategy (when budget allows)
**Option A (Cheap)**: 用 V4.1-Flash 或 R1 替代 V4-Pro 作为 judge
- 成本接近 Flash，仍能测试"自评 bias"假设（只要 judge ≠ agent 模型即可）
- 缺点：V4.1-Flash 与 V4-Flash 同源，可能仍有部分 bias

**Option B (Targeted)**: 只对 baseline 中判定边界题目 (final_score ∈ [0.4, 0.6]) 用 V4-Pro 重评
- 预计 5-10 题，V4-Pro 成本仅为全量的 10-20%
- 优势：聚焦真正可能翻盘的题目，统计信号更强

**Option C (Full)**: 完整 V4-Pro judge 跑 50 题
- 最严谨，但成本最高

**Recommended**: Option B（边界题目 + V4-Pro），平衡成本与统计价值。

## Status
PAUSED (awaiting cost approval)
