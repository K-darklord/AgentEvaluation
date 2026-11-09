# Error-Guided Test-Time Elimination (EGTE) — Paper Draft

> **2026-10-31 trim.** Single story: EGTE as a train-free, gold-free test-time elimination method on
> the same base model, with the error bank as the only external signal. HLE-400 is the main evidence
> (the bank never contains an HLE item). Hypotheses follow the seven-stage framework: H1 identifiable /
> H2 mechanism-sensitive / H3 decision value; A2 is the irrelevant-change control for H2.
> Engineering history: `docs/PHASE2_SUMMARY.md`, `docs/PHASE3_SUMMARY.md`, `docs/WORKMAP.md`.
> Implementation parameters and the frozen runtime standard: Appendices B–C.

---

## 1. EGTE: definition and objective

### 1.1 What EGTE is

EGTE (Error-Guided Test-Time Elimination) treats a model's own **error bank** as a test-time
elimination information source. It targets capability that pretraining already imparted but that
sampling fails to hold: under self-consistency the correct answer often *appears* in the candidate pool
and is then discarded by the vote. EGTE does not train or prompt the model to *produce* the correct
answer; it distills, offline and from a gold-annotated error bank, a finite set of **generalizable
wrong-execution behaviours**, and uses them at test time — without gold, without training, on the
**same base model** — to **exclude** wrong candidates.

The design choice is asymmetric: model "what goes wrong" (a few answer-free, falsifiable exclusion
rules) rather than "what is right" (a scorer of the correct direction). This is stated as motivation,
not as a tested claim. The distilled memory is **answer-free** — a class-level `mechanism` +
`check_procedure` that never names a molecule / number / option — so it *can* transfer across questions
and families; whether it does is what the HLE-400 evaluation tests.

### 1.2 The two-state chain: EIR and ECR, per round and per item

- **Per-round rates (Liu & Meng).** `EIR` = P(correct → wrong) per round; `ECR` = P(wrong → correct)
  per round, over all (item, round) transition opportunities of an arm's full loop.
  `final = init + corrected(ECR) − flipped(EIR)`; iteration helps only while
  `ECR / EIR > Acc / (1 − Acc)` (standard two-state chain; cited, not claimed).
- **Per-item quantities (whole loop).** `P_act` = P(correct answer committed at least once);
  `P_flip` = P(a once-correct commit is not the locked answer). Under A-seeding (§2.2), every arm's
  round 0 is A's deterministic T=0 answer, so activation is split: `P_act_init` = P(correct at round 0,
  inherited from A) and `P_act_loop` = P(correct first committed at round ≥ 1) — only `P_act_loop` is
  the critic's contribution.
- **Who moves which rate.** The critic introduces both EIR and ECR; the evaluator does not raise ECR
  and only suppresses EIR (revert misdirected transitions, lock an already-activated correct answer).

## 2. Roles and arms

### 2.1 The roles, and the quantity each optimizes

Three strategy roles — **distiller**, **critic**, **evaluator** — framed by the **solver** (generates)
and the **scorer** (grades). Each role is a separate call on the same base model; correctness lives
only in the scorer.

| Role | When | Gold? | Produces | Optimizes |
|---|---|---|---|---|
| **distiller** | offline, over the error bank | yes | answer-free `mechanism` + `check_procedure` + `trigger` | the exclusion rules both runtime roles consume |
| **critic** | in-loop | no | 1–3 suspicions (archetype + the step to re-verify) | `P_act` ↑ at controlled EIR |
| **evaluator** | offline, on an answer transition only | no | `CUT` / `KEEP` / `UNSURE` → elimination + mode lock | `P_flip` ↓ (suppress EIR) |
| **solver** | generation | no | candidate answer + CoT | — |
| **scorer** | final grading, all arms | yes | correctness verdict | — (frozen) |

**Distiller.** Instance-level wrong-operation mechanisms → per-benchmark classes grouped by the shared
*wrong verb* → cross-benchmark **archetypes** (7: `constraint_blind`, `descriptor_conflation`,
`memory_substitution`, `procedure_truncation`, `sign_normalization_slip`, `retrieval_abort`,
`format_nonconformance`), each with a gold-free `check_procedure` and a `trigger`. Per-model banks;
never names answer text. (Chain → Appendix A.)

**Critic.** Reads the question, the committed answer, the hidden CoT and the archetype vocabulary;
reasons which archetype(s) this answer most likely violates; emits 1–3 suspicions naming the step /
value / assumption to re-verify. Never reads gold, never emits a probability, never names an answer.
Each suspicion is recorded as a structured `critic_direction` (archetype + suspicion) per round — the
unit of the mechanism evidence in §4.2.

**Evaluator (`rubric_ce`).** Offline; consumes only answer **switch edges**. A judge scores
`contradiction / error` over the transition's reasoning, `error` backlinked to the archetype bank; a
switch is `CUT` (revert) when either dimension clears the bar with open evidence, `KEEP` when the
transition is clean, otherwise `UNSURE` (= not eliminated; no abstention promised). Aggregation =
elimination + mode; all-UNSURE → mode. (Rubric, bar, survive-scores → Appendix B.)

