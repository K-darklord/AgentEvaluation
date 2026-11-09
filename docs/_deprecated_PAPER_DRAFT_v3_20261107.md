# Paper draft v3 (2026-11-07) — full first draft

> **Status.** Complete first draft on frozen HLE-400 data. Every number is freeze-key + sidecar v2 and traceable
> to `docs/HLE400_FROZEN_DATA.md`, `docs/PERSISTENCE_MECHANISM.md`, `docs/EVALUATOR_RESULTS.md`,
> `docs/ERROR_BANK_PROVENANCE.md`. Items marked **[TBD-x]** are listed in §R (remaining tasks) and in
> `docs/PAPER_CLOSEOUT_TASKS.md`. Two title variants are kept until C2 (bank-free critic) is read out.
> Previous draft archived as `docs/_deprecated_PAPER_DRAFT_20261031.md`.

---

## Title

- **Variant A (if C2 shows the bank matters — `C2_BANK_FREE_CRITIC_SPEC.md` §6 "bank 有效"):**
  *Error-Guided Critique Raises the Reachable Ceiling: A Generation–Selection Account of Train-Free, Gold-Free Test-Time Loops*
- **Variant B (if C2 shows the bank does not matter — "bank 无效"):**
  *Critique-Induced Persistence: Why a Zero-Parameter Counter Beats Self-Consistency, and Why a Same-Model Evaluator Cannot Beat the Counter*

- **Variant C (outcome-neutral; puts the positive result first):**
  *Two Frontiers of Test-Time Loops: Error-Guided Critique Raises the Reachable Ceiling, and the Vote Count Is
  the Limit of Same-Model Selection*

**[TBD-1]** choose after C2 (C is the default if C2 lands in the grey zone).

## Abstract (draft)

