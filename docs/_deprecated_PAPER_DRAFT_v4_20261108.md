# Paper draft v4 (2026-11-08) — revised after C2

> **Status.** Second full draft; C2 (bank-free critic) read out under the pre-registered rules → "bank not
> identifiable". Title and contributions rewritten accordingly. All numbers freeze-key + sidecar v2. C2 numbers
> are given **after** the hle_201 adjudication (7 rounds exactly equal to gold; see §4) — the regenerated frozen
> files are pending **[TBD-3b]**; until then the frozen files read C2.mode 158 / ceiling 197.
> Sources: `HLE400_FROZEN_DATA.md`, `PERSISTENCE_MECHANISM.md`, `EVALUATOR_RESULTS.md`, `ERROR_BANK_PROVENANCE.md`,
> `C2_BANK_FREE_CRITIC_SPEC.md`. Remaining tasks: §R. Previous drafts: `_deprecated_PAPER_DRAFT_v3_20261107.md`.

---

## Title

**Self-Critique Is a Sampler, Not a Corrector: Critique-Driven Resampling Beats Self-Consistency, and the Vote
Count Is the Limit of Same-Model Selection**

Alternative (shorter): *Two Frontiers of Test-Time Loops: Structured Self-Critique Raises the Reachable Ceiling;
the Vote Count Is the Limit of Same-Model Selection.*

## Abstract (≤ 250 words; current ≈ 240)

Test-time loops that let a model revise its answer under feedback are usually judged by the accuracy of the last
answer, and by that measure intrinsic self-correction is known to be unreliable. We argue that the last answer is
the wrong object. On 400 Humanity's Last Exam items, with one model (deepseek-v4-flash) acting as solver and
critic, a loop whose critic must name a specific suspicion and a concrete check every round raises the number of
items whose trajectory ever contains the correct answer from 154 (content-free "reconsider" feedback) to 191–198
(paired p < 10⁻⁸), and makes correct answers stickier than wrong ones across rounds. A zero-parameter majority
over rounds turns this into a selected answer that beats ten-sample self-consistency — 154–159/400 vs 136/400,
McNemar p ≤ 0.018 — at 72 % of its solver tokens, while the loop's own last answer (140–148) does not. Whether the
critic's suspicions come from a vocabulary distilled offline from the model's past errors or from the model's
free judgement makes no measurable difference (159 vs 154, p = 0.67): the distilled vocabulary is not
identifiable as the active ingredient. We then ask whether any same-model judge can recover the 37–39 items that are reached but not
selected, and answer no: three differently framed judges are 0.50 accurate exactly where they disagree with the
vote count, Bayes-weighted aggregation fitted on half the items never beats the count on the other half, and an
exhaustive sweep of aggregation rules fails even in-sample — on this model and benchmark, the count is where
same-model selection ends. The count is also a usable confidence for abstention, which the
placebo's count is not. We reconcile these
results with the self-correction literature through a two-state stability condition, and show by simulation on
the frozen trajectories how the ceiling gain converts to accuracy as external verification improves.

---

## 1. Introduction

**Two readings of a revision loop.** A model that answers, receives a critique, and answers again can be read
as a *corrector* — judged by whether its last answer is better — or as a *sampler* — judged by the distribution
of answers it visits. The corrector reading has been tested and found wanting: without external information,
intrinsic self-correction does not improve reasoning accuracy and often degrades it (Huang et al., 2023). This
paper is about the sampler reading.

**Two frontiers.** Any test-time method's accuracy factorizes into how often the correct answer is *reached*
(the reachable ceiling, pass@trajectory) and how often it is then *selected* (the realization rate). Sampling
with majority vote reaches a high ceiling and selects poorly; the correct answer is often in the pool and
out-voted. We show that structured self-critique reaches an equally high ceiling with fewer, more structured
samples, so that a trivial selector realizes more of it — and then we establish where the selection frontier for
a single model actually lies.

