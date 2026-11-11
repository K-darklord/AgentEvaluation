# Two Frontiers of Test-Time Revision: Answer-Specific Self-Critique Raises the Reachable Ceiling, and the Vote Count Bounds Same-Model Selection

## Abstract

Revision loops, in which a model answers, is critiqued, and answers again, are usually judged by their last answer, and by that measure intrinsic self-correction is unreliable. We study such loops as samplers of answer distributions. On 400 items from Humanity's Last Exam, with a single model acting as solver and critic, a critic that must name a specific suspicion and a concrete check in every round raises the number of items whose trajectory ever contains the correct answer from 154 under a reassuring placebo to 191–198 (p ≤ 8 × 10⁻⁸). A parameter-free majority over rounds then selects the correct answer on 157 items, against 137 for nine-sample self-consistency (p = 0.004) and 136.5 for a cost-matched adaptive variant (p = 0.001), at a higher total cost. Two pre-specified controls locate the active ingredient. A vocabulary distilled from the model's own past errors is not the active ingredient: critics with and without it do not differ (p = 0.67). Answer-specificity is: a dose-matched placebo that issues templated, answer-blind suspicions reaches 170 items instead of 198 (p = 0.0001) and selects 142 instead of 157 (p = 0.03). The last answers of all loops improve no more than a placebo's, in line with the negative literature on self-correction. Finally, no same-model judge of the loop's own transitions adds detectable information to the vote count: three judge framings are at chance wherever they disagree with it (0.46–0.50), and neither Bayes-weighted aggregation fitted on half of the items nor an exhaustive sweep of aggregation rules improves on it, although gains of a few items cannot be excluded at this sample size.

## 1 Introduction

A language model that answers a question, receives a critique, and answers again can be evaluated in two ways. Read as a *corrector*, the loop is judged by whether its last answer is better than its first. Read as a *sampler*, it is judged by the distribution of answers it visits. The corrector reading has been tested extensively and the result is discouraging: without external information, intrinsic self-correction does not reliably improve reasoning accuracy and often degrades it (Huang et al., 2024; Kamoi et al., 2024). This paper examines the sampler reading.

The sampler reading rests on a decomposition that applies to any test-time method. Accuracy is the product of how often the correct answer is *reached* and how often it is then *selected*. We call the first quantity the reachable ceiling, the number of items for which the correct answer appears at least once among the candidates, by analogy with pass@k (Chen et al., 2021). Sampling with a majority vote (Wang et al., 2023) reaches a high ceiling and selects poorly: the correct answer is often in the pool and is outvoted. A revision loop produces an ordered trajectory instead of an exchangeable pool, and the question is whether that order carries information a simple selector can use.

We ask three questions about a gold-free, training-free revision loop in which one model plays both solver and critic. First, does the loop reach the correct answer more often than a loop with content-free feedback? Second, does a simple rule select the correct answer more often than self-consistency on the same items? Third, can a same-model evaluator of the loop's own transitions improve on that rule? The second question carries the falsification test we fixed before running the benchmark: a paired comparison of the loop's selected answer against nine-sample self-consistency.

On 400 items from Humanity's Last Exam (Phan et al., 2025) the answers are yes, yes, and no. A critic that must produce a specific suspicion and a concrete check every round raises the reachable ceiling from 154 to 198 items. A majority over the rounds of the trajectory selects the correct answer on 157 items, against 137 for self-consistency and 136.5 for an adaptive variant matched in solver cost. Two controls, both specified before their data were collected, identify what in the critique matters. Removing a vocabulary of error archetypes distilled from the model's own past mistakes changes nothing measurable. Replacing the critique with the same number of templated suspicions that never read the answer removes most of the effect: the ceiling falls to 170 and the selected answer returns to the level of the placebo. The effective ingredient is therefore that the critique is specific to the answer it criticizes.

The third question has a negative answer, and we give it a structure. An oracle that undoes every harmful switch in the trajectories would recover 19 more items, so the information exists in principle. Three same-model judges with different framings fail to extract it: wherever a judge disagrees with the vote count, it is right half of the time. Aggregating verdicts with likelihood ratios fitted on half of the items never improves on the count on the other half, and an exhaustive sweep of aggregation rules fails to improve on it even in-sample.

