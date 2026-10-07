# A Proxy-Based Meta-Cognitive Evaluation Framework for LLM Agents

**Document type**: Research plan (experiment protocol) · **Version**: 0.9 (Draft) · **Date**: 2026-10-05
**Target venues**: Nature Machine Intelligence / IEEE TPAMI / NeurIPS (primary); ACL / EMNLP workshop (early checkpoint).

---

## Abstract

Current evaluation of LLM agents rests on a single static number — accuracy — which conceals two uncertainties: the *problem boundary* (a finite budget of steps, truncation, tool availability, and response time decides whether a task is "solved") and the *evaluation scale* (LLM-as-a-Judge introduces self-validation loops and homologous bias, while hyperparameters further perturb the score). We propose to redefine capability as a **cost–reliability curve** rather than a point estimate, and to measure it through an external **meta-cognitive proxy**: an error taxonomy, a Top-K feedback signal, a conservative (Bayesian-style) update, and a bounded feedback–self-correction loop. The central empirical question is whether, under repeated structured feedback, a model's combined capability **converges** — and, if so, at what cost. We formulate the problem distributionally (three candidate mathematical framings are held open), decouple three confounded notions (capability dimensions, activation vs. locking, recognizing vs. correcting errors), and structure the work into a tiered experiment over a **model × task × error-type** capability matrix, factorized to localize which capability a model lacks.

---

## 1. Motivation and Problem Statement

### 1.1 The inadequacy of static accuracy

A single accuracy number hides two fundamental uncertainties.

1. **Uncertainty in the problem boundary.** A finite budget — maximum steps, truncation, tool availability, response time — decides whether a task is solved. A wrong answer under a limited budget does not prove lack of capability, just as a human may fail under time pressure.
2. **Uncertainty in the evaluation scale.** LLM-as-a-Judge introduces self-validation loops and homologous bias; hyperparameters (temperature, top-p, truncation) further perturb the score.

The assumed mapping from *task* to *capability score* is therefore itself inaccurate. A pilot study within this program has quantified the effect in a finance-agent benchmark (FAB): evaluation-framework defects (tool design, format, prompting, hyperparameters, and judge bias) induced a measured **26 percentage-point spurious capability deficit** that is fully attributable to the framework rather than the model. This is the empirical warrant for replacing single-shot accuracy with a cost–reliability formulation.

### 1.2 The engineering thesis

The historical analogy is deliberate: a four-engine aircraft is not a categorical leap over a single-engine one; it is redundancy bought with cost, raising reliability under extreme conditions. Likewise, a model scoring 48% in one shot may reach 90% through repeated sampling, self-correction, and aggregation — provided enough budget. As inference cost falls, the bottleneck shifts from raw capability to the cost of reaching a target reliability. The question is therefore reframed:

> **Old question**: *What is the agent's accuracy?* → **New question**: *Given a target accuracy, what is the expected cost (steps / tokens / retries) to reach it?*

### 1.3 Convergence as the central empirical question

Convergence is **not assumed a priori**. The object of study is whether, under repeated structured feedback, a model's behaviour converges toward correctness. The inspiration is related in spirit to ensemble methods and the Central Limit Theorem — aggregate many weak signals and the mean may converge — but LLM outputs are correlated and systematically biased, so convergence is not guaranteed. Whether it holds, and for which models, is the research question.

---

## 2. Related Work

Four frontier threads frame this work; the complete literature map with citations is maintained in `docs/WORKMAP.md`.

- **Agent evaluation** — the move from static accuracy to cost–reliability; evaluation-framework bias and interference.
- **Verification & self-correction** — self-refine, Reflexion, and the negative result that LLMs often cannot self-correct without external signal; this motivates the *external* proxy.
- **Optimization** — test-time search, best-of-N, verifier-guided decoding.
- **Inference scaling** — test-time compute scaling laws and the cost–accuracy trade-off.

**Core positioning (2026-10-07).** The centre of gravity is a **new evaluation paradigm**: replace static
single-shot accuracy with round-dimension dynamic observables — activation ceiling `P(A)`, locking rate
`P(F | A)`, locking loss, reversibility — and quantify the **cost–reliability** and **risk** relationship that
follows. This is a measurement contribution, not a capability-improvement one (we deliberately do not optimise
L1/L2). The subordinate claim is an **existence proof**: a cheap, gold-free *weak critic* acting as a
metacognition proxy can still raise the activation ceiling, establishing metacognition — and its locking/correction
half — as a separable, optimisable axis of its own rather than a by-product of raw ability (§3.1).

**Nearest-neighbour works to differentiate against.** Three lines already observe the same phenomena from other
angles; the novelty claim must be drawn against them explicitly.

- **Feedback Friction (Jiang et al., arXiv:2506.11930)** — models plateau *below their performance ceiling* even
  with high-quality feedback; that ceiling is the closest published analogue to our `P(A)`, and the plateau to our
  locking loss. Difference: their feedback is binary / reflective / strong-model (near-oracle), ours is a
  *gold-free statistical critic*; they read the plateau as "resistance to feedback", we read it as a *separable
  locking quantity* with a risk-factor model.
- **Overthinking in test-time scaling (Zhou et al., arXiv:2604.10739)** — "flip events" where a correct answer is
  abandoned inside a single chain. This is our state-2 (locking deficit), but located *within one CoT under token
  scaling*, not across a *multi-round external feedback loop*.
- **Activation-probe self-correction ("The Count Is There, but Misaligned"; "The Shape of Addition", arXiv:2606.03645)**
  — the correct answer is encoded in internal activations yet not emitted ("decision-locking points"); white-box,
  mechanism-side evidence of activation-without-locking, versus our black-box, gold-free protocol-side measure.

Together these confirm the *phenomena* are real and independently observed. What is not established is the
synthesis unique to this program: (i) a protocol that promotes activation/locking to first-class round-dimension
observables, (ii) a gold-free proxy driving them, and (iii) a causal arm design (A/A2/C) plus a survival-hazard
risk-factor model of locking.

---

## 3. Theoretical Framework

### 3.1 Four-layer capability hypothesis

We hypothesise four separable capabilities; this separation is the conceptual core.

| Layer | Capability | Definition |
|---|---|---|
| **L1** | Base | Single-shot correctness of the naked model, with no external aid — the raw latent accuracy. |
| **L2** | Augmentation | The extent to which the model is embedded in an agent system: function/tool calling, retrieval harness, workflow orchestration, multi-sample voting, search, retry, best-of-N. A property of *model-plus-system*, not of the model alone. |
| **L3** | Meta-cognitive (activation) | The ability, given an external error signal, to *activate* the correct answer at least once across feedback rounds. Measures whether the correct candidate is within reach. |
| **L4** | Correction (locking) | The ability to *lock onto* the correct answer — to resist a misleading signal, hold a correct answer, and not oscillate. Probes inference-time compute scaling (added 2026-10-06). |

**Terminology note.** The middle layer is named *Augmentation* (in the sense of agent augmentation) because it is not merely optimisation — it is any capacity gained by placing the model inside an augmented system. A model with weak L1 but strong L2 may still solve a task purely as an engineering/cost outcome. Our role is **not** to improve L1 or L2 directly; we construct an external signal system and test whether the model can use it.

