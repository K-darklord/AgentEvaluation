# Paper draft v6 (2026-11-10) — A2′ read out; all headline numbers frozen

> **Status.** Fourth full draft. Changes from v5: the perturbing placebo A2′ (pre-specified) is scored and read
> out ("content has an effect": ceiling 170 vs C2 198, p = 0.0001); C2 numbers are now in the frozen files
> (159 / 198 after the hle_201 exact-equality rule); critic tokens measured by replay for C2 (≈ 23 M); Judge-R+
> row updated to its current coverage; analysis-status and multiplicity paragraph added (§4); claims registry and
> consistency manifest added (Appendix G); abstract cut to ≤ 250 words.
> All numbers freeze-key + sidecar v2 and traceable through `CLAIMS_REGISTRY.md`. Open items: §R.

---

## Title

**Two Frontiers of Test-Time Loops: Structured Self-Critique Raises the Reachable Ceiling on Humanity's Last
Exam, and Where Same-Model Selection Ends**

(long form, if the venue allows a subtitle: *Self-critique is a sampler, not a corrector — free critique beats
fixed and adaptive self-consistency; a vocabulary of the model's own errors adds nothing identifiable; no
same-model judge adds to the vote count.*)

## Abstract (≈ 240 words)

Revision loops in which a model answers, is critiqued, and answers again are usually judged by their last
answer, and by that measure intrinsic self-correction is unreliable. We read such loops as samplers of answer
distributions. On 400 Humanity's Last Exam items, with one model (deepseek-v4-flash) as solver and critic, a
critic that must name a specific suspicion and a concrete check every round raises the number of items whose
trajectory ever contains the correct answer from 154 (a reassuring placebo loop) to 191–198 (p ≤ 8 × 10⁻⁸). A
parameter-free majority over rounds then selects the correct answer on 157/400 items, against 137 for
nine-sample self-consistency (p = 0.004, ties randomized on both sides) and 136.5 for a cost-matched adaptive
variant (p = 0.001), at higher total cost. Two pre-specified controls locate the active ingredient. A
vocabulary distilled from the model's own past errors is not it: critics with and without it do not differ
(p = 0.67). Answer-specificity is: a dose-matched placebo issuing templated, answer-blind suspicions reaches
170 items rather than 198 (p = 0.0001) and selects 142 rather than 157 (p = 0.03). The loops' last answers
improve no more than a placebo's, consistent with the negative self-correction literature. Finally, no
same-model judge of the loop's own transitions adds detectable information to the vote count: three framings
are at chance where they disagree with it (0.46–0.50), and neither cross-half Bayes weighting nor an exhaustive
rule sweep beats it, though gains of a few items cannot be excluded at this sample size.

---

## 1. Introduction

**Two readings of a revision loop.** A model that answers, receives a critique and answers again can be read
as a *corrector*, judged by whether its last answer is better, or as a *sampler*, judged by the distribution
of answers it visits. The corrector reading has been tested and found wanting: without external information,
intrinsic self-correction does not improve reasoning accuracy and often degrades it (Huang et al., 2023). This
paper is about the sampler reading.

**Two frontiers.** A test-time method's accuracy factorizes into how often the correct answer is *reached* (the
reachable ceiling; pass@trajectory) and how often it is then *selected* (the realization rate). Sampling with
majority vote reaches a high ceiling and selects poorly. We ask whether structured self-critique reaches a
comparable ceiling with a trajectory whose structure a trivial selector can exploit, and then where the
selection frontier for a single model lies.

**Main question and pre-specified test.** Can a gold-free, train-free revision loop on one model (i) reach the
correct answer more often than a content-free placebo loop, (ii) select it more often than self-consistency on
the same items, and (iii) be improved further by a same-model evaluator of its own transitions? The falsification
test for (ii), recorded in the project protocol before the HLE runs, was a paired McNemar of the loop's selected
answer against nine-sample self-consistency; three selection rules (final, settle, mode) were listed, mode was not
designated primary, and we therefore report all three and treat mode's result with that in mind (§5.1).

**Findings.** (i) Yes, strongly, for both critic arms (191 and 198 vs 154). (ii) Yes for the free-critique arm
under every treatment of ties and against a cost-matched adaptive baseline (157.4 vs 137.3 with ties randomized
on both sides, p = 0.004; vs adaptive sampling p = 0.001); for the error-bank arm the direction is the same but
the test is not significant once ties are treated symmetrically (150.7 vs 137.3, p = 0.08; it reaches p = 0.03
only with its own recency tie-break against a randomized baseline), so we do not claim it; no for the placebo
(145.9, p = 0.27). A model that starts at 80 % on a benchmark would need a repair/damage ratio above 4 for a
revision to help at all; at HLE's 28 % the threshold is 0.39, which is why revision loops can gain here and not
there (§5.3). Two pre-specified controls locate the active ingredient. Against a reassuring placebo (A2) the
critic arms' selected-answer advantage is not significant (+9 / +14; p = 0.21 / 0.07). Against a dose-matched
*perturbing* placebo (A2′: the same number of suspicions per round, drawn at random from the five archetype
names in a fixed answer-blind template) it is: answer-blind perturbation alone lifts the ceiling from 154 to 170
(p = 0.011) and does nothing for the selected answer (142 vs 146), while answer-specific critique adds the rest
(ceiling 170 → 198, p = 0.0001; selected 142 → 157, p = 0.03). (iii) No: conditional on the vote count,
same-model judgments of the transitions carry no detectable information.

