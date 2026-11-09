# Experiment: INT-05 max_steps Interference Test

## Experiment ID
INT-05-max_steps

## Date
2026-09-16

## Hypothesis
max_steps=25 prematurely terminates model search, causing "Not found" results.
Increasing to 50 will allow the model to complete search and find answers for some tasks.

## Evidence (Baseline)
- 20/20 "Not found" tasks hit >=24 steps (100%)
- 9/30 correct tasks hit >=24 steps (30%)
- Not found avg steps: 30.7, Correct avg: 18.8
- Baseline accuracy: 48% (24/50)

## Method
- Control: v3 with max_steps=25 (current baseline, 48%)
- Treatment: v3 with max_steps=50 (single variable change)
- All other parameters held constant
- Same model: DeepSeek-V4-Flash-0731
- Same test set: FAB 50 public tasks
- Same evaluation: T1/T2 2-tier scoring

## Expected Outcome
- Accuracy increase: 48% → 55-60% (+7-12pp)
- "Not found" decrease: 20 → 10-15
- Some tasks that were cut off at step 25 will find answers with more steps

## Variables
| Variable | Control (baseline) | Treatment |
|---|---|---|
| max_steps | 25 | 50 |
| Model | V4-Flash-0731 | V4-Flash-0731 (same) |
| Test set | FAB 50 public | FAB 50 public (same) |
| Evaluator | T1/T2 2-tier | T1/T2 2-tier (same) |
| All other params | unchanged | unchanged |

## Git References
- Baseline: tag v3-interference-fix-60pct, commit fe225bc (48% on 50 tasks)
- Treatment: will tag after experiment

## Status
RUNNING

## Incident Log

### Incident 1: Race condition (2026-09-16 17:12)
- **Type**: Test harness bug (NOT an LLM interference)
- **Root cause**: Two `runner.py` processes (PID 27334 @ 16:23, PID 28288 @ 16:44) wrote to the same `output/trajectories.jsonl` simultaneously. The file is opened with `ft.open("w", ...)` in `runner.py:40` without a file lock, so concurrent `ft.write(json.dumps(record) + "\n")` calls can interleave at the OS level.
- **Impact**: Line 12 of `trajectories.jsonl` became corrupt — partial JSON (8170 chars of SEC filing text, no opening brace). Line 11 and Line 13 both contain `task_id=fab_011`, meaning both processes solved the same task and wrote to the same file.
- **Evidence**: `experiments/20260916_int05_max_steps/CORRUPT_LINE_EVIDENCE.txt`
- **Fix applied at runtime**: Killed duplicate process (PID 28288) at 17:12 to prevent further corruption. Main process (PID 27334) continues.
- **Fix needed in code**: `runner.py` should either (a) use file locking, or (b) refuse to start if `trajectories.jsonl` already exists and is non-empty, or (c) write each run to a unique file named with `run_id`.
- **Cleanup plan**: After the main process finishes, remove the corrupt line 12 and the duplicate `fab_011` entry (keep only the main process's record, i.e., line 11) before running the evaluator.

## Results (COMPLETED 2026-09-16 18:56)

### Primary Outcome
- **Hypothesis CONFIRMED**: max_steps=25 was an interference. Increasing to 50 improved accuracy.
- Baseline (max_steps=25): 48% (24/50)
- Treatment (max_steps=50): 54% (27/50)
- **Delta: +6pp** (95% CI not computed; single-run)

### Error Distribution Comparison
| Metric | Baseline (max_steps=25) | Treatment (max_steps=50) | Delta |
|---|---|---|---|
| Accuracy | 48% (24/50) | 54% (27/50) | +6pp |
| complete_failure | 20 | 13 | -7 |
| Total errors | 26 | 23 | -3 |

### By Difficulty (Treatment)
- Easy: 15/22 = 68.18%
- Medium: 8/16 = 50.00%
- Hard: 4/12 = 33.33%

### By Category (Treatment)
- Financial Modeling Projections: 4/4 = 100.00%
- Quantitative Retrieval: 7/9 = 77.78%
- Qualitative Retrieval: 6/9 = 66.67%
- Numerical Reasoning: 5/8 = 62.50%
- Beat or Miss: 3/7 = 42.86%
- Trends: 1/3 = 33.33%
- Complex Retrieval: 1/3 = 33.33%
- Market Analysis: 0/3 = 0.00%
- Adjustments: 0/4 = 0.00%

### Interpretation
1. **Interference confirmed**: Increasing max_steps gave the model more search budget, allowing it to find answers it previously couldn't.
2. **Diminishing returns expected**: Going beyond 50 may not yield proportional gains; some "Not found" tasks are genuine model capability limits, not step limits.
3. **Hard tasks remain hard**: Hard difficulty only 33%, suggesting max_steps alone cannot fix complex multi-step reasoning.
4. **Category gaps persist**: Adjustments (0%) and Market Analysis (0%) point to capability, not budget, issues.

### Caveats
- Single-run (no multi-seed), so +6pp is point estimate.
- T2 judge is same model (INT-07 not yet addressed), so absolute numbers may shift once judge interference is addressed.
- Race condition incident (Incident 1) required cleanup, but final trajectories.jsonl is 50 clean records.

## Status
COMPLETED (2026-09-16 18:56)