**Reconstruction (2026-10-06): static baseline vs. round-dynamics.** Reframe the four layers as two orthogonal axes. L1+L2 jointly define the *static accuracy* — the **intercept** of the cost–reliability curve (§3.4). L3 and L4 define the *round-dynamics* — the **shape** of that curve. Two models with identical accuracy are indistinguishable classically, yet a model with higher L3/L4 produces a stable cost–reliability curve (and thus scales under inference-time compute), whereas a model with broken L3/L4 cannot scale at all. Formally the intercept is L1+L2 and the shape parameter is k = f(L3, L4): k > 1 (accelerating convergence) ⇔ strong L4 locking; k < 1 / oscillation ⇔ an L3 or L4 deficit (§3.4).

### 3.2 The meta-cognitive proxy

Since models lack intrinsic meta-cognition, we construct an **external proxy** that simulates the monitoring function. The proxy does not modify the agent's output directly; it only provides structured signals. Four components:

1. **Error taxonomy** — a structured, inductively built catalogue of error types (numerical miscalculation, missing unit, logic jump, source hallucination, retrieval failure, …), extensible across domains.
2. **Evaluator / signal generator** — receives the agent's output, computes distances to each error category, and returns the **Top-K** most likely error directions as feedback, without revealing the gold answer.
3. **Conservative update (Bayesian flavour)** — after revision, compares the new answer's distance to the original and to known error categories; down-weights changes that move toward known errors, preventing over-correction and oscillation.
4. **Feedback–self-correction loop** — agent receives signal → revises voluntarily → proxy updates belief → repeat, for a bounded number of rounds.

The minimal implementation is a boosting-style **prior-weighted feedback**: maintain an error-category × model contingency table; update it each round; and give downstream rounds a stronger signal on high-frequency error categories.

### 3.3 What converges: the combined capability, not the problem

The framework is *not* a study of whether "a problem converges." Individual questions serve only as probes; convergence is an attribute of the model's capability under feedback, not of any single task. The object of study is the **trajectory across a population of questions**.

- The raw score is a finite-sample observation of latent capability. Under repeated rounds, the three layers (L1, L2, L3) interact and their combined effect is progressively sampled by the feedback process. Static accuracy is the *baseline* from which the trajectory departs.
- Because the mean may be moving, the process is **not** i.i.d. from a fixed distribution; a suitable stochastic model must be posited (§3.5).

**Convergence-surface hypothesis.** Whether the combined capability converges depends on its configuration (L1, L2, L3); if any component is strong enough, convergence may still occur through engineering; if all are weak, it may never arise:

| Base (L1) | Meta-cognitive (L3) | Augmentation (L2) | Predicted convergence |
|---|---|---|---|
| High | Low | High | Likely — strong base + engineering |
| Low | High | High | Possible — tool / ensemble compensation |
| Low | Low | Low | Unlikely to converge |
| Any | High | Any | Very likely — strong self-correction |

When convergence is present, the framework answers *how many rounds are required to reach a target accuracy*; when absent, it reports non-convergence as the diagnosis.

### 3.4 From accuracy to cost–reliability prediction

For a model whose combined capability converges, the cost–accuracy relationship is modelled as

```
Accuracy(c) = f(c; θ)
```

where c is cumulative cost (rounds / tokens / retries) and f is an increasing function (power-law or logistic). The prediction goals are: (i) whether convergence will occur, and (ii) the expected number of rounds to reach a target accuracy (e.g., 90%), estimated from the first 2–3 rounds. This is a cost-forecasting problem, analogous to estimating the sample size required for a statistic to reach a prescribed precision.

A candidate parametric form (extreme-value family) is proposed for the probability of reaching reliability R within N rounds:

$$P(\text{reach } R \text{ within } N \text{ rounds}) = 1 - \exp\!\left(-\left(\frac{N}{\theta(R)}\right)^{k}\right)$$

where θ(R) is a characteristic scale increasing in R, and the shape parameter k classifies the process: **k > 1** acceleration (the proxy is effective), **k = 1** a random walk (proxy ineffective), **k < 1** deceleration (oscillation / degradation).

### 3.5 Three candidate mathematical framings

Three framings are held open; pilot data will be used to compare them for fit and predictive quality rather than assuming one in advance.

- **Candidate A — Stochastic approximation (Robbins–Monro type).** The feedback loop as a stochastic approximation algorithm, where a latent capability state updates each round from a noisy observation of performance. Naturally handles a moving mean, but requires a well-defined latent state and update rule.
- **Candidate B — Markov chain and stationary distribution.** The loop as a Markov chain over model states; if ergodic, the distribution converges to stationarity. Convergence is diagnosed by mixing (e.g., Gelman–Rubin R̂ across parallel chains), and "converged accuracy" is the stationary expectation.
- **Candidate C — Sequential analysis and stopping time.** Feedback rounds as sequential observations; a stopping rule is defined by target accuracy and confidence, and the quantity of interest is the expected stopping time. Directly answers the cost question, but relies on assumptions (martingale / controlled dependence) that moving means may violate.

### 3.6 Three methodological decouplings

1. **Capability-dimensional decoupling (revised 2026-09-29).** L1 (base, no-tool) and L2 (augmentation, tool) are *a priori* design partitions — fixed by the task-family split — so a static tensor cannot "recover" them: factorizing model × family × error-type merely projects the imposed taxonomy back (rank-1, PCs aligned one-to-one with families; verified empirically). L1/L2 are therefore **not inverted** from a static matrix. Only **L3/L4** are open process properties, living on the *round* dimension (presence vs. selection of the correct candidate across feedback rounds), not on static error labels (§5.10).
2. **Activation vs. locking.** *Activation* (event A): the correct answer appears at least once within N rounds — measures **proxy** effectiveness. *Locking* (event B): the final round is correct — measures **model** capability. Activation without locking diagnoses the model, not the proxy.
3. **Recognizing vs. correcting errors.** *Recognizing* (metacognitive) is the object of proof; *correcting* is an engineering concern outside the current scope. The proxy needs only to raise the probability that the correct answer appears, not to guarantee it is locked.

---

## 4. Research Questions

| ID | Question |
|---|---|
| **RQ1** | Does a model's combined capability (L1, L2, L3), under external meta-cognitive feedback, exhibit convergence across a population of probe questions? |
| **RQ2** | Which (if any) of the three mathematical framings best describes the observed convergence process? |
| **RQ3** | When convergence occurs, what is the expected cost (rounds / tokens) to reach a target accuracy, and how accurately can it be predicted from early rounds? |
| **RQ4** | When convergence does not occur, what trajectory features diagnose the underlying meta-cognitive deficit? |

Convergence is classified into four classes: **convergent**, **oscillating**, **divergent**, **stagnant**.

---

## 5. Experimental Design

### 5.1 Probes and models

Probes (individual questions) are drawn from multiple task families; the design is **cross-domain** and retains **finance** as one family (reusing the FAB setup). The metrics are task- and model-focused, not problem-focused.