Our contributions are as follows.

1. A generation–selection decomposition for revision loops, with the reachable ceiling as a first-class metric, and a one-step repair-to-damage criterion that places our setting and the negative self-correction results on a single axis.
2. Evidence that answer-specific self-critique is a competitive sampler: it matches the ceiling of nine-sample self-consistency with fewer candidates, and a parameter-free majority over its trajectory beats both fixed and adaptive self-consistency, at a higher total cost.
3. Two pre-specified controls that locate the active ingredient: a null result for an error vocabulary distilled from the model's past mistakes, and a positive result for answer-specificity against a dose-matched perturbing placebo.
4. A bounded negative result on same-model evaluation: conditional on the vote count, three judge framings carry no detectable information about which transition was correct.
5. A frozen and audited scoring protocol for free-form answers on Humanity's Last Exam, released with all trajectories, judge verdicts and analysis code.

## 2 Related Work

**Sampling and voting.** Self-consistency (Wang et al., 2023) draws several reasoning paths and returns the most frequent answer. Adaptive variants stop sampling once the vote is settled and recover most of the accuracy at lower cost (Aggarwal et al., 2023); universal self-consistency replaces the vote with a model-based selection for free-form answers (Chen et al., 2023). We use fixed and adaptive self-consistency as baselines and adopt the pass@k view of sampling (Chen et al., 2021) to separate reaching an answer from selecting it.

**Self-correction.** Self-Refine (Madaan et al., 2023) and Reflexion (Shinn et al., 2023) iterate generation and feedback from the same model. Huang et al. (2024) show that the gains reported for intrinsic self-correction largely vanish when no oracle information leaks into the loop, and Kamoi et al. (2024) survey the conditions under which self-correction helps. We take the negative result for the last answer as given, reproduce it, and show that the trajectory as a whole is nevertheless informative.

**Verifiers and judges.** Process reward models and trained verifiers (Lightman et al., 2023) supply the external signal that self-correction lacks, at the cost of training data with positive labels; we exclude them by design. Language models used as judges are known to be imperfect and to prefer their own outputs (Zheng et al., 2023; Panickssery et al., 2024). Our third question quantifies this for the specific task of judging a model's own answer transitions, in the form of a conditional information bound.

## 3 Method

### 3.1 Loop and conditions

A solver answers each question greedily (temperature 0). In every subsequent round it receives its previous answer together with a feedback message and answers again; it is told to keep its answer if it believes the answer is correct. A loop stops after three identical consecutive answers or after ten rounds. All conditions share the solver's greedy first answer, so they differ only in what follows it. The solver and the critic are the same model, deepseek-v4-flash, with a reasoning budget of 16,384 tokens and a visible-output margin of 8,192 tokens per call.

We compare six conditions (Table 1). The *reassuring placebo* returns a fixed sentence stating that no error direction was found. The *free critic* is a separate call to the same model that reads the question, the current answer and the tail of the solver's reasoning, and must return between one and three suspicions, each with a concrete check the solver can carry out without the reference answer; it may not state a probability, name an answer, or remain silent. The *bank critic* is identical except that each suspicion must be drawn from a vocabulary of five error archetypes (Section 3.2). The *perturbing placebo* issues the same number of suspicions per round as the free critic, with archetype names drawn at random and rendered through fixed generic sentences in the critic's exact output format, without reading the question, the answer or the reasoning; it involves no model call. *Self-consistency* draws nine independent samples at temperature 0.7. *Adaptive self-consistency* consumes the same samples in random order and stops when an answer has three votes.

**Table 1.** Conditions. All loops share the greedy first answer, the stopping rule and the token budget.

| Condition | Feedback in rounds ≥ 1 | Reads the answer | Model calls per round |
|---|---|---|---|
| Greedy | none | – | 1 |
| Reassuring placebo | fixed sentence: no error direction found | no | 1 |
| Perturbing placebo | 1–3 templated suspicions, archetype names drawn at random | no | 1 |
| Bank critic | 1–3 answer-specific suspicions with checks, from a five-archetype vocabulary | yes | 2 |
| Free critic | 1–3 answer-specific suspicions with checks, in the critic's own words | yes | 2 |
| Self-consistency | nine independent samples at temperature 0.7 | – | 9 in total |

