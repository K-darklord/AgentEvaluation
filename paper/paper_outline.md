# Paper Outline: Error-Guided Test-Time Elimination (EGTE)

> Re-anchored 2026-10-10 (RSI); **rewritten 2026-10-17** to follow the seven-stage
> evidence-chain framework (problem → gap → motivation → hypotheses → mechanism →
> decision → boundary). Supersedes the 2026-09 finance-interference skeleton.

## Working title (draft)

"Error-Guided Test-Time Elimination (EGTE)"

## Target venue

Nature Machine Intelligence / IEEE TPAMI / NeurIPS (primary); ACL / EMNLP workshop (early checkpoint).

---

## 1. Introduction · [stage 1 — main question]

- **Failure-oriented open**: a single static accuracy confounds capability with
  evaluation-framework artifacts (measured 26 pp spurious deficit, FAB pilot;
  `docs/RESEARCH_PLAN.md §1.1`).
- **Intrinsic self-correction is unreliable** (Huang 2023): external feedback is necessary.
- **One-sentence, falsifiable main question**: *Is an error set an effective information
  source for recursive self-improvement — i.e. does gold-free error-set feedback beat
  directionless sampling, and does the gain decompose into reachability (Stage A) +
  locking (Stage B), realised test-time as the three-role EGTE pipeline?*
- **Falsification boundary** (framework stage 1): *if C3 does not systematically beat A3 on
  the hard slice (Δ_act ≤ 0 AND net Δ ≤ 0), the error-set-as-RSI-source claim fails.*
- **One instrument, used twice**: the diagnosis layer is the measurement substrate of the
  improvement — not the deliverable.
- **Error-set hook**: "knowing what you don't know" (Kadavath et al.; Reinforced
  Hesitation) is realized by an *external, error-set transition signal*, not intrinsic
  confidence.

## 2. Related Work · [stage 2 — gap]

- Four threads (full map + 52 sources in `docs/WORKMAP.md`): agent evaluation (static →
  capability curve), verification/self-correction (external feedback necessary),
  optimization (RLVR), inference scaling (test-time compute).
- Gap: no unified trajectory-class system; no external gold-free error signal that is
  *also* a test-time-elimination engine.
- Nearest neighbours (differentiate explicitly): Feedback Friction, Overthinking,
  Activation-probe self-correction, Liu & Meng (EIR/ECR — the **source** of the EIR/ECR
  vocabulary, stability threshold, and steady state we reuse; our contribution is the gold-free
  *test-time elimination* realisation over the error bank, not the chain quantities).
- **The "learn-from-mistakes" family is already occupied** — Mistake Notebook Learning
  (abstracted error patterns), PRISM (asymmetric FP bias), Cliff (first-mistake negative
  feedback), LANPO (relevant abstraction), Agent-R / TAPO / LEMMA (error-driven distillation).
  The full EGTE-vs-neighbour positioning table is `PHASE2_SUMMARY §13.3`.

## 3. Motivation / Preliminary · [stage 3 — simple-explanations-first]

- Control arms as simple-explanation exclusion: **A3** (i.i.d. sampling, T=0.7, N=10) =
  "just sample more" baseline; **C3** (strong critic + offline evaluator) must beat it.
- **Observation vs inference separation**: early anomalies traced to measurement / rubric
  drift, not a treatment effect (`PHASE2_SUMMARY §4`).
- **settle > final** (+3–13 pp, zero extra cost) motivates a cheap Stage-A selector and
  pushes Stage B onto a small hard slice.

## 4. Research Questions & Hypotheses · [stage 4]

- Q1–Q5 — the five core research questions (Q1 signal generalization [distiller → critic];
  Q2 directional exploration (critic → solver), `P_act ≥ A3` [critic]; Q3 exclusion & abstention [evaluator];
  Q4 selection mechanism evidenced per question; Q5 A3-vs-C3 by question type).
- Two falsifiable hypotheses with support + failure criteria:
  - **H1 activation** — the strong critic lifts reachability vs A3: `P_act ≥ A3` at controlled EIR (↔ Q2 + Q5).
  - **H2 mechanism** — the evaluator's elimination + mode lock beats a plain majority vote on the hard slice (↔ Q3 + Q4).

## 5. Method: Error-Guided Test-Time Elimination (EGTE) · [stage 5 — mechanism]