Test-time loops that let a model revise its answer under feedback are usually judged by one number, final
accuracy. We show that this number hides a two-factor structure: a loop's gain is the product of how often the
correct answer is *reached* (the generation frontier) and how often it is then *selected* (the selection
frontier). On 400 Humanity's Last Exam items never seen by any component, a train-free, gold-free loop in which
the same model (deepseek-v4-flash) acts as solver, critic and evaluator moves the first frontier and not the
second. An error-guided critic — a critic whose vocabulary of suspicions is distilled offline from the model's
own past errors on six unrelated benchmarks — raises the number of items whose trajectory ever contains the
correct answer from 154 (content-free placebo feedback) to 191 (paired p < 10⁻⁴), and makes correct answers
stickier than wrong ones (per-step stay ratio 1.5 vs 1.25). A zero-parameter majority-over-rounds rule
("mode") cashes part of this: 154/400 versus 136/400 for ten-sample self-consistency (McNemar p = 0.018) at 72 %
of its solver tokens — while the placebo's mode reaches 145, i.e. the critic's entire 37-item ceiling gain is
realized only to the extent of +9 (n.s.). We then ask whether any same-model evaluator can recover the
remainder and answer no, with three independent diagnostics: an oracle that undoes every harmful switch would
reach 173, but three differently framed judges (rubric scoring of the new answer, question-visible cited
falsification, and judging whether the critic's suspicion was warranted) are each 0.50 ± 0.03 accurate exactly
on the edges where they disagree with the vote count; Bayes-optimal weighting of their verdicts, fitted on half
the items and applied to the other half, never beats the count; and an exhaustive sweep over aggregation rules
fails to beat it even in-sample. The vote count is a sufficient statistic of the information a same-model judge
can extract. We conclude that error-guided critique is a generation-side intervention whose value is bounded by
the verifiability of the task, and that recovering the remaining ceiling requires an information-asymmetric
judge, not a better aggregator. **[TBD-1: one sentence on C2.]**

---

## 1. Introduction

**The gap self-consistency leaves.** Sampling N answers and taking the majority is the standard test-time
scaling baseline. Its failure mode is well documented: the correct answer frequently *appears* among the
samples and is then out-voted. Intrinsic self-correction — asking the model to reconsider without new
information — is unreliable (Huang et al., 2023); process reward models and trained verifiers supply an
external signal but need training data with positive labels.

**Two frontiers, not one.** We propose to read any test-time loop through two quantities that the final
accuracy conflates: the *reachable ceiling* (the fraction of items whose trajectory contains the correct answer
at least once; pass@trajectory) and the *realization rate* (how much of that ceiling the final selection rule
cashes). On tasks with a verifier — unit tests, numeric checkers, executable tool calls — the ceiling *is* the
deployable accuracy. On tasks without one, the realization rate is the bottleneck. Humanity's Last Exam (HLE)
is the hardest case: expert-level, mostly free-form, no verifier.

**Main question (falsifiable).** Can a model's own past errors, distilled offline into answer-free error
mechanisms, serve as the external signal for a gold-free, train-free loop on the *same* model that (i) raises
the reachable ceiling beyond what content-free iteration achieves and (ii) is realized better than
self-consistency, on harder problems the error bank has never seen? **Falsification boundary**: if the loop's
selected answer does not beat ten-sample self-consistency on the same 400 items (paired McNemar not
significant), the claim fails.

**What we find.** (i) holds strongly (ceiling 191 vs 154, p < 10⁻⁴); (ii) holds (154 vs 136, p = 0.018) and
the mechanism is persistence: the critic makes correct answers stickier, so a zero-parameter count over rounds
is a good selector. But the same selector on content-free feedback reaches 145, so the critic's ceiling gain is
largely unrealized (+9, n.s.). We therefore spend the second half of the paper on the selection frontier and
establish, with three independent diagnostics, that no same-model evaluator can beat the count: conditional on
the vote structure, same-model judgments carry no residual information about which answer is correct.

**Contributions.**
1. A generation–selection decomposition for test-time loops, with pass@trajectory as a first-class metric.
2. An error-guided critic (offline distillation of answer-free error mechanisms from six unrelated benchmarks)
   that raises the HLE-400 ceiling by 37 items over a content-free placebo and beats self-consistency on the
   realized answer at lower solver cost. **[TBD-1: attribution to bank vs structure, from C2.]**
3. A mechanism account — activation × persistence under a sequential stopping rule — that explains why a
   counter beats sampling and where its headroom lies.
4. A negative result with a proof structure rather than a list of failed attempts: conditional on the vote
   count, three differently framed same-model judges carry no residual information (edge-level conditional
   test, Bayes-weighted cross-half test, exhaustive aggregation sweep), bounding what a same-model evaluator
   can add on this benchmark.
5. A frozen, audited scorer protocol for free-form HLE answers (three tiers, K = 3 adjudication, truncation
   rule) and a full provenance of the error bank, released.

**Existence claim.** EGTE is an unoptimized instantiation; we show that the mechanism yields the stated
effects, not that any role is optimal.

## 2. Related work (compressed; citations to be filled **[TBD-2]**)

Self-consistency and best-of-N; intrinsic self-correction and its limits; self-refine / reflexion-style
feedback loops; process reward models and trained verifiers; LLM-as-judge reliability and self-preference;
test-time compute scaling and pass@k as a ceiling metric; error taxonomies and "learning from mistakes"
prompting. Our position: a feedback loop whose external signal is distilled from the model's own errors, with
the evaluator studied as an information problem rather than a design problem.

## 3. Method: Error-Guided Test-Time Elimination (EGTE)

### 3.1 Roles

Three strategy roles on one base model, framed by the solver (generates) and the scorer (grades; gold-visible;
frozen; never touches the loop).

| Role | When | Gold? | Produces |
|---|---|---|---|
| Distiller | offline, over the error bank | yes | answer-free `mechanism` + `check_procedure` per error class |
| Critic | in-loop, every round, never silent | no | 1–3 suspicions (archetype name, past-participle suspicion, concrete gold-free check), grounded in the solver's CoT tail |
| Evaluator | offline, on answer transitions | no | edge-level verdicts aggregated into a selection (§6) |
| Solver | generation | no | answer + hidden CoT |
| Scorer | grading | yes | per-round correctness |

### 3.2 The error bank and what the critic actually sees

33 wrong single-shot answers of deepseek-v4-flash on six benchmarks (GPQA-Diamond 9, MMLU-Pro 7, MATH-500 5,
BFCL 5, BBH 4, AIME 3; **no HLE item, answer or error enters any bank**) are distilled in three levels:
instance-level answer-free mechanism + check (L1, 33) → per-benchmark classes by shared wrong verb (L2, 24) →
a frozen cross-benchmark bank (L3, 24 entries, 7-archetype vocabulary; commit 63d0991, 2026-10-21). At test
time the critic prompt deduplicates the bank to **five** archetype entries (name + one instance-level definition
+ one check procedure): constraint-blind decimation, descriptor/label conflation, procedure truncation /
omission, retrieval-abort, format / precision non-conformance. The critic must pick from these, write a
suspicion specific to the current answer, and name a check; it never sees gold, never emits a probability, and
never names an answer. Full provenance, release list and the no-leakage audit: Appendix A
(`ERROR_BANK_PROVENANCE.md`).

### 3.3 Loop and arms

Round 0 of every arm is the bare solver's deterministic (T = 0) answer (A-seeding), so arms differ only in
what happens afterwards.

| Arm | Rounds ≥ 1 | Selection rules reported |
|---|---|---|
| A | none | init |
| A2 (placebo) | same loop, fixed content-free feedback ("No confident error direction was found for this answer.") | final, settle, **mode** |
| A3 (self-consistency) | 9 i.i.d. samples at T = 0.7 (N = 10 with round 0) | **vote** |
| C3 (EGTE) | error-guided critic feedback each round | final, settle, **mode**, evaluator |
| C2 (bank-free critic) **[TBD-3]** | same critic prompt with the five-entry vocabulary removed | same as C3 |

Loop constants (identical across arms): max 10 rounds; early stop after 3 identical commits; thinking budget
16 384 + content margin 8 192 = 24 576 max tokens per solver call; T = 0 except A3's samples; no self-reported
rationale. Selection rules: *final* = last commit; *settle* = first commit of the last run of ≥ 3 identical
commits; *mode* = most frequent committed answer over rounds, ties to the latest; *vote* = majority over the
samples. Answer identity for all rules is one frozen normalizer (shape-aware: option letter / integer / normalized
string, with CoT-tail recovery for length-truncated structured answers); a length-truncated round may vote but a
truncated winner is scored wrong (Appendix C).

## 4. Evaluation protocol

**Data.** HLE-400: 400 items stratified from HLE (84 multiple-choice, 316 open-form). **Scorer.** Three tiers,
frozen before any arm comparison: T1 exact match by answer shape; T2 LLM false-negative rescue
(deepseek-v4-pro); T3 independent judge (astra) at K = 1, with all T1/T3 disagreements re-judged at K = 3 and
every residual dispute (22) adjudicated per answer variant by a second agent and accepted item-by-item, with the
rule "same substance ⇒ same verdict in every arm and round". Per-round correctness from this scorer (sidecar
v2) is the only legal input to every downstream analysis. **Statistics.** Paired McNemar (exact) on the same
400 items; bootstrap intervals for ratios; dev = even item ids, test = odd item ids for anything fitted.
**Pre-registration.** The evaluator acceptance criteria (§6.2) and the C2 read-out rules (Appendix E) were
written before the corresponding data were seen; post-hoc analyses are labelled.

## 5. Results

### 5.1 Main table

| Arm · rule | Correct / 400 | Acc | Ceiling (pass@trajectory) | Solver tokens | Tokens / correct |
|---|---|---|---|---|---|
| A · init | 113 | .283 | 113 | 5.10 M | 45 k |
| A2 · final / settle / **mode** | 142 / 136 / **145** | .363 | **154** | 24.66 M | 170 k |
| A3 · **vote** (N = 10) | **136** | .340 | **190** | 51.32 M | 377 k |
| C3 · final / settle / **mode** | 140 / 117 / **154** | .385 | **191** | 37.05 M | 241 k |
| C3 · evaluator (same-model, best of three judges) | = mode (§6) | — | — | **[TBD-4]** | — |
| C2 · **[TBD-3]** | | | | | |

Ceiling (pass@trajectory) = items for which some candidate, among the rounds the selection rule votes over (A3: its nine samples; A2/C3: all rounds), has its last occurrence scored correct — i.e. the best any selector could do under the frozen scorer. Definition identical for all arms; A3 counted over all ten rounds would read 195. Tokens are
solver-side only; critic and evaluator tokens **[TBD-4]**.

**Paired comparisons (McNemar exact).** C3.mode vs A3.vote: 35 / 17, **p = 0.018**. C3.mode vs A2.mode:
25 / 16, p = 0.21. Every loop or vote arm beats the bare solver (all p ≤ 0.0014). Ceiling: C3 vs A2 47 / 8,
**p < 10⁻⁴**; C3 vs A3 20 / 25, p = 0.55.

**Reading.** The error-guided loop beats ten-sample self-consistency on the realized answer at 72 % of its
solver tokens, and matches its ceiling with 5.7 commits per item instead of 7.9. Against the placebo it raises
the ceiling by 37 items but the realized answer by only 9 — and **C3's realized accuracy (154) equals A2's
ceiling (154)**: a perfect selector on the placebo could at best tie a counter on the critic. The gap between
C3's ceiling and its realization (37 items) is the subject of §6.

### 5.2 Answer form

| rule | MCQ (n = 84) | open-form (n = 316) |
|---|---|---|
| init | 31 | 82 |
| A2.mode | 36 | 109 |
| A3.vote | 35 | 101 |
| C3.mode | **40** | **114** |

The gain over self-consistency is larger on open-form items (+13) than on MCQ (+5): it is not an artefact of
voting over a small option set (H2-iii).

### 5.3 Stability condition

Per-round rates from the frozen sidecar: C3 ECR 0.113, EIR 0.298 (A2: 0.058, 0.097). With Acc₀ = 0.283 the
two-state stability threshold ECR/EIR > Acc₀/(1 − Acc₀) = 0.39 is met by A2 (0.60) and sits at the boundary
for C3 (0.38): the critic triples both the repair rate and the damage rate. That symmetry is the mechanism
(§5.4) and the evaluator's problem (§6) in one number.

### 5.4 Mechanism: activation × persistence under a sequential stopping rule

*(full analysis: `PERSISTENCE_MECHANISM.md`; all numbers frozen)*

**Activation.** The critic is what puts the correct answer into the trajectory: 191 items vs 154 for the
placebo (paired 47 / 8, p < 10⁻⁴), with 3.2 distinct candidates per item vs 1.9. Sampling reaches the same
ceiling (190) with 4.1 candidates.

**Persistence.** The statistic the selector exploits is the per-step probability that the next commit repeats
the current one, split by whether the current one is correct:

| | P(stay · correct) | P(stay · wrong) | ratio |
|---|---|---|---|
| A3 (i.i.d.) | 0.54 | 0.34 | 1.6 |
| C3 | 0.55 | 0.36 | 1.5 |
| A2 | 0.79 | 0.63 | 1.25 |

Correct answers are stickier than wrong ones in every arm, but the placebo makes *everything* sticky (it
rarely moves at all), so its count carries less information per commit. Under the early-stop rule the asymmetry
compounds: a correct answer reaches a run of three 2.3× as often as a wrong one in C3, and when the correct
answer appears exactly three times C3 locks it 107/110 times, where A3 locks a once-sampled correct answer only
18/53 times. Retention of the correct answer from first appearance to selection: 0.94 (A2) / 0.80 (C3) /
0.69 (A3).

**Consequence.** The selector's information is exactly the asymmetry of persistence. Any downstream
correction to the count is informative only where the count is; where frequencies tie, counts are noise, and
so is any weighted version of them (§6).

## 6. The selection frontier: can a same-model evaluator beat the count?

*(data: `EVALUATOR_RESULTS.md`; auto-generated tables: `_judge_audit_autogen.md`)*

### 6.1 How much is there to recover, and is it symmetric?

Of C3's 191 reachable items, mode selects 154. The 37 recoverable items are: 8 ties (mostly 11-round
free-form trajectories with 11 distinct answers), 27 where the correct answer was held and then abandoned, and
2 late convergences. An oracle that undoes every correct→wrong switch reaches **173**; one that undoes only the
switches the solver explicitly attributes to the critic's feedback reaches **165**. But the same switches are
not one-sided: of 301 decisive switches (freeze-key), 159 repair and 142 break, and undoing *all*
feedback-attributed switches blindly gives 149 (+6 / −11). Recovering the headroom therefore requires telling a
warranted suspicion from an unwarranted one.

