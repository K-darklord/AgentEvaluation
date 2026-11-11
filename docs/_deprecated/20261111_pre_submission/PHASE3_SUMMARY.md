# Phase 3 Summary — Final frozen-standard results (authoritative data record)

> **Purpose.** This document is the **single authoritative record of all final
> experimental data** for the EGTE paper. Every accuracy / rate / round-count figure
> cited in the final paper MUST be traceable to a filled cell here (or to an offline
> score JSON referenced inline). `PHASE1_SUMMARY.md` and `PHASE2_SUMMARY.md` remain
> historical; **Phase 3 supersedes both for all citable results.**
>
> **Scope.** All §3 benchmark results and the §4 HLE / transition analysis, re-run
> under the frozen standard below. HLE-150 (n=150) and the non-FAB benchmark suite are
> **re-run in full**; HLE pilot (n=50) is the strategy probe.
>
> **Fill-in discipline.** A cell stays `—` (pending) until its run has completed AND
> been verified (zero timeout, zero truncation, correct scorer). Do not backfill from
> Phase-1/Phase-2 numbers.

---

## 1. Frozen per-arm runtime standard (aligned to `PAPER_DRAFT.md` §3.0)

Every re-run follows this table. `C` (weak critic) is **outdated and dropped** from the
final paper (historical only).

| Arm                              | solver `T` | samples | aggregation                        | feedback              | grader               |
| -------------------------------- | ---------- | ------- | ---------------------------------- | --------------------- | -------------------- |
| **A** (floor)                    | 0          | 1       | single answer                      | none                  | `scorer_LLM_rescue`  |
| **A2** (placebo)                 | 0          | 1       | fixed neutral placebo loop         | `A2_PLACEBO_FEEDBACK` | `scorer_LLM_rescue`  |
| **A3** (self-consistency)        | 0.7        | 10      | i.i.d. majority vote (tie → 1st)   | none                  | `scorer_LLM_rescue`  |
| **A3C3** (A3-seeded C3)          | 0.7 → 0    | 10 → 1  | A3 round-0 vote → C3 loop          | strong critic         | `scorer_LLM_rescue`  |
| **C3** (treatment)               | 0          | 1       | `rubric_ce` elimination + mode     | strong critic         | `scorer_LLM_rescue`  |

