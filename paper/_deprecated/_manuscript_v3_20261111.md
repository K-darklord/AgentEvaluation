# Revision Loops as Samplers: Self-Critique Raises the Reachable Ceiling, and Same-Model Judges Add Nothing Detectable to the Vote Count

## Abstract

Revision loops, in which a model answers, is critiqued, and answers again, are usually judged by their last answer, and by that measure intrinsic self-correction is unreliable. We study such loops as samplers of answers. On 400 items from Humanity's Last Exam, with one model as solver and critic, a critic that must name a specific suspicion and a concrete check in every round raises the reachable ceiling, the number of items whose trajectory contains the correct answer, from 153 under a reassuring placebo to 192–198 (p < 10⁻⁶). The gain holds when the number of candidates is matched and when only exact-match scoring is counted. A parameter-free majority over rounds selects the correct answer on 157 items against 137 for nine-sample self-consistency (difference 20.7, 95% interval [9.0, 32.4]); a difference of 13.0 [2.1, 23.8] remains under a conservative bound that pools all answers scored correct for an item before voting. The loop uses about 1.7 times the tokens of a sampling baseline matched in solver tokens. Two pre-specified controls probe the critique. A vocabulary distilled from the model's past errors adds nothing identifiable. A dose-matched placebo of templated suspicions that reads neither the question nor the answer reaches 171 items instead of 198 (p = 0.0002); its selected answer is 11 items lower, a difference that is not significant (p = 0.07). Generated critique therefore reaches more than pressure alone, and the control does not separate reading the answer from generating the feedback. Last answers improve no more under critique than under a placebo. Finally, no same-model judge of the loop's transitions adds detectable information to the vote count: three framings are at chance where they disagree with it (0.46–0.50), and likelihood-weighted aggregation does not improve on it out of sample.

## 1 Introduction

A language model that answers a question, receives a critique, and answers again can be evaluated in two ways. Read as a *corrector*, the loop is judged by whether its last answer is better than its first. Read as a *sampler*, it is judged by the set of answers it visits. The corrector reading has been tested extensively and the result is discouraging: without external information, intrinsic self-correction does not reliably improve reasoning accuracy and often degrades it (Huang et al., 2024; Kamoi et al., 2024). This paper examines the sampler reading.

The sampler reading rests on a decomposition that applies to any test-time method. Accuracy is the product of how often the correct answer is *reached* and how often it is then *selected*. The first quantity is coverage in the sense of Brown et al. (2024), the fraction of problems solved by any sample; we call its count the reachable ceiling. Sampling with a majority vote (Wang et al., 2023) reaches a high ceiling and selects poorly: the correct answer is often in the pool and is outvoted. A revision loop produces an ordered trajectory instead of an exchangeable pool, and the question is whether that trajectory reaches as much and is easier to select from.

We ask three questions about a gold-free, training-free revision loop in which one model plays both solver and critic. First, does the loop reach the correct answer more often than a loop with content-free feedback? Second, does a simple rule select the correct answer more often than self-consistency on the same items? Third, can a same-model evaluator of the loop's own transitions improve on that rule?

On 400 items from Humanity's Last Exam (Phan et al., 2025) the answers are yes, a qualified yes, and no. A critic that must produce a specific suspicion and a concrete check every round raises the reachable ceiling from 153 to 198 items, and the gain survives matching the number of candidates and restricting scoring to exact matches. A majority over the rounds of the trajectory selects the correct answer on 157 items against 137 for self-consistency. Independent samples spread correct answers over more distinct forms than a loop does, which may split their vote; under a conservative bound that pools all answers scored correct for an item, a difference of 13 items remains. Against a reassuring placebo, which is cheaper, the difference in the selected answer is 12 items and is not significant, so iteration with a count accounts for much of the gain and critique for the rest.

Two controls, both specified before their data were collected, probe what in the critique matters. Removing a vocabulary of error archetypes distilled from the model's own past mistakes changes nothing measurable. Replacing the critique with the same number of templated suspicions that read neither the question nor the answer removes most of the effect on the ceiling, which falls to 171, and leaves the selected answer at the level of the reassuring placebo. Pressure alone is therefore insufficient to reach what generated critique reaches. The control does not tell us whether the critique must read the answer or only the question, and we state the conclusion at that resolution.

The third question has a negative answer, and we give it a structure. An oracle that undoes every harmful switch in the trajectories would recover 19 more items, so the information exists in principle. Three same-model judges with different framings fail to extract it: wherever a judge disagrees with the vote count, it is right half of the time. Aggregating verdicts with likelihood ratios fitted on half of the items never improves on the count on the other half, and a sweep of 81 aggregation rules gains at most two items in-sample.

Our contributions are as follows.