### 6.2 Three judges, one aggregator, pre-registered acceptance

Every evaluator is a source of **edge-level verdicts** on answer switches, fed to one aggregator:
s(c) = log count(c) + Σ ± log LR(v), with LR(v) = P(v · repair edge) / P(v · break edge) estimated on dev
(even items) and frozen for test (odd items); all LR = 1 recovers mode. Three judges, same model, no gold:

- **Judge-R** (rubric): scores the new answer on disconnection / contradiction / error (0–10); max ≥ 8 → CUT,
  all zero → KEEP, else UNSURE.
- **Judge-R+** (question-visible, cited): the judge sees the question, must quote the offending step
  (line id + fragment) and name a falsifier class; CUT / NO_CUT.
- **Judge-C** (recovery): sees the question, the critic's suspicion and check, and the *criticized* answer's
  reasoning only; judges whether the suspicion was WARRANTED or OVER-stated. N = 2 with order swap; a quote
  that is not verbatim in the criticized reasoning voids the verdict.

Acceptance (written before the runs): E1 edge accuracy on decisive edges; E2 LR confidence intervals;
E3 dev-fitted aggregation applied to test vs mode; E4 sign stability of LR across halves.

### 6.3 Results

| Judge | E1 edge acc. (all) | LR CIs contain 1 | E3 dev→test (mode 76) | E4 test→dev (mode 78) | Acc. when disagreeing with the count | Aggregation sweep, in-sample max |
|---|---|---|---|---|---|---|
| Judge-R | 56/97 = 0.577 | yes | 76 (+2 −2) | 73 (+5 −10) | 18/36 = **0.500** | 154 (no config ≥ 155) |
| Judge-R+ | 72/126 = 0.571 | yes | 77 (+3 −2) | 76 (+4 −6) | 38/80 = **0.475** | 156 (31/81 configs ≥ 155; 0 across halves) |
| Judge-C | 120/181 = 0.663 | **no** (OVER 0.51 [0.32, 0.80]; WARRANTED 1.87 [1.24, 2.81]) | 71 (+3 −8, p = 0.23) | 77 (+8 −9) | 32/66 = **0.485** | 155 (6/81; 0 across halves) |