**Contributions.**
1. A generation–selection decomposition for revision loops with pass@trajectory as a first-class metric, and a
   one-step repair/damage account of when a loop's last answer can improve, which places our setting and the
   negative self-correction results on one axis.
2. Evidence that structured self-critique is a competitive sampler: a ceiling equal to nine-sample self-
   consistency with fewer candidates and, for free critique, a parameter-free selection that beats both
   fixed and cost-matched adaptive self-consistency (at higher total cost, §5.1); and two pre-specified
   controls that locate the active ingredient: not the distilled error-bank vocabulary (C2 vs C3, null) but the
   answer-specificity of the critique (C2 vs the perturbing placebo A2′).
3. A mechanism account (activation, persistence and a sequential stopping rule) with an explicit accounting of
   what the recency tie-break contributes, and the vote margin as a usable abstention signal.
4. A bounded negative result on same-model evaluation: three judge framings, Bayes-weighted aggregation and an
   exhaustive rule sweep add no detectable information to the count; the headroom (oracle 173) requires
   information the trajectory does not contain.
5. A frozen, audited scorer for free-form HLE answers (three tiers, K = 3 adjudication, truncation rule), the
   error bank with full provenance, and all judge verdicts, released.

## 2. Related work **[TBD-2 citations]**

Self-consistency, best-of-N and pass@k; *adaptive* / early-stopping self-consistency (our cost-matched baseline);
intrinsic self-correction and its limits (Huang et al. 2023; Reflexion / Self-Refine): we take the negative
result for the last answer as given and study the loop as a distribution; process reward models and trained
verifiers (excluded by design); LLM-as-judge reliability and self-preference, which §6 quantifies as a
conditional information bound; error taxonomies and "learning from mistakes" prompting, whose content we cannot
identify against structured critique.

## 3. Method

### 3.1 Roles, arms and selection rules

One base model plays solver and critic; a frozen, gold-visible scorer grades every round and never touches the
loop. Round 0 of every arm is the bare solver's T = 0 answer (A-seeding).

