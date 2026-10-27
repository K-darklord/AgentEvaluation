# HLE Pilot (n=50) — A3 vs C3 transition analysis record

**Status**: verified quantitative record · **Date**: 2026-10-26
**Companion to**: `docs/PAPER_DRAFT.md` · **Scorer**: `scorer_LLM_rescue` (T1 exact-match + T2 one-way FN judge).
**Data**: `experiments/_analysis/hle_head2head_rows.json` (aligned per-question), `experiments/_analysis/hle_rubric_ce.jsonl` (lock_status / strict-correct / activated).

---

## 1. Aggregate (verified, aligned scorer_LLM_rescue)

- tasks compared: **50**
- A3 (self-consistency, N=10 @ T=0.7): vote = 7/50 = 0.14
- C3 strong-critic alone (T=0): final = 7/50 = 0.14
- C3 full = strong critic + rubric evaluator (`rubric_ce`): final = 10/50 = 0.20
- C3 full with abstain fallback (`rubric_v5`): final = 3/50 = 0.06

Head-to-head (A3 vote vs C3 full):
- both correct: **6** — hle_008, hle_010, hle_022, hle_042, hle_045, hle_048
- C3 saves (A3 wrong -> C3 right): **4** — hle_028, hle_032, hle_038, hle_040
- C3 loses (A3 right -> C3 wrong): **1** — hle_013
- net (saves − losses) = **3**
- discordant pairs total = **5** (McNemar needs ~20–25)

---

## 2. Evaluator lock_status decomposition (34 multi-answer tasks)

`strict` = locked verdict string == gold (T1). `rescue` = strict missed but T2 judge credited.

| lock_status | n | strict-correct | rescue-correct (final) | mechanism |
|---|---|---|---|---|
| `locked_directional` | 7 | 0 | 0 | evidence-anchored endorsement (EGTE-specific) |
| `locked_majority` | 7 | 1 | 2 | majority vote over surviving fragments |
| `all_unsure_fallback_mode` | 17 | 3 | 5 | all-UNSURE -> mode fallback |
| `no_survivors` | 1 | 0 | 0 | no surviving candidates |
| `undecided_switch` | 1 | 0 | 0 | undecided switch |
| `tie_abstain` | 1 | 0 | 0 | tie -> abstain |

Key fact: `locked_directional` fires 7 times and is correct **0** times (strict AND rescue).
Every correct C3 output flows through `locked_majority` or the mode fallback. The mode fallback is
**not** a copy of A3's i.i.d. majority vote: it selects the answer that *persists across the critic's
rounds* — a sticky settle state of the sequential loop. That is a real, distinguishable selection
mechanism; it is simply not the evidence-anchored `locked_directional` channel EGTE claims.

---

## 3. The saves and the loss, per question

### 3.1 C3 saves (A3 wrong, C3 right) — 4

**hle_028** · shape=`symbol` · gold=`\pi` · lock=`None`
  SAVE — single-answer; already correct at C3 round-0 (T=0 greedy). A3 N=10 vote missed it. Temperature/init artifact, NOT a loop correction.

**hle_032** · shape=`word` · gold=`(r,t)` · lock=`locked_majority`
  SAVE — locked_majority (evaluator majority), gold `(r,t)`; T2 judge credited (strict string differs). Majority over surviving fragments, not evidence-anchored elimination.

**hle_038** · shape=`symbol` · gold=`$9\pi(3 + 2\sqrt{3})$` · lock=`all_unsure_fallback_mode`
  SAVE — all_unsure_fallback_mode, gold `9pi(3+2sqrt3)`; T2-judge-rescued symbolic equivalence. Sticky-mode fallback, not evidence-anchored elimination.

**hle_040** · shape=`text` · gold=`-2+1/((1-DawsonF[1])/E^3+DawsonF[2])` · lock=`all_unsure_fallback_mode`
  SAVE — all_unsure_fallback_mode, text gold; T2-judge-rescued equivalence. Sticky-mode fallback, not evidence-anchored elimination.

### 3.2 C3 loss (A3 right, C3 wrong) — 1

**hle_013** · shape=`text` · gold=`fluent_0(object_1_type_0, object_1_type_0)` · lock=`all_unsure_fallback_mode`
  LOSS — A3 majority vote correct (`fluent_0(...)`), C3 mode fallback wrong. C3 not uniformly better.

### 3.3 Reading

Of the 4 saves: hle_028 is already correct at C3 init (temperature/init, not the loop);
hle_032/038/040 are judge-rescued *sticky/fallback* selections, not evidence-anchored eliminations.
Net effect is +3. Reachability is essentially a wash (A3 16/50 vs C3 15/50 activated) and the shared
judge grades both arms identically, so neither is the differential: the +3 is a **selection**
difference — C3's sticky-mode lock commits the correct-equivalent answer where A3's i.i.d. majority
does not (and the reverse on hle_013).

---

## 4. Per-question matrix (A3 vote vs C3 full)

