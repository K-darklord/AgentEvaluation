# Paper PPT — Slide Content & Layout (EGTE)

**Source of truth**: `paper/paper_outline.md` (seven-stage evidence chain) + `docs/PAPER_DRAFT.md`
(§2 roles/arms, §3 frozen standard, §4 results, §5 research questions). Aligned as of **2026-10-27**.

---

## P1 — Title & the falsifiable main question · [stage 1 — main question]

**Layout**: title band (top), one-sentence question (center, large), falsification strip (bottom bar).

**Content**

- **Title**: *Error-Guided Test-Time Elimination (EGTE): Distilling Answer-Free Error Mechanisms for
  Train-Free Recursive Self-Improvement.*
- **One-sentence, falsifiable claim**: *Is a generalized error set an effective information source for recursive
  self-improvement — does gold-free error-set feedback beat directionless sampling?*
- **Falsification boundary**: *if C3 does not systematically beat A3 on the hard slice (Δ_act ≤ 0 AND
  net Δ ≤ 0), the error-set-as-RSI-source claim fails.*

**Key output**: the single question the rest of the deck must answer; the failure criterion that gates it.

---

## P2 — Gap & motivation · [stage 2–3 — gap + simple-explanations-first]

**Layout**: left = "gap" (4 threads + the empty cell); right = "control arms as simple explanations".

**Content**

- **Static accuracy confounds capability with framework artifacts** — Intrinsic self-correction is unreliable → external feedback is necessary.
- **Gap**: no unified trajectory-class system; no external *gold-free* error signal that is *also* an
  RSI engine. The "learn-from-mistakes" family is occupied (Mistake Notebook, PRISM, Cliff, LANPO,
  Agent-R/TAPO/LEMMA) — EGTE differentiates on *answer-free, per-model, lower-bound* exclusion.
- **Simple explanations first**: the control arms are laid down to exclude the cheap alternatives — **A**
  (bare re-solve, T=0, single answer) is the floor; **A2** (fixed neutral placebo) rules out scaffolding
  alone; **A3** ("just sample more": i.i.d. sampling, T=0.7, N=10) is the test-time scaling baseline EGTE must beat.

**Key question**: *Is the effect attributable to the error-set signal, not to sampling or scaffolding?*
**Key output**: the arm table (P5) and the hard-slice definition.

---

## P3 — Core research questions & two hypotheses · [stage 4 — the questions that gate the claim]

**Layout**: top = Q1–Q5 band (each anchored to its role + hypothesis); bottom = two hypothesis cards with support + failure columns.

**Content**

- **Q1–Q5** — the five research questions the paper must answer (they are the contributions, not future work):

| #  | Research question | Role / hypothesis |
| -- | ----------------- | ----------------- |
| Q1 | Does the distiller's answer-free `mechanism` + `check_procedure` generalize to the critic's signal — firing on the right archetype across questions and families, not just the bank items? | distiller → critic |
| Q2 | Does the critic steer the solver toward correct directions — activating a correct answer at least as often as A3's i.i.d. sampling (`P_act ≥ A3`) at controlled EIR? | critic (H1) |
| Q3 | Does the evaluator exclude definitively-wrong candidates without cutting a correct one, stay `UNSURE` when evidence is weak, and lock the sticky state? | evaluator (H2) |
| Q4 | Is the selection mechanism itself evidenced per question — a traceable error mechanism, not noise or a lucky re-sample? | evaluator (H2) |
| Q5 | Is the C3-vs-A3 advantage question-type dependent (A3 strong on a multiple-choice vote, C3 broader on open-ended)? | boundary (H1) |

- **H1 (activation)** — the strong critic lifts reachability vs A3: `P_act ≥ A3` at controlled EIR.
  **Support**: transition evidence shows critic-activated correct answers ≥ A3's i.i.d. sampling.
  **Failure**: `P_act < A3`, or EIR exceeds ECR.  ↔ **Q2 + Q5**
- **H2 (mechanism)** — the evaluator's *elimination + mode* lock beats a plain majority vote on the hard slice.
  **Support**: lock raises accuracy vs a mode baseline while suppressing EIR, per-question traceable.
  **Failure**: lock ≤ vote, or elimination cuts a correct answer.  ↔ **Q3 + Q4**

**Key question**: *which of Q1–Q5, if answered, make the error-set-as-RSI-source claim survive?*
**Key output**: the two-hypothesis table (outline Tab 2) and the falsification grid (P1).

---

## P4 — Mechanism: the three-role, train-free EGTE pipeline · [stage 5 — mechanism]

**Layout**: top = role pipeline (5 boxes, one call each); bottom = EIR/ECR stability strip + single metric.

**Content**

- **Solver + three roles are SEPARATE calls** (correctness lives only in the scorer):
  1. **distiller** (build, gold available) → answer-free `mechanism` + `check_procedure`;
  2. **critic** (execute, gold-free) → `trigger` flags an answer *transition*, the evaluator wakes only then;
  3. **evaluator** (post-transition) → rubric judge (`contradiction / error / disconnection`) → `CUT / KEEP / UNSURE`.