### 3.2 Error vocabulary

The bank critic's vocabulary was distilled offline from 33 incorrect single-shot answers of the same model on six benchmarks unrelated to the evaluation set (GPQA-Diamond, MMLU-Pro, MATH-500, BFCL, BBH and AIME). Each error was abstracted into an answer-free description of the faulty operation and a check procedure, and the descriptions were merged across benchmarks into five archetypes: constraint-blind decimation, descriptor or label conflation, procedure truncation or omission, retrieval abort, and format or precision non-conformance. No item, answer or error from Humanity's Last Exam enters the vocabulary. The free critic differs from the bank critic in four textual places only: the vocabulary block, one line of the output format, one clause of the system prompt, and the fallback path (Appendix B).

### 3.3 Selection rules

We report three rules for loops. *Final* returns the last answer. *Settle* returns the answer of the last run of at least three identical answers and counts as incorrect when no such run exists. *Mode* returns the most frequent answer across rounds. For self-consistency, *vote* returns the most frequent answer among the samples. Answers are compared through a fixed normalization that depends on the answer type (option letter, integer, or normalized string). A round truncated at the token limit may contribute a vote when its answer can be recovered from the end of its reasoning, but a truncated winner is scored as incorrect.

Ties need care. For a loop, the natural rule is recency, returning the tied answer that occurred last, since later answers have survived more critique; we fixed this rule in the scoring code before any comparison. For exchangeable samples no tie rule carries information, and the two deterministic conventions happen to give 136 and 141 correct on our data. To avoid crediting the loops with a rule the baseline cannot use, all headline comparisons use a *symmetric convention*: ties are broken at random in both conditions and results are integrated over 300 paired draws. We report the recency figures alongside and quantify what recency contributes.

## 4 Experimental Setup

**Data.** We use 400 items from Humanity's Last Exam, of which 84 are multiple choice and 316 are open-form.

**Scoring.** Every answer of every round is scored once, by a protocol frozen before the conditions were compared. Answers are first matched exactly according to answer type. Unmatched answers are then examined by a model-based rescue of false negatives and by an independent judge from a different model family; disagreements are re-judged three times, and residual disputes are adjudicated by answer variant under the rule that the same substance receives the same verdict in every condition and round (Appendix C). Because the rescue step can only turn rejections into acceptances, scoring errors could inflate the ceiling of conditions that produce more distinct candidates; Section 8 returns to this.

**Statistics.** Conditions are compared on the same 400 items with exact McNemar tests. Ratios carry bootstrap intervals over items. Anything fitted is fitted on items with even index and evaluated on items with odd index.

**Analysis status.** The falsification test, the reassuring placebo, the read-out rules for the free critic and the perturbing placebo, and the acceptance criteria for evaluators were written down, with dated records, before the corresponding data were seen. The generation–selection decomposition as applied here, the one-step criterion, the conditional-on-count test, selective prediction and the verifier simulation are exploratory. The symmetric tie convention, the adaptive baseline, the accounting of the recency rule and the robustness analyses of Section 6 were added after internal review; each moves the conclusions in the conservative direction. Three selection rules were listed in advance without a designated primary rule; we report all three, and note that the main comparison survives a Bonferroni factor of three.

## 5 Results

### 5.1 Reaching and selecting

**Table 2.** Correct items out of 400. *Ceiling* is the number of items for which some candidate in the trajectory is correct. *Selected* uses mode for loops and vote for sampling, with ties broken at random (recency in parentheses). Tokens are in millions.