1. An application of the coverage–selection decomposition to revision loops, with two placebo controls and a dose-matched design that separate iteration, pressure and generated critique.
2. Evidence that self-critique is a competitive sampler: it matches the ceiling of nine-sample self-consistency with fewer distinct candidates, the gain over placebos holds at matched candidate counts, and a parameter-free majority over its trajectory selects more correct answers than fixed or adaptive self-consistency, at a higher total cost and with part of the margin attributable to vote splitting in the baseline.
3. A null result for an error vocabulary distilled from the model's past mistakes, and a positive result on the ceiling for generated critique against answer-blind pressure of the same dose.
4. A negative result on same-model evaluation: conditional on the vote count, three judge framings carry no detectable information about which transition was correct.
5. A frozen and audited scoring protocol for free-form answers on Humanity's Last Exam, released with all trajectories, judge verdicts and analysis code.

## 2 Related Work

**Sampling, coverage and voting.** Self-consistency (Wang et al., 2023) draws several reasoning paths and returns the most frequent answer. Adaptive variants stop sampling once the vote is settled and recover most of the accuracy at lower cost (Aggarwal et al., 2023); universal self-consistency replaces the vote with a model-based selection for free-form answers (Chen et al., 2023). Brown et al. (2024) separate coverage, the fraction of problems solved by any sample, from the ability to pick the solving sample, and show that coverage keeps growing with the number of samples while majority voting and reward models plateau where no automatic verifier exists. We adopt this decomposition, following the pass@k view of sampling (Chen et al., 2021), and apply it to trajectories produced by revision instead of independent draws.

**Self-correction.** Self-Refine (Madaan et al., 2023) and Reflexion (Shinn et al., 2023) iterate generation and feedback from the same model. Huang et al. (2024) show that the gains reported for intrinsic self-correction largely vanish when no oracle information leaks into the loop, and Kamoi et al. (2024) survey the conditions under which self-correction helps. Yang et al. (2025) decompose accuracy after one correction step into the rate of keeping correct answers and the rate of fixing incorrect ones; the criterion we use in Section 5.3 is a rearrangement of their identity. Closest to our positive result, Bilal et al. (2026) refine each of eight sampled rollouts with self-critique and vote over the refined answers, reporting gains over majority voting on mathematics benchmarks with small open models at a fixed number of rollouts. Our study differs in what it controls: a single trajectory is voted over its own rounds, the critique is compared with two placebos, the comparison with sampling is reported under token accounting, and the result is separated into what is reached and what is selected.

**Verifiers and judges.** Process reward models and trained verifiers (Lightman et al., 2023) supply the external signal that self-correction lacks, at the cost of training data with positive labels; we exclude them by design. Language models used as judges are imperfect and prefer their own outputs (Zheng et al., 2023; Panickssery et al., 2024). Zhao et al. (2025) report that sampling many responses and verifying them with the same model scales well for a frontier model, in part because verification improves with the size of the pool and with direct comparison of responses. Our third question concerns a narrower object, verdicts on a model's own answer transitions within one trajectory, and asks what such verdicts add once the vote count is known; Section 6.4 discusses the difference in setting.

## 3 Method

### 3.1 Loop and conditions

A solver answers each question greedily (temperature 0). In every subsequent round it receives its previous answer together with a feedback message and answers again; it is told to keep its answer if it believes the answer is correct. A loop stops after three identical consecutive answers or after ten rounds. All conditions share the solver's greedy first answer, so they differ only in what follows it. The solver and the critic are the same model, deepseek-v4-flash, with a reasoning budget of 16,384 tokens and a visible-output margin of 8,192 tokens per call.

We compare the greedy answer with five conditions (Table 1) and one baseline simulated from recorded samples. The *reassuring placebo* returns a fixed sentence stating that no error direction was found. The *free critic* is a separate call to the same model that reads the question, the current answer and the tail of the solver's reasoning, and must return between one and three suspicions, each with a concrete check the solver can carry out without the reference answer; it may not state a probability, name an answer, or remain silent. The *bank critic* is identical except that each suspicion must be drawn from a vocabulary of five error archetypes (Section 3.2). The *perturbing placebo* issues the same number of suspicions per round as the free critic, with archetype names drawn at random and rendered through fixed generic sentences in the critic's exact output format, without reading the question, the answer or the reasoning; it involves no model call. *Self-consistency* draws nine independent samples at temperature 0.7. *Adaptive self-consistency* consumes the same samples in random order and stops when an answer has three votes.

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

Ties need care. For a loop, the natural rule is recency, returning the tied answer that occurred last, since later answers have survived more critique; we fixed this rule in the scoring code before any comparison. For exchangeable samples no tie rule carries information, and the two deterministic conventions happen to give 136 and 141 correct on our data. To avoid crediting the loops with a rule the baseline cannot use, all headline comparisons use a *symmetric convention*: ties are broken uniformly at random in every condition, and each item receives its expected score, which is computed exactly and can be fractional. We report the recency figures alongside and quantify what recency contributes.

## 4 Experimental Setup

**Data.** We use 400 items from Humanity's Last Exam, of which 84 are multiple choice and 316 are open-form. Trajectories in which any call failed at the interface were discarded and rerun in full, in every condition (29 items for the perturbing placebo and between one and four for the others); an error message never counts as an answer.