- Measurement layer: **EIR/ECR** (per-round) vs **P_act / lock-in** (whole-loop), bridged
  algebraically (`r = 1 − ∏(1−ECR)`). Both EIR and ECR are introduced by the in-loop critic;
  the offline evaluator acts only on the EIR side (revert + lock), never raising ECR.
- **Three-role, train-free pipeline (solver + three roles are SEPARATE calls):**
  1. **distiller** (build, gold available): wrong answer → answer-free `mechanism` + `check_procedure`.
  2. **critic** (execute, gold-free): `trigger` signature flags when the answer transitions; the
     evaluator wakes only then (never reads the round's CoT at rest).
  3. **evaluator** (post-transition): rubric judge (disconnection/contradiction/error) consumes
     `check_procedure` + `evidence` → `CUT` / `KEEP` / `UNSURE`; elimination + mode yield the lock.
- Single graded dimension: **accuracy** (the metacognition dimension is dropped).
- EGTE raises accuracy by *reducing errors* (lower-bound optimization), not by scoring the
  correct path — the solver's capability is lifted by mechanism, never by memorization.
- Intervention controls (H2): vary only the rationale/signal; key-change delta must exceed
  irrelevant-change delta.
- **Eliminator switch (H2 ablation, inside C3)**: toggling the critic-free exclusion selector
  inside C3 — `off` = strong critic alone + mode (activation only), `on` = evaluator elimination +
  mode (full EGTE) — isolates the exclusion selector's Stage-B contribution from the critic's
  in-loop activation (replacing the dropped A3+Selector arm).

## 6. Main Results / Decision Evaluation · [stage 6 — decision]

- Three-axis comparison on the hard slice (low-confidence / activated-but-unlocked tasks;
  definition in `PHASE2_SUMMARY §13`): `Δ_act`, settle vs vote, net final.
- Fixed-denominator comparison (headroom buckets exclude `never`); accuracy and EIR/ECR vs
  strong baselines (settle / mode / A3).

## 7. Robustness & Limitations · [stage 7 — boundary]

- Cross-model (12–15) / cross-task-family reproduction; cost–benefit (settle free vs Stage B
  cost); explicit failure-case list (settle-locked-wrong, no-commit, inconsistent transitions).
- Transition-evidence generalisation: the Stage-B lock's evidence is question-type-dependent —
  it currently shows on one slice but not on `HLE` — so Phase 3 must test whether the transition
  rationale transfers across benchmark families, not just within a single slice.

### 7.1 The outer loop: recursive error-bank refinement

Beyond the inner test-time elimination (EGTE, over a frozen error bank), the "recursive" half of the
title is an **outer loop**: after each benchmark pass, newly gold-scored failures are distilled
back into the L3 bank (re-distillation), sharpening the same answer-free mechanisms rather than
accumulating instance memory. Label provenance is pinned — error labels come only from the frozen
scorer on failed runs, and the distiller is the sole gold reader, so the answer-free mechanism
never leaks gold to the runtime roles. The recursion is **bounded**: marginal bank information
`g(B_t)` is non-increasing (Proposition 2), so refinement saturates rather than diverges — the
bank converges into a reusable, cross-benchmark memory / generalization primitive.

## 8. Conclusion · [evidence correspondence]

- Map each conclusion to the four evidence types: motivation / mechanism / decision / boundary.

## Appendices

- A: error-mechanism distillation (L1/L2/L3) + strong-critic construction.
- B: anomaly / interference registry (evidence of measurement discipline).
- C: reproducibility (seeds, config, git tags, `REPRODUCIBILITY.md`).
- D: trajectory examples (activation / locking / no-commit / None-state).

## Key figures / tables

- Fig 1: capability curve → self-improvement engine (reframe).
- Fig 2: the three-role EGTE pipeline (distiller / critic / evaluator) over the EIR/ECR stability diagram.
- Fig 3: Stage-B evaluator pruned state chain → CUT / KEEP / UNSURE.
- Tab 1: control arms (A / A2 / A3 / C3 / A3C3).
- Tab 2: two hypotheses (H1 activation / H2 mechanism) + falsification criteria.
- Tab 3: accuracy and EIR/ECR across arms on the hard slice.
- Tab 4: robustness matrix (cross-model × task family).