| Condition | Final | Settle | Selected | Ceiling | Solver tokens | Critic tokens |
|---|---|---|---|---|---|---|
| Greedy | 113 | – | 113 | 113 | 5.1 | 0 |
| Reassuring placebo | 142 | 136 | 145.9 (145) | 154 | 24.7 | 0 |
| Perturbing placebo | 135 | 127 | 142.1 (143) | 170 | 30.2 | 0 |
| Self-consistency | – | – | 137.4 | 190 | 51.3 | 0 |
| Adaptive self-consistency | – | – | 136.5 | – | 36.0 | 0 |
| Bank critic | 140 | 117 | 150.5 (154) | 191 | 37.1 | ≈ 20 |
| Free critic | 148 | 121 | **157.4 (159)** | **198** | 38.1 | ≈ 23 |

**The ceiling.** Both critics reach the correct answer far more often than the reassuring placebo (191 and 198 against 154; paired p = 8 × 10⁻⁸ and 4 × 10⁻⁹) and as often as nine-sample self-consistency (190; p = 0.55 for the bank critic). The two critics do not differ from each other (p = 0.42).

**The selected answer.** Under the symmetric convention the free critic selects 157.4 correct answers against 137.3 for self-consistency (median p = 0.004, significant in 97% of draws) and against 136.5 for adaptive self-consistency (p = 0.001). The bank critic points the same way but does not reach significance (150.7 against 137.3, p = 0.076); with its own recency rule against a randomized baseline it reaches p = 0.030, and we do not rest a claim on it. The reassuring placebo does not differ from self-consistency (p = 0.27). The recency rule contributes +3.5 items to the bank critic, +1.6 to the free critic and −0.9 to the placebo; the advantage of the critics lies in the counts.

**The last answer.** In every loop the last answer is worse than the majority (142 against 146, 135 against 142, 140 against 151, 148 against 157), and no loop's last answer differs significantly from self-consistency (p = 0.13 for the free critic).

**Cost.** The critics use about as many solver tokens as adaptive self-consistency (37–38 million against 36 million) and in addition pay for one critic call per round, which a replay of 50 calls puts at about 23 million tokens for the free critic, most of it hidden reasoning. Their total cost is therefore about 1.6 times that of adaptive self-consistency and above that of fixed self-consistency.

### 5.2 What in the critique matters

The two pre-specified controls give a clear picture (Table 3). The vocabulary does not matter: the free critic is at least as good as the bank critic on every measure and the differences are not significant. The read-out rule for this comparison classified the vocabulary as "not identifiable" if the free critic's ceiling was no more than five items below the bank critic's and their persistence intervals overlapped; both conditions hold.

Answer-specificity does matter. The perturbing placebo applies the same pressure, in the same format and at the same dose as the free critic, without reading the answer. It raises the ceiling over the reassuring placebo from 154 to 170 (p = 0.011), which shows that pressure alone makes the solver explore. It stops well short of the free critic's 198 (p = 0.0001), and on the selected answer it gains nothing over the reassuring placebo (142.1 against 146.0, p = 0.63) while the free critic gains about 15 items over it (p = 0.032, significant in 74% of draws). The read-out rule for this control classified content as effective if the perturbing placebo's ceiling fell at least 15 items below the free critic's at p < 0.05; it fell 28 below. Of the 44-item ceiling gain of the free critic over the reassuring placebo, roughly a third is attributable to answer-blind pressure and the rest to the critique reading the answer; of the selection gain, all of it.

**Table 3.** Paired comparisons for the two controls (discordant items in parentheses).

| Comparison | Ceiling | Selected answer |
|---|---|---|
| Free critic vs bank critic | 198 vs 191 (22/16), p = 0.42 | 159 vs 154 (27/23), p = 0.67 |
| Free critic vs perturbing placebo | 198 vs 170 (40/12), p = 0.0001 | 157.4 vs 142.1, p = 0.032 |
| Perturbing vs reassuring placebo | 170 vs 154 (26/10), p = 0.011 | 142.1 vs 146.0, p = 0.63 |
| Free critic vs reassuring placebo | 198 vs 154 (50/7), p = 4 × 10⁻⁹ | 157.4 vs 146.0, p = 0.14 |

One behavioural difference between the critics should be noted. Freed from the vocabulary, the free critic issued three suspicions in 86% of rounds, whereas the bank critic issued one in 57% and three in 12%. The two critics therefore differ in dose as well as in content, which is a further reason not to read the free critic's nominal lead as superiority; the perturbing placebo is matched to the free critic's dose.

