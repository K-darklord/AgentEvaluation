# Paper Outline: The Error Set as an RSI Information Source

> Re-anchored 2026-10-10 (RSI); **rewritten 2026-10-17** to follow the seven-stage
> evidence-chain framework (problem → gap → motivation → hypotheses → mechanism →
> decision → boundary). Supersedes the 2026-09 finance-interference skeleton.

## Working title (draft)

"Error-Guided Test-Time Elimination (EGTE): Distilling Answer-Free Error Mechanisms for
Train-Free Recursive Self-Improvement"

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
  locking (Stage B), realised test-time as the three-role EGTE evaluator?*
- **Falsification boundary** (framework stage 1): *if C does not systematically beat A3 on
  the hard slice (Δ_act ≤ 0 AND net Δ ≤ 0), the error-set-as-RSI-source claim fails.*
- **One instrument, used twice**: the diagnosis layer is the measurement substrate of the
  improvement — not the deliverable.
- **Metacognition hook**: "knowing what you don't know" (Kadavath et al.; Reinforced
  Hesitation) defined by an *external transition signal*, not intrinsic confidence.

## 2. Related Work · [stage 2 — gap]

- Four threads (full map + 52 sources in `docs/WORKMAP.md`): agent evaluation (static →
  capability curve), verification/self-correction (external feedback necessary),
  optimization (RLVR), inference scaling (test-time compute).
- Gap: no unified trajectory-class system; no external gold-free metacognitive proxy that
  is *also* an RSI engine.
- Nearest neighbours (differentiate explicitly): Feedback Friction, Overthinking,
  Activation-probe self-correction, Liu & Meng (EIR/ECR).
- **The "learn-from-mistakes" family is already occupied** — Mistake Notebook Learning
  (abstracted error patterns), PRISM (asymmetric FP bias), Cliff (first-mistake negative
  feedback), LANPO (relevant abstraction), Agent-R / TAPO / LEMMA (error-driven distillation).
  The full EGTE-vs-neighbour positioning table is `PHASE2_SUMMARY §13.3`.

## 3. Motivation / Preliminary · [stage 3 — simple-explanations-first]

- Control arms as simple-explanation exclusion: **A3** (i.i.d. sampling, T=0.7, N=10) =
  "just sample more" baseline; **C** (weak-critic perturbed) must beat it.
- **Observation vs inference separation**: C < A3 anomalies traced to measurement / rubric
  drift, not a treatment effect (`PHASE2_SUMMARY §4`).
- **settle > final** (+3–13 pp, zero extra cost) motivates a cheap Stage-A selector and
  pushes Stage B onto a small hard slice.

## 4. Research Questions & Hypotheses · [stage 4]

- RQ1–6 (RQ1–4 = measurement layer; RQ5–6 = RSI claim).
- Three falsifiable hypotheses with support + failure criteria:
  - **H1 recognition** — weak critic lifts `P_act` (Claim 1).
  - **H2 mechanism** — transition rationale is a real, task-sensitive signal (Claim 2 / metacognition).
  - **H3 decision value** — locking beats strong baselines at equal cost/coverage (Claim 3).
  - (Full table: `PHASE2_SUMMARY §2.8`.)

## 5. Method: Error-Guided Test-Time Elimination (EGTE) · [stage 5 — mechanism]

- Measurement layer: **EIR/ECR** (per-round) vs **P_act / lock-in** (whole-loop), bridged
  algebraically (`r = 1 − ∏(1−ECR)`).
- **Three-role, train-free evaluator (solver + three roles are SEPARATE calls):**
  1. **distill** (build, gold available): wrong answer → answer-free `mechanism` + `check_procedure`.
  2. **check** (execute, gold-free): `trigger` signature flags when the answer transitions; the
     evaluator wakes only then (never reads the round's CoT at rest).
  3. **review** (post-transition): rubric judge (disconnection/contradiction/error) consumes
     `check_procedure` + `evidence` → `CUT` / `UNSURE` / `ANSWER` (metacognitive abstain).
- Two orthogonal scores: **accuracy** + **metacognition** (honest UNSURE on `never`).
- EGTE raises accuracy by *reducing errors* (lower-bound optimization), not by scoring the
  correct path — the solver's capability is lifted by mechanism, never by memorization.
- Intervention controls (H2): vary only the rationale/signal; key-change delta must exceed
  irrelevant-change delta.

## 6. Main Results / Decision Evaluation · [stage 6 — decision]  ⚠ after experiments

- Three-axis comparison on the hard slice (low-confidence / activated-but-unlocked tasks;
  definition in `PHASE2_SUMMARY §13`): `Δ_act`, settle vs vote, net final.
- Fixed-denominator comparison (headroom buckets exclude `never`); same-coverage risk vs
  strong baselines (settle / mode / A3).
- Metacognition dimension: honest-abstain on `never` tasks — the incremental value A3 lacks.

## 7. Robustness & Limitations · [stage 7 — boundary]  ⚠ after Phase 3

- Cross-model (12–15) / cross-task-family reproduction; cost–benefit (settle free vs Stage B
  cost); explicit failure-case list (settle-locked-wrong, no-commit, inconsistent transitions).

## 8. Conclusion · [evidence correspondence]

- Map each conclusion to the four evidence types: motivation / mechanism / decision / boundary.

## Appendices

- A: weak-critic construction + error taxonomy.
- B: anomaly / interference registry (evidence of measurement discipline).
- C: reproducibility (seeds, config, git tags, `REPRODUCIBILITY.md`).
- D: trajectory examples (activation / locking / no-commit / None-state).

## Key figures / tables

- Fig 1: capability curve → self-improvement engine (reframe).
- Fig 2: the three-role EGTE evaluator (distill / check / review) over the EIR/ECR stability diagram.
- Fig 3: Stage-B / EGTE review role pruned state chain → CUT / UNSURE / ANSWER.
- Tab 1: control arms (A / A2 / A3 / C / C*).
- Tab 2: three claims + falsification criteria + required n.
- Tab 3: same-coverage risk across selectors on the hard slice.
- Tab 4: robustness matrix (cross-model × task family).