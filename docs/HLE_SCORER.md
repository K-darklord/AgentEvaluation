# HLE-400 Scorer Document (T1 / T2 / T3)

> **Note (2026-11-11).** Current frozen scores are sidecar v3 (`docs/HLE400_FROZEN_DATA.md`, top block): v2 plus re-scoring of trajectories rerun after interface failures. The second model, the third model and the two added self-consistency samples are scored with truncation rule → exact match → independent judge (K=1) → the existing adjudication rules, without a new round of dispute resolution. A human audit of the model-based tier is specified in `docs/HUMAN_AUDIT_PLAN.md`.

**Version**: 1.3 (2026-11-02) — K=3 adjudication applied; §1.2 is authoritative
**Scope**: `hle400` slice, n = 400
**Arms**: A / A2 / A3 / C3  (A3C3 is an empty placeholder in this slice)
**Protocol alignment**: `docs/EVALUATION_STANDARD.md` §0 (role separation), §2 (tier
dispatch), §5 (T3 review); authoritative protocol `docs/RESEARCH_PLAN.md` §5.9.

This document is the **single audit surface for the scorer**. It records, per arm, the
three-tier grading result and the evidence trail for every correction (FN and FP). It
does **not** restate solver/critic/evaluator work — scoring is a separate runtime role
(§0).

---

## 0. Tier definitions (one line each)

| Tier | What it does | Deterministic? | Reads |
|---|---|---|---|
| **T1** | token-free exact match, dispatched by `answer_type` / `shape` | yes | committed final answer only |
| **T2** | one-way **FN rescue**: LLM judge re-reads the committed final answer (never CoT), only on T1-missed rows, never overturns a T1-correct row | no (judge) | committed final answer |
| **T3** | contested-row human/multi-judge review (small set, not an automated override) | n/a | row evidence |

**Truncation rule (top priority, all arms).** Any elected winning round whose
`finish_reason == "length"` is a budget-truncated fragment, not a clean commit. It is
scored **wrong** (no-commit) and never sent to a judge, uniformly across all arms and
metrics. This runs before T1/T2/T3 and can roll back a row that T1/T2/astra would
otherwise call correct.

**FN vs FP.** A T1→T2 raise is a **FN rescue** (`disagreement == "FN"`). A row that T1
scored correct but may be a false positive is an **FP candidate** (risk channels:
multipleChoice first-letter extraction, symbol/word/text `_norm` collapsing).

**Metric definitions.** `init` = round-0 commit; `final` = last commit; `settle` =
trailing 3-identical-commit (abstain if none); `mode` = majority committed answer
(tie → latest); `vote` (A3 only) = majority over `rounds[1:]` (excludes A-seeded
round-0), tie → earliest-appearing.

---

## 0.5 Experiment data (raw input + per-arm trajectories)

Every number in §1–§6 is produced from these inputs. An auditor can re-derive the scorer
from the trajectories alone (the scorer reads only the committed `final_answer` per round).

| Data | File | Arm |
|---|---|---|
| 400-question raw input | `data/raw/hle/hle_400_new.jsonl` (`question`/`gold`/`answer_type`/`shape`) | — |
| selection index | `data/raw/hle/hle_400_new_selection.json` | — |
| A trajectories | `experiments/hle400_A/deepseek-v4-flash/loop_trajectories.jsonl` + `loop_summary.json` | A |
| A2 trajectories | `experiments/hle400_A2/deepseek-v4-flash/loop_trajectories.jsonl` + `loop_summary.json` | A2 |
| A3 trajectories | `experiments/hle400_A3/deepseek-v4-flash/loop_trajectories.jsonl` + `loop_summary.json` | A3 |
| C3 trajectories | `experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl` + `loop_summary.json` | C3 |

Each trajectory JSONL records per-task rounds with `final_answer`, `reasoning_content`,
`finish_reason` — the exact fields fed to `_early_stop_key` and to the scorer.

---

## 1. Frozen aggregate scores (single source of truth)

Source: `experiments/hle400/hle_arms.json` (git-committed / tagged). `accuracy =
t1_accuracy + fn_rescued / n`. `judge_n` = number of T1-missed rows sent to the T2 judge.

