# A Proxy-Based Meta-Cognitive Evaluation Framework for LLM Agents

**Document type**: Research plan (experiment protocol) · **Version**: 0.2 (Draft) · **Date**: 2026-09-26
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

---

## 3. Theoretical Framework

### 3.1 Three-layer capability hypothesis

We hypothesise three separable capabilities; this separation is the conceptual core.

| Layer | Capability | Definition |
|---|---|---|
| **L1** | Base | Single-shot correctness of the naked model, with no external aid — the raw latent accuracy. |
| **L2** | Augmentation | The extent to which the model is embedded in an agent system: function/tool calling, retrieval harness, workflow orchestration, multi-sample voting, search, retry, best-of-N. A property of *model-plus-system*, not of the model alone. |
| **L3** | Meta-cognitive | The ability to monitor one's own reasoning, receive external signals, and self-correct accordingly. Largely absent today; this is what the proxy is designed to probe. |

**Terminology note.** The middle layer is named *Augmentation* (in the sense of agent augmentation) because it is not merely optimisation — it is any capacity gained by placing the model inside an augmented system. A model with weak L1 but strong L2 may still solve a task purely as an engineering/cost outcome. Our role is **not** to improve L1 or L2 directly; we construct an external signal system and test whether the model can use it.

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

1. **Capability-dimensional decoupling.** Do not pre-impose L1/L2/L3; use tensor decomposition to extract latent capability axes from the data. Expectation: the proxy's effect concentrates on a few feedback-sensitive latent dimensions.
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

- **Task families** (Probe: math (GSM8K), commonsense (MMLU), finance (FAB); Feasibility adds code (HumanEval), factual consistency (TruthfulQA), multi-hop (HotpotQA), translation (WMT zh–en); Full extends to 12–15 families, with L2/L3-level items ≥ 40%).
- **Models** (three tiers):
  - *Weak*: Qwen2.5-1.5B, TinyLlama-1.1B (local);
  - *Mid*: Qwen2.5-7B, Llama-3.1-8B (local, Q4);
  - *Strong*: GPT-4o-mini, Claude-3-Haiku (API); full phase extends to GPT-4o, Claude-3.5-Sonnet, Gemini-1.5-Pro/Flash, DeepSeek-V4-Flash, etc.

### 5.2 Experimental stages

| Stage | Purpose | Configuration |
|---|---|---|
| **1. Signal validity** | Build the error taxonomy + rule-based evaluator; validate Top-K against human-labelled errors. | Finance (FAB) + math (GSM8K); validate the proxy signal. |
| **2. Trajectory collection** | Run the feedback loop up to ~10 rounds over a fixed probe set; log full trajectories (correctness, error type, output distance, cumulative cost per round). | DeepSeek, GPT-4o-mini, Llama-3; gather cost–accuracy data. |
| **3. Convergence analysis** | Assess convergence of the population trajectory; compare the three mathematical framings (§3.5). | Math · Finance · Fact QA · Open generation; test capability convergence. |
| **4. Cost prediction** | Fit converged trajectories; predict required cost from the first 2–3 rounds, out-of-sample. | Cross-model and cross-domain; validate the cost forecast. |

### 5.3 Capability matrix and tensor decomposition

Construct a tensor **T ∈ R^{M × T × E}** (model × task family × error type), optionally 4th-order with round R. Factorize via PARAFAC / Tucker / PCA to extract latent capability axes. The diagnostic output is a structured report mapping each model to bottleneck capability axes (with factor loadings relative to a model-class mean) and a recommended intervention.

### 5.4 Ablation matrix

| ID | Condition | Alternative explanation ruled out |
|---|---|---|
| A1 | No proxy; model self-loops N rounds | gain is from "more rounds", not the proxy |
| A2 | Proxy emits random feedback (not prior-based) | gain is from "someone told me to check", not correct direction |
| A3 | No voting; take first revision | gain is from "aggregating candidates", not correction itself |
| A4 | Uniform prior instead of statistical prior | gain is from "prior existence", not prior quality |
| A5 | Different temperature (0 vs 0.7 vs 1.0) | sampling randomness |
| A6 | Different feedback strength (Top-1 vs Top-3 vs Top-5) | signal-strength effect |

### 5.5 Metrics and statistics

- **Observed**: activation rate, first-activation round, locking rate.
- **Test**: Fisher's exact test, p < 0.05, for activation-rate differences between proxy and baseline arms.
- **Success criteria** (any): a statistically significant activation-rate gain on ≥ 1 task family; or an activation gain on ≥ 1 weak model.
- **Stop conditions** (any): no activation gain on any model × family; gain < 5%; ablation shows equal gain without the proxy.

---

## 6. Reproducibility and Implementation

The full reproducibility standard (three-tier reproduction, repository layout, seeds, config manifest, experiment log, one-command reproduction) is specified in `docs/REPRODUCIBILITY.md`. Key invariants:

- All parameters read from configuration files (no hard-coding); exact dependency pinning.
- Deterministic components (data processing, statistics, plotting) are fully reproducible; LLM sampling is logged with explicit temperature and seed, and each experiment is run ≥ 3 times with different seeds.
- Trajectories, judgments, and curves are stored under `results/` with per-run `manifest.json` (hashes); each run maps to a git commit `[EXP] name | config=… | seed=…`.
- Evidence-chain convention: `claim → experiment-log record → config + seed → raw trajectories → code version`.

### 6.1 Environment and compute

**Hardware**: Apple M4 MacBook Air, 24 GB unified memory (no CUDA). Local inference via MLX / Ollama / llama.cpp.

| Tier | Feasible locally | Throughput (est.) |
|---|---|---|
| 0.5B–3B | yes | >60 tok/s |
| 7B–8B (Q4) | yes | ~30–50 tok/s |
| 14B (Q4) | marginal | ~15–20 tok/s |
| 32B / 70B | no | — |

**Model-routing strategy**: weak/mid tiers run locally (free); strong tier runs on budget API. The three-tier design and the Mac's capabilities are complementary: the weak tier (which API providers do not serve) is exactly what the Mac runs natively, and the strong tier (which the Mac cannot run) is exactly what budget APIs make cheap.

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

**Methodological stance.** Negative results are informative: if feedback makes a model increasingly wrong, that reveals an absent or broken meta-cognitive loop — the more consequential diagnosis. The framework is robust to either outcome.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | Initial working draft (internal). |
| 0.2 | 2026-09-26 | Restructured into an academic experiment protocol; incorporated the two-uncertainty motivation, three-layer capability hypothesis, three candidate mathematical framings, cost–reliability extreme-value form, three decouplings, and three contributions; removed process/decision content (moved to `DECISION_LOG.md`). |