**Main question (falsifiable).** Can a gold-free, train-free revision loop on one model (i) reach the correct
answer more often than content-free iteration, (ii) be realized better than self-consistency on the same items at
no higher cost, and (iii) be improved further by a same-model evaluator of its own transitions? Falsification:
(ii) fails if the loop's selected answer does not beat ten-sample self-consistency (paired McNemar).

**Findings.** (i) Yes, strongly: ceiling 191 (error-bank critic) and 198 (bank-free critic) versus 154 for the
placebo. (ii) Yes: 154 and 159 versus 136, p = 0.018 and 0.0013, at lower solver cost. (iii) No, and not for lack
of trying: conditional on the vote count, same-model judgments of the loop's transitions carry no information
about which transition was right; the count is the limit. A secondary, pre-registered result: the distilled
error-bank vocabulary is not identifiable as the active ingredient of the critique (C2 vs C3, p = 0.67); what
both critic arms share — a per-round obligation to name a specific suspicion and a concrete check — is, but we
cannot separate "specific content" from "forced output every round" without a critic allowed to abstain (§8).

**Contributions.**
1. A generation–selection decomposition for revision loops, with pass@trajectory as a first-class metric and a
   two-state stability condition that reconciles our positive result with the negative self-correction literature.
2. Evidence that structured self-critique is a better sampler than temperature sampling: equal ceiling, more
   persistent correct answers, a zero-parameter selector that beats self-consistency at lower solver cost; and a
   pre-registered null showing the distilled error-bank vocabulary is not the active ingredient.
3. A mechanism account — activation × persistence under a sequential stopping rule — with the vote count
   doubling as a calibrated confidence (selective prediction).
4. A bounded negative result on same-model evaluation: three judge framings, Bayes-weighted aggregation and an
   exhaustive rule sweep all reduce to the count; the headroom (oracle 173) requires information the trajectory
   does not contain.
5. A frozen, audited scorer for free-form HLE answers (three tiers, K = 3 adjudication, truncation rule), the
   error bank with full provenance, and all judge verdicts, released.

## 2. Related work **[TBD-2 citations]**

Self-consistency / best-of-N and pass@k as a ceiling; intrinsic self-correction and its limits (Huang et al.
2023; the Reflexion / Self-Refine debate) — we take the negative result as given for the *last answer* and show
the loop is informative as a *distribution*; process reward models and trained verifiers (external information we
deliberately exclude); LLM-as-judge reliability and self-preference, which §6 quantifies as a conditional
information bound rather than a bias; error taxonomies and "learning from mistakes" prompting, whose content
contribution we find unidentifiable against structured critique.

## 3. Method

### 3.1 Roles and arms

One base model plays solver and critic; a frozen, gold-visible scorer grades every round and never touches the
loop. Round 0 of every arm is the bare solver's T = 0 answer (A-seeding), so arms differ only afterwards.

| Arm | Rounds ≥ 1 | Rules reported |
|---|---|---|
| A | none | init |
| A2 (placebo) | same loop; fixed content-free feedback "No confident error direction was found for this answer." | final, settle, mode |
| A3 (self-consistency) | 9 i.i.d. samples at T = 0.7 (N = 10 with round 0) | vote |
| C3 (error-bank critic) | critic picks 1–3 suspicions from a five-entry vocabulary distilled from the model's own past errors, writes an answer-specific suspicion and a concrete gold-free check, grounded in the solver's CoT tail; never silent | final, settle, mode |
| C2 (bank-free critic) | identical prompt and rules with the vocabulary removed; the critic names the shortcoming in its own words | final, settle, mode |