| Arm | Metric | accuracy | t1_accuracy | judge_n | fn_rescued |
|---|---|---|---|---|---|
| A | init | 0.2350 | 0.1575 | 337 | **31** |
| A2 | init | 0.2350 | 0.1575 | 337 | 31 |
| A2 | final | 0.2800 | 0.2000 | 320 | **32** |
| A2 | settle | 0.2700 | 0.1900 | 295 | **32** |
| A2 | mode | 0.2800 | 0.2000 | 320 | **32** |
| A3 | init | 0.2350 | 0.1575 | 337 | 31 |
| A3 | vote | 0.2925 | 0.2200 | 312 | **29** |
| C3 | init | 0.2350 | 0.1575 | 337 | 31 |
| C3 | final | 0.2975 | 0.2100 | 316 | **35** |
| C3 | settle | 0.2400 | 0.1825 | 211 | **23** |
| C3 | mode | 0.2900 | 0.2075 | 317 | **33** |

> `init` is **shared** across A / A2 / A3 / C3 (identical round-0 bare re-solve commit),
> so the `init` FN list is one and the same 31-row set (`hle_t3_contested_A.json`).

## 1.1 T3-final scores (K=1 astra, truncation rule) — superseded by §1.2

`correct = T1_correct (minus FP) \u222a astra-correct T1-missed`. Drift-free — does not
read the non-deterministic DeepSeek T2 verdict. Authority:
`experiments/hle400/t3/t3_final_scores.json` + `t3_revision_detail.json` +
`docs/HLE400_T3_AUDIT_REPORT.md`.

| Arm | Metric | T1 | T1+T2 (frozen) | **T3 final** | \u0394 |
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

Evaluator (`C3 eval` / `A3C3 eval`) is **offline and blank** — fill from the evaluator
run, not this table.

---

## 1.2 K=3 adjudicated final scores (v2) — **authoritative**

Pipeline: K1 astra per-round sidecar → truncation rule → K=3 re-review of the 69 winner-churn rows and
376 gap rows → **second-agent adjudication of the 22 disputed rows** (`experiments/hle400/t3/k3_dispute_list.md`),
with **one verdict per answer variant** applied uniformly to every arm / round / winner
(`scripts/t3_k3_adjudicate_and_recompute.py`). Outputs: `t3/k3_adjudication.json` (25 overrides, each with
reason + confidence), `t3/is_correct_t3_sidecar_v2.json` (per-round correctness — the ONLY legal input for
EIR/ECR/P_act and for evaluator scoring), `t3/t3_final_scores_v2.json`, `t3/transition_metrics_v2.json`.

**Truncation-round voting rule (freeze-key).** For *structured* answers a length-truncated round recovers
its key from the CoT tail (`_early_stop_key`) and still casts a vote; for *free-text* answers a truncated
string is treated as a **singleton vote**; a truncated round that gets elected is scored **wrong**. Tasks
affected: `hle_379`, `hle_078`, `hle_115`, `hle_371`. If this rule were instead changed, the readouts would
move to C3.mode = **155**, C3.settle = **116**, A3.vote = **138** — **not adopted** in this project.

| Arm | Metric | T1 | T1+T2 (frozen) | T3 K1 (§1.1) | **v2 final** | correct/400 |
|---|---|---|---|---|---|---|
| A / A2 / A3 / C3 | init | 0.1575 | 0.2350 | 0.2800 | **0.2825** | 113 |
| A2 | final | 0.2000 | 0.2800 | 0.3525 | **0.3550** | 142 |
| A2 | settle | 0.1900 | 0.2700 | 0.3375 | **0.3400** | 136 |
| A2 | mode | 0.2000 | 0.2800 | 0.3525 | **0.3550** | 142 |
| A3 | vote | 0.2200 | 0.2925 | 0.3325 | **0.3400** | 136 |
| C3 | final | 0.2100 | 0.2975 | 0.3475 | **0.3500** | 140 |
| C3 | settle | 0.1825 | 0.2400 | 0.2925 | **0.2950** | 118 |
| C3 | mode | 0.2075 | 0.2900 | 0.3600 | **0.3625** | 145 |