The gain of the critics over self-consistency is larger on open-form items than on multiple-choice items (free critic: 124 against 101 open-form, 35 against 35 multiple choice), so it is not an artefact of voting over a small set of options.

### 5.3 The last answer and the self-correction literature

Let the repair rate be the probability that an item wrong at the greedy answer is correct after one revision, and the damage rate the probability that a correct item becomes wrong. One revision improves accuracy only if the ratio of repair to damage exceeds a/(1 − a), where a is the initial accuracy. Here a = 0.283 and the threshold is 0.39. The first revision repairs 17 items and damages 7 under the reassuring placebo (ratio 0.96), 38 and 19 under the bank critic (0.79), and 45 and 20 under the free critic (0.89). All are above the threshold, and the critics move two to three times as many items in each direction as the placebo. On a benchmark where the model starts at 80%, the same ratios would have to exceed 4, and a critique that moves items in both directions would lower accuracy. This is the regime in which the negative results on self-correction were obtained.

Two cautions apply. Rates pooled over all rounds are not a substitute for this one-step check, because items that settle early contribute few rounds and items that keep cycling contribute many. And the criterion does not show that critique corrects: the last answer improves as much under the reassuring placebo as under the critics. At low initial accuracy any revision with a nearly balanced profile helps a little, and the effect of the critique appears in the trajectory, in what is reached and how often it recurs.

### 5.4 Mechanism: activation, persistence and stopping

**Activation.** The critics widen the set of answers the solver visits: 3.5 and 3.7 distinct candidates per item, against 2.1 for the reassuring placebo and 2.7 for the perturbing placebo. The cumulative ceiling of the bank critic exceeds the placebo's final ceiling after two rounds. Self-consistency reaches the same ceiling with more candidates, which shows that non-specific variation suffices to reach an answer; the perturbing placebo shows that the solver responds to answer-blind suspicions far less than to suspicions that read its answer.

**Persistence.** The selector exploits the probability that the next answer repeats the current one, which differs according to whether the current answer is correct (Table 4). Correct answers are more persistent than incorrect ones in every condition. The reassuring placebo makes all answers persistent, so its count carries little information per round. The bank critic's asymmetry equals that of independent sampling, and the free critic's is higher, with overlapping intervals. What distinguishes the critics from sampling is therefore the sequential structure on which the stopping rule acts: repeats are consecutive, three in a row end the loop, and the trajectory has a direction. Stopping alone does not explain the gap, since adaptive self-consistency, which applies the same stopping rule to exchangeable samples, gains nothing over fixed sampling.

**Table 4.** Probability that the next answer repeats the current one, by correctness of the current answer (95% bootstrap intervals).

| Condition | Current correct | Current incorrect | Ratio |
|---|---|---|---|
| Self-consistency | 0.54 | 0.34 | 1.6 |
| Bank critic | 0.55 [0.49, 0.62] | 0.36 [0.32, 0.40] | 1.5 [1.3, 1.8] |
| Free critic | 0.57 [0.51, 0.64] | 0.30 [0.26, 0.33] | 1.9 [1.6, 2.2] |
| Perturbing placebo | 0.71 [0.66, 0.77] | 0.50 [0.46, 0.54] | 1.4 [1.3, 1.6] |
| Reassuring placebo | 0.79 | 0.63 | 1.25 |

**Normalization.** In the critic conditions 27% of transitions between two correct answers change the normalized form of the answer (16% under the placebo). Equivalent correct answers written differently split the vote, so the count understates the support for correct answers. Merging them would require an equivalence judge, which is the problem of Section 6 in another form.

### 5.5 The vote margin as an abstention signal

If items are ranked by the margin between the two most frequent answers and only the top fraction is answered, the critics yield higher accuracy at every coverage (Table 5). The area under the ROC curve of the margin as a predictor of a correct selection is 0.64 for both critics and for self-consistency and 0.59 for the reassuring placebo, with overlapping intervals. Adding judge verdicts to the margin does not improve it out of sample.

**Table 5.** Accuracy when only the most confident fraction of items is answered.