Loop constants (identical across arms): max 10 rounds; early stop after 3 identical commits; thinking budget
16 384 + margin 8 192 = 24 576 tokens per solver call; T = 0 except A3's samples; no self-reported rationale.
Selection rules: *final* = last commit; *settle* = first commit of the last run of ≥ 3 identical commits;
*mode* = most frequent committed answer over rounds, ties → the answer whose last occurrence is latest; *vote* =
majority over samples, ties → first encountered (neutral for i.i.d. samples). Answer identity is one frozen,
shape-aware normalizer; a length-truncated round may vote but a truncated winner is scored wrong (Appendix C).

### 3.2 The critic's content: error bank vs free critique

C3's vocabulary comes from 33 wrong single-shot answers of the same model on six unrelated benchmarks
(GPQA-Diamond 9, MMLU-Pro 7, MATH-500 5, BFCL 5, BBH 4, AIME 3; no HLE item, answer or error enters any bank),
distilled to 24 answer-free mechanism + check entries and deduplicated at test time to five archetype entries
(constraint-blind decimation, descriptor/label conflation, procedure truncation / omission, retrieval-abort,
format / precision non-conformance). C2 removes exactly this block and nothing else (four textual differences,
Appendix B; critic fallback never touches the bank). The pre-registered read-out rule (Appendix E) was: bank
"effective" if C2's ceiling is ≥ 15 items below C3's at p < 0.05 or its persistence asymmetry is lower;
"not identifiable" if C2's ceiling is within 5 of C3's with overlapping asymmetry.

## 4. Evaluation protocol

HLE-400 (84 MCQ, 316 open-form). Scorer: T1 exact match by shape → T2 LLM false-negative rescue
(deepseek-v4-pro) → T3 independent judge (astra) at K = 1, all disagreements at K = 3, residual disputes
adjudicated per answer variant with the rule "same substance ⇒ same verdict in every arm and round" (22 for
A/A2/A3/C3; for C2, 21 ambiguous verdicts of which 11 fell under existing rules, 7 — all seven forms of hle_201 —
were verified exactly equal to the gold rational multiple of π and scored correct, and 4 — hle_393 ×3, hle_379 —
confirmed wrong). Per-round correctness from this scorer is the only input to every analysis. Statistics: paired
McNemar on the same 400 items; bootstrap intervals for ratios; dev = even ids / test = odd ids for anything
fitted; pre-registered criteria for §6 and for C2.

## 5. Results

### 5.1 Main table

*Ceiling (pass@trajectory)*: items for which some candidate, among the rounds the selection rule votes over (A3:
its nine samples; loop arms: all rounds), has its last occurrence scored correct — the best any selector could do
under the frozen scorer (A3 over all ten rounds would read 195).

| Arm · rule | Correct / 400 | Acc | Ceiling (pass@trajectory) | Solver tokens | Critic tokens | Tokens / correct |
|---|---|---|---|---|---|---|
| A · init | 113 | .283 | 113 | 5.10 M | 0 | 45 k |
| A2 · final / settle / **mode** | 142 / 136 / **145** | .363 | 154 | 24.66 M | 0 | 170 k |
| A3 · **vote** (N = 10) | **136** | .340 | 190 | 51.32 M | 0 | 377 k |
| C3 · final / settle / **mode** | 140 / 117 / **154** | .385 | 191 | 37.05 M | **[TBD-4]** | 241 k + critic |
| C2 · final / settle / **mode** | 148 / 121 / **159** | .398 | **198** | **[TBD-4]** | **[TBD-4]** | — |

Selectors (mode, vote) cost no tokens; judge tokens (§6) are diagnostic, not part of any arm.

**Paired comparisons (McNemar exact).** Selected answer: C3.mode vs A3.vote 35/17, **p = 0.018**; C2.mode vs
A3.vote 33/11, **p = 0.0013**; C2.mode vs C3.mode 27/23, p = 0.67; C3.mode vs A2.mode 25/16, p = 0.21; C2.mode
vs A2.mode 32/19, p = 0.09; all arms vs A.init p ≤ 0.0014. Ceiling: C3 vs A2 47/8, **p < 10⁻⁴**; C2 vs A2 50/7,
**p < 10⁻⁸**; C2 vs C3 22/16, p = 0.42; C3 vs A3 20/25, p = 0.55.