**Scoring.** Every answer of every round is scored once, by a protocol frozen before the conditions were compared. Answers are first matched exactly according to answer type. Unmatched answers are then examined by a model-based rescue of false negatives and by an independent judge from a different model family; disagreements are re-judged three times, and residual disputes are adjudicated by answer variant under the rule that the same substance receives the same verdict in every condition and round (Appendix C). Because the rescue step can only turn rejections into acceptances, scoring errors could inflate the ceiling of conditions that produce more distinct candidates; Section 8 returns to this.

**Statistics.** Conditions are compared on the same 400 items. Ceilings and last answers are binary and are compared with exact McNemar tests. Selected answers are compared through the per-item expected scores with a paired sign-flip permutation test (10,000 permutations), and differences carry 95% bootstrap intervals over items. Ratios carry bootstrap intervals over items. P-values are unadjusted. Anything fitted is fitted on items with even index and evaluated on items with odd index.

**Analysis status.** The falsification test was fixed for the bank critic, which was the method under study at the time; the free critic and the perturbing placebo were introduced afterwards as controls, each with a read-out rule written before its data were seen. The falsification test, the reassuring placebo, the read-out rules for the free critic and the perturbing placebo, and the acceptance criteria for evaluators were written down, with dated records, before the corresponding data were seen. The generation–selection decomposition as applied here, the one-step criterion, the conditional-on-count test, selective prediction and the verifier simulation are exploratory. The symmetric tie convention, the adaptive baseline, the accounting of the recency rule, the matched-candidate and exact-match ceilings, the merging of equivalent answers and the robustness analyses of Section 6 were added after review; each tests the conclusions against an alternative explanation. Three selection rules were listed in advance without a designated primary rule; we report all three.

## 5 Results

### 5.1 Reaching and selecting

**Table 2.** Correct items out of 400. *Ceiling* is the number of items for which some candidate in the trajectory is correct. *Selected* uses mode for loops and vote for sampling and is the expected score under random ties, with the recency rule in parentheses. Tokens are in millions; critic tokens are extrapolated from replays of 50 calls per critic.

| Condition | Final | Settle | Selected | Ceiling | Solver tokens | Critic tokens |
|---|---|---|---|---|---|---|
| Greedy | 113 | – | 113 | 113 | 5.1 | 0 |
| Reassuring placebo | 141 | 135 | 145.0 (144) | 153 | 24.6 | 0 |
| Perturbing placebo | 142 | 134 | 146.1 (147) | 171 | 31.8 | 0 |
| Self-consistency | – | – | 136.7 | 190 | 51.4 | 0 |
| Adaptive self-consistency | – | – | 135.8 | – | 35.5 | 0 |
| Bank critic | 140 | 117 | 150.9 (154) | 192 | 37.1 | ≈ 29 |
| Free critic | 148 | 121 | **157.4 (159)** | **198** | 38.1 | ≈ 23 |

**The ceiling.** Both critics reach the correct answer far more often than the reassuring placebo (192 and 198 against 153; discordant items 47/8 and 52/7, p = 8 × 10⁻⁸ and 1 × 10⁻⁹) and as often as nine-sample self-consistency (190; 24/22 for the bank critic and 29/21 for the free critic, p = 0.88 and 0.32). The two critics do not differ from each other (23/17, p = 0.43).

A ceiling is a maximum over candidates, and the conditions differ in how many distinct candidates they produce (Section 5.4), so we repeat the comparison with the pool size held fixed and with the model-based scoring tier removed (Table 3). Taking only the first k distinct candidates of every trajectory, the free critic stays ahead of the perturbing placebo at k = 2, 3 and 4 (33/9, 35/11 and 37/10; p ≤ 0.0005) and ahead of the reassuring placebo by a wider margin. Counting only answers accepted by exact matching lowers every ceiling and preserves the order (free critic against perturbing placebo 31/11, p = 0.003; against reassuring placebo 38/7, p < 10⁻⁵). The advantage arises at the first revision. When the first candidate is wrong, the critics produce a second candidate more often, and that second candidate is correct on 48 of 204 items for the free critic (0.24) and 43 of 198 for the bank critic (0.22), against 26 of 171 for the perturbing placebo (0.15) and 23 of 135 for the reassuring placebo (0.17). Later candidates are correct at similar and low rates in all conditions.

**Table 3.** Robustness of the ceiling: first k distinct candidates per trajectory, and exact-match scoring only.

| | Reassuring placebo | Perturbing placebo | Self-consistency | Bank critic | Free critic |
|---|---|---|---|---|---|
| k = 2 | 141 | 148 | 169 | 166 | 172 |
| k = 3 | 150 | 157 | 178 | 177 | 181 |
| k = 4 | 151 | 164 | 183 | 180 | 191 |
| all candidates | 153 | 171 | 190 | 192 | 198 |
| all candidates, exact match only | 91 | 102 | 120 | 115 | 122 |

