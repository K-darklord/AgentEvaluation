# A3 — Critic / Evaluator token cost (auto-generated)

> Offline-only artifact (`docs/_token_cost_autogen.md`). No new API calls were made.
> Estimated values are marked `≈`; real values cite their source file path. Produced to
> fill the critic + evaluator gap in `HLE400_FROZEN_DATA.md` §6; to be merged externally.

---

## 1. Solver tokens (real, frozen)

Copied from `HLE400_FROZEN_DATA.md` §6 (unchanged):

| arm | solver rounds | solver tokens (prompt+completion) |
|---|---|---|
| A | 400 | 5.10 M |
| A2 | 1 948 | 24.66 M |
| A3 | 4 000 | 51.32 M |
| C3 | 2 688 | 37.05 M |

Correct counts (best metric, `HLE400_FROZEN_DATA.md` §1): A = 113 (init), A2 = 145 (mode),
A3 = 136 (vote), C3 = 154 (mode), evaluator (`rubric_ce`) = 151.

---

## 2. C3 critic tokens — 2 288 calls (≈ estimated, not logged per round)

Source of the prompt & output schema: `src/strong_critic.py` (`StrongCritic._build_user`,
`SYSTEM`, `_vocab`). The critic is **not** logged per round (confirmed: `loop_summary.json`
carries only solver tokens; `loop_trajectories.jsonl` round records carry only the solver's
`prompt/completion/reasoning_tokens`, never the critic's). So prompt is reconstructed and
completion is estimated from the stored critic output fields.

**Facts measured from `experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl`:**

- Critic fired on **2 288** feedback rounds (= 2 688 total rounds − 400 round-0). Matches §6.
- Critic output digest stored per round as `critic_direction`: list of 1–3 directions
  (`{archetype_id/archetype_name, suspicion, check}`); mean **1.55** directions/call
  (histogram: 1→1315, 2→693, 3→280); 3 541 direction entries in total.
- `suspicion` mean **176.2** chars (54–356); `check` mean **242.9** chars (102–491);
  `archetype_name` mean **27.2** chars.

**Prompt reconstruction (per call, in characters):**

| component | avg chars |
|---|---|
| SYSTEM (`src/strong_critic.py`) | 591 |
| fixed user template (headers + JSON-format instructions) | 3 221 |
| vocabulary `level3_bank_deepseek-v4-flash.json` (5 unique entries by id: constraint_blind, descriptor_conflation, procedure_truncation, retrieval_abort, format_nonconformance) | 2 436 |
| question (`task.prompt`) | 948 |
| committed answer (prev round `final_answer`) | 171 |
| solver reasoning tail (last 6 000 chars of `reasoning_content`) | 5 798 |

Total measured prompt text = **24.90 M characters** over 2 288 calls
(per-call mean 10 883, median 10 550 chars).

**Estimated critic tokens (≈):**

| quantity | estimate |
|---|---|
| `pt` (prompt) | ≈ **6.2 M** tokens (@ 4 chars/token; sensitivity 5.5–7.1 M @ 4.5–3.5 chars/token) |
| `ct` (completion, visible JSON only) | ≈ **0.44 M** tokens (≈ 765 chars/call → ~191 tokens/call @ 4 c/t) |
| `rt` (hidden reasoning CoT) | ≈ **~9 M** tokens — NOT logged; see caveat below |
| critic total (pt + visible ct + rt) | ≈ **16 M** tokens (visible-only lower bound ≈ **6.6 M**) |

**Caveats / assumptions (read before merging):**

1. `pt` is char-based with a stated coefficient; the reasoning tail (cap 6 000 chars) is the
   dominant prompt term, so `pt` is fairly tight (±15 % from the coefficient range).
2. `ct` visible JSON assumes `{"directions":[{"id","suspicion","check"},…]}` with the measured
   field lengths; it is a lower bound because it excludes hidden CoT.
3. `rt` is the large uncertainty. The critic runs `deepseek-v4-flash` with model-default
   **thinking ON** and `thinking_budget = 16384` (+ `content_margin = 1024` ⇒ `max_tokens`
   17 408) — the same configuration under which the solver and both judges emit large hidden
   CoT (solver rt ≈ 32.0 % of completion; judges rt ≈ completion). Because the critic discards
   the usage object at runtime, its CoT is unrecoverable. Proxy: **judge-C** (`judge_c_
   verdicts_dashscope.jsonl`, same model, an analogous "read the criticism + emit a verdict"
   task) averages **rt ≈ 8.7 k / call**. Applying that per-call rate to 2 288 critic calls
   gives rt ≈ 19.9 M (upper proxy); applying a lighter "emit 1–3 directions" rate of ≈4 k/call
   gives ≈ 9.2 M. The headline `≈ 9 M` is the conservative end; the honest range is
   **≈ 9–20 M** and the merged table should either use a stated proxy or present the range.
4. Every one of the 2 288 calls is an LLM call (the TF-IDF weak-critic fallback only triggers
   on JSON-parse failure, *after* tokens were already consumed by the LLM).

---

## 3. Judge tokens (real, summed from pt/ct/rt fields)

Token field conventions: `pt` = prompt_tokens, `ct` = completion_tokens, `rt` =
reasoning_tokens (hidden CoT subset; `ct` already includes `rt`, matching the solver
accounting in §6 where completion bundles reasoning).

### 3.1 Judge-R — `rubric_ce` evaluator

Source: `experiments/hle400/t3/c3_rubric_ce.jsonl` (252 tasks) + `.../c3_rubric_ce.log`
(log summary line `[tokens] prompt=20015020 completion=4129299 reasoning=4056503`).

| field | tokens |
|---|---|
| pt (prompt) | 20 015 020 |
| ct (completion) | 4 129 299 |
| rt (reasoning) | 4 056 503 |
| **pt + ct** | **24 144 319 ≈ 24.14 M** |

Coverage: **252 / 400** tasks — the multi-answer slice that actually runs the LLM rubric
(`lock_status` in the file: locked_majority 115, all_unsure_fallback_mode 98,
locked_directional 35, tie_abstain 2, undecided_switch 2; `correct` = 32). The single-answer
remainder is resolved deterministically (`single_answer` lock), no LLM tokens.

### 3.2 Judge-C — edge adjudicator (1201 edges × N=2 = 2 402 calls)

Source: `experiments/hle400/t3/judge_c_verdicts_dashscope.jsonl` (1 201 edges; each edge has
`calls` length 2; per-call `pt`/`ct`/`rt`).

| field | tokens |
|---|---|
| pt (prompt) | 6 605 732 |
| ct (completion) | 21 164 694 |
| rt (reasoning) | 20 880 383 |
| **pt + ct** | **27 770 426 ≈ 27.77 M** |

Per-call means (2 402 calls): pt ≈ 2 750, ct ≈ 8 811, rt ≈ 8 692.

### 3.3 Judge-R+ — Q-CUT

Source: `experiments/hle400/t3/qcut_result.jsonl` (766 records; per-record `pt`/`ct`/`rt`).

| field | tokens |
|---|---|
| pt (prompt) | 10 242 185 |
| ct (completion) | 8 751 665 |
| rt (reasoning) | 8 662 776 |
| **pt + ct** | **18 993 850 ≈ 18.99 M** |

Coverage: **766 records**, static since 2026-11-03 21:38 (file mtime), i.e. **partial**
relative to the 1 201-edge switch universe (overlap with judge-C edges = 744/766; 63.8 % of
the judge-C edge set). If a parallel run is still completing this file, re-sum before merging.

---

## 4. Master cost table

`tokens/correct` uses each arm's best metric (`HLE400_FROZEN_DATA.md` §1). Critic and
critic-bearing totals are `≈` (from §2); everything else is real (§1 + §3).

| row | solver tokens | critic tokens (≈) | judge tokens | total | correct | tokens / correct |
|---|---|---|---|---|---|---|
| A (init) | 5.10 M | 0 | 0 | 5.10 M | 113 | 45.1 k |
| A2 (mode) | 24.66 M | 0 | 0 | 24.66 M | 145 | 170.1 k |
| A3 (vote) | 51.32 M | 0 | 0 | 51.32 M | 136 | 377.4 k |
| C3 (mode) — solver + critic | 37.05 M | ≈ 16 M | 0 | ≈ 53.05 M | 154 | ≈ 344.5 k |
| C3 (mode) — solver only | 37.05 M | 0 | 0 | 37.05 M | 154 | 240.6 k |
| Judge-R (`rubric_ce`, evaluator readout) | 0 | 0 | 24.14 M | 24.14 M | 151 | 159.9 k |
| Judge-C (edge adjudicator, 1 201×2) | 0 | 0 | 27.77 M | 27.77 M | n/a (edge-level) | n/a |
| Judge-R+ (Q-CUT, 766 rec, partial) | 0 | 0 | 18.99 M | 18.99 M | n/a (edge-level) | n/a |
| **C3 full pipeline** (solver + critic + Judge-R → 151) | 37.05 M | ≈ 16 M | 24.14 M | ≈ 77.19 M | 151 | ≈ 511.2 k |

Notes:

- The "C3 full pipeline" row is the paper-relevant headline: to take a C3 answer from round-0
  to the `rubric_ce` evaluator readout (151/400) costs ≈ solver 37.05 M + critic ≈ 16 M +
  evaluator 24.14 M ≈ **77.19 M** tokens ⇒ ≈ **511 k tokens / correct** (vs 240.6 k for the
  bare C3 mode-154 solver, and 45.1 k for the bare A solver). If only the critic *visible*
  completion is credited (lower bound ≈ 6.6 M instead of ≈ 16 M), the pipeline total is
  ≈ 67.79 M ⇒ ≈ 449 k tokens / correct.
- Judge-C and Judge-R+ are edge/fragment adjudicators and do not map to a per-400 correct
  count; they are listed for completeness of the pt/ct/rt ledger.
- `rt` is shown for the judges in §3 but, following §6's convention (completion bundles
  reasoning), the master table's "judge tokens" and all totals use `pt + ct`.

---

## 5. TODO (merge)

TODO: merge this table (critic ≈ + judge tokens + totals + tokens/correct) back into
`HLE400_FROZEN_DATA.md` §6; replace the critic `≈` with any recovered per-round log if one
is later found, and re-sum `qcut_result.jsonl` if that file is still being appended.