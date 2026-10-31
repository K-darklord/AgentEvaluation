# Paper Outline: Error-Guided Test-Time Elimination (EGTE)

> Follows the seven-stage evidence-chain framework (problem → gap → motivation → hypotheses →
> mechanism → decision → boundary). **Trimmed 2026-10-31**: single story (EGTE as a train-free
> test-time elimination method), HLE-400 as the main evidence, hypotheses remapped to the framework's
> H1 identifiable / H2 mechanism-sensitive / H3 decision value.

## Working title (draft)

"Error-Guided Test-Time Elimination: Excluding Wrong Candidates with Answer-Free Error Mechanisms"

---

## 1. Introduction · [stage 1 — main question]

- **Open on the gap self-consistency leaves**: with sampling + majority vote, the correct answer
  often *appears* in the candidate pool but is not *held*.
- **Intrinsic self-correction is unreliable** (Huang 2023): an external signal is necessary; PRMs /
  verifiers supply one but need training and positive labels.
- **One-sentence, falsifiable main question**: *Can a model's own past errors — distilled offline into
  answer-free error mechanisms — serve as the external signal for a gold-free, train-free test-time
  loop that recovers the correct answers self-consistency cannot hold, on harder problems the error
  bank has never seen?*
- **Falsification boundary**: *if C3 does not systematically beat A3 on HLE-400 (paired McNemar not
  significant and Δacc ≤ 0), the claim fails.*
- **Existence claim** (stated up front): EGTE is an unoptimized instantiation; the paper shows the
  mechanism yields a gain, not that each role is optimal.

## 2. Related Work · [stage 2 — gap]

- Written as a contrast table (what prior work established / what remains to test), not a list.
  Three threads: test-time scaling (self-consistency, best-of-N + verifier); self-correction with
  external feedback (Reflexion, Self-Refine, LLM-as-judge; Liu & Meng for the per-round EIR/ECR
  vocabulary); learn-from-mistakes (Mistake Notebook, PRISM, Cliff, LANPO, Agent-R / TAPO / LEMMA).
- Candidate gap: no gold-free, train-free error signal that (i) stores answer-free *mechanisms* rather
  than instances, (ii) only *excludes*, never scores the correct direction, (iii) wakes only on an
  answer transition — and no test of whether such a signal transfers to an unseen harder family.

## 3. Motivation / Preliminary · [stage 3 — simple-explanations-first]

- Simple-route baselines, same model / split / scorer, with cost recorded: **A** (raw ability),
  **A2** (feedback scaffold with no content), **A3** (just sample more). Each tests one simple
  explanation.
- Evidence: on the bank-source benchmarks these baselines leave little separable headroom; the
  unexplained failures concentrate on HLE, where A3 activates correct answers it does not hold (`P_act(A3)` vs A3 vote acc).
- **Observation vs inference separation**: early anomalies traced to measurement / rubric drift, not a
  treatment effect (`PHASE2_SUMMARY §4`).
- Outcome: **continue** — simple routes insufficient, remaining failures describable.

## 4. Research Questions & Hypotheses · [stage 4 — problem narrowing]

- Narrowed question: *fixing the solver, the loop and the scorer, does an answer-free error bank give
  the critic + evaluator information beyond what a content-free feedback loop (A2) or i.i.d. sampling
  (A3) already provides, on HLE?*
- **Operational definition** of the intermediate object (answer-free `mechanism` + `check_procedure`):
  class-level / gold-isolated / cross-family / data-distilled — with counter-examples (PPT P4).
- Three hypotheses, each with support + failure criteria:
  - **H1 identifiable** — the critic's gold-free suspicion names the archetype the solver actually
    committed on HLE items it has never seen. *Measured offline*: an independent gold-visible judge
    (same role class as the distiller) labels the archetype of every wrong round of C3's trajectories;
    hit = judge label ∈ critic's archetype set; reported against a permutation baseline with a bootstrap
    interval, plus a 20-item human spot check of the judge. *Weakens*: hit rate at the permutation
    baseline, or one archetype fires regardless.
  - **H2 mechanism-sensitive** — three layers, all offline from the four arms: (i) C3 beats A2 (the
    irrelevant-change control: same loop, content-free feedback) on the same items; (ii) C3's
    wrong→correct transitions are preceded by a `critic_direction` suspicion while A2's are preceded by
    none (by construction); (iii) on open-form HLE items, where the A3 vote collapses, C3's gain
    persists — so the gain cannot be voting (`PHASE2_SUMMARY §18.2`). *Weakens*: C3 ≈ A2, or the
    gain is confined to MCQ items.
  - **H3 decision value** — on the same 400 items, C3 beats the strong baseline A3 at no higher
    cost (tokens per correct). *Weakens*: gain not significant, or cost exceeds A3.