### 2.2 Arms

All arms share the same solver base model, the same items, and the same scorer; they differ only in the
feedback / aggregation treatment.

| Arm | Definition | Role in the design |
|---|---|---|
| **A** | bare re-solve, T=0, single answer | floor: raw latent accuracy |
| **A2** | the same feedback loop with **content-free** placebo feedback (`critic_direction = None`) | **irrelevant-change control** for H2: scaffold without the error bank |
| **A3** | self-consistency (Wang et al. 2022), init = A round-0 + N-1 = 9 i.i.d. T=0.7 samples, majority vote over the 9 | strong baseline for H3 |
| **C3** | critic (in-loop) + evaluator `rubric_ce` (offline), elimination + mode | treatment: key intervention |
| **A3C3** (optional) | A3-seeded round-0, then the C3 loop | stacked; reported if run |

**A-seeding (shared round-0 anchor).** A's deterministic T=0 answer is round 0 of A2 / A3 / C3 — the
arms differ only from round 1 on, so "round-0 drift" (a T=0 re-solve that itself changes the answer)
cannot confound init-to-final movement. A3 = A-init + N-1 = 9 i.i.d. T=0.7 samples, majority-voted;
A itself never enters the vote pool.

**Ablation under H3 — eliminator on/off.** From the same C3 trajectories: `off` = critic alone + mode
lock; `on` = evaluator elimination + mode. **Optional strengthening of H2** — a bank-free critic (same
prompt, no archetype vocabulary).

---

## 3. Motivation and setup

### 3.1 Simple routes on the bank-source benchmarks (framework stage 3)

A / A2 / A3 on GSM8K, MATH-500, MMLU-Pro, BFCL, AIME, BBH, GPQA-Diamond — the benchmarks whose
errors built the bank. Same model, same scorer, cost recorded.

| Benchmark | n | A | A2 | A3 |
|---|---|---|---|---|
| … | 50 (198) | — | — | — |

Reading: simple routes leave little separable headroom here; the unexplained failures are on HLE, where A3
activates correct answers it does not hold (`P_act(A3)` vs A3 vote accuracy — the motivating gap).
Outcome: continue.

### 3.2 Bank provenance vs evaluation target (Tab 2) — full detail in `docs/ERROR_BANK_PROVENANCE.md`

| | Benchmarks | In the bank? | Role in the paper |
|---|---|---|---|
| **bank source** | GPQA-Diamond 9, MMLU-Pro 7, MATH-500 5, BFCL 5, BBH 4, AIME 3 = **33 wrong answers** → 24 answer-free entries, 7-archetype vocabulary (5 instantiated); frozen 2026-10-21 | yes — this model's errors on these items | provenance only; per-arm accuracies on these benchmarks are pre-freeze and not reported |
| **evaluation target** | **HLE-400** | **never** — no HLE item or error enters any bank | all hypotheses |

### 3.3 Model, standard, metrics

Model `deepseek-v4-flash` as solver, critic and evaluator. One frozen runtime standard for every arm —
`thinking_budget = 16384` (hidden CoT) + `REASONING_CONTENT_MARGIN = 8192` (visible answer) = `max_tokens 24576` per solver call, identical for all arms,
rounds, early stop, scorer (Appendix C). `T = 0.7` only for A3's samples; all other calls `T = 0`.