| Arm | Rounds ≥ 1 | Stopping | Rules reported |
|---|---|---|---|
| A | none | — | init |
| A2 (placebo) | same loop; fixed feedback "No confident error direction was found for this answer." — a content-free *reassurance*, not a prompt to reconsider | 3 identical commits / 10 rounds | final, settle, mode |
| A3 (self-consistency) | 9 i.i.d. samples at T = 0.7 | none (fixed N) | vote over the 9 samples |
| A3-adaptive (cost-matched; simulated on A3's samples in order) | same samples | stop when an answer has 3 votes | vote |
| C3 (error-bank critic) | critic picks 1–3 suspicions from a five-entry vocabulary distilled from the model's own past errors, writes an answer-specific suspicion and a concrete gold-free check grounded in the solver's CoT tail; never silent | as A2 | final, settle, mode |
| A2′ (perturbing placebo) | each round k suspicions (k drawn from C2's empirical distribution: 3 with p = .86, 2 with .11, 1 with .03), drawn without replacement from the five archetype names and rendered with fixed, answer-blind generic sentences in the critic's exact output format; no LLM critic call | as A2 | final, settle, mode |
| C2 (free critic) | identical prompt with the vocabulary removed; the critic names the shortcoming in its own words | as A2 | final, settle, mode |

Loop constants: max 10 rounds; thinking budget 16 384 + margin 8 192 = 24 576 tokens per solver call; T = 0
except A3's samples; no self-reported rationale. Mean rounds per item: A2 4.9, C3 6.7, C2 6.9 (A3 fixed 10).

*Rules.* final = last commit; settle = first commit of the last run of ≥ 3 identical commits (scored wrong if no
such run); mode = most frequent committed answer over rounds; vote = majority over samples. All rules are
parameter-free at selection time (the stop threshold and round cap are loop constants). *Tie-breaks.* For the
loop arms, mode breaks ties by the answer whose last occurrence is latest, a recency rule that is part of the
method (a sequential process converges) and was fixed in the scorer before any HLE comparison. For A3 the samples
are exchangeable, so no tie rule carries information; we therefore randomize A3's ties and report every
comparison against the distribution over 300 draws (A3 mean 137.4, range 129–145; the two deterministic
conventions give 136 and 141). Because a recency rule is available to the loop arms and meaningless for the
baseline, every headline comparison is reported under the **symmetric convention** (ties randomized on both
sides and integrated over 300 paired draws), with the method-as-specified (recency) figures given alongside and
the recency rule's contribution quantified (§5.1). *A3-adaptive* is simulated on A3's nine samples: for each of
300 permutations of the samples (drawn without replacement), votes accumulate in that order and stop when an
answer reaches three; ties random; tokens are those of the samples consumed.
Answer identity is one frozen shape-aware normalizer; a length-truncated round may vote but a truncated winner
is scored wrong (Appendix C).

### 3.2 The critic's content: error bank vs free critique

C3's vocabulary comes from 33 wrong single-shot answers of the same model on six unrelated benchmarks (GPQA-
Diamond 9, MMLU-Pro 7, MATH-500 5, BFCL 5, BBH 4, AIME 3; no HLE item, answer or error enters any bank),
distilled to 24 answer-free mechanism + check entries and deduplicated at test time to five archetype entries. C2
removes exactly this block. The four textual differences are the vocabulary block, one output-format line, one
clause of the system prompt, and the fallback path, which never touches the bank (Appendix B). One behavioural
difference followed: freed from the vocabulary, the C2 critic emitted three suspicions in 86 % of rounds (C3:
one suspicion in 57 %, three in 12 %), so the two critic arms differ in perturbation dose as well as in
content; the perturbing placebo (§8) is dose-matched to C2. The read-out rule,
written in the project protocol after C3's results were known and before C2 was run (Appendix E, dated commit):
bank "effective" if C2's ceiling is at least 15 items below C3's at p < 0.05 or its persistence asymmetry is
significantly lower; "not identifiable" if C2's ceiling is **no lower than C3 − 5** with overlapping asymmetry
intervals; otherwise grey zone with a further control. Outcome: C2's ceiling 198 vs C3's 191, asymmetry 1.9
[1.6, 2.2] vs 1.5 [1.3, 1.8]: "not identifiable".

## 4. Evaluation protocol

HLE-400 (84 MCQ, 316 open-form). Scorer: T1 exact match by shape → T2 LLM false-negative rescue (deepseek-v4-
pro; one-directional, same model family as the solver) → T3 independent judge (astra) at K = 1, all
disagreements at K = 3, residual disputes adjudicated per answer variant with the rule "same substance ⇒ same
verdict in every arm and round" (22 answer variants for A/A2/A3/C3; for C2, 21 ambiguous verdicts: 11 under
existing rules, 7 (all seven forms of hle_201) verified equal to the gold rational multiple of π by exact arithmetic and
scored correct, 4 confirmed wrong). Because T2 is one-directional, scorer false positives inflate pass@trajectory
more for arms with more distinct candidates (3.5–3.7 per item in the critic arms vs 2.1 in A2); the human check
**[TBD-11]** is therefore stratified to over-sample items reached only in a critic arm and verdicts that came
from T2 or K = 3. Statistics: paired McNemar on the same 400 items; A3 comparisons integrated over tie draws;
bootstrap intervals for ratios; dev = even ids / test = odd ids for anything fitted (200/200). "Pre-specified"
below means recorded in the project's protocol documents with dated commits before the corresponding data were
seen; no external registry was used.

**Analysis status.** We label every analysis by provenance (full registry with claim → evidence mapping:
Appendix G, `CLAIMS_REGISTRY.md`). *Pre-specified*: the falsification test (selected answer vs nine-sample
self-consistency, paired McNemar), the placebo arm, the C2 read-out rule, and the evaluator criteria E1–E4.
*Exploratory* (proposed after seeing data, before external review): the generation–selection decomposition
as applied here, the one-step repair/damage account (§5.3), the conditional-on-count test (§6.3), selective
prediction (§5.5), the verifier simulation (§5.6) and the trajectory-feature contrast. *Post hoc robustness*
(added in response to review; conclusions do not depend on them, and each moves in the conservative direction):
the symmetric tie convention, the adaptive self-consistency baseline, the recency-rule accounting, the
three-role Bayes aggregator, the aggregation sweep and the intervals on disagreement accuracies.
**Multiplicity.** Three selection rules (final, settle, mode) were listed in the protocol without a primary;
we report all three. Read with a Bonferroni factor of 3, C2.mode vs self-consistency remains p < 0.02 under the
symmetric convention; C3.mode does not. Three judge framings are all reported; none was selected after the fact.
Numbers that recur across sections are tracked in a consistency manifest (`consistency_manifest.json`) and
checked mechanically before each draft.

## 5. Results

### 5.1 Main table

*Ceiling (pass@trajectory)*: items for which some candidate, among the rounds the selection rule votes over (A3:
its nine samples; loop arms: all rounds), has its last occurrence scored correct; this is the best any selector could do
under the frozen scorer.