| Coverage | Reassuring placebo | Self-consistency | Bank critic | Free critic |
|---|---|---|---|---|
| 1.00 | 0.362 | 0.343 | 0.385 | 0.398 |
| 0.80 | 0.391 | 0.387 | 0.425 | 0.453 |
| 0.50 | 0.425 | 0.445 | 0.485 | 0.510 |
| 0.33 | 0.386 | 0.470 | 0.515 | 0.492 |

### 5.6 From ceiling to accuracy under external verification

The ceiling becomes accuracy when candidates can be verified. To see how the conditions would fare with an imperfect verifier, we simulate one on the recorded trajectories: it accepts each candidate independently with accuracy q, the most frequent accepted candidate is returned, and the majority is returned when nothing is accepted (Table 6). With independent errors, the critics' advantage over the reassuring placebo grows with q, from 4 to 37 items for the bank critic, and their advantage over self-consistency shrinks towards the difference in ceilings without changing sign. When the verifier is assumed weaker on items with more candidates and on items the greedy answer got wrong, the advantage over self-consistency no longer shrinks, because sampling carries the most candidates and suffers most from false acceptances. These are simulations under stated assumptions, and we draw one qualitative conclusion: trajectories produced under critique are at least as good a candidate pool as samples, and the less reliable the verification, the larger their advantage.

**Table 6.** Simulated correct items when a verifier of per-candidate accuracy q filters the candidates.

| Verifier errors | q | Reassuring placebo | Self-consistency | Bank critic | Free critic |
|---|---|---|---|---|---|
| independent | 0.5 | 135 | 126 | 139 | 146 |
| independent | 0.7 | 144 | 151 | 160 | 166 |
| independent | 0.9 | 151 | 177 | 182 | 187 |
| independent | 1.0 | 154 | 190 | 191 | 198 |
| correlated with difficulty | 0.7 | 140 | 135 | 148 | 154 |
| correlated with difficulty | 0.9 | 147 | 152 | 163 | 168 |

## 6 Can a Same-Model Evaluator Improve on the Count?

The bank critic reaches 191 items and its majority selects 154. This section asks whether the model itself can recover any of the remaining 37, using the bank critic's trajectories throughout.

### 6.1 Headroom

Of the 37 recoverable items, 11 are ties, 10 have a margin of one vote and 16 a larger margin. The trajectories contain 1,201 switches between two committed answers, of which 159 turn an incorrect answer into a correct one and 142 do the opposite. An oracle that undoes every harmful switch would reach 173 correct items, and one restricted to switches the solver explicitly attributes to the feedback would reach 165. Undoing all feedback-attributed switches without knowing which are harmful gives 149, a loss of five. Recovery therefore requires telling a warranted suspicion from an unwarranted one.

### 6.2 Judges, aggregation and acceptance criteria

An evaluator is a source of verdicts on switches, combined with the vote by a rule. We test three judge framings, all with the same model and without reference answers. *Judge-R* scores the new answer on three dimensions (disconnection from established steps, contradiction, and a locatable error) and votes to cut it when any score is high. *Judge-R+* additionally sees the question, must quote the step it objects to, and must name a class of falsifier. *Judge-C* judges the critique instead of the answer: given the question, the suspicion and the criticized answer, it decides whether the suspicion was warranted. Verdicts require agreement across two presentations in swapped order.

The aggregation rule adds to the logarithm of each candidate's count the log-likelihood ratios of the verdicts on the switches entering and leaving it, where a ratio compares the probability of a verdict on repairing and on damaging switches. Ratios are estimated on development items and frozen for test items; when all ratios equal one, the rule reduces to the majority. Before running the judges we fixed four criteria: accuracy on decisive switches, intervals of the likelihood ratios, the test-set comparison with the majority, and stability of the ratios across halves.

### 6.3 Results

**Table 7.** Same-model judges on the bank critic's trajectories. Decisive switches are those that change correctness. The majority selects 76 correct items on the test half and 78 on the development half.

