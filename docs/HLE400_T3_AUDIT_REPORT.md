# HLE-400 T3 Audit Report

**Version**: 1.0 (2026-11-02)
**Scope**: `hle400` slice, n = 400, arms A / A2 / A3 / C3 (A3C3 empty placeholder)
**Model under test**: `deepseek-v4-flash`
**Independent review judge**: `gpt-6-astra` (K = 1, stronger tier, external gateway)
**Status**: T3 review COMPLETE (deterministic T1 pool fully re-judged). Evaluator offline (placeholder).

This report is the **single consolidated experiment report** for the scorer and its T3
review. It is written for a second agent to re-audit every number from the raw
trajectories alone. Every correction carries a `task_id` + evidence pointer.

---

## 1. Summary

T3 review re-judged the **complete T2 audit surface** — all 1082 unique rows that the
deterministic T1 matcher marked wrong (these are exactly the rows the T2 LLM judge
could act on). An independent, stronger judge (`gpt-6-astra`, K=1) replaced the
drift-prone DeepSeek T2 judge. Result of the full re-judgment:

| class | definition (vs DeepSeek T2 prev label) | unique resp-keys |
|---|---|---|
| `missed_rescue` | T2 said *wrong*, astra says *right* | **64** |
| `false_rescue` | T2 said *right*, astra says *wrong* | **2** |
| `confirmed` | T2 said *right*, astra says *right* | 74 |
| `true_neg` | T2 said *wrong*, astra says *wrong* | 932 |
| `none` | astra returned empty verdict | 7 |

The final score is **drift-free**: `correct = T1_correct (minus FP) ∪ astra-correct
T1-missed`. It no longer depends on the non-deterministic DeepSeek T2 verdict.

Net effect on accuracy: every arm metric **rises** (astra rescued more rows than the
frozen T2 judge did). Largest gains on loop arms (A2/C3 `final`/`mode`), smallest on
bare `vote`.

---

## 2. Scorer protocol (three tiers)

| Tier | Action | Deterministic | Reads |
|---|---|---|---|
| **T1** | token-free exact match dispatched by `answer_type`/`shape` | yes | committed final answer |
| **T2** | one-way FN rescue by LLM judge (`deepseek-v4-pro`), only on T1-missed rows, never overturns a T1-correct row | no | committed final answer (never CoT) |
| **T3** | contested-row review by an independent stronger judge | no (judge) | row evidence |

The **key architectural fact** that defines the T2 audit surface: `score_hle()` has a
one-way guard — if T1 says `correct`, it returns immediately and the judge is *never*
consulted. Therefore:

- **FP direction** (T1 ruled correct but actually wrong) is *never* seen by the T2
  judge and must be audited separately (§7.1).
- **FN direction** (T1 wrong) has two sub-directions: *false rescue* (judge raised a
  wrong row) and *missed rescue* (judge failed to raise a right row). Both are fully
  enumerated by the deterministic T1-missed pool (§6).

Metric definitions: `init` = round-0 commit; `final` = last commit; `settle` = trailing
3-identical-commit (abstain if none); `mode` = majority committed answer (tie → latest);
`vote` (A3) = majority over `rounds[1:]` (excludes the A-seeded round-0 anchor), tie →
earliest.

---

## 3. Experiment data

| Data | File | Arm |
|---|---|---|
| 400-question input | `data/raw/hle/hle_400_new.jsonl` (`question`,`gold`,`answer_type`,`shape`) | — |
| A trajectories | `experiments/hle400_A/deepseek-v4-flash/loop_trajectories.jsonl` | A |
| A2 trajectories | `experiments/hle400_A2/deepseek-v4-flash/loop_trajectories.jsonl` | A2 |
| A3 trajectories | `experiments/hle400_A3/deepseek-v4-flash/loop_trajectories.jsonl` | A3 |
| C3 trajectories | `experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl` | C3 |

`init` is **shared** across A / A2 / A3 / C3 (the four arms seed from the same bare
round-0 re-solve), so an `init`-level correction propagates to all four arms.

---

## 4. Raw scores (T1 + T2, frozen)

Source: `experiments/hle400/hle_arms.json` (frozen). `accuracy = t1_accuracy +
fn_rescued/n`.

