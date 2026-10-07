# Phase 1 Summary: Per-Family Activation and Locking

**Document type**: Phase 1 (probe) summary · **Version**: 0.1 · **Date**: 2026-10-07
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
| **Locking rate** `P(F | A)` | Fraction of activated tasks finalized correct — how much of the reachable ceiling is actually held. |
| **Locking loss** | `P(A) − P(final)`, in percentage points. The avoidable loss between ceiling and final accuracy. |
| **Never-activated** (state 6) | Tasks where the correct answer never appears in any round — a *true reachability* (L1/L2) gap, distinct from a locking gap. |

## 3. Per-family results (`n = 50` per cell)

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

## 4. Pooled results (250 tasks)

| Model | r0 | Activation | Final | Locking | Loss (pp) | Never-activated |
|---|---|---|---|---|---|---|
| deepseek-v4-flash | 84.8% (212) | 93.6% (234) | 85.6% (214) | 91.5% | 8.0 | 16 |
| glm-5.3 | 79.2% (198) | 90.4% (226) | 78.0% (195) | 86.3% | 12.4 | 24 |
| qwen3.8-flash | 80.8% (202) | 94.0% (235) | 84.4% (211) | 89.8% | 9.6 | 15 |

## 5. Observations

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

## 6. Conclusions

- The activation/locking decomposition **does discriminate models once split by family**,
  and the signal lives entirely on the round dimension — the only place the plan (§5.4)
  argued inversion is possible. The result is therefore methodologically non-trivial.
- The dominant deficit **type differs by model**: glm = locking (math500) + reachability
  (finance); qwen = locking (bfcl) with consistently high activation; deepseek = nearest to
  balanced.
- The instrument works (taxonomy, critique, six end-states, self-consistent decomposition);
  what remains unestablished is the *causal effect* of the proxy (no no-proxy / random-feedback
  control arm) and the *cost* axis (no token instrumentation).

## Appendix: provenance and caveats

- **Config**: temperature = 0, single deterministic arm C (tier-C weak critic). No arm A
  (self-loop) or A2 (random feedback) control was run in this phase; `Δ = E[Y_C] − E[Y_A]`
  is therefore not yet estimable.
- **BFCL scoring**: recomputed offline with the v0.14 fixed evaluator (five false-negative
  function calls — notation/format mismatches — resolved; 0 regressions).
- **Finance qualitative scoring**: uses the registered T2 LLM-judge rescue, which is
  false-negative-prone; finance locking loss is therefore measured with uncertainty.
- **Cost**: HuggingFaceAgent drops usage, so no per-round token/cost data exists in this run.

---

*Generated from `experiments/feedback_loop_20261006_173715/{model}/loop_trajectories.jsonl`; see
`src/run_feedback_loop.py` and `src/evaluator.py` for the scoring code.*