**K=3 dispute resolution (22 rows → per-task verdicts, applied to every variant of the same answer):**

| task | K3 proposal | adjudication | basis |
|---|---|---|---|
| `hle_021` | demote ×3, unstable ×2 | **correct** (encoding `f(w)=⊥^w⊸1`, `C=f(b)^{⊗m}`) | derivability checked on {1,1}/m1b2 ✓, {2}/m2b1 ✗, {1,2}/m3b1 ✗, {1,3}/m2b2 ✗, {4}/m2b2 ✗; `1⊸X≡X` collapsing variants and `⊥^{⊗w}` variants stay wrong. **User may overrule** |
| `hle_030` | demote (0/3) | **correct** for every answer exhibiting `r^{A(1−cosθ)+B sinθ}`; wrong-sign / `e^{Bθ}` variants wrong | K1 scored identical formulas C/w across rounds; made uniform. **User may overrule (corrector-only strictness)** |
| `hle_036` | demote | **wrong** (1.0436) | 0.5 % tolerance on 1.03; 1.029/1.031/1.035 stay correct |
| `hle_129` | demote (+αP₁ clip) / restore (−αP₁) | **demote rejected, restore rejected**; sign of the first stated `b` decides | derived: `|K_Y|=(P₁+1)(P₂+2bα+1)−(b+α)²`, max at `b=αP₁` for `X₂=U₂+bZ₁`; clipping to `|b|≤√P₂` is the feasible optimum. 10 clip/piecewise rounds (A3/C3) raised, A2 r8 (`−αP₁`) lowered |
| `hle_280` | demote ×5, unstable ×2 | **correct** for `2+` regularised forms (sum or max); `1+`, `√BL+L`, `B+…` wrong | Θ-equivalent to gold in both regimes; K3 votes on identical formulas were 0/3, 1/3, 2/3 — pure judge noise. **User may overrule** |
| `hle_386` | demote | **correct** (trans–cis photoisomerization = rotation about N=N); "flat at sunrise and sunset" variants wrong | same claim as the 15 rounds K1 already accepted |
| `hle_170` | unstable (keep) | **wrong** (C3 r8 and A3 r8 are scansion fragments, no D/S string) | only `DDSSDS` counts |
| `hle_121` | unstable ×2 | **correct — all variants**, incl. the 2 `none` rows and 5 K1-wrong rounds | each big-M / `b↔1−b` variant verified case-by-case to force `y=min(0,x)` for `x<1` (needs `l≤0`, as the gold does) |
| `hle_153` | unstable | **correct** (path-integral forms incl. grand-canonical) | question asks for the path-integral form; gold is the trace form. **User may overrule (strict-gold)** |
| `hle_374` | unstable | **correct** | compresses to `ULDL` by the question's own rule |

Sensitivity for the four user-overrulable tasks (setting the task to *wrong* removes it from): `hle_021` →
A2.final/settle/mode, C3.final/settle/mode (−1 each); `hle_030` → all four init, A2.final/settle/mode (−1 each);
`hle_153` → every metric (−1 each, symmetric); `hle_280` → all four init, A3.vote (−1 each).

**Paired (McNemar exact), v2:** C3.mode vs A3.vote 32/23 (p = 0.28); C3.final vs A3.vote 26/22 (p = 0.67);
C3.final vs A2.final 26/28 (p = 0.89); C3.mode vs A2.mode 21/18 (p = 0.75). Every loop/vote arm beats
A.init (p ≤ 0.0014). **vs shared init (113):** A2.final kept 107 / lost 6 / gained 35; A3.vote 100 / 13 / 36;
C3.final 94 / **19** / 46; C3.mode 102 / 11 / 43.

**Transition metrics (per-round correctness from sidecar v2; A3 rounds are i.i.d. samples, so its EIR/ECR
are NOT loop rates and must not be reported as such):**

| arm | P_act | P_flip (final) | EIR (num/den) | ECR (num/den) | wrong→correct switches | correct→wrong switches | mean rounds |
|---|---|---|---|---|---|---|---|
| A2 | 0.385 | 0.030 | 0.097 (38/391) | 0.058 (67/1157) | 65 | 37 | 4.87 |
| C3 | 0.4825 | 0.1325 | 0.298 (168/564) | 0.113 (195/1724) | 190 | 162 | 6.72 |
| A3 (samples) | 0.495 | — | n/a | n/a | — | — | 10 |

