# Phase 2 Plan: Widening the Capability Axis and Establishing the Proxy's Causal Effect

**Document type**: Phase 2 experiment plan (draft for discussion) · **Version**: 0.1 · **Date**: 2026-10-07
**Companion documents**: `PHASE1_SUMMARY.md` (per-family results), `RESEARCH_PLAN.md` (protocol §5).

---

## 0. Motivation — what Phase 1 established and what it left open

Phase 1 validated the instrument but not the object of study. Concretely:

- The activation/locking decomposition **works** on the round dimension, and splits by family
  into interpretable, non-trivial model×family signals (glm's low-lock math500 profile,
  glm's finance reachability deficit, qwen's lock-only bfcl deficit). See `PHASE1_SUMMARY.md`.
- Three gaps block any publishable claim:
  1. **The model axis is nearly flat** — only mid-tier models were run (pooled activation
     spread ≤ 4 pp). Capability discrimination needs a deliberately widened span.
  2. **No control arm** — `Δ = E[Y_C] − E[Y_A]` (weak-critic vs. no-proxy) is not yet estimable,
     so "the proxy raises the ceiling" remains confounded with "run more rounds".
  3. **No cost axis** — token usage is dropped by the agent harness, so the cost–reliability
     core (RQ3) is unmeasurable.

**Phase 2 objective.** Close those three gaps so the central claim — *capability localized as a
cost–reliability surface, discriminable on the model axis* — is testable. Phase 2 is a go/no-go
for scaling, not a production run.

## 1. Model tiers: weak + strong (break the flat axis)

**Weak tier** (`qwen3.6-flash`, `glm-4.7-flash`; deferred from Phase 1).

- **Function calling is the binding issue.** These models may lack native function calling.
  Fallback to **ReAct** is acceptable but is an *intervention* and one that changes the L2
  harness, confounding a weak→strong L2 comparison. Two rules follow:
  - **Declare the FC carrier explicitly.** Record `fc_carrier ∈ {native, react}` per run as an
    intervention field, mirroring the `eval_tier` convention.
  - **Treat the carrier as an ablation axis, not an ad-hoc fallback.** Where feasible run the
    weak models in *both* `native` and `react` arms so "model L2" and "harness format" separate
    (extension of ablation A3, §5.5).
- **Budget staging.** Weak models enter on L1 (math / math500 / mmlu) + light FC (bfcl) first;
  finance (heavy FC, O(N²) token growth) is the last cell to add and only if native FC holds.

**Strong tier** (`Claude Opus 5.5`, `GPT-6 Astra`).

- **Channel conflict (open decision §7).** No domestic channel carries Claude/GPT; this also
  collides with the "no OpenAI" hard constraint. This must be resolved *before* strong-tier work.
- **Cost containment.** If a strong channel opens, run strong models only on the discriminating
  cells (finance + a hard L1 anchor), arm C (weak critic) only, and a reduced task subset —
  never the full 250×R loop.

**Principle.** The goal is the *minimum span along the capability axis* that breaks the flat
model axis — a clearly-weak model added to the existing mid tier is the cheapest, highest-leverage
move and does not require the strong tier to be resolved first.

## 2. Control arms — prove the weak critic raises the ceiling

This is the gating validation (plan §5.6 success criterion, §5.7 feasibility check 2).

- **arm A (no-proxy self-loop):** the model re-solves each task for R rounds with no feedback
  (or a neutral "revise if needed" prompt). Measures the ceiling gain from *rounds alone*.
- **arm A2 (random feedback):** the critic emits randomly shuffled / placebo direction signals.
  Measures the gain from *being told to check*, absent correct direction.
- **arm C (weak critic, tier C):** the Phase-1 configuration, reused as the treatment.
- **Test.** `Δ_act = P(A)_C − P(A)_A` and `Δ_final = P(F)_C − P(F)_A`, per family;
  Fisher's exact test on task-level counts + paired bootstrap on rates; one-sided p < 0.05.

**Success / stop.** Go if the weak critic beats both A and A2 on ≥ 1 family; stop (proxy
ineffective) if C ≈ A2, which would confirm the §8.2 "critic cannot discriminate" risk as fatal
to the current design and redirect effort to §3.

## 3. Weak-critic optimization (simple, effective)

Root cause already diagnosed (§8.2): the evidence `s = W_Q·sim_q + W_A·sim_a` is dominated by
question similarity (`W_Q = 0.7`), so template-rich families flag everything (~98% of correct
answers) while open-domain families (finance) are *reversed*. Three cheap, high-yield moves, in
order:

1. **Per-family threshold + weights.** Replace the global 0.1 threshold with per-family
   calibration, and down-weight `W_Q` (or drop it) for finance/mmlu where question similarity
   is structure-less.
2. **Answer-shape features for open domains.** Substitute the gold-free answer-shape priors
   (empty / number-count / tool-call count, §5.8) for embedding similarity as the evidence source
   in finance and mmlu — these are already computed and do not require new instrumentation.
3. **Reframe the critic's objective from hit rate to specificity.** The critic's failure mode is
   flagging correct answers, not missing wrong ones; optimise `P(flag | correct)` rather than
   top-K direction hit rate.

**Discipline.** The critic's value is measured only by its downstream `Δ` (§2); a hit-rate gain
that does not move `Δ_act` is noise. Establish the causal baseline first, then iterate the critic
against it (never optimise the critic before knowing arm C's effect size).

## 4. Task-set expansion (variation that references better)

Goal is **model-axis discrimination**, not question volume.

- **Priority 1 — hard L1.** Add `GPQA-Diamond` (science, ~25%) as a second letter-format L1
  family. GSM8K is ceiling-saturated (98–100%) in Phase 1 and carries no model signal; hard L1
  is where mid-tier L1 differences become visible (the math500 effect already shows this).
- **Priority 2 — a second light-FC family.** Add `multi-hop / HotpotQA` or `HumanEval` to give
  the L2 axis a second cell beyond finance/bfcl at near-zero token cost.
- **Avoid another heavy-FC sink** (web / SWE) in this phase; finance remains the single heavy-FC
  anchor.
- **Per-family onboarding cost.** Every new family needs (i) a scorer in the three-tier framework,
  (ii) a critic observation schema, and (iii) a gold format. Pilot each on ≤ 20 tasks before
  scaling to the 50-question cell.

## 5. Round-level dynamics — k/θ cost curves (steps/tokens)

Upgrade from six end-states to a parametric trajectory model per model × family (RQ2, RQ3).

- **Form.** Fit the extreme-value hazard (§3.4) to the per-round correctness time series:

  ```
  P(correct appears by round r) = 1 − exp(−(r / θ)^k)
  ```

  with **`k` = activation shape** (k > 1: the proxy accelerates reachability; k < 1: oscillation)
  and **`θ` = locking scale** (how many rounds it takes to lock a reachable answer).
  - `k` is estimated from the cumulative activation curve `A(r)`;
  - `θ` / locking from `P(F | A ∧ ¬S)` per round.
- **Cost axis.** Steps (rounds) are already logged; add **token instrumentation** per round —
  at minimum for finance (the N² heavy-FC sink). This requires patching the agent to retain
  `usage` (currently dropped).
- **Output.** A per model × family triple `(k, θ, cost(R))`, producing the first cost–reliability
  curves the plan (§3.4) centres on; out-of-sample: predict rounds-to-90% from the first 2–3
  rounds.

## 6. Execution order and dependencies

| Step | Work | Depends on | Blocks |
|---|---|---|---|
| P2.1 | Control arms A / A2 vs C (§2) | nothing (cheap, L1-first) | critic verdicts, §3 |
| P2.2 | Add weak tier, FC-carrier ablation (§1) | channel: Aliyun (available) | model-axis width |
| P2.3 | Critic optimization (§3) | P2.1 baseline | proxy quality |
| P2.4 | k/θ fitting + token instrumentation (§5) | trajectories (exist) + P2.2 | cost–reliability |
| P2.5 | Strong tier + family expansion (§1, §4) | §7 channel decision | full matrix |

## 7. Open decision for discussion (raise first with the advisor)

1. **Strong-tier channel.** No domestic endpoint serves Claude/GPT, and using one contradicts the
   "no OpenAI" hard constraint. Options: (a) resolve to overseas endpoint + relax the constraint
   for the strong tier only, (b) drop strong tier and construct the axis from weak + mid +
   model-size scaling within a domestic provider, or (c) defer strong tier to Phase 3.
2. **FC-carrier convention.** Confirm that `fc_carrier` is recorded as an intervention field so
   the native-vs-ReAct ablation is auditable.

---

*This plan extends `RESEARCH_PLAN.md` §5.3 Stages 2–4 with the concrete Phase-2 scope; all
reproducibility constraints (temperature/seed declaration, YAML config, budget-calibrate-archive)
from `REPRODUCIBILITY.md` apply unchanged.*