**The selected answer.** The free critic selects 157.4 correct answers against 136.7 for self-consistency (difference 20.7, 95% interval [9.0, 32.4], p < 0.001) and 135.8 for adaptive self-consistency (21.5 [10.0, 33.6], p < 0.001). The bank critic, for which the falsification test was written, selects 150.9 (14.1 [2.5, 26.7], p = 0.026). Neither placebo differs from self-consistency (reassuring 8.2 [−4.0, 21.1], p = 0.20; perturbing 9.4 [−2.4, 20.7], p = 0.11). The recency rule contributes +3.1 items to the bank critic, +1.6 to the free critic and −1.0 to the reassuring placebo; the advantage of the critics lies in the counts.

**Vote splitting.** The gain over self-consistency is confined to open-form items; on multiple-choice items all conditions are within three items of one another. Open-form answers can be written in several ways, and independent samples are more exposed to this than a loop in which the solver sees its previous answer: 24% of correct samples in self-consistency fall outside the item's most common correct form, against 20% of correct rounds under the critics and 11% under the reassuring placebo. Two analyses bracket the effect. The first is reference-free: stripping display wrappers, boxing and spacing macros from open-form answers before voting, for correct and incorrect answers alike, merges few candidates and leaves the comparison unchanged (free critic 159.1 against 137.5 for self-consistency; 21.6 [10.0, 32.6], p < 0.001). An earlier canonicalization of purely numeric answers merged candidates on four items. Formatting therefore explains little, and what remains are re-expressions that only a semantic judgement can equate. The second analysis is a conservative bound: we pool all answers scored correct for an item into one candidate before voting, in every condition (Table 4). This uses the reference answers, leaves incorrect answers split, and also pools answers that differ in substance and were each accepted by the scorer, so it overstates splitting and is a diagnostic, not a selection rule. Under this bound self-consistency gains 13 items and the free critic 5.5; the difference between them falls to 13.0 [2.1, 23.8] (p = 0.019), and 14.7 [3.9, 25.1] against the adaptive variant (p = 0.007). For the bank critic the difference falls to 10.0 [−0.9, 20.9] (p = 0.08). The pre-specified test therefore passes nominally and does not survive the bound, and the stronger evidence comes from the free critic, which was introduced as a control. Under the bound, both critics exceed the reassuring placebo (free critic 17.4 [3.6, 30.3], p = 0.011; bank critic 14.4 [1.7, 26.4], p = 0.019), which they do not without it (12.4 [−1.6, 25.6], p = 0.08, and 5.9, p = 0.34): critique scatters correct answers over more forms than reassurance does, and the plain count understates its effect.

**Table 4.** Selected answer under the plain vote and under the bound that pools all answers scored correct for an item into one candidate.

| | Reassuring placebo | Perturbing placebo | Self-consistency | Adaptive self-consistency | Bank critic | Free critic |
|---|---|---|---|---|---|---|
| Plain vote | 145.0 | 146.1 | 136.7 | 135.8 | 150.9 | 157.4 |
| Correct answers pooled | 145.5 | 149.1 | 149.8 | 148.1 | 159.9 | 162.9 |

**The other rules.** The last answer is worse than the majority in every loop (141 against 145, 142 against 146, 140 against 151, 148 against 157), and no loop's last answer differs significantly from self-consistency (free critic 11.3 [−2.1, 24.2], p = 0.10). Settle, which counts an item as incorrect when its trajectory contains no run of three identical answers, falls below self-consistency for both critics (117 and 121).

**Cost.** The critics use about as many solver tokens as adaptive self-consistency (37–38 million against 36 million) and in addition pay for one critic call per round, which the replays put at about 23 million tokens for the free critic and 29 million for the bank critic, most of it hidden reasoning. Their totals are about 1.7 and 1.9 times that of adaptive self-consistency, 1.2 and 1.3 times that of nine-sample self-consistency, and 2.5 and 2.7 times that of the reassuring placebo. We did not run self-consistency with the eleven samples that would match the free critic's total.

### 5.2 What in the critique matters

**The vocabulary.** The free critic is at least as good as the bank critic on the ceiling and on every selection rule, and the differences are not significant (Table 5). The read-out rule for this comparison classified the vocabulary as "not identifiable" if the free critic's ceiling was no more than five items below the bank critic's and their persistence intervals overlapped; both conditions hold. The two critics also differ in dose: freed from the vocabulary, the free critic issued three suspicions in 86% of rounds, whereas the bank critic issued one in 57% and three in 12%. This is a further reason not to read the free critic's nominal lead as superiority. The perturbing placebo is matched to the free critic's dose, so the comparison below is not affected.

**Pressure against generated critique.** The perturbing placebo applies the same pressure, in the same format and at the same dose as the free critic, without reading the question, the answer or the reasoning. It raises the ceiling over the reassuring placebo from 153 to 171 (p = 0.005), which shows that pressure alone makes the solver explore. It stops well short of the free critic's 198 (39/12, p = 0.0002), and the gap persists at matched candidate counts and under exact-match scoring (Table 3). The read-out rule for this control classified content as effective if the perturbing placebo's ceiling fell at least 15 items below the free critic's at p < 0.05; it fell 27 below. Of the 45-item ceiling gain of the free critic over the reassuring placebo, 18 items are attributable to answer-blind pressure and 27 to generated critique.