| Arm · rule | Correct / 400 | Ceiling | Solver tokens | Critic tokens | Notes |
|---|---|---|---|---|---|
| A · init | 113 | 113 | 5.10 M | 0 | |
| A2 · final / settle / **mode** | 142 / 136 / **145** | 154 | 24.66 M | 0 | mode under random ties 145.9 |
| A3 · vote (9 samples) | **137.4** ± (129–145) | 190 | 51.32 M | 0 | deterministic conventions: 136 / 141 |
| A3-adaptive · vote | 136.5 (129–145) | — | 36.0 M (35.3–36.5) | 0 | stop at 3 votes; 300 sample permutations |
| A2′ · final / settle / **mode** | 135 / 127 / **143** | 170 | 30.22 M | 0 | mode under random ties 142.1 |
| C3 · final / settle / **mode** | 140 / 117 / **154** | 191 | 37.05 M | ≈ 16–23 M (2 288 calls; **[TBD-4b]** re-estimate with the same 50-call replay as C2) | total ≈ 53–60 M; mode under random ties 150.5 |
| C2 · final / settle / **mode** | 148 / 121 / **159** | **198** | 38.13 M | ≈ 23 M (2 358 calls; replay of 50: 2.6 k prompt + 7.2 k completion incl. 6.9 k hidden reasoning per call; range 19–27 M) | total ≈ 61 M; mode under random ties 157.4 |

Selectors cost no tokens. Critic tokens are estimated by replaying a sample of critic calls under the frozen
configuration (the critic runs with hidden reasoning, hence the range). Judge tokens (§6: Judge-R 24 M, Judge-C
28 M, Judge-R+ 19 M on partial coverage) are diagnostic, not part of any arm.

**Paired comparisons (McNemar exact; medians and IQR over 300 paired draws).**
*Symmetric convention (ties randomized on both sides):* C2 157.4 vs A3 137.3, p = **0.004** [0.001, 0.009],
significant in 97 % of draws; C3 150.7 vs 137.3, p = 0.076 [0.044, 0.161], significant in 30 %; A2 145.9 vs
137.4, p = 0.27. Vs A3-adaptive (random orders and ties): C2 (recency) p = **0.001** [0.001, 0.005]; C3 (recency)
p = 0.021 [0.012, 0.044], 80 %. *Method as specified (recency for loop arms, randomized baseline):* C2 159,
p = 0.002, 100 %; C3 154, p = 0.030 [0.016, 0.058], 70 %; A2 145, p = 0.34. We claim the symmetric-convention
results. Perturbing placebo (pre-specified read-out, Appendix E): ceiling A2′ vs C2 12/40, **p = 0.0001**; A2′ vs
A2 26/10, p = 0.011; selected answer A2′ vs C2 under the symmetric convention 142.1 vs 157.4, p = 0.032
[0.019, 0.054], significant in 74 % of draws (recency: 143 vs 159, 15/31, p = 0.026); A2′ vs A2 p = 0.63; A2′ vs
A3 p = 0.54. Between loop arms: C2.mode vs
C3.mode 27/23, p = 0.67; C3.mode vs A2.mode 25/16, p = 0.21; C2.mode vs A2.mode 33/19, p = 0.07. All arms vs
A.init p ≤ 0.0014. Final-answer rule: C3.final vs A3.vote 26/22, p = 0.67; C2.final vs A3.vote 32/20, p = 0.13.
Ceiling: C3 vs A2 47/8, **p = 8 × 10⁻⁸**; C2 vs A2 50/7, **p = 4 × 10⁻⁹**; C2 vs C3 22/16, p = 0.42; C3 vs A3
20/25, p = 0.55.

**Recency rule.** Mode under randomized ties reads 145.9 / 150.5 / 157.4 for A2 / C3 / C2: the recency
tie-break contributes −0.9 / +3.5 / +1.6 items. It is part of the method (a sequential process converges) and was
fixed before any HLE comparison, but since it is unavailable to the baseline we do not let it carry a claim: C3's
significance depends on it and is therefore not claimed; C2's does not.

**Reading.** The ceiling gain over the reassuring placebo decomposes into +16 from answer-blind perturbation
(A2 → A2′) and +28 from answer-specific critique (A2′ → C2). On the selected answer the perturbation alone buys
nothing (142–143 vs 145–146) and answer-specific critique buys about +15 over the dose-matched placebo
(p ≈ 0.03), a comparison the reassuring placebo could not resolve. The free-critique arm beats
self-consistency under the symmetric convention and against a
cost-matched adaptive baseline; the error-bank arm points the same way but is not significant under symmetric
ties; the placebo is not. The two
critic arms do not differ from each other. The critic arms' advantage over the placebo on the *selected* answer
(+9 / +14) is not significant, whereas their advantage on the *ceiling* (+37 / +44) is large: the
critique's identifiable contribution is to reach, not to select. Cost: the critic arms use about as many solver
tokens as adaptive self-consistency (37–38 vs 36 M) and in addition pay for one critic call per round
(≈ 23 M for C2 by replay; C3 of the same order); their total cost (≈ 55–61 M) is therefore about 1.6 times that of
adaptive self-consistency and above fixed ten-sample self-consistency (51 M), not lower. The critic's hidden
reasoning (≈ 7 k tokens per call) accounts for most of it. The last
answer is worse than the count in every loop arm (142 < 145, 140 < 154, 148 < 159).

