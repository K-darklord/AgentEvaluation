# Experiment: INT-06 T2 Judge Context Length Interference Test

## Experiment ID
INT-06-context_length

## Date
2026-09-16

## Hypothesis
T2_MAX_TRAJECTORY_CHARS=4000 truncates the agent trajectory sent to the LLM judge.
For long SEC 10-K filings (50K+ chars in trajectory), this truncation may cut off
key tool observations the judge needs to verify the answer correctly.

Increasing to 20000 chars will allow the judge to see more context, leading to
more accurate (and likely higher) scoring of correct answers.

## Evidence (Baseline)
- Reuses INT-05 trajectories.jsonl (50 tasks, max_steps=50)
- Baseline eval (T2_MAX_TRAJECTORY_CHARS=4000): 54% (27/50)
- Avg trajectory size: ~60KB per task (well above 4000 char limit)

## Method
- Control: T2_MAX_TRAJECTORY_CHARS=4000 (current default, 54%)
- Treatment: T2_MAX_TRAJECTORY_CHARS=20000 (single variable change)
- Same trajectories.jsonl (from INT-05 run, 50 tasks)
- Same model: DeepSeek-V4-Flash for both agent and T2 judge
- Same T1/T2 2-tier scoring logic
- Single variable changed: trajectory truncation length for T2 judge

## Variables
| Variable | Control (baseline) | Treatment |
|---|---|---|
| T2_MAX_TRAJECTORY_CHARS | 4000 | 20000 |
| Trajectories source | INT-05 (50 tasks) | INT-05 (50 tasks, same) |
| Agent model | V4-Flash | V4-Flash (same) |
| T2 judge model | V4-Flash | V4-Flash (same) |
| T1/T2 logic | unchanged | unchanged |

## Expected Outcome
- Accuracy may go up (judge sees more context, scores correct answers higher)
- OR may stay flat (judge already had enough context in 4000 chars)
- OR may go down (more context could confuse judge with irrelevant info)
- Most likely: small +/- 2pp shift; if >5pp, interference is confirmed

## Status
RUNNING

## Results (COMPLETED 2026-09-16 19:08)

### Primary Outcome
- **Hypothesis PARTIALLY CONFIRMED**: T2 trajectory truncation has small interference effect.
- Baseline (T2_MAX_TRAJECTORY_CHARS=4000): 54% (27/50)
- Treatment (T2_MAX_TRAJECTORY_CHARS=20000): 56% (28/50)
- **Delta: +2pp** (minimal, single-run)

### Error Distribution Comparison
| Metric | Baseline (4000) | Treatment (20000) | Delta |
|---|---|---|---|
| Accuracy | 54% (27/50) | 56% (28/50) | +2pp |
| complete_failure | 13 | 13 | 0 |
| numeric_error | 5 | 4 | -1 |
| factual_contradiction | 3 | 3 | 0 |
| qualitative_incomplete | 2 | 2 | 0 |
| Total errors | 23 | 22 | -1 |

### By Difficulty Comparison
| Difficulty | Baseline | Treatment | Delta |
|---|---|---|---|
| Easy | 68.18% (15/22) | 68.18% (15/22) | 0 |
| Medium | 50.00% (8/16) | 50.00% (8/16) | 0 |
| Hard | 33.33% (4/12) | 41.67% (5/12) | +8.34pp |

### By Category Comparison
| Category | Baseline | Treatment | Delta |
|---|---|---|---|
| Beat or Miss | 42.86% (3/7) | 57.14% (4/7) | +14.28pp |
| Other categories | unchanged | unchanged | 0 |

### Interpretation
1. **Minimal interference**: +2pp is within noise range (single-run, T2 temperature=0 but T1 is deterministic so 1 task flipping is the only signal)
2. **Hard tasks benefit most**: Hard +8.34pp, while Easy/Medium unchanged. Long trajectories on hard tasks benefit from more judge context.
3. **T1 unchanged**: Numeric accuracy didn't change (deterministic), confirming only T2 (semantic judge) is affected by trajectory truncation.
4. **Not a major bottleneck**: Unlike INT-05 (+6pp), INT-06 (+2pp) suggests T2 judge was already extracting key info in 4000 chars for most tasks.

### Caveats
- Single-run, T2 has temperature=0 so should be reproducible
- T2 judge self-eval bias (INT-07) not yet addressed
- Only 1 task flipped (Beat-or-Miss Hard), small sample limits statistical confidence

## Status
COMPLETED (2026-09-16 19:08)