On the selected answer the evidence is weaker. The perturbing placebo does not differ from the reassuring placebo (1.2 [−10.1, 12.5], p = 0.84). The free critic selects 11.3 more correct answers than the perturbing placebo, with an interval that includes zero ([−0.8, 23.7], p = 0.07); under the pooling bound of Section 5.1 the difference is 13.8 [2.1, 25.0] (p = 0.016). The extra candidates that pressure produces do not become votes for the correct answer, and whether generated critique converts more of them is suggested and not established.

**What the control does not isolate.** The free critic differs from the perturbing placebo in three respects: it reads the question, it reads the answer and the end of the solver's reasoning, and it is generated by the model with a reasoning budget of its own. A critic with that budget may partly re-solve the problem and pass its solution to the solver through the check it proposes, in which case it would act as a second solver more than as a reader of the first. Two observations on the 301 switches of the bank critic that change correctness speak against this account without excluding it. The critic's text contains the solver's new answer in none of the 129 repairing switches with a numeric or free-text answer and in 2 of the 112 damaging ones, so an answer is not passed on literally; what the solver receives is a check to carry out. And repairing and damaging switches are almost equally frequent (159 and 142), whereas a critic that had solved the problem would be expected to repair far more often than it damages. A critic that reads the question and is denied the answer would separate the accounts directly, and we have not run it. We therefore attribute the effect to generated critique of this question and this answer, and leave open which of the two inputs carries it.

**Table 5.** Paired comparisons for the controls. Ceiling: totals, discordant items in parentheses, exact McNemar. Selected answer: difference in expected score, 95% interval, permutation test.

| Comparison | Ceiling | Selected answer |
|---|---|---|
| Free critic vs bank critic | 198 vs 192 (23/17), p = 0.43 | +6.5 [−6.4, 18.9], p = 0.32 |
| Free critic vs perturbing placebo | 198 vs 171 (39/12), p = 0.0002 | +11.3 [−0.8, 23.7], p = 0.07 |
| Perturbing vs reassuring placebo | 171 vs 153 (28/10), p = 0.005 | +1.2 [−10.1, 12.5], p = 0.84 |
| Free critic vs reassuring placebo | 198 vs 153 (52/7), p = 1 × 10⁻⁹ | +12.4 [−1.6, 25.6], p = 0.08 |
| Bank critic vs reassuring placebo | 192 vs 153 (47/8), p = 8 × 10⁻⁸ | +5.9 [−6.8, 18.5], p = 0.34 |

### 5.3 The last answer and the self-correction literature

Let the repair rate be the probability that an item wrong at the greedy answer is correct after one revision, and the damage rate the probability that a correct item becomes wrong. One revision improves accuracy only if the ratio of repair to damage exceeds a/(1 − a), where a is the initial accuracy; this is the identity of Yang et al. (2025) solved for the break-even point. Here a = 0.283 and the threshold is 0.39. The first revision repairs 17 items and damages 7 under the reassuring placebo (ratio 0.96), 38 and 19 under the bank critic (0.79), and 45 and 20 under the free critic (0.89). All are above the threshold, and the critics move two to three times as many items in each direction as the placebo. On a benchmark where the model starts at 80%, the same ratios would have to exceed 4, and a critique that moves items in both directions would lower accuracy. This is the regime in which the negative results on self-correction were obtained.

Two cautions apply. Rates pooled over all rounds are not a substitute for this one-step check, because items that settle early contribute few rounds and items that keep cycling contribute many. And the criterion does not show that critique corrects: the last answer under the critics does not differ from the last answer under the reassuring placebo (140 and 148 against 141; 27/28 and 29/22, p = 1.0 and 0.40). At low initial accuracy any revision with a nearly balanced profile helps a little, and the effect of the critique appears in the trajectory, in what is reached and how often it recurs.

### 5.4 Mechanism: activation, persistence and stopping

**Activation.** The critics widen the set of answers the solver visits: 3.5 and 3.7 distinct candidates per item, against 2.1 for the reassuring placebo and 2.7 for the perturbing placebo. The cumulative ceiling of the bank critic exceeds the placebo's final ceiling after two rounds. Self-consistency reaches the same ceiling with more candidates, which shows that non-specific variation suffices to reach an answer; the perturbing placebo shows that the solver responds to answer-blind suspicions far less than to suspicions that read its answer.

**Persistence.** The selector exploits the probability that the next answer repeats the current one, which differs according to whether the current answer is correct (Table 6). Correct answers are more persistent than incorrect ones in every condition. The reassuring placebo makes all answers persistent, so its count carries little information per round. The bank critic's asymmetry equals that of independent sampling, and the free critic's is higher, with overlapping intervals. What distinguishes the critics from sampling is therefore the sequential structure on which the stopping rule acts: repeats are consecutive, three in a row end the loop, and the trajectory has a direction. Stopping alone does not explain the gap, since adaptive self-consistency, which stops exchangeable samples once an answer has three votes, gains nothing over fixed sampling.