Three readings, in increasing strength:

1. **Marginal signal exists for one judge.** Judging whether the critic's suspicion was warranted (Judge-C)
   is easier than judging the answer: 66 % on decisive edges, with likelihood ratios whose intervals exclude 1.
   Judging the answer, with or without the question, is at 57–58 %.
2. **No judge converts it at the task level.** Bayes-weighted aggregation fitted on one half and applied to
   the other is at or below mode for all three (E3 column), and the sign of the fitted LRs is unstable for
   Judge-R. The pre-registered result for Judge-C on test is −5 (p = 0.23).
3. **The reason is that the signal is the count, restated.** A rule that uses only vote counts ("the switch is
   a repair iff the new answer ends with at least as many votes as the old") is 0.58 / 0.60 / 0.67 accurate on
   the same edges as Judge-R / R+ / C — never below the judge. Where a judge *disagrees* with this rule — the
   only place a judge can change the selection — its accuracy is 0.500, 0.475 and 0.485. Conditional on the
   vote structure, same-model verdicts carry no information about correctness.

Two consistency checks close the argument. A candidate-level logistic model over count features plus all
verdict features, fitted *and evaluated* on all 400 items (an optimistic bound), reaches 150 < 154. An exhaustive
sweep over aggregation rules — where the verdict acts (boundary node / whole run / whole candidate), separate
weights for the two verdict directions, and gating to low-margin items — reaches at most 155–156 in-sample out of
81 configurations and 0 gain when the best configuration on one half is applied to the other. Why 66 % is still
not enough has a one-line explanation: overturning mode is a repair only on 37 of the 123 multi-answer items
where mode could be overturned (prior 0.30); a judge with edge accuracy p flips with precision
0.30p / (0.30p + 0.70(1 − p)), which is 45 % at p = 0.66 and crosses 50 % only at p > 0.70.

### 6.4 Statement

*Conditional on the vote structure, none of the three same-model, gold-free judges carried information
beyond the count* (disagreement accuracy 0.500 / 0.475 / 0.485; Bayes-weighted cross-half gain ≤ 0; in-sample
sweep ≤ +2). We state this as an empirical finding on one model, one benchmark and three judge framings, not
as a theorem: a judge that beats the count on these edges would falsify it. The 37-item headroom exists
(oracle 173) and is even partially visible at the edge level (Judge-C), but recovering it needs a judge whose
information is not a function of the trajectory the solver already produced — a stronger model, external
verification, or, on the prevention side, a critic that abstains. **[TBD-5: one line on Judge-R+ full
coverage.]**

## 7. Hypotheses revisited

- **H1 — the content effect is identifiable.** The critic's content, not the loop, raises the ceiling:
  C3 vs A2 +37 (p < 10⁻⁴) with a sharper stay asymmetry (1.5 vs 1.25). Whether the *distilled* content matters
  beyond structured critique is tested by C2 **[TBD-3]**. (The original H1 — archetype hit-rate of the critic's
  suspicions against a gold-visible labeller — is dropped: §6 shows the critic's archetype labels carry no
  conditional information, so a hit-rate would not bear on the claims.)
- **H2 — mechanism-sensitive.** (i) C3 ≠ A2 on ceiling and persistence; (ii) by construction every C3
  repair follows a suspicion and no A2 repair does; (iii) the gain over A3 is larger on open-form than on MCQ.
  Supported on (i) and (iii); the *realized* difference to A2 (+9) is not significant, and §6 explains why it
  cannot be made so by a same-model selector.
- **H3 — decision value.** C3.mode beats A3.vote on the same items (p = 0.018) at 72 % of its solver tokens
  **[TBD-4: + critic tokens]**. Supported.
- **Falsification boundary**: not crossed.

## 8. Limitations, scope and future work

- **Existence, not optimality.** One base model, one bank, one benchmark; no role was tuned on HLE.
- **Realization is the bottleneck on unverifiable tasks.** The critic's main effect is on the ceiling. Where a
  verifier exists the effect is deployable as pass@trajectory 191 vs 154; on HLE it is realized as +9 (n.s.).
  We report the ceiling as a first-class metric and recommend the field does too.
- **Same-model judging has an information bound** (§6.4). Three framings, two aggregation families and an
  exhaustive sweep all reduce to the count. We did not test a stronger judge, because it would also lift the
  self-consistency baseline and break the single-model claim; an abstaining critic (prevention) is the
  cheaper direction and is left to future work with the pre-registered design in Appendix E.
- **Power.** 400 items resolve a 17-item paired difference (C3 vs A3) but not a 9-item one (C3 vs A2).
- **Scorer.** Free-form HLE grading required an LLM judge tier with K = 3 adjudication; all 22 adjudications
  and their rationales are released (Appendix D).
- **Bank footprint.** At test time the critic sees five archetype entries; the bank's generalization claim is
  about those five, instance-level definitions included.

## 9. Conclusion

An error-guided critic turns a feedback loop into a better *generator* — it reaches the correct answer on 37
more items than content-free iteration and makes correct answers more persistent — and a zero-parameter count
over rounds turns that persistence into a selected answer that beats self-consistency at lower cost. It does
not turn the same model into a better *selector*: conditional on the vote count, nothing the model can say
about its own transitions carries information about which of them was right. The decomposition into a
reachable ceiling and a realization rate makes both halves of the result precise and tells practitioners
where the value of such loops lies: wherever the task can be verified.

---

## Appendices (pointers)

- **A. Error bank**: source instances, three distillation levels, the five test-time entries, no-leakage audit,
  release list — `ERROR_BANK_PROVENANCE.md`.
- **B. Frozen runtime**: budgets, loop constants, arm definitions, prompts (solver / critic / three judges).
- **C. Scorer**: three tiers, truncation rule, answer identity and the two-stage truncated-vote rule, K = 3
  adjudication table — `HLE_SCORER.md` §1.2, `HLE400_T3_SECOND_AUDIT.md`.
- **D. Evaluator**: full per-judge tables (dev / test / all), three-role naive-Bayes robustness, aggregation
  sweep, 26-feature trajectory contrast (AUC 0.43–0.59, none stable), premise probe (75/81 not about the
  question), revision log (verifier v2; aggregator specification) — `EVALUATOR_RESULTS.md`,
  `_judge_audit_autogen.md`, `switch_contrast.py`.
- **E. Pre-registered C2 design and read-out rules** — `C2_BANK_FREE_CRITIC_SPEC.md`.
- **F. Mechanism figures** — `PERSISTENCE_MECHANISM.md` §5.2.5.

---

## §R. Remaining tasks (this draft → submission)

| id | task | blocks | owner |
|---|---|---|---|
| TBD-1 | Choose title variant; write the one C2 sentence in abstract/contribution 2 | C2 read-out | PI after agent |
| TBD-2 | Related-work citations (self-consistency, intrinsic self-correction, PRMs, LLM-as-judge, pass@k, error-taxonomy prompting) | — | agent |
| TBD-3 | **C2 bank-free critic**: run, score (full T1/T2/T3 + K = 3), fill main-table row, H1 sentence, §5.4 paired C3 vs C2 | — | agent (spec frozen) |
| TBD-4 | Critic tokens for C3 (2 288 calls; recover from API logs or estimate and mark ≈) + evaluator tokens (three judges, `pt/ct/rt`) → main-table tokens/correct | — | agent |
| TBD-5 | Judge-R+ full coverage (remaining 123 multi-answer items, ≈ 700 calls) → regenerate `_judge_audit_autogen.md`; else footnote "130-item subset" | — | agent |
| TBD-6 | Figures: (F1) two-frontier plot ceiling vs realized per arm; (F2) stay-asymmetry bars; (F3) count-bucket lock rates; (F4) judge disagree-accuracy bars | — | agent |
| TBD-7 | Frozen-doc sync: `HLE400_FROZEN_DATA.md` (evaluator row → §6; ceiling row), `HLE_SCORER.md` truncated-vote note, `EVALUATOR_FINAL_DESIGN.md` §4/§6, `EVALUATOR_FINAL_QCUT.md` header, `ERROR_BANK_PROVENANCE.md` five-entry note | — | agent |
| TBD-8 | Deprecate intermediate evaluator docs (CEL/MPC/COV/QV-MPC/MOVE_PAIRWISE/CHECK_OUTCOME/lock_rule_study/sweeps) → `docs/_deprecated/` | — | agent |
| TBD-9 | Outline + PPT re-synced to this draft's section order; evaluator page becomes a "boundary" page | TBD-1 | agent |
| TBD-11 | Human spot-check of the LLM scorer: 100 items (stratified MCQ/open, incl. all 22 adjudicated), two annotators blind to the T3 verdict, report agreement and κ vs sidecar v2 | — | PI + one annotator |
| TBD-12 | Abstract to ≤ 250 words (compress the three diagnostics into one sentence) | TBD-1 | agent |
| TBD-10 | Journal-format pass (venue template, word limits, reference style); final number audit by a second agent reading only §0 files | all above | agent → PI |