| | Judge-R | Judge-R+ | Judge-C |
|---|---|---|---|
| Switches judged (of 1,201) | 1,185 | 1,041 | 1,201 |
| Accuracy on decisive switches | 0.58 | 0.60 | 0.66 |
| Likelihood-ratio intervals exclude 1 | no | yes | yes |
| Fitted on development, applied to test | 76 (+2, −2) | 73 (+3, −6) | 71 (+3, −8) |
| Fitted on test, applied to development | 73 (+5, −10) | 72 (+5, −11) | 77 (+8, −9) |
| Accuracy where the judge disagrees with the count | 18/36 = 0.50 [0.35, 0.65] | 53/116 = 0.46 [0.37, 0.55] | 32/66 = 0.49 [0.37, 0.60] |
| Best of 81 aggregation rules, in-sample | 154 | 156 | 155 |

No judge improves on the majority. Judging the critique is easier than judging the answer, and two of the three judges carry statistically detectable information at the level of single switches. That information does not survive aggregation in either direction of the split, and the reason is visible in the sixth row. A rule that uses only the counts, predicting that a switch is a repair when the new answer ends with at least as many votes as the old one, is as accurate on decisive switches as the judges are. Where a judge disagrees with this rule, which is the only place it can change the selection, its accuracy is 0.50, 0.46 and 0.49. The verdicts restate the count.

Two further checks support this reading. A logistic model over count features and all verdict features of Judge-C, fitted and evaluated on all 400 items, selects 150 correct answers, fewer than the majority. A sweep over 81 aggregation rules, varying where a verdict acts (on the boundary round, the whole run, or the whole candidate), the weights of the two verdict directions, and gating to low-margin items, gains at most two items in-sample and nothing when the best rule on one half is applied to the other.

Why an accuracy of 0.66 on single switches is insufficient follows from base rates. Overturning the majority is a repair on 37 of the 123 items with several candidates where it can be overturned. A judge with accuracy p on a switch therefore overturns correctly with precision 0.30p / (0.30p + 0.70(1 − p)), which is 45% at p = 0.66 and exceeds 50% only for p above 0.70. On the 56 tied items the count is silent and Judge-C does carry conditional information (17 of 26 disagreements correct), but this changes the selection on few items, and the recency rule alone already recovers 14 of the 23 ties whose tied set contains the correct answer.

### 6.4 Interpretation

Conditional on the vote count, none of the three same-model judges carried detectable information about which answer was correct. This is a statement about one model, one benchmark and three framings, with the power of 400 items; gains of a few items per judge are not excluded, and a judge that outperforms the count on these switches would refute it. The three framings are not independent evidence, since they share a model and each correlates with the count, which is the finding. The headroom is real, and recovering it requires information that is not a function of the trajectory the solver has already produced: a stronger model, external verification, or a critic that withholds unwarranted suspicions in the first place.

## 7 Discussion

The results recast what a self-critique loop is for. As a corrector it performs as the literature predicts: its last answer is no better than a placebo's. As a sampler it has two properties that temperature sampling lacks. Its variation is directed at the current answer, which is what raises the ceiling beyond what answer-blind pressure achieves, and its samples are ordered, which lets a count over rounds act as a selector and as an abstention signal without any additional model call.

The two controls sharpen a claim that is often left vague. The benefit does not come from telling the model what kinds of error exist, and a vocabulary distilled from the model's own past errors adds nothing identifiable to a critic that is free to name the shortcoming itself. The benefit comes from the critique being about this answer. This also explains the cost: the critic's reading of the answer is most of the additional tokens.

The negative result on evaluation is the counterpart of the positive result on selection. The count works because correct answers recur more than incorrect ones, and a judge from the same model sees the same evidence that made the solver return to an answer. Its verdicts are therefore informative in isolation and redundant given the count. Progress on selection in this setting should be sought in information the trajectory does not contain.

## 8 Limitations