### 5.2 Answer form

| rule | MCQ (84) | open (316) |
|---|---|---|
| init | 31 | 82 |
| A2.mode | 36 | 109 |
| A3.vote (first-encountered convention) | 35 | 101 |
| C3.mode | 40 | 114 |
| A2′.mode | 38 | 105 |
| C2.mode | 35 | **124** |

The critic arms' gain over self-consistency is larger on open-form items than on MCQ: not a voting-over-few-
options artefact.

### 5.3 The last answer: a one-step repair/damage account

Let ECR₁ = P(wrong at round 0 → correct at round 1) and EIR₁ = P(correct → wrong) over the first revision, where
every item is still running. The last answer improves over a step only if ECR₁/EIR₁ > Acc₀/(1 − Acc₀) = 0.39
at Acc₀ = 0.283. Observed: A2 17 up / 7 down (ratio 0.96), C3 38/19 (0.79), C2 45/20 (0.89), all above the
threshold, all positive, and the critic arms move two to three times as many items in each direction as the
placebo.
On a benchmark where the model starts at 80 %, the same ratios would need to exceed 4; a critique that moves
items symmetrically then degrades accuracy, which is the regime of the negative self-correction results. Pooled
multi-round rates are not a substitute for this check: under early stopping, items that lock early (mostly
correct) contribute few rounds and cycling items (mostly wrong) many, so pooled ECR/EIR (C3: 0.113 / 0.298) describe
a length-biased mixture and would predict a decline where +27 is observed. Over the whole loop, round-level
transitions reconcile exactly with final − init (C3: 195 up, 168 down, +27; C2: +35; A2: +29); the smaller
counts of §6.1 (159 repair / 142 break) count only switches between two committed answers.

The reconciliation with Huang et al. is therefore not that critique corrects (the placebo's last answer improves
as much as the critic arms', 142 vs 140 / 148) but that at low initial accuracy any revision with a near-
symmetric repair/damage profile helps a little, and that the trajectory, not the last answer, is where the
critique's effect shows.

### 5.4 Mechanism: activation, persistence and the stopping rule

**Activation.** Both critic arms put the correct answer into the trajectory far more often than the placebo
(191 / 198 vs 154) with 3.5–3.7 distinct candidates per item vs 2.1; the perturbing placebo sits in between
(170, 2.7 candidates, 772 switches vs 475 for A2 and 1 323 for C2): the solver reacts to answer-blind
suspicions, but far less than to suspicions that read its answer; so does temperature sampling (190, with
4.1 candidates), which shows that a non-specific perturbation suffices to reach the ceiling. Ceiling by round:
C3 passes A2's final ceiling (154) at round 2 (165) and reaches 180 by round 4; A2 is at 151 by round 4 and
stops.

**Persistence.** Per-step probability that the next commit repeats the current one, by correctness of the
current one:

| | P(stay · correct) | P(stay · wrong) | ratio |
|---|---|---|---|
| A3 (i.i.d.; P(next draw = current)) | 0.54 | 0.34 | 1.6 |
| C3 | 0.55 [0.49, 0.62] | 0.36 [0.32, 0.40] | 1.5 [1.3, 1.8] |
| C2 | 0.57 [0.51, 0.64] | 0.30 [0.26, 0.33] | 1.9 [1.6, 2.2] |
| A2′ | 0.71 [0.66, 0.77] | 0.50 [0.46, 0.54] | 1.4 [1.3, 1.6] |
| A2 | 0.79 | 0.63 | 1.25 |

The asymmetry in the error-bank arm equals that of i.i.d. sampling; the free-critique arm's is higher
(1.9 vs 1.5, intervals overlapping) and the placebo's lower, since the placebo makes everything sticky. C2's
higher asymmetry runs in the direction of its higher ceiling and mode and satisfies the "not lower" clause of the
read-out rule; because the two critic arms do not differ significantly on any outcome, we do not read it as
free critique being superior. What differs between the critic arms and sampling is not the per-step asymmetry but the
sequential structure the stopping rule acts on: consecutive repeats form runs, a run of three stops the loop,
and the recency rule reads the end of the trajectory. The cost-matched adaptive baseline (stop at 3 votes on
i.i.d. samples) isolates part of this: it reaches 136.5 vs 137 for fixed-N sampling (the stopping rule on
exchangeable samples buys nothing) while the critic arms reach 151–157 under the same tie convention; so the
stopping rule alone does not explain the gap; the ordered trajectory does something sampling
does not, and §6 shows that whatever it is, it is fully captured by the count. Retention of the correct answer
from first appearance to selection: 0.94 (A2, 145/154) / 0.80 (C3, 154/191) / 0.72 (A3, 136/190).

**Normalizer.** 27 % of correct→correct transitions in the critic arms (16 % in A2) change the normalized key —
equivalent correct answers expressed differently. The count therefore under-counts correct answers; a semantic
merger would raise mode but needs an equivalence judge, which is the problem of §6 in another form. We report
this as a limitation and a direction.

### 5.5 The count as an abstention signal (`scripts/selective_prediction.py`)

Ranking items by vote margin (top-1 minus top-2) and answering only the top fraction (A3: mean over 100 tie
draws; loop arms: recency rule):

| coverage | A2 | A3 | C3 | C2 |
|---|---|---|---|---|
| 1.00 | .362 | .343 | .385 | .398 |
| 0.80 | .391 | .387 | .425 | **.453** |
| 0.50 | .425 | .445 | .485 | **.510** |
| 0.33 | .386 | .470 | **.515** | .492 |

AUROC of the margin for "selected answer is correct" (bootstrap 95 %): A2 0.59 [0.54, 0.64]; A3 0.64
[0.58, 0.69]; C3 0.64 [0.58, 0.70]; C2 0.64 [0.59, 0.69]. The placebo's margin is the least informative (its
accuracy falls at low coverage because nearly every answer became a three-run), but the intervals overlap, so we
state this as a trend. Adding any judge's verdicts to the margin does not improve it out of sample (AUROC
0.60 → 0.60; Appendix D). We do not claim calibration.