- **Task families** (Probe: 5 families × 50 Qs — math (GSM8K), math500 (MATH-500), logic (MMLU-Pro), finance (FAB), tool-use (BFCL), L1:L2 = 3:2; Feasibility adds code (HumanEval), factual consistency (TruthfulQA), multi-hop (HotpotQA), translation (WMT zh–en); Full extends to 12–15 families, with L2/L3-level items ≥ 40%).
- **Models** (Phase 1 = 3 mid-tier via Aliyun Token Plan; **no local model loading**):
  - *Mid (Phase 1)*: deepseek-v4-flash-0731, qwen3.8-flash, glm-5.3 (Aliyun Token Plan);
  - *Weak*: qwen3.6-flash, glm-4.7-flash (deferred to Phase 2);
  - *Strong*: Claude Opus 5.5, GPT-6 Astra (deferred to Phase 2/3).

### 5.2 Task-Bank Blueprint (Provisional)

> **Status: DRAFT / PROVISIONAL.** Composition, per-question token budgets, and capability-layer
> mapping below are planning estimates to be re-quoted against exact model pricing at execution
> time (§7). This table defines the *candidate pool*; stage-specific subsets (not yet frozen) are
> drawn from it.

**Design principles.**
1. **Balanced L1/L2 coverage (~1:1).** Both the no-tool base tier and the tool-augmented tier must
   carry enough anchoring questions, or the tensor factorization (§5.4) cannot separate the axes.
2. **Hard items replace saturated items in L1.** Pure-knowledge probes (GSM8K, plain MMLU) are near
   ceiling for the mid tier; MATH-500 / MMLU-Pro / GPQA-Diamond recover discrimination.
3. **L2 split into heavy-FC vs light-FC.** Heavy FC (finance FAB, SWE, WebArena) re-injects large
   documents into the tool loop, causing O(N^2) context growth, so it is kept as a small anchor set.
   Light FC (BFCL, HotpotQA, HumanEval) measures native function-calling itself at near-zero cost.
4. **Evaluator matches answer form.** Letter -> exact match; numeric/LaTeX -> numeric comparison;
   open-generation -> LLM-judge or metric (BLEU/COMET); code -> pass@k execution; FC -> tool-trigger
   + parameter check.

**Capability layers.** Four layers are used: **L1 Base** (single-shot, no tools), **L2 Augmentation**
(tool/function-calling under an agent harness), **L3 Meta-cognitive** (recognizes an error on the
external signal but does not change), **L4 Correction** (corrects the error on signal, improves).
L4 is a scope expansion beyond the three-layer hypothesis in §3.1; L3/L4 are *process* properties
sampled across feedback rounds — not static per-question labels — and every question contributes to
them through the round dimension (§5.4).

**Task bank.**

| Family | Benchmarks (easy->hard) | Layer | Answer form | Evaluator | Native FC | Qs / set | Tokens / Q (order) | Stage |
|---|---|---|---|---|---|---|---|---|---|
| math | GSM8K -> MATH-500 / AIME | L1 | numeric / LaTeX | numeric + symbol | no | 50 | 1-5K | P1-P3 |
| logic | BBH -> MMLU-Pro | L1 | letter (10-opt) | exact letter | no | 50 | 2-3K | P1-P3 |
| commonsense | HellaSwag / CSQA | L1 | letter | exact letter | no | 50 | ~1.5K | P2-P3 |
| factual-QA | TriviaQA / NQ / SimpleQA | L1 | short answer | LLM-judge / EM | no | 50 | ~1.5K | P2-P3 |
| science | GPQA-Diamond | L1 | letter (hard) | exact letter | no | 50 | 3-4K | P2-P3 |
| translation | WMT zh-en / FLORES | L1 | generation | BLEU / COMET / judge | no | 50 | ~2K | P2-P3 |
| finance | FAB | L2 heavy-FC | agent + domain tools | max(T1,T2) | yes | 50 | 50-80K | P1-P3 |
| tool-use | BFCL | L2 light-FC | function call | trigger + param | yes | 50 | 2-5K | P1-P3 |
| code | HumanEval -> SWE-bench | L2 light->heavy | code | pass@k | partial* | 50 | 2-150K | P2-P3 |
| multi-hop | HotpotQA / MuSiQue | L2 light-FC | retrieval QA | EM / F1 | yes | 50 | 10-20K | P2-P3 |
| web | WebArena / GAIA | L2 heavy-FC | agent + browser | judge + completion | yes | 50 | 30-100K | P3 |

* HumanEval is generation-only (no FC) unless run under an executor harness; SWE-bench uses
file-edit / bash tools.

**Stage-1 (probe) subset — recommended, provisional.** Every probe set is fixed at **50
questions** for uniform statistical power and tensor-cell comparability. Total 250 Qs at ~¥7-11 per
mid model on the cheap price tier (x~7 on glm-5.3); L1:L2 = 3:2 (three L1 sets, two L2 sets):

| Family | Probe set | Qs | Layer |
|---|---|---|---|
| math | GSM8K 50 | 50 | L1 |
| math | MATH-500 50 | 50 | L1 |
| logic | MMLU-Pro 50 | 50 | L1 |
| finance | FAB 50 (heavy-FC anchor) | 50 | L2 |
| tool-use | BFCL 50 (light-FC anchor) | 50 | L2 |

**Token budget (order of magnitude).** Lower bound = deepseek-v4-flash (¥1/M in, ¥2/M out); upper
bound = glm-5.3 (¥8/M in, ¥28/M out); qwen3.8-flash sits between. L1 no-tool families cost <= ¥1 per
100 Q on the cheap tier, so they can be expanded to 100-200 Q freely. Finance FAB is the sole budget
sink (¥10-15 / 100 Q cheap tier, ¥80-120 / 100 Q glm), reduced 50-70% by the INT-15 chunking + cache
dedup (docs/INTERFERENCE_CAUSAL_TABLE.md). L3/L4 multiply any family's cost by its round count (<=11).

**Budget-calibrate-archive loop.** Every run follows a fixed discipline so results are reusable and
never re-executed needlessly:

1. **Budget first.** Before every run, estimate cost from the table above and record it in the run
   manifest, alongside the explicit temperature / seed / thinking config (see docs/REPRODUCIBILITY.md).
2. **Calibrate after.** After the run, compare actual tokens and cost against the estimate, then
   back-fill the per-question token and per-model unit-price numbers so subsequent estimates tighten.
3. **Archive on pass.** A run that completes without bug or API-failure contamination is archived
   (trajectories.jsonl + summary.json) and reused across stages. Only models that failed on network
   errors are re-run in isolation to fill gaps; already-passed models are not re-run.

### 5.3 Experimental stages

| Stage | Purpose | Configuration |
|---|---|---|
| **1. Signal validity** | Build the annotated error bank + rule-based critique; validate Top-N by its own downstream effect (next-round improvement) — no human labelling (see §5.7–5.8). | 5-family 250-Q probe set (§5.2); validate the proxy signal. |
| **2. Trajectory collection** | Run the feedback loop up to ~10 rounds over a fixed probe set; log full trajectories (correctness, error type, output distance, cumulative cost per round). | deepseek-v4-flash-0731, qwen3.8-flash, glm-5.3; gather cost–accuracy data. |
| **3. Convergence analysis** | Assess convergence of the population trajectory; compare the three mathematical framings (§3.5). | Math · Finance · Fact QA · Open generation; test capability convergence. |
| **4. Cost prediction** | Fit converged trajectories; predict required cost from the first 2–3 rounds, out-of-sample. | Cross-model and cross-domain; validate the cost forecast. |

### 5.4 Capability matrix and tensor decomposition

