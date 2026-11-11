# Phase 2 · Claim 2 — C settle-wrong inventory & Stage-A optimization

**Scope**: deepseek-v4-flash, all task blocks. Settle = Stage-A lock (3 consecutive identical
committed answers = early-stop, PHASE2_SUMMARY §7 item 12). A3 selector = majority vote.
**Companion**: `PHASE2_SUMMARY.md` §2.7 (claims), §2.8 (hypotheses). **Date**: 2026-10-19. **Status**: draft for review.

---

## 1. Headline

| block | n | settle-correct | settle-WRONG | settleAcc | non-settle |
|---|---|---|---|---|---|
| phase1 (math/math500/mmlu_pro) | 150 | 94 | **2** | 97.9% (94/96) | 54 |
| new (aime/gpqa/bbh) | 144 | 129 | **5** | 96.3% (129/134) | 10 |
| gpqa 051-198 | 148 | 120 | **10** | 92.3% (120/130) | 18 |
| **total** | 442 | 343 | **17** | 95.3% (343/360) | 82 |

Claim 2 (`settleAcc(C) > voteAcc(A3)`) already holds on gpqa (92.3% vs 82.4%) and new (96.3% vs
93.8%). This doc inventories the residual **17 settle-wrong** tasks and asks whether Stage A can
push settleAcc higher without burning the settle coverage.

## 2. Two failure classes

`settle-wrong` splits into two mechanistically distinct classes:

- **Class L — lock-wrong after correct appeared (5 tasks).** The correct answer was reached at
  least once, then abandoned; the trailing 3-streak locked onto a *later wrong* answer. This is a
  **Stage-A lock defect** (recency-lock, not stability-lock) and is the only class Stage A can
  actually fix.
- **Class N — never-activated, locked wrong (12 tasks).** The correct answer never appeared; settle
  simply locked a wrong answer fast (3 rounds). This is a **reachability defect** (Claim 1), not a
  lock defect. It is the natural target of **Claim 3 (abstain)** rather than Claim 2.

## 3. Class L inventory (5 tasks) — Stage-A fixable

| # | task | family | gold | settled | rounds | committed sequence |
|---|---|---|---|---|---|---|
| L1 | gpqa_031 | gpqa | D | C | 6 | r0:**D**✓ r1:C r2:**D**✓ r3:C r4:C r5:C |
| L2 | gpqa_095 | gpqa | B | A | 5 | r0:**B**✓ r1:∅ r2:A r3:A r4:A |
| L3 | gpqa_103 | gpqa | B | D | 10 | r0:∅ r1:D r2:∅ r3:D* r4:D r5:**B**✓ r6:A r7:D r8:D r9:D |
| L4 | gpqa_109 | gpqa | C | D | 8 | r0:∅ r1:∅ r2:**C**✓ r3:**C**✓ r4:∅ r5:D r6:D r7:D |
| L5 | gpqa_163 | gpqa | B | A | 9 | r0:A r1:∅ r2:D r3:D r4:**B**✓ r5:∅ r6:A r7:A r8:A |

`∅` = no clean committed answer (prose/truncated round). `*` = scorer anomaly (see §5).

**Common failure pattern**: the model transiently holds the correct answer (L1/L2/L4 even hold it
twice), drops it for one interleaved round, then a *later* wrong value acquires a 3-streak and fires
early-stop. The current settle trigger (`EARLY_STOP_N=3`, recency, no memory of earlier correct or
stable states) cannot distinguish "held the right answer then flinched" from "genuinely converged on
the wrong answer".

## 4. Class N inventory (12 tasks) — Claim-3 territory

| # | task | family | gold | settled | rounds | committed sequence |
|---|---|---|---|---|---|---|
| N1 | mmlu_pro_012 | mmlu_pro | G | C | 3 | C C C |
| N2 | mmlu_pro_014 | mmlu_pro | D | B | 6 | B B H B B B |
| N3 | bbh_0003 | bbh | K | H | 4 | D H H H |
| N4 | bbh_0018 | bbh | A | D | 3 | D D D |
| N5 | bbh_0020 | bbh | F | D | 4 | D D D D |
| N6 | gpqa_018 | gpqa | C | D | 3 | D D D |
| N7 | gpqa_107 | gpqa | A | C | 3 | C C C |
| N8 | gpqa_130 | gpqa | A | B | 3 | B B B |
| N9 | gpqa_131 | gpqa | B | A | 4 | C A A A |
| N10 | gpqa_161 | gpqa | B | D | 3 | D D D |
| N11 | gpqa_168 | gpqa | D | A | 5 | B B A A A |
| N12 | gpqa_187 | gpqa | B | D | 3 | D D D |

These lock fast (median 3 rounds) onto a never-correct answer. Settle cannot rescue them — the
correct answer is outside the trajectory. For Claim 2 they are "fair" against A3-vote (A3 would also
miss them, since pass@k never samples the gold); for Claim 3 they are exactly where C should emit
`UNSURE` instead of a confident wrong commit.

## 5. Stage-A optimization (Claim 2 targets Class L)

Three candidate changes, gold-free (they never see the answer key):

1. **Stability-lock instead of recency-lock.** Replace the trailing-3-run selector with the
   most-stable-state selector already in `src/stable_state_estimator.py` (`freq` / `pi_argmax`). For
   L-class cases the correct answer has positive mass (appears ≥1×) but is not the *last* run; a
   frequency/stationary selector would often re-select it. (L1: freq(D)=2 vs freq(C)=4 → still C;
   L4: freq(C)=2 vs freq(D)=3 → still D — so freq alone is not enough; see note in §6.)
2. **History guard on the settle trigger.** Before honouring a 3-streak, check the trajectory for a
   prior answer that was (a) different from the current streak value and (b) held for ≥2 rounds or
   scored confident. If present, raise the trigger threshold (`EARLY_STOP_N`+=1 or refuse and hand to
   Stage B).
3. **Conservatively raise `EARLY_STOP_N` (3→4/5).** Directly reduces "flip then lock", at the cost
   of more non-settle (settle% falls below 87.8%); the displaced cases become Stage-B input.

Expected effect: settleAcc up, settle% down; the net accuracy move depends on whether Stage B can
handle the displaced cases better than a wrong settle would (that is the Claim-3 question).

## 6. Data caveat & open questions

- **Caveat**: this run is the old `reason_line` C-gpqa (`feedback_loop_C_20261015_175552`); its
  `committed_answer`/per-round `is_correct` are prose-polluted. The **headline settle-wrong=17 and
  settleAcc** are robust (settle fired at runtime), but the per-round "correct appeared" flag has
  some uncertainty — e.g. L3 shows `r3:D✓` against `gold=B`, a scorer artifact. The 5-vs-12 split may
  shift by ±1 once the clean `transition`-mode run (`stageb_rerun_ds_c_gpqa051_198_transition_20261019`)
  completes. Re-verify Class L/N membership on the clean run before tuning constants.
- **Open**: (i) `freq`/`pi_argmax` do not by themselves rescue L1/L4 — a combined "stability + recency"
  score is needed; (ii) the Class-N→`UNSURE` rule (Claim 3) needs the clean transition rationales to
  distinguish "still reasoning" from "confidently wrong", which is the one part correctly deferred to
  Phase 3.