| Metric | Definition |
|---|---|
| `acc` | accuracy of the arm's locked / voted / final answer, scorer-graded |
| `tokens per correct` | total tokens of **all** calls (solver + critic + evaluator, or N samples for A3) ÷ correct items |
| `EIR`, `ECR` | per-round rates over all transition opportunities (§1.2) |
| `P_act`, `P_flip` | per-item activation / flip (§1.2); `P_act` split into `P_act_init` (round 0, from A) vs `P_act_loop` (round ≥ 1, critic's activation) |
| `settle` | the loop's trailing lock on three consecutive identical commits (abstain if none); a second lock alongside `mode` |
| `archetype hit rate` | over C3's wrong rounds, fraction where the gold-visible offline judge's archetype ∈ the critic's archetype set (H1); reported against a permutation baseline |
| `attributed-transition rate` | fraction of wrong→correct transitions whose preceding round carries a `critic_direction` suspicion (H2; presence, not match — match is H1) |
| `false-CUT rate` | fraction of CUT verdicts that removed a correct candidate |
| `McNemar` | exact paired test on the same items |

---

## 4. Results

### 4.1 H3 — decision value: HLE-400 main table (Tab 3)

| Arm | n | acc | settle | tokens / correct | EIR | ECR | `P_act_init` / `P_act_loop` | McNemar vs A3 |
|---|---|---|---|---|---|---|---|---|
| A | 400 | — | – | — | – | – | – | — |
| A2 | 400 | — | — | — | — | — | — | — |
| A3 | 400 | — | – | — | – | – | – | (ref) |
| C3 | 400 | — | — | — | — | — | — | — |

*A3C3 is optional and not run in this study.*

*Expected reading (HLE-200 in hand): C3 > A3 at no higher cost.*

### 4.2 H1 / H2 — mechanism table (Tab 4)

All offline, from the HLE-400 C3 and A2 trajectories (per-round `critic_direction`, committed-answer
trajectory), analogue of `experiments/_analysis/critic_direction_evidence.md`. The frozen standard runs
`rationale_mode = off`, so no solver self-attribution text exists on HLE; attribution is mechanical:
`critic_direction` present on the round preceding a wrong→correct transition.

**H1 — archetype hit rate.** An independent gold-visible offline judge (same role class as the
distiller; sees gold + the round's CoT, never later rounds) labels the archetype of every C3 wrong round
(or "none of the 7"). Hit = judge label ∈ critic's 1–3 archetypes. Baseline = hit rate with judge labels
permuted across rounds; bootstrap interval on the difference. A 20-item human spot check reports
agreement with the judge.

| H1 | value |
|---|---|
| C3 wrong rounds (n) | — |
| archetype hit rate | — |
| permutation baseline | — |
| difference (bootstrap 95% CI) | — |
| human spot check agreement (n = 20) | — |

**H2 — key vs irrelevant, three layers.**

| H2 | C3 | A2 | A3 |
|---|---|---|---|
| acc, all 400 (paired) | — | — | — |
| wrong→correct transitions | — | — | — |
| transitions preceded by a suspicion | — | 0 by construction | — |
| acc, MCQ items | — | — | — |
| acc, open-form items (A3 vote collapses here) | — | — | — |

*H1 holds if the hit rate exceeds the permutation baseline; H2 holds if C3 > A2, C3's transitions are
preceded by suspicions, and the gain persists on open-form items (so it cannot be voting;
`PHASE2_SUMMARY §18.2`).*

### 4.3 Ablation under H3 — eliminator on/off

| Variant | acc | `P_flip` | false-CUT rate |
|---|---|---|---|
| C3, eliminator **off** (critic + mode) | — | — | – |
| C3, eliminator **on** (full EGTE) | — | — | — |
| C3, bank-free critic (optional) | — | — | — |

### 4.4 Transition case studies (Fig 3)

Two to three HLE trajectories showing the full chain — committed answers, critic suspicion (archetype +
step), evaluator verdict per switch — including one failure case.

## 5. Hypotheses and what answers them

| Hypothesis | Supports | Weakens | Answered by |
|---|---|---|---|
| **H1 identifiable** — the critic's gold-free suspicion names the archetype the solver actually committed | hit rate above the permutation baseline; judge validated by spot check | hit at baseline, or one archetype fires regardless | §4.2 offline judge |
| **H2 mechanism-sensitive** — the error-bank direction (C3) beats the content-free scaffold (A2), the corrections follow suspicions, and the gain is not the vote | C3 > A2 paired; transitions preceded by suspicions; gain persists on open-form items | C3 ≈ A2; unattributed transitions; gain MCQ-only | §4.2 |
| **H3 decision value** — C3 beats A3 on the same items at no higher cost | paired McNemar significant; tokens/correct ≤ A3 | not significant; cost exceeds A3 | §4.1, §4.3 |

## 6. Robustness, limitations, conclusion

**For whom it holds.** HLE-400 split by answer type (MCQ vs open-ended); worst subgroup reported.

**Cost.** C3's total consumption vs A3, stated separately from failure conditions.

**Where it fails.** locked-wrong (early stop on a wrong answer), no-commit, inconsistent transitions; false-CUT cases.

**Existence claim and headroom.** The three roles are first instantiations, not optimized ones; the
headroom is the gap between measured EIR/ECR and `Acc/(1−Acc)` — critic EIR can be lowered, evaluator
retention of wrong→correct raised.

**Limitations.** Single solver model; n = 400; no stronger-model comparison (the claim is same-model +
external bank); reliable abstention out of scope (`UNSURE` = not eliminated).

**Conclusion.** One cycle — failures → answer-free distillation → gold-free elimination on an unseen
harder family — mapped to the four evidence types (motivation §3.1, mechanism §4.2, decision §4.1,
boundary §6). The natural continuation re-distills new failures into the bank after each pass; described,
not claimed.

---

## Appendices (pointers)

- **A** — L1/L2/L3 distillation chain, 7 archetype definitions, critic prompt.
- **B** — `rubric_ce` judge prompt, cut bar, survive-score mapping and tie-break; scorer tiers (T1 exact
  match / T2 one-way LLM rescue / T3 review); `settle` metric.
- **C** — frozen runtime standard (`thinking_budget 16384` + `REASONING_CONTENT_MARGIN 8192` = `max_tokens 24576`
  per solver call, `max_rounds 10`, `early_stop_n 3`, seeds, git tags,
  `docs/REPRODUCIBILITY.md`).
- **D** — transition-evidence examples; H1 gold-visible judge prompt and protocol (labels the round's own
  error only, never sees later rounds), permutation baseline, 20-item spot check.