### 5.6 How the ceiling converts under external verification (`scripts/verifier_regimes.py`)

A verifier accepts each candidate independently (sensitivity s on correct, specificity p on wrong); selection =
count among the accepted, fallback mode. Rows: symmetric s = p = q; asymmetric (s, p); and a correlated-error
variant in which the verifier is weaker on items with more candidates and on items the greedy solver got wrong
(q − 0.05 per extra candidate, − 0.05 if hard, floored at 0.5).

| regime | q / (s, p) | A2 | A3 | C3 | C2 | C3 − A2 | C3 − A3 | C2 − A3 |
|---|---|---|---|---|---|---|---|---|
| independent | 0.5 | 135 | 126 | 139 | 146 | +4 | +13 | +20 |
| independent | 0.7 | 144 | 151 | 160 | 166 | +17 | +9 | +15 |
| independent | 0.9 | 151 | 177 | 182 | 187 | +31 | +5 | +10 |
| independent | 1.0 | 154 | 190 | 191 | 198 | +37 | +1 | +8 |
| asymmetric | (0.8, 0.95) | 151 | 178 | 181 | 187 | +30 | +3 | +9 |
| correlated | 0.7 | 140 | 135 | 148 | 154 | +8 | +13 | +20 |
| correlated | 0.9 | 147 | 152 | 163 | 168 | +16 | +11 | +16 |

With independent errors the critic arms' advantage over the placebo grows with verification (+4 → +37) and their
advantage over sampling shrinks towards the ceiling difference (+13 → +1 for C3; +20 → +8 for C2) and never
falls below it. With errors correlated with candidate count and difficulty, the realistic case, the advantage over
sampling does **not** shrink (C3 − A3 ≈ +11–13 at q = 0.7–0.9), because the sampling arm carries the most
candidates and is hurt most by false accepts. The practical reading is therefore: where a verifier is available,
critique-driven trajectories are at least as good a pool as samples and better whenever the verifier's errors
track difficulty; where no verifier is available, persistence is the only selector and the critic arms' margin
over sampling is largest.

## 6. The selection frontier: can a same-model evaluator add to the count?

### 6.1 Headroom and its symmetry
Of C3's 191 reachable items mode selects 154; the 37 recoverable items are 11 ties, 10 with margin one and 16
with margin ≥ 2. Oracle undo of every correct→wrong switch between committed answers: 173; of feedback-
attributed switches only: 165; blind undo of all feedback-attributed switches: 149 (+6 / −11). Of 301 switches
between committed answers that change correctness, 159 repair and 142 break.

### 6.2 Three judge framings, one aggregator, pre-specified acceptance
Edge-level verdicts → s(c) = log count(c) + Σ ± log LR(v), LR fitted on dev, frozen on test; all LR = 1 is mode.
Judge-R (rubric on the new answer), Judge-R+ (question-visible, cited, falsifier class), Judge-C (is the critic's
suspicion warranted; sees only the criticized answer). A pairwise variant (two candidates side by side, question
visible) was run as part of Judge-R+'s development **[TBD-18: report as a fourth row]**. Criteria E1–E4 were
written before the runs.

### 6.3 Results

| Judge (edges judged / 1201; items / 244) | E1 edge acc. | LR CIs ∋ 1 | E3 dev→test (mode 76) | E4 test→dev (mode 78) | acc. when disagreeing with count (Wilson 95 %) | rule sweep, in-sample max |
|---|---|---|---|---|---|---|
| Judge-R (1185; 241) | 0.577 | yes | 76 (+2 −2) | 73 (+5 −10) | 18/36 = 0.50 [0.35, 0.65] | 154 |
| Judge-R+ (1041; 242 **[TBD-5]**) | 0.603 | no (CUT 0.72 [0.52, 0.99]; NO_CUT 1.90 [1.20, 3.02]) | 73 (+3 −6, p = .51) | 72 (+5 −11) | 53/116 = 0.46 [0.37, 0.55] | 156 (0 across halves) |
| Judge-C (1201; 244) | 0.663 | no | 71 (+3 −8, p = .23) | 77 (+8 −9) | 32/66 = 0.49 [0.37, 0.60] | 155 (0 across halves) |