**Reading.** Both critic arms beat self-consistency on the selected answer, and both raise
the ceiling far above the placebo. They do not differ from each other: removing the error-bank vocabulary
changes nothing measurable (if anything C2 is higher). A perfect selector on the placebo could reach at most its
ceiling, 154 — no more than a counter reaches on a critic arm (the exact equality with C3.mode is coincidental).
The cost claim is stated for solver tokens only until critic tokens are in (**[TBD-4]**). The last answer is worse than the count in every loop
arm (A2 142 < 145, C3 140 < 154, C2 148 < 159).

### 5.2 Answer form

| rule | MCQ (84) | open (316) |
|---|---|---|
| init | 31 | 82 |
| A2.mode | 36 | 109 |
| A3.vote | 35 | 101 |
| C3.mode | 40 | 114 |
| C2.mode | **[TBD-3b]** | **[TBD-3b]** |

C3's gain over self-consistency is larger on open-form (+13) than on MCQ (+5): not a voting-over-few-options
artefact.

### 5.3 Why this does not contradict the self-correction literature

With per-round repair rate ECR = P(wrong → correct) and damage rate EIR = P(correct → wrong), a revision loop
improves its last answer only while ECR/EIR > Acc₀/(1 − Acc₀). On benchmarks where the model already scores
80 %+, the threshold is 4 and any critique with symmetric effects degrades accuracy — the regime studied by Huang
et al. On HLE, Acc₀ = 0.283 and the threshold is 0.39; the placebo sits at 0.60 and the critic arms at ≈ 0.38
(C3: ECR 0.113, EIR 0.298 — it triples both rates relative to the placebo). So the last answer barely improves
(final 140–148), exactly as the corrector reading predicts — and the sampler reading explains why the count
nevertheless gains 41–46 items over init: the critic's symmetric perturbation is informative in aggregate even
when each individual revision is a coin flip.

### 5.4 Mechanism: activation × persistence under a sequential stopping rule

*(full analysis `PERSISTENCE_MECHANISM.md`; C2 rows **[TBD-3b]** to be computed with the same script)*

**Activation.** The critic is what puts the correct answer into the trajectory: 191 (C3) and 198 (C2) items vs
154 for the placebo, with 3.5–3.7 distinct candidates per item vs 2.1. Sampling reaches 190 with 4.1 candidates.

**Persistence.** The statistic the selector exploits is the per-step probability that the next commit repeats
the current one, split by whether the current one is correct:

| | P(stay · correct) | P(stay · wrong) | ratio |
|---|---|---|---|
| A3 (i.i.d.) | 0.54 | 0.34 | 1.6 |
| C3 | 0.55 | 0.36 | 1.5 |
| C2 | **[TBD-3b]** (provisional, adjacent-round method: 0.56 / 0.26, ratio 2.2) | | |
| A2 | 0.79 | 0.63 | 1.25 |

The placebo makes everything sticky, so its count carries little information per commit; the critic arms move
often but move away from wrong answers more than from correct ones. Under the early-stop rule this compounds: a
correct answer reaches a run of three 2.3× as often as a wrong one (C3), and when the correct answer appears
exactly three times C3 locks it 107/110 times where A3 locks a once-sampled correct answer 18/53 times.
Retention from first appearance to selection: 0.94 (A2) / 0.80 (C3) / 0.69 (A3).

**Consequence.** The selector's information is the persistence asymmetry; any correction to the count is
informative only where the count is (§6).

### 5.5 The count as a confidence: selective prediction *(provisional; re-run with frozen vote function **[TBD-13]**)*

Ranking items by vote margin (top-1 minus top-2) and answering only the top fraction:

| coverage | A2 | A3 | C3 |
|---|---|---|---|
| 1.00 | .362 | .352 | .385 |
| 0.80 | .391 | .394 | **.425** |
| 0.50 | .425 | .445 | **.485** |
| 0.33 | .386 | .470 | **.515** |

The placebo's margin is nearly uninformative (its accuracy *falls* at low coverage: every answer became a
three-run); the critic arm's margin is a usable confidence. Adding any judge's verdicts to the confidence does not
improve it out of sample (AUROC 0.60 → 0.60; Appendix D).

### 5.6 How the ceiling converts under external verification *(simulation on frozen trajectories **[TBD-14]**)*

A verifier with per-candidate accuracy q, applied independently to every candidate, selecting by count among the
accepted and falling back to mode:

| q | A2 | A3 | C3 | C3 − A2 | C3 − A3 |
|---|---|---|---|---|---|
| 0.5 | 135 | 126 | 138 | +3 | +12 |
| 0.7 | 144 | 151 | 161 | +17 | +10 |
| 0.9 | 151 | 177 | 181 | +30 | +4 |
| 1.0 | 154 | 190 | 191 | +37 | +1 |

Two regimes: against the placebo, the critic's advantage grows with verification (+3 → +37); against
self-consistency it shrinks (+12 → +1) — the critic's value over sampling lies precisely where verification is
weak, which is where persistence is the only selector available. C3 + verifier exceeds C3.mode from q ≈ 0.63.
(Independence of verifier errors is assumed; a correlated-error variant — verifier accuracy decreasing with the
number of candidates and with item difficulty — is **[TBD-14]**; it lowers all curves but, we expect, not the two
regimes. This crossover is promoted to the Discussion as the paper's practical guidance: critique when
verification is weak, sample when it is strong.)

## 6. The selection frontier: can a same-model evaluator beat the count?

*(unchanged from v3 except numbering; data `EVALUATOR_RESULTS.md`, `_judge_audit_autogen.md`)*

### 6.1 Headroom and its symmetry
Of C3's 191 reachable items mode selects 154; the 37 recoverable are 8 ties, 27 abandoned correct answers, 2 late
convergences. Oracle undo of every correct→wrong switch: 173; of feedback-attributed ones: 165; blind undo of
feedback-attributed switches: 149 (+6/−11). Of 301 decisive switches, 159 repair and 142 break.

### 6.2 Three judge framings, one aggregator, pre-registered acceptance
Edge-level verdicts → s(c) = log count(c) + Σ ± log LR(v), LR fitted on dev, frozen on test; all LR = 1 is mode.
Judge-R (rubric on the new answer), Judge-R+ (question-visible, cited, falsifier class), Judge-C (is the critic's
suspicion warranted; sees only the criticized answer). Criteria E1–E4 written before the runs.

### 6.3 Results

| Judge (coverage: multi-answer items judged / 253) | E1 edge acc. | LR CIs ∋ 1 | E3 dev→test (mode 76) | E4 test→dev (mode 78) | acc. when disagreeing with count | rule sweep, in-sample max |
|---|---|---|---|---|---|---|
| Judge-R (253) | 0.577 | yes | 76 (+2 −2) | 73 (+5 −10) | 18/36 = **0.500** | 154 |
| Judge-R+ (178; **[TBD-5]**) | 0.571 | yes | 77 (+3 −2) | 76 (+4 −6) | 38/80 = **0.475** | 156 (0 across halves) |
| Judge-C (253) | 0.663 | **no** | 71 (+3 −8, p = .23) | 77 (+8 −9) | 32/66 = **0.485** | 155 (0 across halves) |