| Arm | Metric | accuracy | t1_accuracy | judge_n | fn_rescued |
|---|---|---|---|---|---|
| A | init | 0.2350 | 0.1575 | 337 | 31 |
| A2 | init | 0.2350 | 0.1575 | 337 | 31 |
| A2 | final | 0.2800 | 0.2000 | 320 | 32 |
| A2 | settle | 0.2700 | 0.1900 | 295 | 32 |
| A2 | mode | 0.2800 | 0.2000 | 320 | 32 |
| A3 | init | 0.2350 | 0.1575 | 337 | 31 |
| A3 | vote | 0.2925 | 0.2200 | 312 | 29 |
| C3 | init | 0.2350 | 0.1575 | 337 | 31 |
| C3 | final | 0.2975 | 0.2100 | 316 | 35 |
| C3 | settle | 0.2400 | 0.1825 | 211 | 23 |
| C3 | mode | 0.2900 | 0.2075 | 317 | 33 |

**Known issue (T2 drift).** The T2 judge runs at `temperature=0` but the served
`deepseek-v4-pro` endpoint is not strictly deterministic: the same
`(question, gold, final_answer)` returns different CORRECT/INCORRECT across runs, moving
only `fn_rescued`. T3 review resolves this by *not depending on the T2 verdict at all*
(see §8).

---

## 5. T3 review method

- **Judge**: `gpt-6-astra` (config `ASTRA_MODEL`), gateway `cf.api.fan/v1`. Served model
  recorded per call (`response.model`) to guarantee no silent downgrade — all 1082 rows
  report `served_model == "gpt-6-astra"`.
- **K = 1** single re-judgment (as requested; astra is a stronger tier, ~3 s/call).
- **Pool**: the full deterministic T1-missed enumeration (1082 unique rows, no API
  needed to enumerate) — the *complete* T2 audit surface, not just the frozen FN rows.
- **Judging target**: committed `final_answer` vs `gold`, same evidence the T2 judge saw
  (never CoT). Verdict parsed from a leading `CORRECT`/`INCORRECT`.
- Covers both T2 error directions in one pass.

Pool composition (1082 rows): `exactMatch` 936 / `multipleChoice` 146; by shape:
`text` 390, `int` 278, `symbol` 249, `mc` 146, `word` 19.

---

## 6. T3 review results (four classes)

Counts are at the **unique resp-key** level (`sha256(question␀gold␀answer_type␀shape␀resp)`).

| class | count | meaning |
|---|---|---|
| `true_neg` | 932 | T2 & astra agree wrong — no change |
| `missed_rescue` | 64 | T2 wrong, astra right — **raise** |
| `confirmed` | 74 | T2 & astra agree right — no change |
| `false_rescue` | 2 | T2 right, astra wrong — **lower** |
| `none` | 7 | astra empty — keep T2 verdict, flag for manual |

`missed_rescue` (64 resp-keys, after truncation rollback) map to **40 unique tasks**; `false_rescue` to 2 tasks.

`missed_rescue` by shape: symbol 33, text 28, int 2, mc 1.

---

## 7. Revision detail

### 7.1 FP direction (T1-correct rows, audited separately)

The FP risk set (`letter` + `norm` first-extraction / normalization risks) is 87
unique rows → **1 true FP**: `hle_182`.

- `hle_182` (multipleChoice, gold `B`): T1's `letter` extractor pulled `B` out of a long
  Go-playout answer, but the committed answer is not actually `B`.
  - Affected metrics: `C3.final`, `C3.mode` (each **−1**).
  - Evidence: `experiments/hle400/t3/fp_judge.jsonl` (K=3, `n_true=0 n_false=3`).

Note: `hle_182` *also* appears as a `missed_rescue` in `A2.final` / `A2.mode` (a
*different* committed answer from the A2 loop that astra judged genuinely correct). The
FP and the missed-rescue are different responses in different metrics — not a conflict.

### 7.2 Missed rescue (64 resp-keys → 40 tasks, after truncation rollback)

T2 said wrong, astra said right. These rows are **raised** to correct. Because `init`
is shared across four arms, and because different loops sometimes converge to the same
committed answer, the 64 resp-keys expand to **244 (arm,metric) scoring instances** (after truncation rollback):