Of the 253 multi-answer items, 244 have at least one switch between two committed answers (1201 edges); the
other 9 change answer only through a no-commit round, have no judgeable edge, and fall back to mode for every
judge. Counts alone predict repair vs break at 0.58 / 0.60–0.62 / 0.67 on the same edges, never below the judge. In-sample
logistic over count + verdict features: 150 < 154. Why 66 % edge accuracy is not enough: overturning mode is a
repair on 37 of the 123 multi-answer items where mode could be overturned (prior 0.30); a judge with edge
accuracy p flips with precision 0.30p/(0.30p + 0.70(1 − p)) = 45 % at p = 0.66, crossing 50 % above 0.70. On the
56 tie items, where the count is silent, Judge-C does carry conditional information at the edge level (17/26
when disagreeing with the count) but it changes the selected answer on few items (+2 −1 / +3 −3 across halves);
the recency rule alone recovers 14 of the 23 ties whose tied set contains the correct answer.

### 6.4 Statement
None of the three same-model judge framings added detectable information to the vote count: where they disagree
with it they are at chance (0.46–0.50, intervals 0.35–0.65), Bayes-weighted aggregation fitted on one half
gains ≤ +1 on the other, and an exhaustive sweep of 81 aggregation rules gains ≤ +2 in-sample. This is a non-
detection with the power of 400 items (gains of up to roughly 5 items per judge are not excluded) on one
model, one benchmark and three framings, and is falsified by any judge that beats the count on these edges. The
three framings are not independent evidence: same model, and each correlates with the count, which is the
finding. The headroom exists (oracle 173) and is partly visible at the edge level (Judge-C), but recovering it
needs information that is not a function of the trajectory: a stronger model, external verification, or a
critic that abstains.

## 7. Hypotheses revisited

- **H1, identifiability of critique content.** Pre-specified as structure vs content (C3 vs C2 vs A2). The
  shared critique structure is identifiable (both critic arms vs placebo on the ceiling, p ≤ 8 × 10⁻⁸); the
  bank's distilled vocabulary is not (C2 ≥ C3 on every endpoint, all n.s.). The residual "structure" is
  decomposed by the perturbing placebo under its pre-specified rule (A2′ ceiling ≤ C2 − 15 at p < 0.05 →
  "content has an effect"): 170 vs 198, p = 0.0001. Answer-blind pressure accounts for about a third of the
  ceiling gain over A2 and none of the selection gain; answer-specific critique accounts for the rest. The protocol's original H1 (a
  gold-visible labeller's archetype hit-rate on wrong rounds) was specified but not executed, because §6 showed
  the critic's archetype labels carry no conditional information about correctness; we report this rather than
  the result.
- **H2, mechanism sensitivity.** Supported on the ceiling (i), by construction (ii) and on the open-form split
  (iii); the realized difference to the placebo (+9 / +14) is not significant and §6 explains why a same-model
  selector cannot enlarge it.
- **H3, decision value.** The free-critique arm beats fixed and adaptive self-consistency on the same items
  under the symmetric tie convention (p = 0.004 / 0.001); the error-bank arm does not (0.08 / 0.02 with its own
  recency rule only) and is not claimed. The original "at no higher cost" clause is
  **withdrawn**: solver tokens are comparable to adaptive self-consistency and critic tokens are additional.
- **Falsification boundary:** not crossed for C2; crossed for C3 under the symmetric convention.

## 8. Limitations and future work

- Existence, not optimality: one model, one benchmark, no tuning on HLE; the selection-frontier statement is
  bounded accordingly.
- The last answer of a revision loop remains unreliable; our gains are in the aggregate. Deployment must read
  the trajectory, not the final message.
- The critique's largest and most secure effect is on the ceiling. On the selected answer it is significant
  against the dose-matched perturbing placebo (p ≈ 0.03) but not against the reassuring one (p = 0.07–0.14), and
  the loop-plus-count alone already accounts for most of the gain over the initial answer.
- Scorer: an LLM tier with one-directional rescue; false positives scale with candidate count and could inflate
  the critic arms' ceilings; the stratified human check **[TBD-11]** bounds this.
- Normalizer: 27 % of correct→correct transitions change key in the critic arms (§5.4).
- Endpoint: C2 ran on the pay-as-you-go alias of the same weights after the subscription quota was exhausted.
  Per-round statistics (rounds ≥ 1) are aligned with C3: mean reasoning tokens 12 414 vs 12 405; truncation
  (finish_reason = length) 7.5 % vs 7.8 %; usable-commit rate (round yields a normalizable answer key) 92.5 % vs
  92.2 %; reasoning length median 45.2k vs 45.4k chars (`endpoint_caveat_alignment.json`). An endpoint artefact
  behind C2 ≥ C3 is excluded on every observable; a 50-item same-route replay is **[TBD-15]** when quota renews.