Counts alone predict repair vs break at 0.58 / 0.60 / 0.67 on the same edges — never below the judge. In-sample
logistic over count + verdict features: 150 < 154. Why 66 % edge accuracy is not enough: overturning mode is a
repair on only 37 of 123 overturnable items (prior 0.30); a judge with edge accuracy p flips with precision
0.30p/(0.30p + 0.70(1 − p)) = 45 % at p = 0.66, crossing 50 % only above 0.70. On tie items (56), where the count is
silent, Judge-C does carry conditional information (17/26 when disagreeing) but it is worth +1 item; the
tie-break "latest" alone recovers 14 of 23 reachable ties.

### 6.4 Statement
Conditional on the vote structure, none of the three same-model judges carried information beyond the count
(0.500 / 0.475 / 0.485; cross-half gain ≤ 0; in-sample sweep ≤ +2). The three framings are not independent
evidence — same model, and each correlates with the count, which is the finding — so this is an empirical bound
on one model, one benchmark, three framings, falsified by any judge that beats the count on these edges. The headroom exists
(oracle 173) and is partly visible at the edge level (Judge-C), but recovering it needs information that is not a
function of the trajectory: a stronger model, external verification, or, on the prevention side, a critic that
abstains. **[TBD-5 footnote on Judge-R+ coverage.]**

## 7. Hypotheses revisited

