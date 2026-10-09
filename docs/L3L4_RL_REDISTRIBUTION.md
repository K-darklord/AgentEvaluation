# L3/L4 and RL: Probability-Redistribution Correspondence

**Version**: 1.0 (2026-10-08)
**Status**: theoretical note (working, pre-paper)
**Scope**: fixes the conceptual frame that separates L3 (meta-cognition) from L4 (locking), links the test-time feedback loop to train-time RL via *probability redistribution* (not isomorphism), and specifies the experimental arms needed to test the resulting propositions. Feeds `docs/RESEARCH_PLAN.md` §5.10–§5.12.

---

## 1. Core proposition

> The test-time meta-cognitive feedback loop and train-time RL (GRPO / RLVR) share the **same probability-redistribution mechanism**, not a mathematical isomorphism.

**Rationale.** The established RL result is that RL *redistributes* probability mass over paths already present in the model's sampling distribution — it does not create capability that was not there. Our feedback loop is the **test-time, directional analogue of that sampling process**: the weak critic emits a (possibly noisy) directional signal, and the model re-samples, moving probability mass from the tail toward the head of the correct path.

The two differ only in *timescale* and *signal source*:

| | Train-time RL (GRPO/RLVR) | Test-time feedback loop |
|---|---|---|
| sampling | from policy π | ≤ 11 re-solve rounds |
| signal | reward model → relative advantage `Aᵢ = (rᵢ − μ)/σ` | weak critic → directional error feedback |
| mechanism | reinforce above-mean directions | model adopts affirmed / revises negated directions |

Both rely on **relative directional signals**, never an absolute ground-truth. The correct term in the paper is **probability redistribution**, deliberately *not* "mathematical isomorphism".

---

## 2. Redefinition of L3 and L4

The prior gloss "L3 = activation / L4 = locking" is sharpened here into a signal-aware definition.

| Layer | Definition | Operationalisation (arm C) |
|---|---|---|
| **L3 meta-cognition** | can the model, given a (possibly noisy) directional signal, reflect on its error and re-activate the correct sampling path | `P_act = correct_appeared / n` |
| **L4 locking** | anti-interference robustness: given the signal, can the model *stably* commit the correct answer | `P_lock = P(F \| A ∧ ¬S)`; `q_stay = P(F \| S)` |

**Key insight.** L4 is precisely what RL training is designed to implement — the redistribution that gives the correct answer enough probability mass to survive perturbation. A low L4 is therefore a direct read-out of "RL under-trained / not yet robust on that dimension" (§5).

L3 is the *ceiling* RL can redistribute up to: RL cannot pull up a path the model cannot even activate under a directional signal. This is the test-time, verifier-free proxy for the RL trainability bound.

---

## 3. Arm hierarchy: A3 ≤ C ≤ C*

Three signal conditions order the L3 measurement from passive lower bound to oracle upper bound.

| Arm | Design | Signal | Measures |
|---|---|---|---|
| **A3** | temperature sampling (T>0), N samples + best-of-N / vote | none (random) | L3 passive lower bound (pure distribution coverage) |
| **C** | weak-critic directional feedback (existing) | noisy directional | L3 meta-cognitive activation |
| **C\*** | oracle verifier (gold-leak-free) | perfect directional | L3 upper bound |

Consequences:

- `C − A3` = **net value of a directional signal, even a noisy one** (the §3.2 proposition "directional > non-directional" made quantitative).
- `C* − C` = **signal-to-noise loss** of the weak critic (how much activation is left on the table due to critic noise).

**C\* must be gold-leak-free.** It cannot consult `gold_answer` to steer; it must use a *verifiable* task: math via sympy / formal verifier, code via a pass@k executor. This is the same requirement as the "strong verifier" oracle control raised in the isomorphism note (§8.5).

---

## 4. Testable propositions

1. **Directional > non-directional**: `P_act(C) > P_hit(A3)` — the noisy critic activates more correct paths than pure random sampling hits.
2. **Oracle upper bound**: `P_act(C*) ≥ P_act(C)`, with `C* − C` quantifying the critic's SNR ceiling.
3. **L3 as RL ceiling**: for any task, RL post-training accuracy should not exceed the L3 activation measured under C (the redistribution bound).

Proposition 1 is the empirical hinge. If it holds, the test-time feedback loop is confirmed as the *same* optimisation process as train-time RL instantiated at a different timescale; the whole framework becomes a **trainability predictor** for RL.

---

## 5. Diagnostic value

| Observation | Diagnosis | Repair direction |
|---|---|---|
| L3 low | capability not in distribution | RL ineffective → back to pretrain / SFT / data |
| L3 high, L4 low | capability present but unstable | **RL sweet spot**: post-train to raise lock rate |
| L3 high, L4 high | saturated | RL marginal return → spend budget elsewhere |

L4 is the more actionable read-out: a low L4 on a dimension is a direct statement that RL has not yet made the model robust there. This is what turns a single accuracy scalar into a *capability map*.

---

## 6. Cost-curve coupling

From `docs/RESEARCH_PLAN.md` §5.12, `cost(R) = Σ_{r=1..R} tokens(r)`, with R governed by the N=3 early-stop. `q_stay` (L4 anti-interference) is the parameter that decides how fast a stable task halts:

- high `q_stay` → early stop → low cost;
- low `q_stay` → oscillation → full R → high cost.

So **L4 is a slope parameter of the cost curve** — the cleaner the L3/L4 numbers, the better the cost model fits. Higher L3/L4 values directly sharpen the cost-vs-reliability frontier.

---

## 7. Open design questions

1. **A3 sampling parameters** — what temperature T and sample count N give statistical power, and how to align A3's compute budget (N samples) with C's round budget (≤ 11 rounds) for a fair comparison.
2. **A3 "hit" definition** — best-of-N (reachability) vs majority-vote (stability): these measure different things and must be named separately.
3. **C\* oracle implementation** — which verifiable tasks can supply a gold-leak-free perfect signal (math formal verifier, code executor), and whether a strong learned verifier is an acceptable approximation.
4. **Scale regularity** — does `C > A3` hold uniformly from small to frontier models, or does the gap shrink as base capability grows.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-08 | Initial note. Reframed L3/L4 as signal-aware meta-cognition / locking; replaced "isomorphism" with "probability redistribution"; introduced A3 ≤ C ≤ C* hierarchy and the `C − A3` / `C* − C` decompositions; tied L4 to RL robustness and to the cost-curve slope. |