- Placebos: A2 is a reassurance; A2′ is a dose-matched perturbation with templated, answer-blind suspicions.
  A2′ controls for pressure, dose and format, not for the fluency or length of the feedback (its sentences are
  generic and identical across items); a critic shown a *different* item's answer would be the stricter control.
- Dose: C2's critic emitted three suspicions per round far more often than C3's (86 % vs 12 %); C2 ≥ C3 is
  therefore confounded by dose as well as content, which is one more reason not to read it as free critique
  being superior.
- Power: 400 items resolve paired differences of ≈ 17–22 items, not 9–14.
- Pre-specification is internal (dated commits), not externally registered.
- Prevention vs repair: an abstaining critic acts where the headroom lives, but its gate faces the same
  information problem as the judges; C2's break share (0.45 vs C3 0.47) suggests the damage comes from firing
  itself, not from the vocabulary.

## 9. Conclusion

Read as a corrector, a self-critique loop on a frontier-level exam does what the literature says: its last
answer improves no more than a placebo's. Read as a sampler, never-silent critique that reads the answer reaches the
correct answer on 37–44 more items than content-free iteration and 21–28 more than answer-blind perturbation
of the same dose, and a parameter-free count over the trajectory
selects it more often than fixed or adaptive self-consistency when the critic reasons freely; when the critic
is confined to a vocabulary of the model's own past errors the direction is the same and the test does not
reach significance under a symmetric tie convention. The count is also where same-model
selection ends on this benchmark: nothing the model says about its own transitions adds detectable information
to how often it returned to an answer. Where tasks can be verified, the reached-but-unselected answers are the
deployable gain; where they cannot, the count is both the selector and the abstention signal.

---

## Appendices (pointers)
A. Error bank — `ERROR_BANK_PROVENANCE.md`. B. Frozen runtime, C2/C3 prompt differences, critic and judge
budgets — `C2_BANK_FREE_CRITIC_SPEC.md`. C. Scorer, truncation and tie rules, K = 3 table incl. hle_201 —
`HLE_SCORER.md`. D. Evaluator tables, pairwise judge, confidence AUROC, revision log — `EVALUATOR_RESULTS.md`.
E. Protocol documents with dated commits (falsification test, C2 read-out, E1–E4). G. Claims registry
(claim → evidence → status) and consistency manifest — `CLAIMS_REGISTRY.md`, `consistency_manifest.json`.
F. Figures: F1 two frontiers;
F2 ceiling by round; F3 stay asymmetry; F4 judge disagree-accuracy with intervals; F5 selective prediction;
F6 verifier regimes.

---

## §R. Remaining tasks (v6 → submission)

| id | task | owner | status |
|---|---|---|---|
| TBD-R | **Second-model replication (qwen3.8-flash)**: finish A3 (199/200) → second 200 → scoring (T1→T2→T3, K = 3) → `REPLICATION_RESULTS.md`; read out R1–R4 once, at n = 400 | agent | first 200 run, unscored |
| TBD-4b | C3 critic tokens by the same 50-call replay as C2 (C2: ≈ 23 M) | agent | open |
| TBD-5 | Judge-R+: rebuild manifest in freeze-key space, judge the 160 missing edges, regenerate the row | agent | open (1041/1201) |
| TBD-18 | Pairwise judge as a fourth row of §6.3 | agent | open |
| TBD-11 | 100-item stratified human double annotation of the scorer (κ) | PI + annotator | open |
| TBD-15 | 50-item same-route replay of C2 when quota renews | agent | waiting on quota |
| TBD-2 | Citations (incl. adaptive-consistency, universal self-consistency, self-preference in LLM judges) | agent | open |
| TBD-6 | Figures F1–F6 (specs in `EXEC_AGENT_WORKLIST.md` E9) | agent | open |
| TBD-7/8 | Frozen-doc sync and deprecation of intermediate evaluator docs | agent | open |
| TBD-C7 | Prose gates (mechanical: passive voice, intensifiers; semantic; independent red team) | author + review agent | em-dashes done |
| TBD-C8 | Third independent review with the ML review checklist and validity-threat table | review agent | after TBD-R |
| TBD-C9 | Alternative introduction/abstract in the "open with the challenge" pattern, for PI choice | author | after TBD-R |
| TBD-10 | Format pass; final audit by a second agent against `CLAIMS_REGISTRY.md` and `consistency_manifest.json` | agent → PI | last |

Closed since v5: hle_201 regeneration (C2 159 / 198 frozen); C2 critic tokens; C2 answer-form split; C2
persistence with intervals; endpoint alignment; A2′ run, scoring and read-out; selective-prediction and
verifier scripts; tie-randomization and adaptive baseline in a repository script; judge coverage units.