The study uses one model and one benchmark, and none of the roles was tuned; the results establish that the effects exist under these conditions and do not establish that they are general. The critique's most secure effect is on the ceiling. On the selected answer it is significant against the dose-matched perturbing placebo and against self-consistency, but not against the reassuring placebo, and iteration with a count already accounts for most of the gain over the greedy answer. The critics cost more than either sampling baseline. Scoring free-form answers required a model-based judging tier; its rescue step can only add acceptances, so scoring errors would favour conditions with more candidates, and the adjudication record is released so that this can be checked. The perturbing placebo controls for pressure, dose and format but not for the fluency or length of the feedback. The answer normalization splits equivalent correct answers. The free critic and the perturbing placebo were run through a different service endpoint for the same model weights than the other conditions; per-round reasoning length, truncation rate and commit rate agree across endpoints. Pre-specification was recorded internally with dated documents and was not registered externally. Finally, 400 items resolve paired differences of roughly twenty items; smaller effects, including small gains from same-model judges, remain undetermined.

## 9 Conclusion

On an expert-level benchmark, a self-critique loop read as a corrector does what the literature reports: its last answer improves no more than a placebo's. Read as a sampler, a critic that never stays silent and that reads the answer it criticizes reaches the correct answer on 44 more items than a reassuring placebo and 28 more than answer-blind pressure of the same dose, and a parameter-free count over its trajectory selects the correct answer more often than fixed or adaptive self-consistency. A vocabulary of the model's own past errors adds nothing identifiable to this. The count is also where same-model selection ends on this benchmark: what the model says about its own transitions adds no detectable information to how often it returned to an answer. Where answers can be verified, the answers that are reached but not selected are the gain to be collected; where they cannot, the count serves as both selector and abstention signal.

## References

Aggarwal, P., Madaan, A., Yang, Y., and Mausam (2023). Let's sample step by step: Adaptive-consistency for efficient reasoning and coding with LLMs. *EMNLP*.

Chen, M., Tworek, J., Jun, H., et al. (2021). Evaluating large language models trained on code. *arXiv:2107.03374*.

Chen, X., Aksitov, R., Alon, U., et al. (2023). Universal self-consistency for large language model generation. *arXiv:2311.17311*.

Huang, J., Chen, X., Mishra, S., et al. (2024). Large language models cannot self-correct reasoning yet. *ICLR*.

Kamoi, R., Zhang, Y., Zhang, N., Han, J., and Zhang, R. (2024). When can LLMs actually correct their own mistakes? A critical survey of self-correction of LLMs. *TACL*.

Lightman, H., Kosaraju, V., Burda, Y., et al. (2023). Let's verify step by step. *arXiv:2305.20050*.

Madaan, A., Tandon, N., Gupta, P., et al. (2023). Self-Refine: Iterative refinement with self-feedback. *NeurIPS*.

Panickssery, A., Bowman, S. R., and Feng, S. (2024). LLM evaluators recognize and favor their own generations. *NeurIPS*.

Phan, L., Gatti, A., Han, Z., et al. (2025). Humanity's Last Exam. *arXiv:2501.14249*.

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., and Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. *NeurIPS*.

Wang, X., Wei, J., Schuurmans, D., et al. (2023). Self-consistency improves chain of thought reasoning in language models. *ICLR*.

Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *NeurIPS Datasets and Benchmarks*.

## Appendix

**A. Error vocabulary.** Source items by benchmark, the three distillation levels, the five archetype entries with their definitions and check procedures, and the audit confirming that no entry contains a reference answer or an item identifier.

**B. Prompts and runtime.** Solver, critic and judge prompts; the four textual differences between the bank critic and the free critic; the generic sentences of the perturbing placebo; token budgets and stopping constants; service endpoints and their alignment statistics.

**C. Scoring protocol.** The three tiers, the truncation rule, the answer normalization and tie rules, and the table of adjudicated answer variants with rationales.

**D. Evaluator details.** Per-judge confusion tables on development, test and all items; likelihood ratios with intervals; a three-role Bayesian aggregator; the sweep of aggregation rules; a contrast of 26 gold-free trajectory features between repairing and damaging switches (areas under the curve between 0.43 and 0.59, none stable across halves); and a probe showing that critic suspicions concern the derivation and not the question text.

**E. Pre-specified rules.** The falsification test, the read-out rules for the free critic and the perturbing placebo, and the evaluator acceptance criteria, with dates.

**F. Additional results.** Results by answer form for every condition and rule; ceiling by round; selective-prediction curves; verifier simulations with asymmetric error rates.