Stability check `ECR/EIR > Acc/(1−Acc)`: C3 0.38 vs 0.39 — at the boundary; A2 0.60 vs 0.39 — inside.
Evaluator (`C3 eval`) remains blank; it is scored against sidecar v2, same rules.

---

## 2. T1 results (deterministic, fully reproducible, no correction pending)

T1 is token-free and intervention-free; its numbers are fixed by the frozen extractor
regression suite and reproduce exactly (`--no-judge` smoke test matches `t1_accuracy`
per metric at zero LLM cost).

| Arm | Metric | t1_accuracy |
|---|---|---|
| A / A2 / A3 / C3 | init | 0.1575 |
| A2 | final | 0.2000 |
| A2 | settle | 0.1900 |
| A2 | mode | 0.2000 |
| A3 | vote | 0.2200 |
| C3 | final | 0.2100 |
| C3 | settle | 0.1825 |
| C3 | mode | 0.2075 |

**No T3 correction applies to T1 rows**: T2/T3 only ever raise a T1-missed row to
correct (FN), never lower a T1-correct row.

---

## 3. T2 (judge) corrections — FN-rescue rows

### 3.1 Counts

| Arm | Metric | frozen fn_rescued | current replay count | status |
|---|---|---|---|---|
| A / A2 / A3 / C3 | init | 31 | 31 | ✅ stable |
| A2 | final / settle / mode | 32 / 32 / 32 | *(in progress)* | ⏳ pending |
| A3 | vote | 29 | *(in progress)* | ⏳ pending |
| C3 | final | 35 | 36 | ⚠️ drift |
| C3 | settle | 23 | 25 | ⚠️ drift |
| C3 | mode | 33 | 35 | ⚠️ drift |

### 3.2 T2 judge drift (historical — resolved by T3, no longer read)

`T2_TEMPERATURE=0` but the `deepseek-v4-pro` judge is **not strictly deterministic
server-side**: the same `(question, gold, final_answer)` returned different
CORRECT/INCORRECT verdicts across runs (frozen C3 `fn_rescued` 35/23/33 vs a fresh
cached replay 36/25/35; `t1_accuracy` and `judge_n` were byte-identical — only
`fn_rescued` moved). This is a **historical note only**: the authoritative T3 final
score (§1.1) no longer reads the DeepSeek T2 verdict
(`correct = T1_correct (minus FP) ∪ astra-correct T1-missed`), so the T2 drift no
longer moves any frozen number. The §1 "T1+T2 (frozen)" column remains as a comparison
baseline, not a source of truth.

### 3.3 Per-row evidence files

| Scope | File | rows |
|---|---|---|
| init (A/A2/A3/C3 shared) | `experiments/hle400/hle_t3_contested_A.json` | 31 |
| C3 final | `experiments/hle400/hle_t3_contested_C3_final.json` | 36 *(drift)* |
| C3 settle | `experiments/hle400/hle_t3_contested_C3_settle.json` | 25 *(drift)* |
| C3 mode | `experiments/hle400/hle_t3_contested_C3_mode.json` | 35 *(drift)* |
| A2 final/settle/mode | `experiments/hle400/hle_t3_contested_A2_{metric}.json` | ⏳ pending |
| A3 vote | `experiments/hle400/hle_t3_contested_A3_vote.json` | ⏳ pending |