- **EIR/ECR (per-round)** bridged to **`P_act` / lock-in (whole-loop)** algebraically (`r = 1 − ∏(1−ECR)`).
  **Both EIR and ECR are introduced by the in-loop critic**; the offline evaluator acts only on the EIR
  side (revert + lock), never raising ECR.
- **Single graded dimension**: **accuracy** (the metacognition dimension is dropped).
- **Lower-bound optimization**: accuracy rises by *reducing* errors, never by scoring the correct path.

**Key question**: *does the mechanism implement exclusion, not self-correction training?*
**Key output**: the role table (outline Fig 2) and the EIR/ECR decomposition.

---

## P5 — Stage A (activation): arm contrast & independent-sampling baseline · [motivation → mechanism]

**Layout**: left = arm table; right = "what this slide rules out" checklist (placebo / sampling / scaffolding).

**Content**

- **Headline causal contrast is A / A2 / A3 / C3 / A3C3**.

| Arm      | Definition                                                             | Role in the design                               |
| -------- | ---------------------------------------------------------------------- | ------------------------------------------------ |
| **A**    | bare re-solve, T=0, single answer, zero intervention                   | floor: raw latent accuracy                       |
| **A2**   | fixed neutral placebo, T=0, single answer                              | placebo control for scaffolding                  |
| **A3**   | self-consistency (Wang et al. 2022), T=0.7, N=10, i.i.d. majority vote | **independent-sampling baseline EGTE must beat** |
| **C3**   | strong critic (in-loop) + evaluator `rubric_ce` (offline)              | treatment: Stage A (activation) + Stage B (lock) |
| **A3C3** | A3-seeded round-0, then the C3 loop                                    | stacked treatment (sampling + EGTE)              |

- **The comparison is to independent sampling and placebo**: A3 answers "does error-set guidance beat
  *more i.i.d. sampling*", A2 answers "does scaffolding alone explain the effect".
- **This slide feeds H1 (Q2)**: the activation evidence is the A3 ↔ C3 contrast, not a new experiment.

**Key question**: *does the strong critic activate a correct answer at least as often as A3's i.i.d.
sampling (`P_act ≥ A3`), at controlled EIR?* → **Key output**: the activation profile (per-arm
`P_act`, EIR) and the arm table (outline Tab 1).

---

## P6 — Stage B (locking): the evaluator's decision rule · [mechanism]

**Layout**: left = review verdict chain (`CUT / KEEP / UNSURE` → elimination + mode).

**Content**

- **Review verdicts**: `CUT` (revert to old) / `KEEP` (clean transition, keep new) / `UNSURE` (keep both);
  aggregation = **elimination + mode**, with an all-UNSURE trace falling back to `mode`.
- **The evaluator only suppresses EIR** — it never raises ECR (Stage B locks, never re-samples toward new error).

**Key question**: *does the evaluator's elimination lock outperform a plain majority vote, and is the
exclusion attributable to a real error mechanism (Q3, Q4)?* → **Key output**: the lock-in rate / EIR-suppression table.

---

## P7 — Decision: three-axis comparison on the hard slice · [stage 6 — decision]

**Layout**: three-axis decision strip; fixed-denominator risk comparison.

**Content**

- **Three axes on the hard slice**: `Δ_act` (activation), settle vs vote, net final.
- **Fixed-denominator comparison** (headroom buckets exclude `never`); same-coverage risk vs strong baselines (settle / mode / A3).
- The A3 ↔ C3 contrast decomposes into Stage A (activation) + Stage B (lock). Numeric results live in the draft master table (§3), withheld here pending the full re-run.

**Key question**: *does C3 beat A3 systematically, and does the gain decompose into Stage A + Stage B?*
**Key output**: the decision table (outline Tab 3) and the falsification verdict (P1).

---

## P8 — Robustness & limitations · [stage 7 — boundary]

**Layout**: robustness matrix (cross-model × task-family); failure-case list.

**Content**

- **Cross-condition reproduction**: cross-model (12–15) × cross-task-family.
- **Cost–benefit**: settle is free vs Stage-B evaluator cost.
- **Explicit failure cases**: settle-locked-wrong, no-commit, inconsistent transitions.
- **Boundary**: the transition-evidence signal is question-type-dependent — it currently shows on one slice but not on HLE; Phase 3 must test whether the transition rationale transfers across benchmark families (not just one slice).

**Key question**: *where does the claim's boundary lie, and under which conditions does it fail?*
**Key output**: the robustness matrix (outline Tab 4) and the failure-case list.

---

## Key figures / tables (cross-slide index)

- **Fig 1** (P2): capability curve → self-improvement engine (reframe).
- **Fig 2** (P4): the three-role EGTE pipeline (distiller / critic / evaluator) over the EIR/ECR stability diagram.
- **Fig 3** (P6): Stage-B evaluator pruned state chain → `CUT / KEEP / UNSURE`.
- **Tab 1** (P5): control arms `A / A2 / A3 / C3 / A3C3`.
- **Tab 2** (P3): two hypotheses (H1 activation / H2 mechanism) + falsification criteria.
- **Tab 3** (P7): same-coverage risk across selectors on the hard slice.
- **Tab 4** (P8): robustness matrix (cross-model × task family).