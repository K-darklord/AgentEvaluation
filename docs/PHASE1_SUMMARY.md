# Phase 1 Summary and Phase 2 Plan

**Document type**: Phase 1 (probe) summary + Phase 2 plan · **Version**: 0.4 · **Date**: 2026-10-08
**Companion documents**: `RESEARCH_PLAN.md` (protocol §5), `REPRODUCIBILITY.md` (config provenance).

---

## 1. Objective and scope

Phase 1 verifies, at minimum scale, that an external metacognitive proxy together with
round-dimension tracking can decompose an agent's capability from a single static accuracy
number into a layered profile: **activation** (the model's reachable ceiling) versus
**locking** (whether a reached answer is held to the final round). It is a *probe*, not a
claim about model quality — the question is whether the instrument discriminates, not
whether any model "wins".

**Setup.** Three mid-tier models (deepseek-v4-flash, qwen3.8-flash, glm-5.3, all Aliyun
Token Plan, no local loading) × 250 tasks (5 families × 50; L1:L2 = 3:2) × up to 11
rounds of tier-C weak-critic feedback. Temperature = 0 (deterministic), single arm C (no
no-proxy or random-feedback control). Zero-LLM scoring (T1), with a registered T2 LLM
judge rescue for qualitative finance answers.

## 2. Definitions

### 2.1 Capability layers (L1–L4)

Four separable capabilities (RESEARCH_PLAN §3.1); the layer labels used throughout this document and the weak-critic feedback.

| Layer | Name | Definition |
|---|---|---|
| L1 | Base | Single-shot correctness of the naked model with no external aid — raw latent accuracy. |
| L2 | Augmentation | Capability gained by embedding the model in an agent system (function/tool calling, retrieval, orchestration) — a property of model-plus-system, not the model alone. |
| L3 | Meta-cognitive (activation) | Given an external error signal, activates the correct answer at least once across feedback rounds — the reachable ceiling. |
| L4 | Correction (locking) | Locks onto the correct answer — resists a misleading signal, holds a correct answer, does not oscillate. |

> **RL framing (2026-10-08).** L3/L4 admit a sharper reading developed in
> `docs/L3L4_RL_REDISTRIBUTION.md`: the test-time feedback loop is the directional, sampling-time
> analogue of train-time RL (GRPO/RLVR) — both **redistribute probability mass** over reachable
> paths rather than create capability. L3 is then *meta-cognition* (re-activating the correct path
> under a possibly-noisy signal), and L4 is *locking* = the robustness RL training is meant to buy.
> The arm ordering `A3 (no-direction sampling) ≤ C (noisy critic) ≤ C* (oracle verifier)` frames the
> testable claim **`C > A3`**. See RESEARCH_PLAN §5.13.

### 2.2 Observed quantities

| Quantity | Definition |
|---|---|
| **Activation rate** `P(A)` | Fraction of tasks where the correct answer appears in ≥ 1 round. The model's *reachable ceiling* (upper bound on accuracy), not a locking property. |
| **Locking rate** `P(F \| A)` | Fraction of activated tasks finalized correct — how much of the reachable ceiling is actually held. |
| **Locking loss** | `P(A) − P(final)`, in percentage points. The avoidable loss between ceiling and final accuracy. |
| **Never-activated** (state 6) | Tasks where the correct answer never appears in any round — a *true reachability* (L1/L2) gap, distinct from a locking gap. |

### 2.3 Six end-states

Each (model × task) loop run lands in exactly one of six mutually exclusive states, jointly operationalising L3 (activation) and L4 (locking). `start` / `final` = round-0 / last-round correctness; “appears” = the correct answer surfaces in ≥ 1 round.

| State | Start | Correct appears | Final | Reading |
|---|---|---|---|---|
| 1 | correct | never flips | correct | L4 full — answer held across all rounds |
| 2 | correct | flips wrong | wrong | L4 deficit — a correct start is misled into an error |
| 3 | correct | flips, then recovers | correct | L4 weak but recoverable |
| 4 | wrong | appears | correct | L3 + L4 full — activated, then locked |
| 5 | wrong | appears | wrong | L3 present, L4 deficit — activated but not held (oscillation) |
| 6 | wrong | never appears | wrong | L3 absent — the signal cannot activate the answer |

## 3. The weak-critic proxy — mechanism and current limits

The round-1..R feedback is emitted by a **weak critic**: a deterministic, *gold-free* classifier
that maps one answer onto a fixed 19-leaf error taxonomy and returns the Top-3 most likely error
directions. It never sees the gold answer, never assigns correctness, and never calls a judge — its
only job is to hand the agent a directional "re-examine this" hint, which the agent may follow or
ignore. Correctness stays entirely in the offline evaluation layer.

**Mechanism (rev 3 — exemplar retrieval).** For a candidate answer the critic computes an evidence
score

```
s = W_Q · sim_q(question) + W_A · sim_a(answer),   W_Q = 0.7, W_A = 0.3
```

i.e. a weighted similarity to the nearest annotated wrong-answer exemplars; the error signal is
`error_score = family_base_rate × s`. An answer is *flagged* only when `s ≥ 0.1` (a "disease-test
positive" cut); the feedback then states the top direction + confidence + `error_score` as a soft
signal. Feedback tiers A/B/C add progressively richer text (type+probability / +cause / +attention)
for ablation, and the agent always decides whether to revise.

**Similarity computation.** `sim_q` is a number-blind TF-IDF cosine over the question: numbers are replaced with a `NUM` placeholder (math also tokenizes operators `+-*/=<>^()[]{}`), words are weighted by TF × IDF (built per family from the wrong bank), and the question is compared against the family's wrong-answer exemplars. `sim_a` is a per-family shallow rule: numeric closeness for math/math500, option-letter set equality for mmlu-pro, Jaccard bag-of-words overlap for finance, and JSON function-name + argument-key match for bfcl. Both are computed over the annotated wrong bank only, never against the gold.

**Why weak.** Inference is statistical, from shallow gold-free shape features (empty output,
number count, option-letter count, tool-call count, valid-JSON), anchored on a small annotated
wrong-answer bank — never from the gold. This is deliberate: the proxy must succeed with minimal
external intervention.

**Current limits (tracked go/no-go item, §8.2).** The evidence `s` does **not** discriminate correct
from wrong answers: on the correct-answer set the flag rate is ~98%, i.e. the critic flags almost
everything. Root cause: `s` is dominated by question similarity (`W_Q = 0.7`), which is structurally
high for template-heavy families (bfcl ≈ 0.65, math500 ≈ 0.46) and low for open-domain families
(finance ≈ 0.16, mmlu ≈ 0.10); in finance/mmlu the evidence is additionally *reversed* (correct
answers resemble the wrong bank more than wrong answers, which are truncated). A single 0.1
threshold therefore yields wildly imbalanced flag counts across families (finance ≈ 83 vs mmlu ≈ 11),
and the top-1 direction hit rate is weak on finance (~45%), largely a large-leaf-prior fallback. The
consequence: the weak critic's **causal effect is not yet established** — which is exactly why §8
(Phase 2) opens with the control arms.

## 4. Per-family results (`n = 50` per cell)

Percentages are followed by raw counts in parentheses. `r0` = round-0 accuracy.

| Family | Model | r0 | Activation | Final | Locking | Loss (pp) | Never-activated |
|---|---|---|---|---|---|---|---|
| math (GSM8K) | deepseek | 96% (48) | 98% (49) | 98% (49) | 100.0% | 0 | 1 |
| | glm | 98% (49) | 98% (49) | 98% (49) | 100.0% | 0 | 1 |
| | qwen | 100% (50) | 100% (50) | 100% (50) | 100.0% | 0 | 0 |
| math500 (MATH-500) | deepseek | 86% (43) | 92% (46) | 86% (43) | 93.5% | 6 | 4 |
| | glm | 76% (38) | **94% (47)** | **76% (38)** | **80.9%** | **18** | 3 |
| | qwen | 70% (35) | 90% (45) | 88% (44) | 97.8% | 2 | 5 |
| mmlu-pro | deepseek | 84% (42) | 92% (46) | 88% (44) | 95.7% | 4 | 4 |
| | glm | 80% (40) | 92% (46) | 86% (43) | 93.5% | 6 | 4 |
| | qwen | 88% (44) | 96% (48) | 94% (47) | 97.9% | 2 | 2 |
| finance (FAB, L2) | deepseek | 58% (29) | 86% (43) | 56% (28) | 65.1% | 30 | 7 |
| | glm | 42% (21) | **68% (34)** | **32% (16)** | **47.1%** | **36** | **16** |
| | qwen | 52% (26) | 84% (42) | 52% (26) | 61.9% | 32 | 8 |
| bfcl (L2) | deepseek | 100% (50) | 100% (50) | 100% (50) | 100.0% | 0 | 0 |
| | glm | 100% (50) | 100% (50) | 98% (49) | 98.0% | 2 | 0 |
| | qwen | 94% (47) | 100% (50) | 88% (44) | 88.0% | 12 | 0 |

## 5. Pooled results (250 tasks)

| Model | r0 | Activation | Final | Locking | Loss (pp) | Never-activated |
|---|---|---|---|---|---|---|
| deepseek-v4-flash | 84.8% (212) | 93.6% (234) | 85.6% (214) | 91.5% | 8.0 | 16 |
| glm-5.3 | 79.2% (198) | 90.4% (226) | 78.0% (195) | 86.3% | 12.4 | 24 |
| qwen3.8-flash | 80.8% (202) | 94.0% (235) | 84.4% (211) | 89.8% | 9.6 | 15 |

## 6. Observations

1. **The pooled number hides the signal.** Pooled activation differs by only ≤ 4 pp across
   models; the per-family split exposes separations of 18–36 pp in specific cells.

2. **math500 is the sharpest L1 discriminator, and it is a pure L4 (locking) story.**
   glm has the *highest* activation (94%) yet the *lowest* final (76%) → locking 80.9%,
   18 pp loss: glm reaches the answer but cannot hold it. qwen is the mirror image —
   lowest activation (90%) but near-perfect locking (97.8%, 2 pp loss). deepseek sits
   between. This is the activation–vs–locking decoupling (§3.6.2) the framework exists to
   see, invisible in any single pooled statistic.

3. **finance is the L2 pivot and the sole reachability deficit.** Activation drops for all
   models (68–86%), but glm collapses to 68% activation *and* 47% locking: 16/50 finance
   tasks where the correct answer never appears in any round — a genuine L2/reachability
   gap, not a locking issue.

4. **bfcl isolates a lock-only deficit in qwen.** qwen activates 100% (the correct function
   call appears every task) but finalizes only 88% → 12 pp locking loss with reversibility
   100% (it recovers the correct call mid-loop yet does not hold it). glm/deepseek lock
   ≥ 98%.

5. **Never-activated is a clean reachability readout.** glm has the most (24 overall, 16 in
   finance alone); qwen the fewest (15). This directly separates "true capability gap" from
   "locking gap" — the framework's core diagnostic.

6. **The model × family interaction now discriminates where the pooled number did not.** The
   ordering of models is not conserved across families (glm leads math500 activation but
   trails finance; qwen leads locking while lagging activation). This is precisely the
   capability-matrix cell structure §5.4 predicts.

## 7. Conclusions

**What Phase 1 can claim.**

- **The instrument discriminates where accuracy cannot.** Split by family, the activation/locking
  decomposition separates models that a single pooled number hides; the signal lives entirely on the
  round dimension — the only place the plan (§5.4) argued inversion is possible.
- **The dominant deficit *type* differs by model.** glm = locking (math500: 94% activation vs 81%
  locking) + reachability (finance: 68% activation); qwen = locking (bfcl: 100% activation vs 88%
  locking) with otherwise high activation; deepseek = nearest to balanced. Locking-loss is a
  *different kind* of failure from never-activation, and a single accuracy score cannot separate them.
- **glm is the cleanest single-model case.** glm's pooled accuracy (78.0%) sits close to qwen
  (84.4%) and deepseek (85.6%), yet its deficit is split across two *different* capability layers: in
  math500 it has the *highest* activation (94%) but the *lowest* locking (80.9%) — an L4 (locking)
  deficit — while in finance it has the *lowest* activation (68%) and the most never-activated tasks
  (16/50) — an L2/L3 (reachability) deficit (§6.2–6.5). A single accuracy number cannot see that one
  model fails by *reaching-but-not-holding* on one family and by *never-reaching* on another; the
  round dimension exposes both, direction-consistent under temperature = 0 (subject to the §9
  non-determinism caveat).

- **This is hard to attribute to chance.** The profile is direction-consistent under temperature = 0
  (subject to the §9 non-determinism caveat), so models with near-identical pooled accuracy still carry structurally distinct
  capability profiles. That itself is the non-triviality claim — it holds even if the weak critic were
  pure noise, because activation/locking is read off the round dimension, not off the feedback.

**What Phase 1 cannot yet claim.**

- **A causal effect of the weak critic.** Only arm C was run, so `Δ = E[Y_C] − E[Y_A]` is unestimable;
  "the proxy raises the ceiling" remains confounded with "more rounds". Needs arm A / A2 (§8.3).
- **That the profiles are intrinsic to the model.** They are measured under arm C (a directed but not
  necessarily effective feedback); an interference-free activation/locking profile needs arm A
  (self-loop, no feedback).
- **Any cost statement.** No per-round token/cost figure was aggregated in this run (Aliyun Token
  Plan); token metering begins in Phase 2 (§8.6).

## 8. Phase 2 plan

### 8.1 What Phase 1 left open

The instrument is validated, but three gaps block a publishable claim: (i) the **model axis is
nearly flat** (only mid-tier models; pooled activation spread ≤ 4 pp); (ii) **no control arm**, so
`Δ = E[Y_C] − E[Y_A]` is unestimable and "the proxy raises the ceiling" stays confounded with "run
more rounds"; (iii) **no cost axis** (token usage dropped). Phase 2 closes these three so the central
claim — *capability localized as a cost–reliability surface, discriminable on the model axis* — is
testable.

### 8.2 Model tiers: weak + strong

**Weak tier** (`qwen3.6-flash`, `glm-4.7-flash`). Function calling is the binding issue: these may
lack native FC, and a ReAct fallback is both *an intervention* and an L2-harness change. Hence
record `fc_carrier ∈ {native, react}` as an intervention field, and treat the carrier as an ablation
axis (run weak models in both arms where feasible) rather than an ad-hoc fallback. Budget staging:
weak models enter on L1 + light FC (bfcl) first; finance (heavy FC, O(N²) growth) last, only if
native FC holds.

**Deployment (weak tier).** Not on the local Mac and not via HF: weak models are planned to run on a
rented Aliyun instance (or the equivalent API channel), decided at execution time.

**Strong tier** (`Claude Opus 5.5`, `GPT-6 Astra`, or the strongest runnable model). No forced choice
(open decision §8.8): the principle is that the axis must span up to the strongest model that can be
run. Channel (overseas endpoint / rented Aliyun instance) is decided at execution; when run, restrict
to the discriminating cells (finance + a hard L1 anchor), arm C only, reduced subset.

**Principle.** Minimum span along the capability axis that breaks the flat model axis — adding one
clearly-weak model is the cheapest, highest-leverage move and does not wait on the strong tier.

### 8.3 Control arms — prove the proxy raises the ceiling, and pin the RL correspondence

**Guiding idea (2026-10-08).** The test-time feedback loop is the directional, sampling-time
analogue of train-time RL (GRPO/RLVR): both **redistribute probability mass** over already-reachable
paths via a relative signal (never an absolute gold), rather than create capability. Under this
reading L3 is *meta-cognition* (re-activating the correct path under a possibly-noisy signal) and L4
is *locking* = the robustness RL training is meant to buy. The control arms are therefore an ordered
signal hierarchy (see `docs/L3L4_RL_REDISTRIBUTION.md`):

| Arm | Signal | Measures |
|---|---|---|
| **A** | none (self-loop, R rounds, no feedback) | μ intercept |
| **A2** | random/placebo directions | multi-round placebo |
| **A3** | none — temperature sampling (T > 0, N samples) + best-of-N / majority vote | L3 **passive lower bound** (no signal use) |
| **C** | noisy weak-critic direction | L3 meta-cognitive activation |
| **C\*** | oracle verifier (gold-leak-free) | L3 **upper bound** |

The key testable claim is **`C > A3`** — directional feedback (even noisy) beats non-directional
sampling — the test-time instantiation of "advantage-guided redistribution > unguided sampling".
`C − A3` = net value of a noisy direction; `C* − C` = the critic's signal-to-noise loss. `C*` must be
**gold-leak-free** (math via sympy / formal verifier, code via a pass@k executor).

- **Test.** `Δ_act = P(A)_C − P(A)_A` and `Δ_final = P(F)_C − P(F)_A` per family (Fisher exact on
  counts + paired bootstrap on rates; one-sided p < 0.05); add `C > A3` and `C* ≥ C` as the second
  hinge.
- **A3 sampling parameters (open).** T and N must be set for statistical power and aligned with C's
  round budget (≤ 11 rounds) for a fair compute comparison; the "hit" definition (best-of-N
  reachability vs majority-vote stability) must be named separately.
- **Go/stop.** Go if C beats A and A2 on ≥ 1 family; stop if C ≈ A2 (critic limits fatal → §8.4).

### 8.4 Weak-critic optimization (simple, effective)

In order: (1) per-family threshold + weights (recalibrate from the global 0.1; down-weight/drop
`W_Q` for finance/mmlu); (2) answer-shape features for open domains (already computed, gold-free);
(3) reframe the objective from top-K hit rate to **flag specificity** `P(flag | correct)`. The
critic's value is measured only by its downstream `Δ` (§8.3) — never optimise the critic before the
causal baseline is known.

### 8.5 Task-set expansion

Priority 1 = **hard L1** (GPQA-Diamond; GSM8K is ceiling-saturated). Priority 2 = **a second
light-FC family** (multi-hop/HotpotQA or HumanEval) for a second L2 cell at near-zero token cost.
Avoid another heavy-FC sink. Each new family needs a scorer + critic schema + gold format; pilot
≤ 20 tasks before the 50-question cell.

**Sizing by activation events, not question count.** k/θ are identifiable only from tasks that first
activate *after* round 0; the expected number per (model × family) cell is `n × (P(A) − r0)` — the
reachable-but-not-yet-correct window measured in Phase 1. The curve model fundamentally targets *hard*
tasks (easy tasks saturate at round 0 and contribute no shape information, only an `P(A) ≈ 1` ceiling), so a
cell should be sized so this window yields ≥ ~30–50 observed first-activation events summed over the models;
for a hard family with `P(A) − r0 ≈ 0.3` that means n ≈ 100–170 tasks per family, i.e. the Phase-1 cells
must be expanded for the dynamics families. Easy families (GSM8K) stay small, as L1 / P(A)-ceiling
calibration only.

### 8.6 Round-level dynamics — k/θ cost curves

Fit the extreme-value hazard to the per-round correctness time series per model × family:

```
P(activated by round r) = P(A) · [1 − exp(−(r / θ)^k)]   (cure-rate form)
```

with **P(A) = activation ceiling** (the §2.2 activation rate, the curve's asymptote), **k = activation
shape** (k > 1 acceleration; k < 1 oscillation), and **θ = activation scale** (rounds to ~63% of P(A)).
Locking is a *separate fourth quantity* `P(F | A)` — not one of these three parameters — so the activation
curve is an ideal upper bound that ignores locking loss. Estimate k and θ from the cumulative activation
curve, locking from `P(F | A)` per round; the cost
axis is steps (already logged) plus token counts. P2.0 meters token usage only — prompt / completion /
reasoning tokens per round — and does not price in-code: a unit price can be applied to the recorded
token counts afterwards without a re-run, since pricing is external to metering. The agent reads
per-call `usage` into `result.total_prompt_tokens/completion_tokens/reasoning_tokens` and each feedback
round records them, so every Phase-2 run drops the axis automatically. Reasoning (thinking) tokens are
separated from content tokens (qwen's default thinking otherwise inflates completion tokens). Output the
first cost–reliability curves, and out-of-sample: predict rounds-to-90% from the first 2–3 rounds.

**Locking as a risk factor (provisional framing).** The activation curve above is the *ideal* upper
bound — it implicitly assumes locking is already mature (`P(F | A) = 1`). When locking is incomplete,
reachable-but-not-held tasks (state 5 / oscillation) inject a heavy right tail into the per-task cost
distribution; the lower the locking rate, the thicker and higher-peaked that tail becomes. Two regimes
anchor the framing: (i) an external verifier — human-in-the-loop, or an *absolute oracle* that confirms
each step — recovers the ideal upper bound, because it converts each round's "activated" answer into a
"locked" one; (ii) human-out-of-the-loop, fully autonomous running, leaves everything
activated-but-not-locked exposed, so tail risk grows as `P(F | A)` falls. Locking thus behaves like a
*risk factor* (survival-hazard-like), with a natural link to long-horizon task planning: a longer horizon
multiplies the exposure to a sub-unit locking rate. The final formulation is open and is a Phase-2
modelling target, not yet claimed.


### 8.7 Execution order and dependencies

Revised ordering (2026-10-07): **token metering first**, then the control arms, then the critic,
and only then the weak tier + task-set expansion. Every downstream run must carry a cost axis from
the start, and the control-arm data must be forward-compatible with Phase 3 so nothing is collected
twice.

| Step | Work | Depends on | Blocks |
|---|---|---|---|
| P2.0 | Token metering (§8.6): per-model prompt/completion/reasoning token counts (no in-code pricing) | nothing | token cost axis for every run below |
| P2.1 | Control arms A (no-feedback self-loop) + A2 (random-direction placebo) + A3 (temperature sampling) vs C (§8.3); tests `Δ_act`/`Δ_final` plus the `C > A3` hinge; `arm` written as a first-class field, schema forward-compatible with Phase 3 | P2.0 (costs captured) | critic verdict (§8.4), Phase-3 control baseline |
| P2.2 | Weak-critic optimization (§8.4) | P2.1 baseline | proxy quality |
| P2.3 | Weak tier + FC-carrier ablation (§8.2) and task-set expansion (§8.5) | P2.0–P2.1 (reusable control data) | model-axis width, full matrix |
| P2.4 | k/θ activation-curve fitting (§8.6) | P2.1–P2.3 (round-dimension data) | cost–reliability surface |
| P2.5 | Strong tier (§8.2) | §8.8 channel decision | axis ceiling |

**Phase-3 reuse contract.** The P2.1 control-arm trajectories (arms A / A2 / A3 / C over the core 5
families, 250 tasks) are not disposable probe artifacts — they are the control-arm slice of the
Phase-3 matrix. To reuse them without re-running: (i) `arm ∈ {A, A2, A3, C}` is written into every loop
trajectory as a first-class field; (ii) the trajectory/summary schema stays backward-compatible with
Phase-1 `loop_trajectories.jsonl` (new fields are additive; nothing is dropped or renamed);
(iii) Phase-3 only adds model/task/arm cells on top, never re-collects a control cell already
present. Because P2.0 meters tokens on the same runs, one collection serves both the Phase-2
feasibility gate and the Phase-3 full matrix.

### 8.8 Open decisions for discussion

1. **Strong-tier channel.** Not a hard blocker. The requirement is only that the strong-tier
   benchmark must be able to run the strongest available model; the concrete channel (overseas
   endpoint, rented Aliyun instance, or a domestic size-scaled stand-in) is decided at execution
   time, not pre-committed here.
2. **FC-carrier convention.** Confirm `fc_carrier` is recorded as an intervention field so the
   native-vs-ReAct ablation is auditable.

3. **Control-arm sampling regime (temperature) — decided: temperature = 0 for arms A / A2 / C,
   with A3 as the one T > 0 sampling arm.** Arm C is the Phase-1 run itself, reused as-is (no
   re-collect); Phase 2 adds arms A and A2 at the same temperature = 0. Under temperature = 0 arm A
   is a clean degenerate baseline (the round dimension does not move without feedback), which is
   exactly the intended no-intervention reference. Arm A3 is the deliberate exception: it is
   *non-directional temperature sampling* (T > 0, N samples, best-of-N / majority vote), the L3
   passive lower bound against which C is tested (§8.3, `C > A3`); its T and N are an open
   sampling-parameter decision (§8.3), not a temperature = 0 arm. Multi-seed (temperature > 0)
   sampling variance across *runs* remains deferred to the Phase-3 ablation matrix.

## 9. Provenance and caveats

- **Config**: temperature = 0, single deterministic arm C (tier-C weak critic). No arm A / A2 was
  run; `Δ` is not yet estimable.
- **BFCL scoring**: recomputed with the v0.14 fixed evaluator (five false-negative function calls
  resolved; 0 regressions).
- **Finance qualitative scoring**: registered T2 LLM-judge rescue, false-negative-prone; finance
  locking loss is measured with uncertainty.
- **Cost**: Phase-1 aggregated no per-round token usage (the run predates usage capture). Token metering
  is added in Phase 2 (P2.0, §8.6); Phase-1 itself carries no token data and is not backfillable.
- **Non-determinism (open)**: deepseek-v4-flash shows run-to-run variation under temperature = 0 on
  CoT-boundary families (AIME scored 46/50 and 42/50 across two identical batch runs). Root cause is
  **undetermined** and deferred to Phase 2; see `REPRODUCIBILITY.md` §3.4. The "reproducible under
  temperature = 0" phrasing in §7 is therefore retracted until the cause is settled.

---

*Generated from `experiments/feedback_loop_20261006_173715/{model}/loop_trajectories.jsonl`; see
`src/run_feedback_loop.py` and `src/evaluator.py` for the scoring code.*