**Table 6.** Probability that the next answer repeats the current one, by correctness of the current answer, among rounds with a committed answer (for self-consistency, over ordered pairs of samples); 95% bootstrap intervals over items.

| Condition | Current correct | Current incorrect | Ratio |
|---|---|---|---|
| Self-consistency | 0.50 [0.44, 0.56] | 0.28 [0.24, 0.32] | 1.8 [1.5, 2.1] |
| Bank critic | 0.52 [0.46, 0.58] | 0.30 [0.27, 0.33] | 1.7 [1.5, 2.0] |
| Free critic | 0.53 [0.48, 0.60] | 0.25 [0.22, 0.28] | 2.1 [1.8, 2.5] |
| Perturbing placebo | 0.69 [0.64, 0.74] | 0.41 [0.38, 0.45] | 1.7 [1.5, 1.9] |
| Reassuring placebo | 0.77 [0.71, 0.83] | 0.54 [0.50, 0.59] | 1.4 [1.3, 1.6] |

**Normalization.** In the critic conditions 27% of transitions between two correct answers change the normalized form of the answer (16% under the placebo). Equivalent correct answers written differently split the vote, so the count understates the support for correct answers. Merging them would require an equivalence judge, which is the problem of Section 6 in another form.

### 5.5 The vote margin as an abstention signal

If items are ranked by the margin between the two most frequent answers and only the top fraction is answered, the critics yield higher accuracy than both baselines at every coverage (Table 7). The curves are not monotone at low coverage: the free critic falls from 0.510 at one half to 0.492 at one third, where the bank critic is ahead. The area under the ROC curve of the margin as a predictor of a correct selection is 0.64 for both critics and for self-consistency and 0.59 for the reassuring placebo, with overlapping intervals. Adding judge verdicts to the margin does not improve it out of sample.

**Table 7.** Accuracy when only the most confident fraction of items is answered (ties by recency for loops).

| Coverage | Reassuring placebo | Self-consistency | Bank critic | Free critic |
|---|---|---|---|---|
| 1.00 | 0.360 | 0.342 | 0.385 | 0.398 |
| 0.80 | 0.391 | 0.387 | 0.425 | 0.453 |
| 0.50 | 0.425 | 0.445 | 0.485 | 0.510 |
| 0.33 | 0.386 | 0.470 | 0.515 | 0.492 |

### 5.6 From ceiling to accuracy under external verification

The ceiling becomes accuracy when candidates can be verified. To see how the conditions would fare with an imperfect verifier, we simulate one on the recorded trajectories: it accepts each candidate independently with accuracy q, the most frequent accepted candidate is returned, and the majority is returned when nothing is accepted (Table 8). With independent errors, the critics' advantage over the reassuring placebo grows with q, from 4 items at q = 0.5 to 31 at q = 0.9 for the bank critic, and their advantage over self-consistency shrinks towards the difference in ceilings without changing sign. When the verifier is assumed weaker on items with more candidates and on items the greedy answer got wrong, the advantage over self-consistency no longer shrinks, because sampling carries the most candidates and suffers most from false acceptances. These are simulations under stated assumptions, and we draw one qualitative conclusion: trajectories produced under critique are at least as good a candidate pool as samples, and the less reliable the verification, the larger their advantage.

**Table 8.** Simulated correct items when a verifier of per-candidate accuracy q filters the candidates.

| Verifier errors | q | Reassuring placebo | Self-consistency | Bank critic | Free critic |
|---|---|---|---|---|---|
| independent | 0.5 | 135 | 126 | 139 | 145 |
| independent | 0.7 | 143 | 152 | 161 | 166 |
| independent | 0.9 | 150 | 177 | 181 | 187 |
| correlated with difficulty | 0.7 | 140 | 135 | 147 | 154 |
| correlated with difficulty | 0.9 | 146 | 153 | 164 | 169 |

## 6 Can a Same-Model Evaluator Improve on the Count?

This section asks whether the model itself can recover any of the items the bank critic reaches and its majority does not select, using the bank critic's trajectories throughout. The analysis was run on the trajectories as first recorded; three of them were later rerun after interface failures (Section 4), so the counts here are 191 reached and 154 selected, one item below Table 2.

### 6.1 Headroom

Of the 37 recoverable items, 11 are ties, 10 have a margin of one vote and 16 a larger margin. The trajectories contain 1,201 switches between two committed answers, of which 159 turn an incorrect answer into a correct one and 142 do the opposite. An oracle that undoes every harmful switch would reach 173 correct items, and one restricted to switches the solver explicitly attributes to the feedback would reach 165. Undoing all feedback-attributed switches without knowing which are harmful gives 149, a loss of five. Recovery therefore requires telling a warranted suspicion from an unwarranted one.

### 6.2 Judges, aggregation and acceptance criteria

An evaluator is a source of verdicts on switches, combined with the vote by a rule. We test three judge framings, all with the same model and without reference answers. *Judge-R* scores the new answer on three dimensions (disconnection from established steps, contradiction, and a locatable error) and votes to cut it when any score is high. *Judge-R+* additionally sees the question, must quote the step it objects to, and must name a class of falsifier. *Judge-C* judges the critique instead of the answer: given the question, the suspicion and the criticized answer, it decides whether the suspicion was warranted. Verdicts require agreement across two presentations in swapped order.

