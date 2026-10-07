# Phase 1 Summary and Phase 2 Plan

**Document type**: Phase 1 (probe) summary + Phase 2 plan · **Version**: 0.2 · **Date**: 2026-10-07
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

| Quantity | Definition |
|---|---|
| **Activation rate** `P(A)` | Fraction of tasks where the correct answer appears in ≥ 1 round. The model's *reachable ceiling* (upper bound on accuracy), not a locking property. |
| **Locking rate** `P(F \| A)` | Fraction of activated tasks finalized correct — how much of the reachable ceiling is actually held. |
| **Locking loss** | `P(A) − P(final)`, in percentage points. The avoidable loss between ceiling and final accuracy. |
| **Never-activated** (state 6) | Tasks where the correct answer never appears in any round — a *true reachability* (L1/L2) gap, distinct from a locking gap. |

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

- The activation/locking decomposition **does discriminate models once split by family**,
  and the signal lives entirely on the round dimension — the only place the plan (§5.4)
  argued inversion is possible. The result is therefore methodologically non-trivial.
- The dominant deficit **type differs by model**: glm = locking (math500) + reachability
  (finance); qwen = locking (bfcl) with consistently high activation; deepseek = nearest to
  balanced.
- The instrument works (taxonomy, critique, six end-states, self-consistent decomposition);
  what remains unestablished is the *causal effect* of the proxy (no no-proxy / random-feedback
  control arm) and the *cost* axis (no token instrumentation).

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

**Strong tier** (`Claude Opus 5.5`, `GPT-6 Astra`). Blocked: no domestic channel carries Claude/GPT,
and this collides with the "no OpenAI" constraint (open decision §8.8). If opened, run strong models
only on the discriminating cells (finance + a hard L1 anchor), arm C only, reduced subset.

**Principle.** Minimum span along the capability axis that breaks the flat model axis — adding one
clearly-weak model is the cheapest, highest-leverage move and does not wait on the strong tier.

### 8.3 Control arms — prove the proxy raises the ceiling

- **arm A** (no-proxy self-loop, R rounds, no feedback); **arm A2** (random/placebo directions);
  **arm C** (weak critic tier C, the Phase-1 config reused as treatment).
- **Test.** `Δ_act = P(A)_C − P(A)_A` and `Δ_final = P(F)_C − P(F)_A` per family; Fisher exact on
  counts + paired bootstrap on rates; one-sided p < 0.05.
- **Go/stop.** Go if C beats both A and A2 on ≥ 1 family; stop if C ≈ A2 (confirms the §3 critic
  limits as fatal to the present design and redirects to §8.4).

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

### 8.6 Round-level dynamics — k/θ cost curves

Fit the extreme-value hazard to the per-round correctness time series per model × family:

```
P(correct appears by round r) = 1 − exp(−(r / θ)^k)
```

with **k = activation shape** (k > 1 acceleration; k < 1 oscillation) and **θ = locking scale**.
Estimate k from the cumulative activation curve, θ/locking from `P(F | A ∧ ¬S)` per round; the cost
axis is steps (already logged) plus **tokens** (needs per-round instrumentation — at minimum for
finance). Output the first cost–reliability curves, and out-of-sample: predict rounds-to-90% from
the first 2–3 rounds.

### 8.7 Execution order and dependencies

| Step | Work | Depends on | Blocks |
|---|---|---|---|
| P2.1 | Control arms A / A2 vs C (§8.3) | nothing (cheap, L1-first) | critic verdicts, §8.4 |
| P2.2 | Add weak tier, FC-carrier ablation (§8.2) | Aliyun channel | model-axis width |
| P2.3 | Critic optimization (§8.4) | P2.1 baseline | proxy quality |
| P2.4 | k/θ fitting + token instrumentation (§8.6) | existing trajectories + P2.2 | cost–reliability |
| P2.5 | Strong tier + family expansion (§8.2, §8.5) | §8.8 channel decision | full matrix |

### 8.8 Open decisions for discussion

1. **Strong-tier channel.** No domestic endpoint serves Claude/GPT; using one contradicts the "no
   OpenAI" constraint. Options: resolve to overseas endpoint + relax the constraint for strong tier
   only / construct the axis from weak + mid + model-size scaling within a domestic provider / defer
   strong tier to Phase 3.
2. **FC-carrier convention.** Confirm `fc_carrier` is recorded as an intervention field so the
   native-vs-ReAct ablation is auditable.

## 9. Provenance and caveats

- **Config**: temperature = 0, single deterministic arm C (tier-C weak critic). No arm A / A2 was
  run; `Δ` is not yet estimable.
- **BFCL scoring**: recomputed with the v0.14 fixed evaluator (five false-negative function calls
  resolved; 0 regressions).
- **Finance qualitative scoring**: registered T2 LLM-judge rescue, false-negative-prone; finance
  locking loss is measured with uncertainty.
- **Cost**: HuggingFaceAgent drops usage, so no per-round token/cost data exists in this run.

---

*Generated from `experiments/feedback_loop_20261006_173715/{model}/loop_trajectories.jsonl`; see
`src/run_feedback_loop.py` and `src/evaluator.py` for the scoring code.*
