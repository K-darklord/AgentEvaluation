# Data Tracker — arm × benchmark completion matrix

**Last updated**: 2026-10-20 09:15 (Asia/Shanghai)

Single source of truth for **data completion**: which `(benchmark, model, arm)` cells
are done and how many questions remain. Each entry is `OK/target`, where:

- `OK` = valid **unique** questions collected (unpolluted, correct protocol, analysable).
  Polluted / wrong-protocol / interrupted questions are **not** counted as OK.
- `target` = total questions designed for that benchmark (see the `Target` column).

Read this table before launching or re-running any collection. Only update the master
number when a run finishes and is verified; log every change in the Change log below.

Model keys: `ds` = deepseek-v4-flash · `glm` = glm-5.3 · `qwen` = qwen3.8-flash.
Arms: `A` = bare re-solve (T=0) · `A2` = form placebo · `A3` = majority vote (T=0.7, N=10) · `C` = weak-critic feedback.

## Completion matrix

| Benchmark | Target | ds A | ds A2 | ds A3 | ds C | glm A | glm A2 | glm A3 | glm C | qwen A | qwen A2 | qwen A3 | qwen C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GSM8K (math) | 50 | 50/50 | 0/50 | 50/50 | 50/50 | 50/50 | 0/50 | 50/50 | 50/50 | 50/50 | 0/50 | 50/50 | 50/50 |
| MATH-500 (math500) | 50 | 50/50 | 0/50 | 50/50 | 50/50 | 50/50 | 0/50 | 50/50 | 50/50 | 50/50 | 0/50 | 50/50 | 50/50 |
| MMLU-Pro (mmlu_pro) | 50 | 50/50 | 0/50 | 50/50 | 50/50⁸ | 50/50 | 0/50 | 50/50 | 50/50⁸ | 50/50 | 0/50 | 50/50 | 50/50⁸ |
| FAB (finance) | 50 | 50/50 | 0/50 | 0/50² | 50/50 | 50/50 | 0/50 | 0/50² | 50/50 | 50/50 | 0/50 | 0/50² | 50/50 |
| BFCL (bfcl) | 50 | 50/50 | 0/50 | 50/50 | 50/50⁸ | 50/50 | 0/50 | 50/50 | 50/50⁸ | 50/50 | 0/50 | 50/50 | 50/50⁸ |
| AIME (aime) | 50 | 50/50 | 0/50 | 50/50 | 50/50 | 50/50 | 0/50 | 50/50 | 0/50⁴ | 50/50 | 0/50 | 50/50 | 50/50 |
| GPQA-Diamond (gpqa) | 198 | 50/198³ | 0/198 | 198/198 | 198/198 | 50/198³ | 0/198 | 173/198⁹ | 183/198⁷⁹ | 50/198³ | 0/198 | 127/198⁵⁹ | 191/198⁹ |
| BBH (bbh) | 44 | 44/44 | 0/44 | 44/44 | 44/44 | 44/44 | 0/44 | 44/44 | 0/44⁴ | 44/44 | 0/44 | 44/44 | 44/44 |

`target` for GPQA = 198 = new-set `gpqa_001-050` (50) + discriminant `gpqa_051-198` (148).

## Footnotes

1. (none — label reserved)
2. **A3 skips FAB/finance by design** — phase-1 A3 covers GSM8K + MATH-500 + MMLU-Pro + BFCL (= 200).
3. **Arm A for GPQA covers only the new-set slice** (`gpqa_001-050`, 50). No A-baseline exists for `gpqa_051-198` yet.
4. **glm C new-set (AIME / BBH) is polluted** (no-commit self-report on feedback rounds). Settle accuracy recovered offline via `feedback_loop_C_new_20261011/loop_summary.corrected.json` (final 0.8194); **no re-run needed** — the 2026-10-19 twostage re-run was deprecated as redundant.
5. **qwen A3 GPQA discriminant slice short by 71** — clean **77/148** on disk (55 all-fail + 11 partial-fail + 1 prose + 4 missing); 71 re-run in flight. See footnote 9.
6. **qwen C GPQA discriminant short by 7** — clean **141/148** on disk (6 all-fail + 1 partial); 7 re-run in flight. See footnote 9.
7. **glm C GPQA uses `twostage`** (settle protocol); discriminant clean **133/148** (15 CoT-leaked prose), Stage-B `transition` pending.
8. **MMLU-Pro / BFCL C-arm scorer/prompt drift** — deepseek MMLU-Pro re-scored via `feedback_loop_C_mmlu_pro_rerun_20261012`.
9. **2026-10-20 round-level pollution audit** (`scripts/check_data_pollution.py`). The discriminant slice (`gpqa_051-198`, 148) previously counted “task_id appears” as OK, hiding waste-value answers (`LLM error: …` quota/connection blobs, CoT-leaked prose). Actual **clean/148** on disk: **qwen A3 77** (55 all-fail + 11 partial-fail + 1 prose + 4 missing), **qwen C 141** (6 all-fail + 1 partial), **glm A3 123** (25 CoT-leaked prose), **glm C 133** (15 CoT-leaked prose). glm `--enable-thinking 0` re-run FAILED — the endpoint forces `enable_thinking=True` and returns `invalid_parameter_error` on all 148. Matrix value = new-set 50 (kept from 10-19, not re-audited) + discriminant clean count.

## Stage B (transition) status

Stage B re-collects the **non-settle** subset under the three-channel `transition` protocol
(rationale / hidden CoT / committed answer isolated). Not a separate arm — tracked as C quality.

| Model | Non-settle set | transition collected | Dir |
|---|---|---|---|
| deepseek | 52 (gpqa 38 + aime 4 + phase1 10) | **complete** (52/52) | `experiments/stageb_rerun_ds_c_transition_full_20261019` |
| glm | — | partial (smoke/non-settle probes) | `experiments/stageb_gpqa_glm_20261019`, `stageb_non_settle_glm_*` |
| qwen | — | partial | `experiments/stageb_gpqa_qwen_20261019`, `stageb_non_settle_qwen_*` |

## Change log

| Date | Change |
|---|---|
| 2026-10-19 | Created tracker. Consolidated deepseek `transition` into `stageb_rerun_ds_c_transition_full_20261019` (52 non-settle, recovered 4 mis-moved dirs from `_deprecated`). Confirmed deepseek A3 complete (gpqa 148 / new 144 / phase1 200), deepseek C gpqa complete (198). |
| 2026-10-19 | qwen C gpqa corrected 196→198/198 (148/148 discriminant confirmed). |
| 2026-10-19 | Deprecated glm C twostage re-run (`glm_c_aime_twostage_20261019`) as redundant — polluted new-set settle accuracy already valid offline (`loop_summary.corrected.json`). |
| 2026-10-20 | Added round-level pollution audit (`scripts/check_data_pollution.py`). Corrected GPQA discriminant OK counts: qwen A3 77, qwen C 141, glm A3 123, glm C 133 clean/148. glm `--enable-thinking 0` re-run failed (endpoint forces thinking=True). qwen A3/C partial re-run in flight. |