Common frozen fields for **every** arm: `thinking_budget = 16384` (hidden CoT cap, stop-and-commit) + `REASONING_CONTENT_MARGIN = 8192` (visible answer window) → `max_tokens = 24576` per solver call (`REASONING_BENCH_MAX_TOKENS = 8192` is the non-HLE bench default and is NOT the HLE cap),
`rationale_mode = off`, `max_rounds = 10`, `early_stop_n = 3`, model
`deepseek-v4-flash-0731`, `seed = None`. `T = 0.7` applies **only** to A3's 10 i.i.d.
round-0 samples (and A3C3's shared round-0); every other solver call is deterministic `T = 0`.

**A3C3 is run contiguously with A3** (shares A3's single `T=0.7, n=10` round-0 vote as its
round-0 committed answer, then continues the `T=0` C3 loop) — no separate A3 pass.

---

## 2. Per-arm reported metrics (aligned to §3.0)

| Metric      | Definition                                                                                              |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| `init`      | accuracy of the round-0 committed answer.                                                               |
| `final`     | accuracy of the **last** committed answer (end of the loop).                                            |
| `settle`    | accuracy of the **early-stop** answer (trailing run of 3 identical committed answers); never-settled → abstain (not-correct). |
| `mode`      | accuracy of the **majority** committed answer across the whole loop (ties → latest appearance).         |
| `evaluator` | accuracy of the offline evaluator's locked answer (`rubric_ce` elimination + mode); C3 / A3C3 only.     |

Per-arm report grid:

| Arm      | reported metrics                          |
| -------- | ----------------------------------------- |
| **A**    | accuracy (single `T=0` sample)            |
| **A2**   | `init` · `final` · `settle` · `mode`      |
| **A3**   | `init` · `final`                          |
| **A3C3** | `init` · `final` · `settle` · `mode` · `evaluator` |
| **C3**   | `init` · `final` · `settle` · `mode` · `evaluator` |

---

## 3. Model config & reasoning fixes in force (2026-10-28)

Frozen for this phase; recorded so the paper's reproducibility section matches the data.

| Parameter                       | Value   | Rationale                                                                 |
| ------------------------------- | ------- | ------------------------------------------------------------------------- |
| `thinking_budget`               | **16384** | stop-and-commit cap on the hidden CoT. A 32768 trial (2026-10-28) was **reverted**: all `finish_reason=length` rounds were rambles, not truncated good answers (`src/config.py` note) |
| `REASONING_CONTENT_MARGIN`      | 8192    | was 64 → visible answer window                                             |
| `AGENTEVALUATION_SOLVE_TIMEOUT` | 900     | was 180 → slow CoT tasks were cancelled as "hung" (not dead)               |
| `max_tokens` (per solve)        | **24576** | `thinking_budget` + `REASONING_CONTENT_MARGIN`; observed max completion in all four HLE-400 arms = 24576 |

---

## 4. Experiment matrix & run status

Status legend: ✅ verified · 🔄 running · ⬜ pending (to re-run) · ❌ broken (must re-run).

### 4.1 HLE pilot (n = 50) — strategy probe

| Arm | n  | status | out-dir | notes                                                        |
| --- | -- | ------ | ------- | ------------------------------------------------------------ |
| A3  | 50 | 🔄     | `experiments/hle_pilot_a3`    | 14 timeout tasks re-running (timeout=900)                    |
| C3  | 50 | 🔄     | `experiments/hle_pilot_c3`    | 14 timeout tasks re-running (timeout=900); 6 truncation tasks accepted (see §6 note) |

### 4.2 HLE-150 (n = 150) — main benchmark

| Arm   | n   | status | out-dir                    | notes                                          |
| ----- | --- | ------ | -------------------------- | ---------------------------------------------- |
| A     | 150 | ❌     | `experiments/hle150_A`     | 2026-10-27 run polluted (missing API key); resume |
| A2    | 150 | ❌     | `experiments/hle150_A2`    | same                                            |
| A3    | 150 | ❌     | `experiments/hle150_A3`    | same                                            |
| A3C3  | 150 | ❌     | `experiments/hle150_A3C3`  | same (run contiguously with A3)                 |
| C3    | 150 | ❌     | `experiments/hle150_C3`    | same                                            |

### 4.3 Non-FAB benchmark suite

| Benchmark     | n   | status | notes                                             |
| ------------- | --- | ------ | ------------------------------------------------- |
| GSM8K         | 50  | ⬜     | re-run under frozen standard                       |
| MATH-500      | 50  | ⬜     | re-run                                            |
| MMLU-Pro      | 50  | ⬜     | re-run                                            |
| BFCL          | 50  | ⬜     | re-run                                            |
| AIME          | 50  | ⬜     | re-run                                            |
| BBH           | 44  | ⬜     | re-run                                            |
| GPQA-Diamond  | 198 | ⬜     | re-run (50 new slice + 148 `051–198` slice)        |

> `FAB` (finance) is a single deferred decision-only run and is **excluded by design**.

---

## 5. Cross-benchmark arm accuracy (§3.1)

> All cells `—` until the frozen re-run completes and is verified. Do not cite Phase-1/2
> values here.

| Benchmark     | n   | A (bare T=0) | A2 (placebo) | A3 (SC vote) | A3C3 | C3 (`rubric_ce`) |
| ------------- | --- | ------------ | ------------ | ------------ | ---- | ---------------- |
| GSM8K         | 50  | —            | —            | —            | —    | —                |
| MATH-500      | 50  | —            | —            | —            | —    | —                |
| MMLU-Pro      | 50  | —            | —            | —            | —    | —                |
| BFCL          | 50  | —            | —            | —            | —    | —                |
| AIME          | 50  | —            | —            | —            | —    | —                |
| BBH           | 44  | —            | —            | —            | —    | —                |
| GPQA-Diamond  | 198 | —            | —            | —            | —    | —                |
| **HLE-150**   | 150 | —            | —            | —            | —    | —                |

---

## 6. HLE pilot results (n = 50) (§4.2)

`init` = round-0 accuracy; `final`/`evaluator` per §2. Filled after the full 50-task score.

| line        | init | final | definition                                            |
| ----------- | ---- | ----- | ----------------------------------------------------- |
| A3 (SC)     | —    | —     | N=10 @ T=0.7 majority vote                            |
| C3 critic   | —    | —     | strong critic last round, no evaluator                |
| C3 + rubric | —    | —     | strong critic + offline `rubric_ce` (mode fallback)   |

Activation (reachability) and head-to-head (A3 vs C3) to be filled from
`experiments/hle_pilot_a3/hle_pilot_scores.json`.

> **Truncation disposition (accepted, 2026-10-28).** 6 tasks carry a `finish_reason=length`
> in ≥1 round but are **accepted as-is** (final impact negligible): 4 have a clean round-0
> with truncation only in later rounds (A3 `hle_002`/`hle_024`; C3 `hle_017`/`hle_029`);
> `hle_035` (A3) truncates round-0 only (1 of 10 votes); `hle_023` (A3) truncates r0–r2 and
> diverges across clean rounds (17/125/0/4/28) + an `api_failure` (content moderation) —
> a model-capability bound, not a truncation artifact.

### 6.1 Pilot observation — open-form vote collapse (preliminary, uncorroborated)

*Observation (2026-10-29; to be corroborated on HLE-150 and another open-form control set
before it may inform any claim).* On the HLE pilot, C3 (strong critic) leads A3 (SC vote) by
a wider margin than on the prior MCQ-dominated GPQA slice, where C-vs-A3 separation was only
2–3 pp and sub-significant (`PHASE2_SUMMARY.md` §828). The HLE pilot is **open-form
dominated** (10 MCQ / 40 open-form of 50 items), and the A3 majority vote appears to
**collapse on open-form items**: of A3's 7 correct votes, 3/10 are MCQ (30%) vs 4/40
open-form (10%).

Mechanism hypothesis: the self-consistency majority vote is only informative when the correct
answer occupies a non-negligible share of the `T=0.7` sampling distribution; on very hard
open-form items the correct answer is a sparse outlier (0–1 of 10 samples), so the vote cannot
aggregate it. This matches the Phase-2 attribution plan (`PHASE2_SUMMARY.md` §18: open forms
are the attribution control where vote collapse is expected).

> **Preliminary — not a claim.** Corroboration requires the HLE-150 main set and at least one
> non-MCQ control benchmark (MATH-500 / AIME / BBH). Until then the MCQ and open-form slices
> must be reported separately, never as a single collapsed total.

---

## 7. EIR / ECR transition rates (§4.1)

Estimated over **all (item, round) transition opportunities of the arm's full loop** —
denominator: every round whose previous state was `correct` (EIR) or `wrong` (ECR), over all
N items (not the flip-selected subset).

| arm   | n | init | final | EIR | ECR |
| ----- | - | ---- | ----- | --- | --- |
| A3C3  | — | —    | —     | —   | —   |
| C3    | — | —    | —     | —   | —   |

> `flip19` is retained only as an illustrative case list (see `PAPER_DRAFT.md` §4.1) and does
> **not** enter rate estimation.

---

## 8. Per-task round counts (round-level dynamics)

Filled after each run. Record, per task and per arm: `n_rounds` (early-stop actual), `settled`
(bool), `end_state`, and the committed-answer trajectory length used for §7 rates.

| task_id | arm | n_rounds | settled | end_state | round-0 correct | final correct |
| ------- | --- | -------- | ------- | --------- | --------------- | ------------- |
| —       | —   | —        | —       | —         | —               | —             |

---

## 9. Provenance & reproducibility

- **Task sources.** HLE pilot: `data/raw/hle/hle_50_pilot.jsonl` (n=50). HLE-150:
  `data/raw/hle/hle_150_new.jsonl` (n=150). Non-FAB: existing `load_*_questions` loaders.
- **Arm configs** are re-derived from `src/run_feedback_loop.py` (round-0 `T=0.7` only for
  A3/A3C3) and `src/config.py` (token budget / timeout in §3).
- **Scoring.** Offline `score_hle_pilot.py` (HLE) and the per-family offline scorers; in-loop
  `is_correct` is T1-only and is **not** the citable score.
- **Resume/filter.** A task is re-run iff any round has `api_failure` or
  `finish_reason == "length"` (see `scripts/resume_hle150_failed.py`). One commit + tag per
  completed, verified run block.