| tid | form | gold (trunc.) | A3.vote | C3.full | verdict | lock_status | C3 activated |
|---|---|---|---|---|---|---|---|
| hle_001 | int | 13425 | n | n | neither | `-` | n |
| hle_002 | symbol | u(t)(v_i(t) + \rho) | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_003 | text | Cut off of LFC > 4 in contaminated... | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_004 | text | 2, 4, 5 | n | n | neither | `all_unsure_fallback_mode` | Y |
| hle_005 | word | Heinemannomyces | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_006 | int | 11 | n | n | neither | `-` | n |
| hle_007 | symbol | \(\Delta E= 0.0423\text{ eV}\) | n | n | neither | `locked_directional` | n |
| hle_008 | word | Spiro[4.5]decan-6-one | Y | Y | both | `all_unsure_fallback_mode` | Y |
| hle_009 | symbol | \mu a. \theta(1, a+\mu b.\theta(0,... | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_010 | int | 4809 | Y | Y | both | `-` | Y |
| hle_011 | int | 5 | n | n | neither | `-` | n |
| hle_012 | symbol | n + (\frac{\pi^2}{6} - 1)n\alpha | n | n | neither | `locked_majority` | n |
| hle_013 | text | fluent_0(object_1_type_0, object_1... | Y | n | **A3-only(LOSS)** | `all_unsure_fallback_mode` | Y |
| hle_014 | word | cliff-room-both-neither-room | n | n | neither | `locked_majority` | n |
| hle_015 | symbol | $\pi_0 = \frac{\rho}{2(e^{\rho} - ... | n | n | neither | `-` | n |
| hle_016 | word | Yes | n | n | neither | `all_unsure_fallback_mode` | Y |
| hle_017 | int | 352311 | n | n | neither | `locked_directional` | n |
| hle_018 | symbol | $\frac{E(1+g) - d}{q}\]$ | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_019 | text | כִּ֗יל סָ֥ף מָ֣ה הִים נַ֣חְ נֶ֑ שַ... | n | n | neither | `locked_directional` | n |
| hle_020 | word | Meyerhold | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_021 | symbol | $f(w)=\bot\multimap\bot^{1+w}, C =... | n | n | neither | `locked_directional` | n |
| hle_022 | int | 841 | Y | Y | both | `locked_majority` | Y |
| hle_023 | int | 6 | n | n | neither | `-` | n |
| hle_024 | int | 9 | n | n | neither | `-` | n |
| hle_025 | int | 142 | n | n | neither | `no_survivors` | Y |
| hle_026 | int | 0 | n | n | neither | `-` | Y |
| hle_027 | int | 12 | n | n | neither | `locked_majority` | n |
| hle_028 | symbol | \pi | n | Y | **C3-save** | `-` | n |
| hle_029 | symbol | (a) Yes (b) 0 (c) $-w^2(g^2 a \cdo... | n | n | neither | `locked_majority` | n |
| hle_030 | symbol | r^{A(1-\cos\theta)+B\sin\theta} | n | n | neither | `undecided_switch` | n |
| hle_031 | text | no,no,no,no,yes,yes,yes,no,yes,2,2... | n | n | neither | `-` | Y |
| hle_032 | word | (r,t) | n | Y | **C3-save** | `locked_majority` | Y |
| hle_033 | int | 2394 | n | n | neither | `-` | n |
| hle_034 | word | Mayakovsky | n | n | neither | `locked_directional` | n |
| hle_035 | text | v₀𝛼arctanh(√(2h𝛼c+h²)/(𝛼c+h), 𝛼=c𝛾... | n | n | neither | `locked_directional` | n |
| hle_036 | int | 1.03 | n | n | neither | `locked_directional` | n |
| hle_037 | int | 3.8 | n | n | neither | `tie_abstain` | n |
| hle_038 | symbol | $9\pi(3 + 2\sqrt{3})$ | n | Y | **C3-save** | `all_unsure_fallback_mode` | n |
| hle_039 | symbol | $18\pi$ | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_040 | text | -2+1/((1-DawsonF[1])/E^3+DawsonF[2... | n | Y | **C3-save** | `all_unsure_fallback_mode` | n |
| hle_041 | mc | D | n | n | neither | `-` | n |
| hle_042 | mc | D | Y | Y | both | `all_unsure_fallback_mode` | Y |
| hle_043 | mc | D | n | n | neither | `-` | n |
| hle_044 | mc | B | n | n | neither | `all_unsure_fallback_mode` | n |
| hle_045 | mc | C | Y | Y | both | `all_unsure_fallback_mode` | Y |
| hle_046 | mc | C | n | n | neither | `locked_majority` | Y |
| hle_047 | mc | B | n | n | neither | `-` | n |
| hle_048 | mc | B | Y | Y | both | `-` | Y |
| hle_049 | mc | D | n | n | neither | `-` | n |
| hle_050 | mc | A | n | n | neither | `all_unsure_fallback_mode` | Y |

---

## 5. Verdict: real or random?

Sub-significant and selection-mediated (not reachability-mediated: activation is ≈ equal at 16 vs 15).
Net = +3 on n=50 with 5 discordant pairs, an order of magnitude below the ~20–25 pairs needed to pin a
~5pp effect. The EGTE-specific `locked_directional` lock contributes 0 correct. The critic does its
job (candidate pool + activation), but the *evaluator* has not yet demonstrated evidence-anchored
elimination: its gain is a real trajectory-sticky selection (a mechanism A3 lacks) but not the
evidence-anchored lock EGTE claims. This pins the conditions (headroom, symbolic-equivalence
activation, CUT gate strength) for the next test; it is not yet a positive claim for EGTE.