- **H1 — identifiability of critique content.** Pre-registered as structure vs content (C3 vs C2 vs A2):
  the shared critique structure is identifiable (both critic arms vs placebo, p < 10⁻⁴ on ceiling); the bank's
  distilled vocabulary is **not** the active ingredient (C2 ≥ C3 on every endpoint, all n.s.). "Structure" here
  is a residual that also contains "forced output every round"; separating the two needs an abstaining critic. The original H1 (archetype hit-rate of the critic's labels) is
  dropped as uninformative given §6.
- **H2 — mechanism-sensitive.** Supported on ceiling and persistence (i), by construction (ii), and on the
  open-form split (iii); the realized difference to the placebo is +9/+14 (p = 0.21 / 0.09) and §6 explains why a
  same-model selector cannot enlarge it.
- **H3 — decision value.** Both critic arms beat A3.vote on the same items (p = 0.018 / 0.0013) at 72 % of its
  solver tokens **[TBD-4 total cost]**. Supported.
- **Falsification boundary:** not crossed.

## 8. Limitations and future work

- Existence, not optimality: one model, one benchmark, no tuning on HLE.
- The last answer of a revision loop remains unreliable (Huang et al.); our gains are in the aggregate. Any
  deployment must read the trajectory, not the final message.
- Realization is the bottleneck on unverifiable tasks (§5.6 quantifies the conversion as verification improves).
- Same-model judging has an information bound (§6.4); the one place with residual conditional signal (tie items,
  Judge-C) is a pre-registered hypothesis for future data, not a result.
- Power: 400 items resolve a 17–22 item paired difference, not a 9–14 item one.
- Scorer: free-form HLE grading required an LLM tier with K = 3 adjudication; all adjudications are released;
  a 100-item human double-annotation **[TBD-11]** reports agreement with the automated verdicts.
- Endpoint: C2 ran on the pay-as-you-go alias of the same weights after the subscription quota was exhausted
  (same model id, thinking on, same budgets); the comparison C2 vs C3 is therefore between identical weights on
  two billing routes **[TBD-15 alignment check: per-round reasoning length, truncation and commit rates]**.
- Prevention vs repair: an abstaining critic acts on the generation side, where the headroom lives, but its gate
  faces the same information problem as the judges; C2's break share (0.45 vs C3 0.47) suggests the damage comes
  from firing itself, not from the vocabulary.

## 9. Conclusion

Read as a corrector, a self-critique loop on a frontier-level exam does what the literature says: its last
answer barely improves. Read as a sampler, the same loop is the best test-time method we measured: structured,
never-silent critique reaches the correct answer on 44 more items than content-free iteration, makes correct
answers persistent, and lets a zero-parameter count beat self-consistency at lower cost — with no measurable
help from a vocabulary of the model's own past errors. The count is also where same-model selection ends:
nothing the model can say about its own transitions adds information to how often it returned to an answer.
Where tasks can be verified, the reached-but-unselected answers are the deployable gain; where they cannot, the
count is both the selector and the confidence.

---

## Appendices (pointers)
A. Error bank: source instances, distillation levels, five test-time entries, no-leakage audit, release list —
`ERROR_BANK_PROVENANCE.md`. B. Frozen runtime and the four C2/C3 prompt differences — `C2_BANK_FREE_CRITIC_SPEC.md`.
C. Scorer: tiers, truncation rule, two-stage truncated-vote rule, K = 3 adjudication table incl. hle_201 exact
equality — `HLE_SCORER.md` §1.2. D. Evaluator: full tables, three-role NB, rule sweep, 26-feature contrast, premise
probe, confidence AUROC, revision log — `EVALUATOR_RESULTS.md`. E. Pre-registered C2 design and read-out —
`C2_BANK_FREE_CRITIC_SPEC.md`. F. Figures: F1 two frontiers; F2 stay asymmetry; F3 count-bucket lock rates; F4
judge disagree-accuracy; F5 selective prediction; F6 verifier regimes.

---

## §R. Remaining tasks (draft v4 → submission)

| id | task | blocks | owner |
|---|---|---|---|
| TBD-3b | Add hle_201 rule (exact rational equality, both forms) to `t3_k3_adjudicate_and_recompute.py`; regenerate sidecar/scores/transitions with C2 (159 / 198); C2 MCQ–open split; C2 persistence rows via `persistence_analysis.py` (stay, run-3, retention) | — | agent |
| TBD-4 | Critic tokens C3 (2 288 calls) and C2 (recover from logs or replay-estimate, mark ≈); check whether critic calls ran with thinking; evaluator tokens as a diagnostic line; main-table cost columns absolute | — | agent |
| TBD-5 | Judge-R+ remaining 209 edges (fix streaming/watchdog first; same thinking setting); else footnote "178-item subset" | — | agent |
| TBD-2 | Citations: self-consistency, pass@k, Huang 2023, Reflexion/Self-Refine, PRMs, LLM-as-judge, error-taxonomy prompting | — | agent |
| TBD-6 | Figures F1–F6 | TBD-3b | agent |
| TBD-7 | Frozen-doc sync (FROZEN_DATA ceiling row + evaluator row; SCORER truncated-vote note + hle_201; EVALUATOR_FINAL_DESIGN §4/§6; QCUT header; PROVENANCE five-entry note; PERSISTENCE 190 note done) | — | agent |
| TBD-8 | Deprecate intermediate evaluator docs → `docs/_deprecated/` | — | agent |
| TBD-9 | Outline + PPT re-synced to v4 section order | — | agent |
| TBD-11 | 100-item human double annotation of the scorer (κ) | — | PI + annotator |
| TBD-13 | Selective prediction with frozen vote/mode functions + AUROC bootstrap (§5.5) | — | agent |
| TBD-14 | `scripts/verifier_regimes.py` + F6 (§5.6), incl. asymmetric (s, p) rows and a correlated-error row (q decreasing with #candidates / difficulty) | — | agent |
| TBD-15 | C2/C3 endpoint alignment check (per-round reasoning length, truncation rate, commit rate; 50-item token-plan replay when quota renews) | — | agent |
| TBD-16 | Optional (PI decision): 100-item HLE replication of A2 / A3 / C2 only (mode, vote, ceiling) on a second model family from the registry (qwen3.8-flash or glm-5.3), same loop constants and scorer protocol — to scope or strengthen the §6.4/title claim | quota | PI |
| TBD-17 | Terminology pass: use "structured self-critique" (method), "critic arm" (C2/C3), "placebo" (A2) consistently | — | agent |
| TBD-10 | Journal-format pass; final number audit by a second agent reading only §0 files | all | agent → PI |