The aggregation rule adds to the logarithm of each candidate's count the log-likelihood ratios of the verdicts on the switches entering and leaving it, where a ratio compares the probability of a verdict on repairing and on damaging switches. Ratios are estimated on development items and frozen for test items; when all ratios equal one, the rule reduces to the majority. Before running the judges we fixed four criteria: accuracy on decisive switches, intervals of the likelihood ratios, the test-set comparison with the majority, and stability of the ratios across halves.

### 6.3 Results

**Table 9.** Same-model judges on the bank critic's trajectories. Decisive switches are those that change correctness. The majority selects 76 correct items on the test half and 78 on the development half.

| | Judge-R | Judge-R+ | Judge-C |
|---|---|---|---|
| Switches judged (of 1,201) | 1,185 | 1,041 | 1,201 |
| Accuracy on decisive switches | 0.58 | 0.60 | 0.66 |
| Likelihood-ratio intervals exclude 1 | no | yes | yes |
| Fitted on development, applied to test | 76 (+2, −2) | 73 (+3, −6) | 71 (+3, −8) |
| Fitted on test, applied to development | 73 (+5, −10) | 72 (+5, −11) | 77 (+8, −9) |
| Accuracy where the judge disagrees with the count | 18/36 = 0.50 [0.35, 0.65] | 53/116 = 0.46 [0.37, 0.55] | 32/66 = 0.49 [0.37, 0.60] |
| Best of 81 aggregation rules, in-sample | 154 | 156 | 155 |

No judge improves on the majority. Judging the critique is easier than judging the answer, and two of the three judges carry statistically detectable information at the level of single switches. That information does not survive aggregation in either direction of the split, and the reason is visible in the sixth row. A rule that uses only the counts, predicting that a switch is a repair when the new answer ends with at least as many votes as the old one, is as accurate on decisive switches as the judges are. Where a judge disagrees with this rule, which is the only place it can change the selection, its accuracy is 0.50, 0.46 and 0.49, and every interval contains one half. The aggregation rule fits the direction of each verdict from data, so a judge that was reliably wrong would have been exploited as readily as one that was reliably right. The verdicts restate the count.

Two further checks support this reading. A logistic model over count features and all verdict features of Judge-C, fitted and evaluated on all 400 items, selects 150 correct answers, fewer than the majority. A sweep over 81 aggregation rules, varying where a verdict acts (on the boundary round, the whole run, or the whole candidate), the weights of the two verdict directions, and gating to low-margin items, gains at most two items in-sample and nothing when the best rule on one half is applied to the other.

Why an accuracy of 0.66 on single switches is insufficient follows from base rates. Overturning the majority is a repair on 37 of the 123 items with several candidates where it can be overturned. A judge with accuracy p on a switch therefore overturns correctly with precision 0.30p / (0.30p + 0.70(1 − p)), which is 45% at p = 0.66 and exceeds 50% only for p above 0.70. On the 56 tied items the count is silent and Judge-C is right on 17 of 26 disagreements, which is suggestive and not significant (p = 0.17), and this changes the selection on few items, and the recency rule alone already recovers 14 of the 23 ties whose tied set contains the correct answer.

### 6.4 Interpretation

Conditional on the vote count, none of the three same-model judges carried detectable information about which answer was correct. This is a statement about one model, one benchmark, three framings and the trajectories of one condition, with the power of 400 items; gains of a few items per judge are not excluded, and a judge that outperforms the count on these switches would refute it. It does not contradict the finding of Zhao et al. (2025) that same-model verification scales with a large pool of independent responses: our judges see one trajectory of three to four candidates produced by a solver that has already reacted to critique from the same model, and they are asked about transitions, not about responses side by side. The three framings are not independent evidence, since they share a model and each correlates with the count, which is the finding. The headroom is real, and recovering it requires information that is not a function of the trajectory the solver has already produced: a stronger model, external verification, or a critic that withholds unwarranted suspicions in the first place.

## 7 Discussion

The results recast what a self-critique loop is for. As a corrector it performs as the literature predicts: its last answer is no better than a placebo's. As a sampler it has two properties that temperature sampling lacks. Its variation is produced in response to critique of the current answer: the solver revises more often, and its first revision is more often correct, than under answer-blind pressure. And its samples are ordered, which lets a count over rounds act as a selector and as an abstention signal without any additional model call.

The two controls sharpen a claim that is often left vague. The benefit does not come from telling the model what kinds of error exist, and a vocabulary distilled from the model's own past errors adds nothing identifiable to a critic that is free to name the shortcoming itself. The benefit comes with critique that the model generates for this question and this answer, and it is paid for in the critic's reasoning, which is most of the additional tokens. Whether the critique must read the answer, or acts as a second attempt at the question, is the main open point of this study.