```
A.init 19   A2.init 19   A2.final 28   A2.settle 26   A2.mode 28
A3.init 19  A3.vote 16   C3.init 19    C3.final 22    C3.settle 20   C3.mode 28
```

40 unique tasks (full per-row evidence in `t3_revision_detail.json`):

```
hle_018 hle_030 hle_035 hle_036 hle_040 hle_052 hle_062 hle_064 hle_068
hle_069 hle_070 hle_071 hle_077 hle_079 hle_096 hle_100 hle_114 hle_115 hle_121
hle_153 hle_156 hle_162 hle_194 hle_217 hle_225 hle_228 hle_231
hle_254 hle_256 hle_276 hle_280 hle_288 hle_290 hle_312 hle_335 hle_337 hle_343
hle_371 hle_374 hle_388
```

**Truncation rollback (§0 top-priority rule).** 3 missed-rescue resp-keys sat on
`finish_reason == "length"` winning rounds and are downgraded back to wrong: `hle_032`
(A2.final), `hle_182` (A2.final + A2.mode), `hle_202` (C3.final). This reduces the
missed-rescue set from 67 → 64 resp-keys (43 → 40 tasks). `hle_114` C3.final was a
*confirmed* row also truncated to wrong — it changes the §8 scores but not this
missed-rescue count.

### 7.3 False rescue (2 tasks)

T2 said right, astra said wrong. These rows are **lowered** to wrong.

| task | evidence | affected metrics |
|---|---|---|
| `hle_129` | gold `b = \alpha P_1`; committed `b^* = -\alpha P_1` (sign error) | `A.init A2.init A3.init C3.init` |
| `hle_336` | gold 4 values; committed only 2 of the 4 eigenvalues | init×4 + A2.final/settle/mode + C3.final/settle/mode |