**Static decomposition — no-go for L1/L2.** A tensor **T ∈ R^{M × T × E}** (model × task family × error type) is rank-1 dominated: PCs align one-to-one with task families because error labels are defined per-family and the leaf × family structure is block-diagonal. Factorizing it (PARAFAC / Tucker / PCA) only projects the pre-imposed taxonomy back and produces no new L1/L2 axis. L1 (no-tool) and L2 (tool) are already fixed by the task-family partition (§5.2), so "recovering" them is tautological. Static decomposition is retained only as a taxonomy-coverage diagnostic, not as a capability-inversion tool.

**L3/L4 inversion lives on the round dimension** — §5.10 specifies the taxonomy-free activation / locking / correction statistics and two round-level decomposition carriers (state transition, trajectory).

### 5.5 Ablation matrix

| ID | Condition | Alternative explanation ruled out |
|---|---|---|
| A1 | No proxy; model self-loops N rounds | gain is from "more rounds", not the proxy |
| A2 | Proxy emits random feedback (not prior-based) | gain is from "someone told me to check", not correct direction |
| A3 | No voting; take first revision | gain is from "aggregating candidates", not correction itself |
| A4 | Uniform prior instead of statistical prior | gain is from "prior existence", not prior quality |
| A5 | Different temperature (0 vs 0.7 vs 1.0) | sampling randomness |
| A6 | Different feedback strength (Top-1 vs Top-3 vs Top-5) | signal-strength effect |

### 5.6 Metrics and statistics

- **Observed**: activation rate, first-activation round, locking rate.
- **Test**: Fisher's exact test, p < 0.05, for activation-rate differences between proxy and baseline arms.
- **Success criteria** (any): a statistically significant activation-rate gain on ≥ 1 task family; or an activation gain on ≥ 1 weak model.
- **Stop conditions** (any): no activation gain on any model × family; gain < 5%; ablation shows equal gain without the proxy.

---

### 5.7 Phase-1 (probe) execution plan — go/no-go feasibility

**Objective.** Verify at minimum scale that the metacognitive-proxy pipeline is realizable
end-to-end before scaling to Phase 2/3. Phase 1 collapses Stage 1 (signal validity), the
first half of Stage 2 (multi-round trajectory collection), and a first pass at Stage 4
(cost forecast) into one closed loop over the 250-Q probe set (§5.2) and the three mid-tier
models (deepseek-v4-flash-0731 / qwen3.8-flash / glm-5.3; all Aliyun Token Plan, **no local
model loading**). The four feasibility checks and their pass criteria:

1. **Capability decomposition.** Extend the 6-label finance taxonomy into a per-domain error
   taxonomy (math / logic / finance / tool-use), ground-truth-deterministic wherever possible.
   Pass: every wrong answer receives a stable label, and per-error-type anchoring counts are
   non-degenerate (no empty classes), so the later model × task-family × error-type × round
   tensor carries enough information to separate axes.
2. **Rule-based critique as proxy meta-cognition.** A single critique module (no evaluator / judge /
   gold) emits reflective probes from three deterministic gold-free signal layers — answer shape, process
   primitives, and history delta (§5.8). Pass: signal-named questions improve next-round at a significantly
   higher rate than unnamed ones (Fisher exact p < 0.05), and the static ranking prior beats the
   random-feedback (A2) and uniform-prior (A4) arms.
3. **L3/L4 discrimination.** All candidate answers across rounds are logged and judged against the gold
   *offline*. If a correct answer appeared anywhere in the trajectory, the model could *activate* it (L3,
   recognizing/activation); if it appeared but was not selected as the final answer, the model failed to
   *lock* it (L4, correcting deficit). Pass: per-model activation-without-locking (L4-deficit) quantities
   are separable and interpretably different across the three models — information visible only under
   multi-round feedback.
4. **Cost–reliability curves.** Fit Accuracy(c) = f(c; θ) over cumulative rounds/tokens per model ×
   family; classify the extreme-value shape k (§3.4): k > 1 acceleration, k = 1 random walk, k < 1
   oscillation. Pass: at least one model × family shows monotonic reliability growth and k separates
   the models.

**Build before burn (execution order).** Multi-round runs multiply the finance FAB budget sink by the
round count, so the expensive loop starts only after the cheap foundations pass on the existing
d1_baseline data (zero additional API cost): (i) capability-matrix definition — fix the tensor axes and
verify the matrix is information-rich against d1_baseline; (ii) error bank + critique — the analysed
and annotated wrong-answer bank, instance embedding, and Top-N retrieval, exercised end-to-end. Then run
the feedback loop to **N = 10 rounds in ~3-round segments**, inspecting activation/locking after each
segment for signal-driven change before spending the next; stop and diagnose if a segment shows no change.

**No human labelling.** The error-type annotations on the reference bank are produced automatically,
grounded in offline gold-based scoring (math numeric, logic letter, BFCL function/parameter, finance
T1/T2) — never by hand. The online critique never sees the gold: it matches a candidate to annotated
wrong-answer instances by embedding similarity (§5.8). Signal effectiveness is established by its own
downstream effect (next-round improvement) against the random-feedback and uniform-prior controls —
consistent with the premise that the proxy must succeed with minimal external intervention.

**Go/no-go.** Go if the four checks pass (or the §5.6 success subset); otherwise stop, adjust the
critique (embedding / N / prior), and rerun at most twice before reassessing direction (§8.2).

### 5.8 Weak critic specification — taxonomy-prior × Naive-Bayes classifier

**Positioning.** The meta-cognitive proxy's feedback generator is the **weak critic**: a
deterministic, gold-free classifier that maps one answer onto the fixed 19-leaf error taxonomy and
returns the **Top-3** most likely error directions with probabilities. It never assigns
correctness, never consults the gold, and never calls a judge. Its only job is to emit a few
directional reflections for the agent to re-examine. Correctness stays entirely in the offline
evaluation layer (§5.9).

**Two-layer pipeline.**

