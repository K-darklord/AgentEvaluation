# Data Manifest — active vs deprecated runs (deepseek-v4-flash)

Single source of truth for **which experiment dir an analysis script should read**.
Analysis scripts MUST resolve run paths from here, not hard-code them (this is what
caused repeated read-the-wrong-run errors). `DEPRECATED` = superseded by a newer run;
never read it for a claim.

## ACTIVE (read for analysis)

| Purpose | Claim | Run dir(s) | Note |
|---|---|---|---|
| A3 baseline (vote) | 1/2 | `experiments/experiments/a3_phase1_20261010_t0.7`, `a3_new_20261010_t0.7`, `experiments/a3_gpqa_full_deepseek_20261013` | clean, complete |
| C settle (Stage A) | 2 | `experiments/feedback_loop_20261006_173715` + `experiments/feedback_loop_C_mmlu_pro_rerun_20261012` (phase1), `experiments/feedback_loop_C_20261008` (new), `experiments/feedback_loop_C_20261015_175552` (gpqa 051-198) | settle accuracy is valid despite prose pollution |
| C transition (Stage B) | 3 | `experiments/stageb_rerun_ds_c_gpqa051_198_transition_20261019`, `experiments/stageb_rerun_ds_c_gpqa001_050_transition_20261019` | IN PROGRESS (24/148 as of 2026-10-19); clean reasoning_content + finish_reason |

## DEPRECATED (do NOT read for a claim)

| Run dir | Why deprecated |
|---|---|
| `experiments/c_gpqa_full_deepseek_20261013` | `rationale off` — forfeits Stage B |
| `experiments/c_gpqa_001_050_deepseek_20261013` | `rationale off`, stopped 36/50 |
| `experiments/c_smoke_rationale_20261013` | 3-task smoke only |
| `experiments/feedback_loop_C_new_20261011` | glm/qwen models (not deepseek) |
| `experiments/feedback_loop_C_20261008` *(glm/qwen subdirs)* | other models |
| all `experiments/stageb_twostage_*` | superseded by `transition` protocol (§12) |
| all `experiments/stageb_non_settle_*`, `stageb_ds_newscheme_smoke_*`, `smoke_twostage_*` | intermediate probes, superseded |

## Pending triage

The remaining `experiments/stageb_*` dirs (per-task 32768 / 16384 reruns) are a mix of
in-flight background jobs and one-off probes. Do not move/delete while jobs are writing.
Physical archive (`experiments/_deprecated/`) to be applied after the background jobs finish.

## Key rule

- **Claim 2 (settle)**: settle questions do NOT need re-run — settle fired at runtime, accuracy is fixed.
- **Claim 3 (abstain / Stage B)**: only the non-settle set needs the clean `transition` run; if a
  residual issue is format-only (no accuracy effect), defer to Phase 3.