The negative result on evaluation is the counterpart of the positive result on selection. The count works because correct answers recur more than incorrect ones, and a judge from the same model sees the same evidence that made the solver return to an answer. Its verdicts are therefore informative in isolation and redundant given the count. Progress on selection in this setting should be sought in information the trajectory does not contain.

## 8 Limitations

The study uses one model, one benchmark and one run per condition, and none of the roles was tuned; the results establish that the effects exist under these conditions and do not establish that they are general. The benchmark's reference answers are known to contain errors, which adds noise to every condition.

The critique's most secure effect is on the ceiling. On the selected answer its advantage over self-consistency lies between 13 and 22 items depending on how equivalent answers are treated; the lower figure comes from a bound that relies on reference answers, and a reference-free semantic merge with a universal self-consistency baseline remains to be done. Against either placebo the selected answer is not significantly better without pooling. The falsification test was written for the bank critic and passes only nominally; the clearer result belongs to a control arm.

The perturbing placebo controls for pressure, dose and format. It does not control for generation, for reading the question, or for the length and fluency of the feedback, so the effect is attributed to generated critique and not specifically to reading the answer.

The critics cost more than either sampling baseline, and we did not run a sampling baseline matched in total tokens. Critic token counts are extrapolated from a replay.

Scoring free-form answers required a model-based tier that can only add acceptances. The ceiling comparison holds under exact matching alone, but the tier has not been audited by human annotators. The free critic and the perturbing placebo were run through a different service endpoint for the same model weights than the other conditions; per-round reasoning length, truncation rate and commit rate agree across endpoints.

The evaluator analysis uses the bank critic's trajectories only and judges from the solver's own model; it says nothing about stronger judges. Pre-specification was recorded internally with dated documents and was not registered externally, and p-values are not adjusted for the number of comparisons. Finally, 400 items resolve paired differences of roughly twelve items or more in the selected answer; smaller effects, including small gains from same-model judges, remain undetermined.

## 9 Conclusion

On an expert-level benchmark, a self-critique loop read as a corrector does what the literature reports: its last answer improves no more than a placebo's. Read as a sampler, a critic that never stays silent reaches the correct answer on 45 more items than a reassuring placebo and 27 more than answer-blind pressure of the same dose, at matched candidate counts and under exact-match scoring alike. A count over its trajectory selects the correct answer more often than fixed or adaptive self-consistency, by 21 items as counted and by at least 13 under a bound that pools every correct answer, at a higher total cost. A vocabulary of the model's own past errors adds nothing identifiable, and whether the critic must read the answer or only the question is open. The count is also where same-model selection stops on this benchmark, within the resolution of 400 items: what the model says about its own transitions adds no detectable information to how often it returned to an answer. Where answers can be verified, the answers that are reached but not selected are the gain to be collected; where they cannot, the count serves as both selector and abstention signal.

## References

Aggarwal, P., Madaan, A., Yang, Y., and Mausam (2023). Let's sample step by step: Adaptive-consistency for efficient reasoning and coding with LLMs. *EMNLP*.

Bilal, A., Mohsin, M. A., Umer, M., Trigg, L., Subhan, A., Ali, M., and Hougen, D. F. (2026). Refining over resampling: Test-time self-correction for LLM reasoning. *arXiv:2608.05643*.

Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Ré, C., and Mirhoseini, A. (2024). Large language monkeys: Scaling inference compute with repeated sampling. *arXiv:2407.21787*.

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

Yang, Z., Zhang, Y., Wang, Y., Xu, Z., Lin, J., and Sui, Z. (2025). Confidence v.s. critique: A decomposition of self-correction capability for LLMs. *arXiv:2412.19513*.

Zhao, E., Awasthi, P., and Gollapudi, S. (2025). Sample, scrutinize and scale: Effective inference-time search by scaling verification. *arXiv:2502.01839*.

Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *NeurIPS Datasets and Benchmarks*.

## Appendix

**A. Error vocabulary.** Source items by benchmark, the three distillation levels, the five archetype entries with their definitions and check procedures, and the audit confirming that no entry contains a reference answer or an item identifier.

**B. Prompts and runtime.** Solver, critic and judge prompts; the four textual differences between the bank critic and the free critic; the generic sentences of the perturbing placebo; token budgets and stopping constants; service endpoints and their alignment statistics.

**C. Scoring protocol.** The three tiers, the truncation rule, the answer normalization and tie rules, and the table of adjudicated answer variants with rationales.

**D. Evaluator details.** Per-judge confusion tables on development, test and all items; likelihood ratios with intervals; a three-role Bayesian aggregator; the sweep of aggregation rules; a contrast of 26 gold-free trajectory features between repairing and damaging switches (areas under the curve between 0.43 and 0.59, none stable across halves); and a probe showing that critic suspicions concern the derivation and not the question text.

**E. Pre-specified rules.** The falsification test, the read-out rules for the free critic and the perturbing placebo, and the evaluator acceptance criteria, with dates.

**F. Additional results.** Results by answer form for every condition and rule; ceiling by round; selective-prediction curves; verifier simulations with asymmetric error rates.