1. **Layer-0 prior — the taxonomy.** `src/build_error_taxonomy.py` auto-labels every wrong
   instance in d1_baseline with one of the 19 leaves (model × family × prompt/gold), producing the
   error bank `experiments/error_taxonomy_v2/wrong_bank.jsonl`. This is the *prior*: the base rate
   of each error direction per family. Each leaf also carries two fixed, gold-free static fields —
   **cause** (one-sentence error reason) and **attention** (one-sentence directional "how to
   check", never pointing at the correct value).
2. **Layer-1 classifier — Naive Bayes.** `src/build_weak_critic.py` reads the bank, estimates the
   per-family conditional tables P(signal | leaf) and P(leaf) with Laplace smoothing, and returns
   the posterior over that family's leaves, ranked descending.

**Why Naive Bayes.** The bank holds only a few dozen wrong instances per family; after the
model × type split most cells hold 0–20 rows, so any capacity-rich model would overfit. Laplace
smoothing (α = 1) keeps every leaf reachable. Phase 2 (larger data) is the upgrade point to
logistic / random-forest.

**Gold-free observations.** Features are computed from `final_answer` only, plus (finance) the
recorded tool-call count — never from `gold_answer`:

| Family | Observation features (categorical) |
|---|---|
| math / math500 | empty / number count {0,1,2+} / sign of any number |
| mmlu_pro | empty / distinct option-letter count {0,1,2+} |
| finance | empty / tool-call count {0,1,2+} |
| bfcl | empty / valid-JSON |

The leaves split into *gold-free observable* (`empty_or_unparseable`, `non_letter_output`,
`multiple_letters`, `json_parse_error`, `empty_pred`, `tool_error`, `retrieval_failure`) and
*gold-dependent* (`sign_flip`, `magnitude_error`, `factor_error`, `near_miss`, `wrong_symbolic`,
`wrong_option`, `contradiction`, `complete_failure`, `numeric_error`, `coverage_incomplete`,
`wrong_function_name`, `wrong_argument`). The latter are inferred only statistically through their
shape profile — which is precisely why the critic is *weak*.

**Top-K feedback.** The critic returns the top **K = 3** leaves with probabilities, phrased as
natural-language type phrases (never the internal leaf names) and a neutral open ending. The
feedback carries a three-tier ablation:

- **A** = type phrase + probability (baseline)
- **B** = A + cause
- **C** = B + cause + attention

The ablation burns A/B/C against next-round improvement to test whether the extra diagnostic text
helps (§5.7), recorded in `EXPERIMENT_LOG`. The prompt obeys three rules: no mechanism
self-confession (never "based on statistics / a reference bank"), no internal leaf labels, and a
neutral closing ("if any applies, revise accordingly; otherwise keep your answer as is").

**Feedback loop.** Reflective feedback is applied **in parallel** to produce candidate revisions
from the same starting point; the agent then selects one to carry into the next round — the critic
only activates candidates, it never chooses. Runs go the full **N = 10 rounds with no early
stopping** (early stopping masks oscillation / divergence); sequential single-direction revision
is a separate ablation axis (A3, §5.5).

**Separation from L3/L4.** The critic is single-round and generates feedback; L3/L4 (§5.10) are
cross-round offline diagnoses (activation vs. locking). The two touch only through the
round-dimension events, which stay gold-free.

**Rev 3 — exemplar retrieval + evidence threshold + error signal (2026-10-06, replaces Rev-2 Naive Bayes).** `src/build_weak_critic.py` (CRITIC_VERSION v2.0) is now an exemplar-retrieval classifier over the wrong bank. The evidence for an answer is the weighted similarity to the nearest wrong exemplars, s = W_Q·sim_q(question) + W_A·sim_a(answer) (W_Q=0.7 primary, W_A=0.3), and the error signal is error_score = family_base_rate × s. Flagging is a "disease-test positive" cut on the **evidence** (`EVIDENCE_THRESHOLD`, currently 0.1): s ≥ threshold → feedback, else silent. The feedback hands the agent the **error direction (Top-K leaf) + confidence** and the error_score as a soft signal, and lets the agent decide whether to revise.

**Critic is a hint, not a verifier.** Correctness stays entirely in the offline layer (§5.9). The critic never decides right/wrong, so its quality metric is the **top-K direction hit rate** (84–100% on the wrong bank), not any false-positive rate.

**Known risk (recorded 2026-10-06, unresolved).** The evidence s has no discriminating power between correct and wrong answers — on the correct-answer set the flag rate is ~98%. Root cause: s is dominated by *question* similarity (0.7), which is structurally high for template-heavy families (bfcl ≈ 0.65, math500 ≈ 0.46) and low for open-domain families (finance ≈ 0.16, mmlu ≈ 0.10); finance/mmlu evidence is further *reversed* (correct answers resemble the wrong bank more than wrong answers, which are truncated). The scalar error_score is therefore also reversed for finance. Tracked in §8.2; a go/no-go item for the real feedback loop.

### 5.9 Evaluation tiers (three-tier scoring framework)

Correctness scoring is dispatched into three tiers by answer form and by how recoverable the
answer is from the model's full response. Every scored row records which tier produced its final
score in an `eval_tier` field, so hybrid scoring stays reproducible at per-question granularity.

- **T1 — deterministic match (no LLM).** Numeric / symbol / letter / JSON answers are compared to
  the gold by rule or symbol equivalence (sympy). For MATH-500, a deterministic extraction layer
  (T1b) recovers a final answer buried inside the reasoning chain: candidates are drawn from
  `\boxed{}`, the trailing `= …`, the last non-empty line, the last number (excluding year tokens
  in 1900–2100), or the last option letter, and each is symbol-compared to the gold. T1 is the
  zero-cost default for math / logic / BFCL.
- **T2 — LLM-assisted parse + judge (deepseek-v4-pro; registered intervention).** When T1 marks a
  row wrong but the answer may be present-yet-unrecoverable by the extractor (failure mode A:
  "answer is in the response, the parser failed"), the full response is re-read by the strongest
  judge model against a known gold and scored CORRECT / INCORRECT. T2 runs *only* on T1-missed rows
  (tier-2 rescue) to contain cost, and is disabled by default (`T2_RESCUE_ENABLED`) until an API
  key is supplied. T2 counts as an intervention and is recorded in `eval_tier`.
- **T3 — multi-LLM voting.** Open / qualitative answers (finance FAB rubric, generation) whose gold
  is not exhaustively expressible are judged by multiple LLMs with majority vote; the current
  finance path uses `max(T1, T2)` rubric coverage as an interim stand-in pending a multi-judge setup.

**False-negative convention.** `correct` is the positive class, so "scored wrong but actually
right" is a **false negative (FN)** and "scored right but actually wrong" is a false positive. The
T1b extraction layer and the T2 rescue both target FN specifically. FNs are quantified per model by
re-scoring stored answers (zero API) and comparing against a strict rule re-label before/after.

**Intervention registration.** Only T1 is intervention-free. T2 (LLM re-judge) and T3 (multi-judge)
change the scoring decision and must be declared as interventions in every result they touch. The
"answer-format-doesn't-matter" stance is *not* a universal default: it must be declared per task
family (e.g. a direct-letter prompt for MMLU-Pro), and a format-enforcing prompt applied to the
*generator* is itself an intervention — separate from, and not a substitute for, a sound evaluator.

### 5.10 L3/L4 discrimination — round-dimension scheme

**Scope rationale (2026-09-29).** L1/L2 are *a priori* (task-family split, §5.2) and not inverted (§5.4). L3 (meta-cognitive: recognise an error on the external signal) and L4 (correction: fix it once recognised) are *process* properties observable only across feedback rounds. Their operationalisation is **taxonomy-free** — it needs only two per-round events, not an error-type label, so it is immune to the block-diagonal projection that defeats the static matrix.

**Events (per model × task, over N rounds).**
- A — *activation*: ≥1 candidate across the N rounds is scored correct against the gold **offline**. Measures proxy effectiveness + the model's activatability.
- B — *locking*: the final selected candidate is correct. Measures model capability.

**Derived statistics (per model × family).**
- activation rate = P(A); locking rate = P(B); correction rate = P(B | A);
- L4-deficit = 1 − P(B | A) (activated but failed to lock);
- first-activation round (early activation ⇒ easily activated);
- L3-deficit separated via the A1 ablation (self-loop, no proxy): the activation-rate gap proxy − A1 isolates the signal's activation contribution, and the A-event internals split "recognised but did not move" from "never recognised".

**Round-dimension data schema (per model × task trajectory).**
```
per_round[]: candidates[] {text_hash, offline_gold_match}, selected_idx,
             critique_topn {error_type: prob}  # proxy arm only, cost_tokens
derived:      first_activation_round, final_selected_correct
```

**Decomposition carriers (Level 2).** Both are used; neither touches the static model × family × error-type matrix.
- **Carrier A — state transition.** `M_model ∈ R^{E×E}` over the unified leaf (or 6-axis) error states, read as which error types are corrected under feedback and which recur. Spectral decomposition (Perron–Frobenius / mixture-Markov deconvolution) localises absorbent vs. recurrent error classes — the L4 correction profile.
- **Carrier B — trajectory.** `X ∈ R^{(model×task) × round}`, one binary correctness time-series per row. PCA / MDS of X separates convergent, oscillating, and divergent trajectories and shows how they stratify by model.

**Execution order (build before burn).** The N=10 in ~3-round segments loop (§5.7) is the data precondition for L1/L2 inversion. First the round-dimension schema + Level-1 statistics are built against the existing single-round d1_baseline (round=1 degenerates to static — pipeline check only); the A1 ablation and multi-round data then unlock Level-1 measurement and both Level-2 carriers.

**Six end-states (2026-10-06).** Every (model × task) loop run falls into exactly one of six mutually exclusive end-states, jointly operationalising L3 (activation) and L4 (locking / anti-interference):

| End-state | Start | Correct appears | Final | Reading |
|---|---|---|---|---|
| 1 | correct | — (never flips) | correct | L4 full (strong anti-interference) |
| 2 | correct | flips wrong | wrong | L4 deficit (misled into an error) |
| 3 | correct | flips + recovers | correct | L4 weak but recoverable |
| 4 | wrong | appears | correct | L3 + L4 full |
| 5 | wrong | appears | wrong | L3 present, L4 deficit (oscillation) |
| 6 | wrong | never appears | wrong | L3 absent (signal cannot activate) |

End-states 2/3 are the "oscillation / flip-correct-to-wrong" phenomenon; the critic's false-positives here double as a *natural L4 anti-interference stress test*. End-states 5 vs 4 isolate "can activate" (L3) from "can lock" (L4).

---

### 5.11 Feedback-loop implementation (Phase 1)

The §5.10 round-dimension scheme is implemented as a bounded feedback–self-correction driver, `src/run_feedback_loop.py`, which produces the raw L3/L4 trajectory data (§5.10 activation/locking events, §5.10 six end-states).

**Loop mechanics.** For each (model, task): round 0 is a baseline solve with no feedback; rounds 1..R inject the previous answer plus the weak critic's gold-free feedback as an extra user message and re-solve the *same* question **independently** (fresh context, not a multi-turn continuation), so the agent's natural single-question behaviour is unaltered. Tool results are cached across rounds so a finance task does not re-fetch the same document every round. The agent alone decides whether to revise - no forced output format, preserving the design constraint against prompting the agent to emit only the answer.

**Hyperparameters (this probe).** R = 10 max feedback rounds (round 0 baseline + rounds 1..10); early-stop N = 3 - the loop halts once the final answer is unchanged for 3 consecutive rounds (case/whitespace-normalized), bounding finance over-oscillation. Feedback tier C (error type + probability + cause + attention). temperature = 0, seed = None (deterministic; temp=0 makes the seed a no-op).

**Zero-LLM scoring within the loop.** Per-round correctness drives early stopping and the six end-states; it is a deliberate *lower-bound proxy*, not a re-statement of baseline accuracy.

- math / math500 / mmlu_pro / bfcl - T1 deterministic rules (`_score_t1_numeric` / `_score_math500` / `_score_mmlu_pro` / `_score_bfcl`).
- finance quantitative - T1 numeric or normalized rubric coverage.
- finance qualitative - T2 LLM-judge rescue (`_score_t2_llm_semantic`, deepseek-v4-pro 3-vote median + dealbreaker). This is a **registered intervention** (§5.9); every round's answer, gold answer, and prompt are still recorded, so any bad judge call can be re-scored offline afterwards.

**Scope & outputs.** 3 mid-tier models (deepseek-v4-flash, glm-5.3, qwen3.8-flash, Aliyun Token Plan) × 250 tasks (5 families × 50). Per model: `experiments/feedback_loop_{run_id}/{model}/loop_trajectories.jsonl` (one JSON per task - full per-round record: answer, correctness, evidence, error_score, no_signal, top-3 leaves, tool calls, latency - plus gold_answer and prompt for offline re-judge) and `loop_summary.json` (initial/final accuracy, end-state distribution, L3 activation rate, L4 lock rate, L4 misled rate, mean rounds).

**Concurrency note.** The weak critic's `_predict` returns (top-k, evidence, error) atomically so the 6-way ThreadPoolExecutor never cross-contaminates one task's signal with another's.

---

### 5.12 Capability-layered dynamics model (L1/L2 + L3 + L4 → accuracy/cost)

**Motivation (2026-10-06).** §5.10 defines the L3/L4 round-dimension events; §5.11 produces them. Here we state *why* a directional weak critic — even a near-noise one — is predicted to lift accuracy, and turn that prediction into an estimable model whose parameters become the evaluation target.

**Statistical skeleton.** Model ability on a task is a latent mean μ (the intercept = L1/L2). A single observation Y is μ plus noise from sampling, LLM-as-Judge variance, and rubric noise. Three arms:

- **A — no feedback (baseline):** `E[Y_A] = μ`.
- **B — directionless noise (random feedback / self-loop / extra test-time re-solve):** `E[Y_B] ≈ μ`. Noise widens variance but does not shift the mean — the expected "more test-time compute does not guarantee a better result" outcome.
- **C — directional weak critic:** `E[Y_C] = μ + Δ`.

**The L3 existence claim.** Estimate `Δ = E[Y_C] − E[Y_B]`. A significant `Δ > 0` is the minimal evidence that a *directional* weak critic (a weak but non-zero L3) has value, independent of critic strength. The contrast is **C vs B**, not C vs A: C vs A confounds "multiple rounds" with "directional signal", whereas C vs B isolates the directional contribution. This is what separates L3 from L4 — L4 is the locking/anti-interference profile *inside* arm C; L3 is the directional lift *between* arms.

**L3/L4 separation inside arm C.** Four per-task quantities, defined over the looping events (`A` = "correct answer appears in ≥ 1 round"; `S` = "round-0 correct"; `F` = "final round correct"):

- `P_act = P(A)` — **L3 activation = the model's reachable ceiling** (§5.11 `l3_activation_rate`). The fraction of tasks where the correct answer is produced *at least once* anywhere in the loop (round 0 included) — the upper bound on the accuracy the model can reach. It is deliberately **not** a locking property: a task where the answer never appears (end-state 6) is a true reachability deficit of the model's own capability (an L1/L2 gap), whereas a task that appears but is not locked in finally (end-state 5) is a separable L4 deficit. Low activation therefore signals a raw capability gap, not merely a failure to lock — this is the distinction the analysis now prioritises over locking alone.
- `r = P(A | ¬S)` — **reversibility (初错可逆率)** (§5.11 `l3_reversibility_rate`): among first-wrong tasks, the fraction that later produce the correct answer under feedback.
- `P_lock = P(F | A ∧ ¬S)` — **L4 lock**: among first-wrong-but-activated tasks, the fraction locked to the correct final answer.
- `q_stay = P(F | S)` — **L4 anti-interference**: among first-correct tasks, the fraction not misled (= 1 − misled rate).

Because `S ⊆ A` (a correct round-0 answer trivially "appeared"), the ceiling and the final accuracy decompose as

```
P_act = μ + (1 − μ)·r
```

```
final_acc = μ·q_stay + (1 − μ)·r·P_lock
```

The first term is "knew it and was not misled"; the second is "did not know it, recovered it, and locked it". This single identity carries L1/L2 (μ), L3 (`P_act` via `r`), and L4 (`P_lock`, `q_stay`). The gap

```
locking_loss = P_act − final_acc
```

is the fraction of tasks where the correct answer was within reach but not locked in — the model's avoidable loss.

**Self-consistency check (deepseek, arm C, 250 tasks).** μ-hat = 207/250 = 0.828 (round-0 accuracy), r = 22/43 ≈ 0.512 (reversibility), P_lock = 13/22 ≈ 0.591, q_stay = 196/207 ≈ 0.947, and P_act = μ + (1 − μ)·r = 0.828 + 0.172·0.512 ≈ 0.916. Then μ·q_stay = 0.784 and (1 − μ)·r·P_lock = 0.052, summing to 0.836 — exactly the observed final accuracy — leaving a locking loss of 0.916 − 0.836 ≈ 0.080 (≈ 8 pp). The decomposition is internally consistent on the existing arm-C data.

**Cost side.** `cost(R) = Σ_{r=1..R} tokens(r)`, where finance's repeated tool re-injection makes tokens(r) grow (documents re-inserted per step). R is governed by the N = 3 early stop, so stable tasks (high q_stay) halt at 3 rounds at low cost while oscillating tasks (finance) run the full R at high cost — cost is coupled to the L4 stability profile.

**New evaluation target.** Replace the single accuracy scalar with a capability-layered profile:

```
model_score = ( μ, P_act, r, P_lock, q_stay, cost(R) )
```

This distinguishes a model strong at baseline (high μ) from one with a wide reach but weak locking (high `P_act`, low `P_lock`), and from one recovering chiefly through feedback (high `r`) — possibly equal final accuracy but different ceiling, dynamics, and cost — and supports an accuracy–cost frontier stratified by capability layer. `P_act` is the primary "model ceiling" metric the analysis now emphasises over accuracy alone.

**Three-arm ablation (statistical design).**

| Arm | Feedback | Estimates | Purpose |
|---|---|---|---|
| A | none (single pass) | μ | L1/L2 intercept |
| B | directionless noise | μ_B | control for multi-round / test-time |
| C | directional weak critic (tier C) | μ + Δ, P_act, r, P_lock, q_stay | directional lift + L3/L4 internals |

**Reuse of arm A.** Arm C's round 0 is a no-feedback single pass, so it already supplies the arm-A μ estimate (init accuracy); arm A need not be run separately. Only arm B must be added to identify Δ.

The B-arm noise generator must match C in perturbation strength and message format while erasing direction (e.g. shuffle C's top-K leaf labels, or draw a random leaf from the same family prior); otherwise C vs B is not a clean Δ.

**Data status (2026-10-06).** Arm C exists today (3 models × 250 tasks) and already yields μ-hat, P_act, r, P_lock, q_stay per model (§5.11 `loop_summary`). Δ remains unidentified until arm B is run against the same question set.

---

## 6. Reproducibility and Implementation

The full reproducibility standard (three-tier reproduction, repository layout, seeds, config manifest, experiment log, one-command reproduction) is specified in `docs/REPRODUCIBILITY.md`. Key invariants:

- All parameters read from configuration files (no hard-coding); exact dependency pinning.
- Deterministic components (data processing, statistics, plotting) are fully reproducible; LLM sampling is logged with explicit temperature and seed, and each experiment is run ≥ 3 times with different seeds.
- Trajectories, judgments, and curves are stored under `results/` with per-run `manifest.json` (hashes); each run maps to a git commit `[EXP] name | config=… | seed=…`.
- Evidence-chain convention: `claim → experiment-log record → config + seed → raw trajectories → code version`.

### 6.1 Environment and compute

**Hardware**: Apple M4 MacBook Air, 24 GB unified memory (no CUDA). No local model loading is planned (local MLX / Ollama / llama.cpp is deprecated).

| Tier | Feasible locally | Throughput (est.) |
|---|---|---|
| 0.5B–3B | yes | >60 tok/s |
| 7B–8B (Q4) | yes | ~30–50 tok/s |
| 14B (Q4) | marginal | ~15–20 tok/s |
| 32B / 70B | no | — |

**Model-routing strategy**: Phase 1 loads **no model locally** — all three mid-tier models run on the Aliyun Token Plan. For Phase 2, weak-tier models are planned to run on a **rented Aliyun instance** rather than local MLX / Ollama / llama.cpp; HF is abandoned.

---

## 7. Budget and Timeline

**Budget** (planning estimates; re-quote at execution time based on exact model pricing).

| Scenario | Phase 1 (probe) | Phase 2 (feasibility) | Phase 3 (full) |
|---|---|---|---|
| Top-tier-API-heavy (nominal) | < $200 | ~$1,500 | ~$10,000 |
| Budget-tier API + local (M4-adapted) | < $50 | ~$300 | ~$1,500–3,000 |

The dominant cost driver is the number of API model × question × round cells plus LLM-as-a-Judge reuse; the budget-tier scenario keeps total program API cost within the low thousands of dollars. Local inference is cost-free but is the throughput bottleneck for large matrices.

**Timeline** (nominal ≈ 90 working days; buffer included).

| Phase | Duration | Milestone |
|---|---|---|
| Phase 1 — probe | ~1 week | signal-validity report and go/no-go |
| Phase 2 — feasibility | ~2–3 weeks | scaled validation + ablation matrix |
| Phase 3 — full matrix | ~6 weeks | tensor decomposition + curve fitting + extrapolation |
| Analysis & theory | ~4 weeks | convergence model + cost forecast |
| Writing & submission | ~4–6 weeks | manuscript + appendix + code repository |

**Compute escalation** (in order): free inference tiers (HF / Groq / Together / Replicate) for small models → spot cloud GPUs (RunPod / Lambda / Vast) for large/parallel → offload more tasks to budget API.

---

## 8. Contributions and Risk

### 8.1 Three contributions (layered)

1. **Existence (empirical).** A clean external meta-cognitive proxy induces a systematic, statistically significant, attributable change in model output. Answers *"is metacognitive intervention effective?"*
2. **Cost–reliability model (theoretical).** The cost–reliability relationship is described by a unified extreme-value distribution (§3.4), redefining the accuracy paradigm from a static number to a curve family. Answers *"how large is the effect, at what cost?"*
3. **Capability diagnosis (diagnostic).** Curve shape and capability-axis decomposition localize *which* capability a model lacks and what to strengthen, validated by an independent intervention (treatment-verifies-diagnosis). Answers *"why, and how to improve?"*

### 8.2 Risks and the informative negative result

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Proxy design unsound → no systematic change | medium | high | minimal design; rapid pre-experiment |
| Capability axes not clearly separable | medium | medium | fall back to direct curve comparison |
| Cost too high to observe change within N steps | low | medium | pin typical round count via pre-experiment |
| No accuracy gain within N steps | high | low | activation–locking decoupling |
| Oscillation, no convergence | medium | medium | stopping criteria (threshold / max-round / no-improvement) |
| Weak-critic evidence has no discriminating power (98% FPR; reversed for finance/mmlu) | high | high | recorded 2026-10-06; go/no-go — re-derive evidence or accept critic as a pure direction hint |
| Weak critic under-powered (137 wrong exemplars; 0–20 per leaf family) | medium | high | enlarge bank in Phase 2; keep deterministic gold-free features for reproducibility |

**Methodological stance.** Negative results are informative: if feedback makes a model increasingly wrong, that reveals an absent or broken meta-cognitive loop — the more consequential diagnosis. The framework is robust to either outcome.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.17 | 2026-10-07 | §6.1 hardware/model-routing: local MLX/Ollama deprecated; weak tier via rented Aliyun instance. |
| 0.16 | 2026-10-07 | Added §2 core positioning (new evaluation paradigm — round-dimension dynamic observables + cost–reliability/risk as centre of gravity; weak-critic existence proof as subordinate claim) and nearest-neighbour differentiation against Feedback Friction (arXiv:2506.11930), overthinking (arXiv:2604.10739), and activation-probe self-correction (arXiv:2606.03645). |
| 0.15 | 2026-10-07 | Marked Phase 1 complete: per-family activation/locking results (math/math500/mmlu-pro/finance/bfcl, n=50 each, 3 mid models) and the Phase 2 plan are consolidated into `docs/PHASE1_SUMMARY.md` (weak-critic mechanism + limits §3, per-family + pooled tables §4–5, Phase 2 plan §8); `docs/PHASE2_PLAN.md` merged into it and removed. |
| 0.14 | 2026-10-07 | Corrected §5.12 L3 activation semantics: `P_act` redefined as the full-reach activation rate `P(A)` (the model's accuracy ceiling, §5.11 `l3_activation_rate`), decoupled from a separate `r = P(A | ¬S)` reversibility (初错可逆率, §5.11 `l3_reversibility_rate`); decomposition rewritten as `P_act = μ + (1−μ)·r` and `final_acc = μ·q_stay + (1−μ)·r·P_lock` with an explicit locking-loss term `P_act − final_acc`; evaluation target extended to `(μ, P_act, r, P_lock, q_stay, cost(R))`. Fixed `_score_bfcl` false negatives (function-string maths-notation normalisation + list/numeric value tolerance + non-dict guard), resolving 5 state-6 BFCL tasks (correct function calls previously misjudged). |
| 0.13 | 2026-10-06 | Added §5.12 capability-layered dynamics model: latent mean μ (L1/L2 intercept) + directional lift Δ = E[Y_C] − E[Y_B] (L3 existence claim, C-vs-B contrast); L3/L4 separation inside arm C via P_act / P_lock / q_stay with the identity final_acc = μ·q_stay + (1 − μ)·P_act·P_lock (self-consistency verified on deepseek arm-C data); cost side cost(R); layered evaluation target model_score = (μ, P_act, P_lock, q_stay, cost(R)); three-arm statistical design with arm A reused from round 0 and only arm B outstanding. |
| 0.12 | 2026-10-06 | Added §5.11 feedback-loop implementation: bounded re-solve loop (round 0 baseline + R=10 feedback rounds), N=3 consecutive-identical early stop, tier-C critic feedback, temperature=0, independent re-solve with cross-round tool cache, zero-LLM scoring with finance-qualitative T2-judge rescue (registered intervention; full answers recorded for offline re-judge), six-end-state outputs; made the weak-critic prediction race-free (`_predict`). |
| 0.11 | 2026-10-06 | Upgraded §3.1 to a four-layer hypothesis (added L4 = correction/locking) plus a static-baseline-vs-round-dynamics reconstruction (intercept = L1+L2, shape k = f(L3,L4)); appended §5.8 Rev-3 (exemplar retrieval + evidence threshold + error_score; critic redefined as a direction/confidence hint, not a verifier) with its recorded risks; added §5.10 six end-states and §8.2 weak-critic risk rows. |
| 0.10 | 2026-10-06 | Rewrote §5.8 from rule-based metacognition to the **weak critic**: a two-layer pipeline (taxonomy prior `build_error_taxonomy.py` + Naive-Bayes classifier `build_weak_critic.py`, Top-3 over the fixed 19 leaves); added gold-free static cause/attention fields per leaf and a three-tier feedback ablation (A type+prob / B +cause / C +cause+attention). |
| 0.9 | 2026-10-05 | Consistency pass: §5.1 models/task families, §5.3 stages, §5.7 check-2, and §6.1 routing aligned to Phase-1 reality (3 mid Aliyun models, no local loading, rule-based critique). |
| 0.1 | 2026-09-26 | Initial working draft (internal). |
| 0.2 | 2026-09-26 | Restructured into an academic experiment protocol; incorporated the two-uncertainty motivation, three-layer capability hypothesis, three candidate mathematical framings, cost–reliability extreme-value form, three decouplings, and three contributions; removed process/decision content (moved to `DECISION_LOG.md`). |
| 0.3 | 2026-09-27 | Phase-1 probe model tiers + task set revised: weak Qwen3.5-4B+TinyLlama-1.1B (local), mid DeepSeek-V4-Flash+Qwen3.8-Flash (API), strong Claude Opus 5.5+GPT-6 Astra (deferred); tasks math/logic/finance 50 each (150 Qs). |
| 0.4 | 2026-09-28 | Added §5.2 Task-Bank Blueprint (provisional): L1/L2 family × benchmark × capability-layer (L1-L4) × evaluator × token-budget matrix, each probe set fixed at 50 questions; renumbered former §5.2-5.5 to §5.3-5.6. |
| 0.5 | 2026-09-29 | Added §5.7 Phase-1 (probe) execution plan: four feasibility checks (capability decomposition / Bayesian proxy / L3-L4 discrimination / cost–reliability curves), build-before-burn order with N=10 in 3-round segments, and no-human-labelling validation; corrected §5.3 Stage-1 human-labelled errors to outcome-based validation. |
| 0.6 | 2026-09-29 | Added §5.9 three-tier scoring framework (T1 deterministic / T2 LLM re-judge rescue / T3 multi-judge voting), intervention registration, and the false-negative convention (correct = positive). |
| 0.8 | 2026-09-29 | Rewrote §5.8 critique from embedding-based retrieval to a simple rule-based metacognition: three gold-free signal layers (answer shape / process primitives / history delta), static ranking prior, reflective-guide Top-N probes; recorded the simplicity constraint and the L1 no-process data limitation. |
| 0.7 | 2026-09-29 | Revised §3.6 decoupling 1 and §5.4: a static tensor cannot invert L1/L2 (a priori task-family partition; rank-1 projection, empirically verified) — decompose only as taxonomy-coverage diagnostic; added §5.10 L3/L4 round-dimension scheme (taxonomy-free activation/locking/correction events + two decomposition carriers: state transition & trajectory). |
| 0.6 | 2026-09-29 | Renamed the metacognitive proxy from "evaluator" to a single embedding-based **critique** module; added §5.8 spec (offline annotated error bank + online instance-similarity retrieval; deterministic shallow-feature embedding; parallel Top-N candidate revisions with agent self-selection; full N=10 rounds, no early stopping); recast L3/L4 as activation-without-locking. |