Each row carries `task_id`, `gold`, `answer_type`, `shape`, `final_answer`, `question`
(the judge's evidence). The judge's per-call result is persisted under a
`sha256(question␀gold␀answer_type␀shape␀resp)` key in:

- `experiments/hle400/t3/t3_score_cache.jsonl` (A / A2 / C3 shared judge cache)
- `experiments/hle400/t3/t3_score_cache_a3.jsonl` (A3 vote judge cache)

### 3.4 FN per-arm task-id lists (the concrete rescue set)

These are the **FN** rows — T1 judged wrong, T2 judge rescued to CORRECT. One list per
arm×metric. Per-row `id + evidence` (gold, final_answer, question) lives in the
`hle_t3_contested_*.json` file named in §3.3.

**init (shared across A / A2 / A3 / C3 — 31 rows, stable):**

```
hle_028 hle_038 hle_048 hle_067 hle_081 hle_091 hle_096 hle_105 hle_115 hle_129
hle_168 hle_186 hle_209 hle_222 hle_230 hle_235 hle_259 hle_288 hle_289 hle_292
hle_293 hle_312 hle_327 hle_337 hle_354 hle_368 hle_369 hle_386 hle_388 hle_390
hle_400
```

**C3 final (36 replayed / 35 frozen — drift):**

```
hle_001 hle_028 hle_038 hle_040 hle_045 hle_054 hle_081 hle_087 hle_090 hle_091
hle_105 hle_114 hle_121 hle_168 hle_176 hle_186 hle_193 hle_196 hle_209 hle_230
hle_235 hle_258 hle_289 hle_292 hle_293 hle_327 hle_336 hle_350 hle_351 hle_354
hle_368 hle_369 hle_386 hle_390 hle_396 hle_400
```

**C3 settle (25 replayed / 23 frozen — drift):**

```
hle_028 hle_038 hle_040 hle_054 hle_090 hle_091 hle_105 hle_168 hle_176 hle_186
hle_193 hle_209 hle_230 hle_235 hle_258 hle_289 hle_292 hle_293 hle_336 hle_351
hle_354 hle_368 hle_369 hle_390 hle_400
```

**C3 mode (35 replayed / 33 frozen — drift):**

```
hle_001 hle_028 hle_038 hle_040 hle_054 hle_067 hle_081 hle_087 hle_090 hle_091
hle_105 hle_121 hle_168 hle_170 hle_176 hle_186 hle_193 hle_209 hle_222 hle_230
hle_235 hle_258 hle_289 hle_292 hle_293 hle_327 hle_336 hle_350 hle_351 hle_354
hle_368 hle_369 hle_386 hle_390 hle_400
```

**A2 final / settle / mode (32 / 32 / 32 frozen) and A3 vote (29 frozen):** ⏳ per-row
lists still being exported (`t3_fn_export.py`); the aggregate `fn_rescued` is already frozen
in §1. Backfill the concrete ids here once those background exports land, then reconcile
under §3.2.

---

## 4. FP audit (T1-correct rows at false-positive risk)

Source: `experiments/hle400/hle_t3_fp.jsonl` — **137 unique rows** (T1-correct, but the
T1 dispatch could have produced a false positive).

| risk | rows | unique tasks | human-review burden |
|---|---|---|---|
| `letter` | 57 | 38 | ✅ must review (multipleChoice first-letter extraction) |
| `norm` | 30 | 29 | ✅ must review (symbol/word/text `_norm` collapse) |
| `low` | 50 | 48 | auto-pass (strict numeric equality, no review needed) |

→ **87 rows** (`letter` + `norm` = **67 unique tasks**) require human review; `low` =
50 rows (48 tasks) are programmatically clean.

**FP unique task-id lists by risk:**

- `letter` (38):

```
hle_042 hle_045 hle_047 hle_048 hle_050 hle_051 hle_063 hle_065 hle_074 hle_078
hle_111 hle_134 hle_137 hle_143 hle_145 hle_149 hle_165 hle_172 hle_178 hle_182
hle_250 hle_253 hle_296 hle_310 hle_313 hle_314 hle_315 hle_316 hle_318 hle_320
hle_322 hle_335 hle_341 hle_352 hle_357 hle_358 hle_362 hle_383
```

- `norm` (29):

```
hle_008 hle_013 hle_028 hle_031 hle_032 hle_054 hle_068 hle_081 hle_105 hle_131
hle_177 hle_188 hle_189 hle_190 hle_196 hle_245 hle_249 hle_265 hle_274 hle_287
hle_302 hle_303 hle_321 hle_339 hle_349 hle_361 hle_363 hle_367 hle_374
```

- `low` (48):

```
hle_001 hle_010 hle_022 hle_026 hle_036 hle_056 hle_058 hle_059 hle_073 hle_082
hle_087 hle_089 hle_099 hle_103 hle_106 hle_110 hle_119 hle_148 hle_206 hle_210
hle_213 hle_217 hle_218 hle_227 hle_229 hle_235 hle_237 hle_238 hle_240 hle_241
hle_242 hle_244 hle_247 hle_251 hle_257 hle_260 hle_261 hle_266 hle_269 hle_271
hle_277 hle_283 hle_294 hle_300 hle_324 hle_332 hle_346 hle_395
```

> FP and FN are opposite directions and never overlap on the **same** (arm, metric) row:
> a row is either T1-correct (FP audit) or T1-missed (FN rescue). The same *task* can
> appear in both lists only across different arms/metrics (e.g. `hle_028` is FN in `init`
> and FP-`norm` in another metric) because different metrics elect different committed winners.

---

## 5. Answer-cluster (semantic-equivalence) findings

Purpose: A3 `vote` / A2 `mode` / C3 `mode` elect a winner by *answer-identity key*. The
frozen key is a raw-normalized string, so answers that are **substance-equal but
format-different** (`0.96` vs `24/25`, `-1` vs `-1.0000`, `0/1` vs `0`) split into the
wrong buckets and can change the elected winner.

Source: `experiments/hle400/hle_t3_cluster_diff.jsonl` (authoritative current output) +
`experiments/hle400/t3/cluster_log.jsonl` (merge events).

**Questions whose answer rounds are cluster-consistent (format-equivalent commits):**

| task_id | arm.metric | equivalent commits | winner change | verdict flip |
|---|---|---|---|---|
| hle_235 | A3.vote | `0.96` ≡ `24/25` | yes | **yes** ⚠️ |
| hle_126 | C3.mode | `-1` ≡ `-1.0000` | yes | no |
| hle_185 | A2.mode | `0` ≡ `0/1` | no | no |
| hle_249 | A3.vote | `329/150` ≡ `2303/1050` | no | no |
| hle_032 | A3.vote | `(r, t)` vs `r, t` (spacing) | yes | no |

**Conclusion**: exactly **1 genuine verdict flip** from semantic-equivalence —
`hle_235` (A3.vote), where `24/25` and `0.96` are the same number but the frozen T1
`int` parser scores `24/25` as a mismatch. This flip is a **format-equivalence
candidate** to be re-decided by the full `scorer_LLM_rescue` (T1 + judge), not by T1
alone. The other tasks (`hle_126`, `hle_185`, `hle_249`) merge but do not change their
winner; `hle_032` is a normalization-only cosmetic diff.

---

## 6. T3 review — COMPLETE (2026-11-02)

T3 was executed as an independent re-judgment of the **full T1-missed pool** (1082 rows)
with `gpt-6-astra` (K=1). See `docs/HLE400_T3_AUDIT_REPORT.md` (authoritative) and
`experiments/hle400/t3/t2_astra_audit.jsonl` + `t3_revision_detail.json` (per-row evidence).

Result classes (resp-key level): missed_rescue 64 (40 tasks, after truncation rollback),
false_rescue 2,
confirmed 74, true_neg 932, none 7. FP audit: 1 true FP (`hle_182`, C3.final/mode).
Cluster: 1 verdict flip (`hle_235`, verdict unchanged). The final score (§1.1) is
drift-free and does NOT depend on the drifted DeepSeek T2 verdict.

Second-agent audits: `docs/HLE400_T3_SECOND_AUDIT.md` (all 67 missed_rescue, 2 false_rescue, 7 none,
137 FP candidates read individually; truncation rule) and §1.2 (K=3 dispute adjudication). Correction to the
`none` sign-off: `hle_121` init and A3.vote rows are valid MILP encodings → correct (see §1.2).

---

## 7. Data provenance map (where each conclusion lives — for audit)

| Conclusion | Authoritative file | Status |
|---|---|---|
| Raw 400-question input | `data/raw/hle/hle_400_new.jsonl` | ✅ stable |
| Per-arm trajectories | `experiments/hle400_{A,A2,A3,C3}/deepseek-v4-flash/loop_trajectories.jsonl` | ✅ stable |
| Frozen aggregate scores + T1 + T2 `fn_rescued` | `experiments/hle400/hle_arms.json` | committed (frozen) |
| T1 per-metric reproduction | `experiments/hle400/hle_arms_rows.jsonl` (schema: task_id/gold/answer_type/shape/A) | committed |
| T2 FN per-row evidence (init) | `experiments/hle400/hle_t3_contested_A.json` | ✅ stable (31) |
| T2 FN per-row evidence (C3) | `experiments/hle400/hle_t3_contested_C3_{final,settle,mode}.json` | ⚠️ drift (36/25/35) |
| T2 FN per-row evidence (A2/A3) | `experiments/hle400/hle_t3_contested_{A2,A3}_*.json` | ⏳ in progress |
| Judge per-call verdict cache | `experiments/hle400/t3/t3_score_cache.jsonl`, `t3_score_cache_a3.jsonl` | accumulating |
| Judge-drift row tagging | `experiments/hle400/t3/judge_drift.jsonl` | ⏳ pending (t3d) |
| T1-missed pool (audit surface) | `experiments/hle400/t3/t1_missed_pool.jsonl` | ✅ stable (1082) |
| astra independent re-judgment | `experiments/hle400/t3/t2_astra_audit.jsonl` | ✅ stable (1082) |
| **T3 final scores** | `experiments/hle400/t3/t3_final_scores.json` | ✅ authoritative |
| **T3 revision detail (id+evidence)** | `experiments/hle400/t3/t3_revision_detail.json` | ✅ authoritative |
| **Consolidated T3 report** | `docs/HLE400_T3_AUDIT_REPORT.md` | ✅ (K1 stage) |
| K=3 dispute list / payload | `experiments/hle400/t3/k3_dispute_list.md`, `k3_flip_payload.json` | input to adjudication |
| **K=3 adjudication (reasons, confidence, needs_user)** | `experiments/hle400/t3/k3_adjudication.json` | ✅ authoritative |
| **Per-round correctness v2** | `experiments/hle400/t3/is_correct_t3_sidecar_v2.json` | ✅ authoritative — only input for EIR/ECR/P_act/evaluator |
| **Final scores v2 + paired + lost/gained** | `experiments/hle400/t3/t3_final_scores_v2.json` | ✅ authoritative |
| **Transition metrics v2** | `experiments/hle400/t3/transition_metrics_v2.json` | ✅ authoritative |
| Adjudication + recompute script | `scripts/t3_k3_adjudicate_and_recompute.py` | reproducible |
| FP candidate list | `experiments/hle400/hle_t3_fp.jsonl` | ✅ stable (137) |
| Cluster-diff (semantic-equivalence) | `experiments/hle400/hle_t3_cluster_diff.jsonl` | ✅ stable |
| Cluster merge events | `experiments/hle400/t3/cluster_log.jsonl` | historical (superseded summary) |
| Stale pre-fix cluster artifacts | `experiments/hle400/t3/cluster_summary.json`, `winner_changes.jsonl` | ⚠️ obsolete — do NOT audit against these |
| Generator scripts (TRAE workdir) | `c3_contested.py`, `t3_fn_export.py`, `t3_fp_export.py`, `t3_cluster_diff.py`, `t3_judge_drift.py` | reproducible |

> ⚠️ **Two files are superseded**: `t3/cluster_summary.json` and `t3/winner_changes.jsonl`
> were written by an earlier cluster script whose winner derivation contained a tie-break
> bug (now fixed). Audit against `hle_t3_cluster_diff.jsonl`, not those two.

---

## 8. Reproduction commands

```bash
# T1 zero-cost reproduction (must match t1_accuracy exactly)
python3 c3_contested.py --no-judge

# C3 FN rows (T1 + cached judge)
python3 c3_contested.py

# A2 / A3 FN rows
python3 t3_fn_export.py --arm A2 --cache experiments/hle400/t3/t3_score_cache.jsonl
python3 t3_fn_export.py --arm A3 --cache experiments/hle400/t3/t3_score_cache_a3.jsonl

# Cluster semantic-equivalence diff
python3 t3_cluster_diff.py

# Judge-drift stability replay (K majority)
python3 t3_judge_drift.py --k 3
```