> Drift note: `hle_336`'s `rescued` label differs between the frozen T2 run (not
> rescued) and the audit replay (rescued) — a T2 non-determinism boundary row. It does
> **not** affect the final score (which uses astra's verdict, not the T2 label); it only
> changes the semantic *label* between `true_neg` and `false_rescue`.

### 7.4 Cluster / semantic-equivalence

Source: `experiments/hle400/hle_t3_cluster_diff.jsonl`. Exactly **1 verdict flip**:
`hle_235` (A3.vote): elected winner changes `0.96` → `24/25`. These are the same number
(24/25 = 0.96), so the full scorer re-rescues it and the **verdict (accuracy) is
unchanged**; only the T1 layer label moves (`0.96` T1-match → `24/25` T1-mismatch).
Other cluster changes (`hle_126`, `hle_032`, …) change no verdict.

### 7.5 `none` rows (7, astra empty — manual review)

All 7 are `prev=not_rescued`; kept as wrong (no change to score), flagged for manual:

```
hle_121 (A.init/A2.init/A3.init/C3.init) , hle_121 (A3.vote)
hle_021 (A2.final/A2.settle/A2.mode)      , hle_021 (C3.final/C3.settle/C3.mode)
hle_280 (C3.final/C3.mode)
hle_393 (C3.mode) , hle_396 (C3.mode)
```

---

## 8. Final scores (three-tier comparison, n = 400)

`correct = T1_correct (minus FP) ∪ astra-correct T1-missed`. Drift-free (does not read
the DeepSeek T2 label except for the 7 `none` fallbacks, which are all negative). A
`finish_reason == "length"` winning round is scored wrong regardless of T1/astra (§0
truncation rule) — this rolled back `hle_032`/`hle_182`/`hle_202` (missed-rescue) and
`hle_114` (confirmed) in the rows below.

| Arm | Metric | T1 | T1+T2 (frozen) | **T3 final** | Δ vs frozen |
|---|---|---|---|---|---|
| A | init | 0.1575 | 0.2350 | **0.2800** | +0.0450 |
| A2 | init | 0.1575 | 0.2350 | **0.2800** | +0.0450 |
| A2 | final | 0.2000 | 0.2800 | **0.3525** | +0.0725 |
| A2 | settle | 0.1900 | 0.2700 | **0.3375** | +0.0675 |
| A2 | mode | 0.2000 | 0.2800 | **0.3525** | +0.0725 |
| A3 | init | 0.1575 | 0.2350 | **0.2800** | +0.0450 |
| A3 | vote | 0.2200 | 0.2925 | **0.3325** | +0.0400 |
| C3 | init | 0.1575 | 0.2350 | **0.2800** | +0.0450 |
| C3 | final | 0.2100 | 0.2975 | **0.3475** | +0.0500 |
| C3 | settle | 0.1825 | 0.2400 | **0.2925** | +0.0525 |
| C3 | mode | 0.2075 | 0.2900 | **0.3600** | +0.0700 |

Authoritative final counts are in `experiments/hle400/t3/t3_final_scores.json`.

**Reading**: the frozen T2 judge under-rescued relative to astra. The `init` rise
(+0.045) is uniform across all four arms (shared round-0). Loop arms gain more on
`final`/`mode` (which compound multiple astra-rescued commits and are where the false
rescues and the FP sit).

---

## 9. Evaluator (offline, placeholder — NOT run)

Per the project constraint, the evaluator (`rubric_ce` locked verdict) runs **offline**
and is **not** part of this scorer audit. `C3 eval` / `A3C3 eval` scores are **left
blank** here and must be filled from the evaluator run, not this report. `A3C3` is an
empty placeholder arm in this slice (n = 0).

| Arm | Metric | T3 final (scorer) | evaluator (offline) |
|---|---|---|---|
| C3 | final | 0.3475 | ⬜ pending |
| C3 | settle | 0.2925 | ⬜ pending |
| C3 | mode | 0.3600 | ⬜ pending |
| A3C3 | (all) | n/a (empty) | ⬜ pending |

---

## 10. Manual review checklist (human sign-off)

1. **`none` rows (§7.5)** — 7 empty astra verdicts; confirm each stays wrong.
2. **FP `hle_182`** — confirm the C3.final/C3.mode committed answer is not the letter
   `B` (Go playout text) and the FP downgrade is correct.
3. **False rescue `hle_129`, `hle_336`** — confirm sign error / missing eigenvalues.
4. **Cluster `hle_235`** — confirm `24/25 ≡ 0.96` (verdict unchanged).
5. **Missed-rescue spot-check** — sample the 40 tasks in `t3_revision_detail.json` and
   confirm astra's `CORRECT` calls are genuine (esp. `symbol`/`text` equality).

---

## 11. Data provenance & reproduction

| Conclusion | Authoritative file | Status |
|---|---|---|
| Raw input | `data/raw/hle/hle_400_new.jsonl` | stable |
| Trajectories | `experiments/hle400_{A,A2,A3,C3}/deepseek-v4-flash/loop_trajectories.jsonl` | stable |
| Frozen T1+T2 scores | `experiments/hle400/hle_arms.json` | frozen |
| T1-missed pool (audit surface) | `experiments/hle400/t3/t1_missed_pool.jsonl` | 1082 rows |
| astra re-judgment | `experiments/hle400/t3/t2_astra_audit.jsonl` | 1082 rows |
| FP evidence | `experiments/hle400/t3/fp_judge.jsonl` | 87 rows, 1 FP |
| Cluster diff | `experiments/hle400/hle_t3_cluster_diff.jsonl` | stable |
| **Final scores** | `experiments/hle400/t3/t3_final_scores.json` | authoritative |
| **Revision detail (id+evidence)** | `experiments/hle400/t3/t3_revision_detail.json` | authoritative |
| Generator scripts (TRAE workdir) | `t3_t1_missed_export.py`, `t3_astra_missed_rescue.py`, `t3_fp_export.py` | reproducible |

```bash
# 1) Enumerate the T2 audit surface (deterministic T1-missed pool, no API): 1082 rows
python3 t3_t1_missed_export.py

# 2) Independent astra re-judgment of the full pool (K=1) -> t2_astra_audit.jsonl
python3 t3_astra_missed_rescue.py

# 3) Recompute the authoritative final score (drift-free):
#    correct = hs.score_t1(...) (minus is_fp)  UNION  astra_verdict==True on T1-missed
#    output: experiments/hle400/t3/t3_final_scores.json
```