- Ablation under H3: eliminator on/off — which stage carries the gain (critic alone + mode vs
  evaluator elimination + mode).
- Optional strengthening of H2: a bank-free generic critic (critic prompt without the archetype
  vocabulary).

## 5. Method: Error-Guided Test-Time Elimination (EGTE) · [stage 5 — mechanism]

- **Control arms & A-seeding**: A (bare T=0) is round 0 of every arm — A2 / A3 / C3 initialize from A's
  deterministic answer (no round-0 drift); A3 = A-init + N-1 = 9 i.i.d. T=0.7 samples, majority-voted
  (A does not enter the vote pool).
- Measurement: **per-round EIR/ECR** (Liu & Meng; stability condition `ECR/EIR > Acc/(1−Acc)`) and
  **per-item `P_act` / `P_flip`** (whole loop; under A-seeding `P_act` splits into `P_act_init` at
  round 0 from A vs `P_act_loop` at round ≥ 1 = the critic's activation). The critic introduces both
  EIR and ECR; the evaluator acts only on the EIR side.
- **Three-role, train-free pipeline (same base model; separate calls):**
  1. **distiller** (offline, gold available): wrong answer → answer-free `mechanism`
     (`trigger` + `definition` + `check_procedure`; 7 cross-benchmark archetypes; chain in Appendix A).
  2. **critic** (in-loop, gold-free): names the archetype the committed answer most likely violates;
     emits 1–3 suspicions with the step to re-verify; never names an answer.
  3. **evaluator** (post-transition, gold-free, offline, `rubric_ce`): each answer switch →
     `CUT` / `KEEP` / `UNSURE` (UNSURE = not eliminated); elimination + mode, all-UNSURE → mode.
- **Mechanism evidence (H1, H2)**: all offline, no new runs — the transition-evidence chain
  (committed answers + per-round `critic_direction` + evaluator verdict) from the HLE-400 C3 and A2
  trajectories (analogue of `experiments/_analysis/critic_direction_evidence.md`); a gold-visible
  offline judge labelling the archetype of each wrong round for H1; the MCQ / open-form split for H2.

## 6. Main Results / Decision Evaluation · [stage 6 — decision]

- **Main table = HLE-400**, same items for every arm: A / A2 / A3 / C3 × {acc, settle, tokens-per-correct
  incl. all role calls, per-round EIR/ECR, `P_act_init`/`P_act_loop`, paired McNemar vs A3}; A3C3 optional,
  not run.
- **Bank provenance table**: which (model, benchmark) errors built the bank vs what is evaluated —
  HLE never in the bank.
- Ablation table: eliminator on/off (+ bank-free critic if run).

## 7. Robustness & Limitations · [stage 7 — boundary]

- **For whom it holds**: HLE-400 split by answer type (MCQ vs open-ended); worst subgroup reported.
- **Cost**: C3's total consumption vs A3; stated separately from failure conditions.
- **Where it fails**: locked-wrong (early stop on a wrong answer), no-commit, inconsistent transitions;
  correct candidates cut (false-CUT rate).
- **Existence claim and headroom**: the three roles are unoptimized; headroom = gap between measured
  EIR/ECR and the threshold `Acc/(1−Acc)`.
- Single solver model; n = 400; no stronger-model comparison (claim is same-model + external bank);
  reliable abstention out of scope.

## 8. Conclusion · [evidence correspondence]

- Map each conclusion to the four evidence types: motivation / mechanism / decision / boundary.
- Two sentences on the outer loop as the natural continuation (re-distilling new failures into the
  bank after each pass): described, not claimed.

## Appendices

- A: error-mechanism distillation (L1/L2/L3) + the 7 archetypes + critic prompt.
- B: evaluator rubric (`rubric_ce`), survive-score mapping, CUT / KEEP / UNSURE definition; scorer tiers.
- C: reproducibility (frozen runtime standard, seeds, config, git tags, `REPRODUCIBILITY.md`).
- D: transition-evidence examples; the gold-visible judge protocol for H1 and its 20-item spot check.

## Key figures / tables

- Fig 1: one EGTE cycle — offline distillation → online elimination.
- Fig 2: the three-role pipeline over the EIR/ECR two-state chain.
- Fig 3: transition-evidence chain on one HLE trajectory (critic suspicion → answer change → verdict).
- Tab 1: arms (A / A2 / A3 / C3 / A3C3).
- Tab 2: bank provenance vs evaluation target.
- Tab 3: HLE-400 main table.
- Tab 4: H1 archetype hit rate vs permutation baseline; H2 (C3 vs A2 paired, attributed transitions, MCQ / open-form split); ablation (eliminator on/off).
