# Error-Guided Test-Time Elimination (EGTE): Research Plan

**Document type**: Research plan (experiment protocol) · **Version**: 0.23 (Draft) · **Date**: 2026-10-21
**Target venues**: Nature Machine Intelligence / IEEE TPAMI / NeurIPS (primary); ACL / EMNLP workshop (early checkpoint).

> **Re-anchored 2026-10-10 → recursive self-improvement (RSI); sharpened 2026-10-21 → Error-Guided Test-Time
> Elimination (EGTE).** The program has moved from a pure measurement contribution (a metacognitive evaluation
> framework) to a self-improvement claim, now given a precise, differentially-positioned name. **EGTE is deliberately
> not a PRM and not a self-correction trainer**: a train-free, three-role evaluator — *distill* (build-time, gold →
> answer-free `mechanism` + `check_procedure`), *check* (execution-time, gold-free `trigger`), *review*
> (post-transition, evidence-anchored CUT / UNSURE / ANSWER) — **eliminates** wrong moves distilled from gold-annotated
> errors instead of scoring the correct path. Solver and the three evaluator roles are **separate calls**; capability
> rises by *mechanism*, never by memorisation. See `docs/WORKMAP.md` §0.4 and `docs/PHASE2_SUMMARY.md` §13–14.
>
> **Condensed 2026-10-21 (v0.23).** This plan has been slimmed to the EGTE backbone. Detailed / superseded stages that
> already live in their authoritative homes were removed and pointed to (see "Retired sections", end of document).
> The surviving sections keep their numbers so cross-references elsewhere in the repo remain valid.

---

## Abstract

Agent evaluation has moved toward reporting capability as a **cost–reliability curve** swept out by compute rather
than a single static number, and self-correction is increasingly treated as a control loop whose per-round error
dynamics — the Error Introduction Rate (EIR) and Error Correction Rate (ECR) — decide whether iteration helps or
hurts. We turn that *diagnosis* into the *engine* of **recursive self-improvement (RSI)**: the error-set prior and
gold-free weak critic already built as a measurement layer are re-purposed as the information source of an agent loop
that raises accuracy. We keep two levels of measurement distinct — the **per-round** pair EIR/ECR versus the
**whole-loop** observables activation rate `P_act` (reachability) and lock-in rate — bound algebraically
(`r = 1 − ∏(1−ECR)`; a lock-in deficit is exactly `EIR > 0`). The improvement is a **two-stage strategy** read at two
resolutions: Stage A raises `P_act` by error-set-guided sampling (no training); Stage B raises the lock-in rate via a
train-free evaluator. The train-free test-time mechanism is named **Error-Guided Test-Time Elimination (EGTE)**: a
three-role evaluator (distill / check / review) that eliminates wrong moves from gold-annotated errors — optimising
the *lower bound* of error rather than scoring the correct path — with no weight update. Across three mid-tier models
and multiple task families we report the per-model activation / locking / correction profile as the intermediate
product and test the central claim: **an error set is an effective RSI information source**.

---

## 1. Motivation and Problem Statement

### 1.1 The inadequacy of static accuracy

A single accuracy number — still the default headline metric — hides two fundamental uncertainties:

1. **Uncertainty in the problem boundary.** A finite budget (max steps, truncation, tools, latency) decides whether a
   task is solved; a wrong answer under budget does not prove a lack of capability.
2. **Uncertainty in the evaluation scale.** LLM-as-a-Judge introduces self-validation loops and homologous bias;
   hyperparameters (temperature, top-p, truncation) further perturb the score.

The assumed mapping from *task* to *capability score* is therefore itself inaccurate. A pilot study within this
program quantified this on a finance-agent benchmark (FAB): evaluation-framework defects induced a measured **26
percentage-point spurious capability deficit** fully attributable to the framework rather than the model. That is the
empirical warrant for treating single-shot accuracy as an unreliable readout. The measurement layer built to separate
the two is exactly the error-set signal that later drives the RSI loop (§1.2): *the diagnostic and the improvement are
one instrument, used twice.*

### 1.2 From measurement to self-improvement

Our earlier framing stopped at the *cost–reliability* reading of the capability curve (`docs/WORKMAP.md` §6). The
re-anchoring moves one step further: the same feedback that draws the curve can, if it carries the right *directional*
signal, be turned from a *measurement* into an *engine* of self-improvement. A model's single-shot accuracy hides two
separable deficits — a **reachability** deficit (the correct answer is never produced under budget) and a **locking**
deficit (produced but not held). An error set attacks both: first as a sampling prior that raises reachability, then
as the transition signal an evaluator reads to raise locking.

### 1.3 The central empirical question

The question is whether **an error set is an effective RSI information source**: does error-set-guided feedback produce
a significant, attributable accuracy gain over directionless noise, and does the gain decompose into the predicted
two stages (reachability first, then locking)? Convergence, cost, and the round-dimension observables remain the
instruments with which we read the answer — not the answer itself.

---

## 2. Related Work

Four frontier threads frame this work; the complete literature map with citations is in `docs/WORKMAP.md`.

- **Agent evaluation** — static accuracy → capability curve; evaluation-framework bias and interference.
- **Verification & self-correction** — the negative result that LLMs often cannot self-correct without external
  signal; this motivates the *external* proxy.
- **Optimization** — test-time search, best-of-N, verifier-guided decoding.
- **Inference scaling** — test-time compute scaling laws and the cost–accuracy trade-off.

**Core positioning.** The centre of gravity has moved from **diagnosis** to **recursive self-improvement (RSI)**. The
round-dimension observables — activation ceiling `P_act`, locking rate `P_lock`, reversibility `r` — are no longer the
deliverable but the **measurement layer** of a self-improvement claim: the error-set prior + weak critic is the
*information source* an agent loop exploits to raise accuracy (§3.7). A subordinate claim (retained) is the
**existence proof**: a cheap, gold-free *weak critic* can itself raise the activation ceiling, establishing
metacognition as a separable, optimisable axis (§3.1).

**Nearest neighbours to differentiate against** (full table in `docs/WORKMAP.md` §0.4):

- **Feedback Friction (Jiang et al., arXiv:2506.11930)** — the closest published analogue to our `P_act` ceiling and
  locking loss, but with near-oracle feedback; ours is a *gold-free statistical critic*.
- **Overthinking in test-time scaling (Zhou et al., arXiv:2604.10739)** — "flip events" inside one CoT, vs our
  multi-round *external feedback loop*.
- **Activation-probe self-correction (arXiv:2606.03645)** — white-box evidence of activation-without-locking, vs our
  black-box gold-free protocol-side measure.

**EIR/ECR feedback-control ancestor.** Liu & Meng 2026 ("Self-Correction as Feedback Control", arXiv:2604.22273)
models the loop as a two-state Markov chain parameterised by EIR/ECR and derives the stability threshold
`ECR/EIR > Acc/(1−Acc)`. We keep EIR/ECR as *per-round* micro quantities, report `P_act`/`P_lock` as *whole-loop*
macro observables, and turn their diagnostic into a two-stage improvement claim.

**EGTE positioning.** The "learn-from-mistakes" family is already occupied — most directly by **Mistake Notebook
Learning** (a training-free persistent KB of *abstracted* error patterns). EGTE's departure: it distills not instance
guidance but an **answer-free `mechanism` + differential `check_procedure`**, enforced by a **transition-triggered,
gold-free verifier** with **evidence-anchored CUT / UNSURE**, and improves capability by *mechanism* rather than by
memorising answers. Contrast summary: `docs/WORKMAP.md` §0.4, `docs/PHASE2_SUMMARY.md` §13.3.

---

## 3. Theoretical Framework

### 3.1 Four-layer capability hypothesis

We hypothesise four separable capabilities; the separation is the conceptual core.

| Layer | Capability | Definition |
|---|---|---|
| **L1** | Base | Single-shot correctness of the naked model, no external aid — raw latent accuracy. |
| **L2** | Augmentation | Capability gained by embedding the model in an agent system: tools, retrieval, orchestration, voting, search, retry, best-of-N. A property of *model-plus-system*. |
| **L3** | Meta-cognitive (activation) | Given an external error signal, *activate* the correct answer at least once across feedback rounds. |
| **L4** | Correction (locking) | *Lock onto* the correct answer — resist misleading signals, hold it, not oscillate. |

**Two orthogonal axes.** L1+L2 jointly define *static accuracy* (the **intercept** of the capability curve); L3 and
L4 define the *round-dynamics* (the **shape**, `k = f(L3, L4)`). Two models with identical accuracy are classically
indistinguishable, yet differ in whether they *scale* under inference-time compute. Our role is **not** to improve
L1/L2 directly; we construct an external signal system and test whether the model can use it.

### 3.2 The meta-cognitive proxy

Since models lack intrinsic meta-cognition, we construct an **external proxy** that only provides structured signals
— it does not modify the agent's output. Four components: (1) an inductively built **error taxonomy** across domains;
(2) an **evaluator / signal generator** returning the Top-K most likely error directions without revealing the gold;
(3) a **conservative update** down-weighting changes that move toward known errors (anti-oscillation); (4) a bounded
**feedback–self-correction loop**. The minimal implementation is a prior-weighted boosting-style feedback over an
error-category × model contingency table.

### 3.3 What converges: the combined capability, not the problem

Individual questions are only probes; convergence is an attribute of the model's capability under feedback. The object
of study is the **trajectory across a population of questions**. Because the mean may move, the process is **not**
i.i.d.; a suitable stochastic model is required. Whether the combined capability converges depends on its (L1, L2, L3)
configuration: strong base + engineering → likely; strong self-correction → very likely; all weak → unlikely. When
present, the framework answers *how many rounds to reach a target accuracy*; when absent, it reports non-convergence.

*(§3.4–§3.6 retired — see "Retired sections".)*

### 3.7 Two-level error dynamics and the two-stage RSI claim

The self-improvement theory sits on top of the measurement framework, borrowing the error-dynamics vocabulary of Liu &
Meng 2026 while keeping two levels of measurement separate.

**Per-round (micro) — EIR/ECR.** Over one self-correction round on the two-state chain {Correct, Incorrect}:
**EIR** = `P(c_{k+1}=wrong | c_k=correct)` (introduce an error); **ECR** = `P(c_{k+1}=correct | c_k=wrong)` (correct
one). Their model yields a **stability threshold** (iterate only while `ECR/EIR > Acc/(1−Acc)`), a **steady state**
`π* = ECR/(EIR+ECR)`, and a **convergence rate** `1−EIR−ECR`. The sharp near-zero EIR boundary (≲0.5%) that separates
beneficial from harmful self-correction is our *locking* concern viewed from the degradation direction.

**Whole-loop (macro) — our observables.** Over an entire ≤10-round loop, `P_act` (activation / reachability) and
`P_lock` / `q_stay` (locking) are whole-loop quantities. The bridge is algebraic, not identical: the macro
reversibility `r = P(A | ¬S)` is the cumulative consequence of per-round ECR, `r = 1 − ∏(1−ECR)`, and a single-step
lock-in deficit is exactly `EIR > 0`. **We report both levels and never merge them.**

**Two-stage RSI strategy.** The two levels separate two improvement levers:

1. **Stage A — raise `P_act` via error-set sampling (no training).** The error-set prior + weak critic steer the loop
   toward reachable regions before it degrades.
2. **Stage B — raise the lock-in rate via a train-free transition evaluator (no training).** An external evaluator
   reads each round's transition rationale, prunes the state chain, and emits an answer / abstain verdict, suppressing
   EIR-driven flips.

**EGTE reframe.** The two-stage decomposition is the *macro* read; EGTE is the *test-time* read of the same loop. The
"train-free transition evaluator" (Stage B) is realised as **three separated roles** — *distill* (build, gold →
`mechanism` + `check_procedure`), *check* (execute, gold-free `trigger`), *review* (post-transition,
evidence-anchored CUT / UNSURE). EGTE optimises the **lower bound** (eliminate wrong moves) rather than the objective
(select the correct one), exploiting the asymmetry that the reachable error space is small and checkable while the
correct space is dense.

---

## 4. Research Questions

| ID | Question |
|---|---|
| **RQ1** | Does a model's combined capability (L1, L2, L3), under external meta-cognitive feedback, exhibit convergence across a population of probe questions? |
| **RQ2** | Which trajectory features separate the convergence classes (convergent / oscillating / divergent / stagnant)? |
| **RQ3** | When convergence occurs, what is the expected cost (rounds / tokens) to reach a target accuracy, and how early can it be predicted? |
| **RQ4** | When convergence does not occur, what trajectory features diagnose the underlying meta-cognitive deficit? |
| **RQ5** | Does error-set feedback (the weak critic) produce a significant RSI gain over directionless noise — i.e. is the error set an effective RSI information source? |
| **RQ6** | Does the two-stage strategy decompose as predicted — Stage A lifting `P_act`, Stage B (EGTE three-role evaluator) lifting lock-in — and does the loop enter `ECR/EIR > Acc/(1−Acc)`? |

RQ1–RQ4 constitute the measurement layer; RQ5–RQ6 constitute the RSI/EGTE claim (§3.7).

---

## 5. Experimental Design

### 5.1 Probes and models

Probes are drawn from multiple task families; the design is **cross-domain** and retains **finance** as one family
(reusing the FAB setup). Metrics are task- and model-focused, not problem-focused.

- **Task families** (Probe: 5 families × 50 Qs — math (GSM8K), math500 (MATH-500), logic (MMLU-Pro), finance (FAB),
  tool-use (BFCL), L1:L2 = 3:2; Feasibility adds code, factual consistency, multi-hop, translation; Full extends to
  12–15 families with L2/L3-level items ≥ 40%). See `docs/PHASE2_SUMMARY.md` §14 for the family-expansion order.
- **Models** (Phase 1 = 3 mid-tier via Aliyun Token Plan; **no local model loading**):
  - *Mid (Phase 1)*: deepseek-v4-flash-0731, qwen3.8-flash, glm-5.3 (Aliyun Token Plan);
  - *Weak*: qwen3.6-flash, glm-4.7-flash (Phase 2); *Strong*: Claude Opus 5.5, GPT-6 Astra (Phase 2/3).
- **Replication order** (`PHASE2_SUMMARY.md` §14): fix arm C first → make **deepseek** work end-to-end → replicate on
  **glm / qwen** with the same method → add more task families.

*(§5.2 Task-Bank Blueprint, §5.3 Experimental stages, §5.4 Tensor decomposition, §5.7 Phase-1 go/no-go plan are retired
— superseded by `docs/PHASE1_SUMMARY.md` / `docs/PHASE2_SUMMARY.md` / `docs/TIMELINE.md`. See "Retired sections".)*

### 5.5 Ablation / control arms

The core contrast set is the four-arm causal design (detailed in §5.16):

| Arm | Perturbation source | Sampling | Aggregate | Isolates |
|---|---|---|---|---|
| **A** | none (bare re-solve) | T=0 | single answer (init acc) | zero-intervention floor |
| **A2** | fixed neutral placebo | T=0 | single answer | scaffold inertia (≈ A) |
| **A3** | i.i.d. temperature | T=0.7, n=10 | majority-vote | sampling diversity (self-consistency) |
| **C** | weak-critic directional | T=0 | freq-vote | directed interference on top of sampling |

A3 is **self-consistency** (Wang et al. 2022), with **pass@k** (Chen et al. 2021) reported alongside. The earlier
proxy-ablation arms A1–A6 (uniform prior, signal strength, temperature sweep) remain valid secondary controls and are
recorded in `configs/ablation/`.

### 5.6 Metrics and statistics

- **Observed**: activation rate, first-activation round, locking rate (and the layered profile `model_score` in §5.12).
- **Test**: Fisher's exact test, p < 0.05, for activation-rate differences between proxy and baseline arms.
- **Success criteria** (any): a significant activation-rate gain on ≥ 1 task family, or on ≥ 1 weak model.
- **Stop conditions** (any): no activation gain on any model × family; gain < 5%; ablation shows equal gain without
  the proxy.

*(§5.7 retired; §5.8–§5.12 follow.)*

### 5.8 Weak critic — gold-free directional signal

**Positioning.** The proxy's feedback generator is the **weak critic**: a deterministic, gold-free classifier that maps
one answer onto the fixed 19-leaf error taxonomy and returns the **Top-3** most likely error directions with
probabilities. It never assigns correctness, never consults the gold, never calls a judge. Correctness stays entirely
in the offline evaluation layer (§5.9).

**Two-layer pipeline.**

1. **Layer-0 prior — the taxonomy** (`src/build_error_taxonomy.py`): auto-labels every wrong instance into one of 19
   leaves, producing the error bank. Each leaf carries two fixed gold-free fields — **cause** (one-sentence error
   reason) and **attention** (one-sentence directional "how to check", never pointing at the correct value).
2. **Layer-1 classifier** (`src/build_weak_critic.py`, CRITIC_VERSION v2.0): an exemplar-retrieval classifier over the
   wrong bank. Evidence `s = W_Q·sim_q(question) + W_A·sim_a(answer)` (W_Q=0.7, W_A=0.3); error signal
   `error_score = family_base_rate × s`; flagging is a cut on evidence (`EVIDENCE_THRESHOLD`, currently 0.1). Feedback
   hands the agent the **error direction (Top-K leaf) + confidence**; the agent decides whether to revise.

**Critic is a hint, not a verifier.** Its quality metric is the **top-K direction hit rate** (84–100% on the wrong
bank), not a false-positive rate. Notation: feedback tiers A (type+prob) / B (+cause) / C (+cause+attention), burned
against next-round improvement.

**Known risk (recorded, unresolved).** Evidence `s` has no discriminating power between correct and wrong answers
(~98% flag rate on correct answers; reversed for finance/mmlu). The scalar `error_score` is therefore *anti*-correlated
with actual error and unusable as a selection signal — which is exactly why Stage B keys on a **stability** signal
(§5.15), not critic `P(wrong)`. A go/no-go item for the real feedback loop.

### 5.9 Evaluation tiers (three-tier scoring framework)

Correctness scoring is dispatched by answer form and recoverability; every scored row records its `eval_tier` so
hybrid scoring stays reproducible at per-question granularity.

- **T1 — deterministic match (no LLM):** numeric / symbol / letter / JSON compared by rule or symbol equivalence
  (sympy). For MATH-500 a deterministic extraction layer (T1b) recovers `\boxed{}` / trailing `= …` answers.
- **T2 — LLM-assisted parse + judge (registered intervention):** when T1 misses but the answer may be present, the
  strongest judge (deepseek-v4-pro) re-reads the full response against the gold. Runs only on T1-missed rows
  (`T2_RESCUE_ENABLED`, default off).
- **T3 — multi-LLM voting:** open / qualitative answers (finance FAB rubric, generation) via majority vote; currently
  `max(T1, T2)` as an interim stand-in.

**False-negative convention:** `correct` is the positive class ("scored wrong but right" = false negative). T1b and T2
both target FNs. Only T1 is intervention-free; T2/T3 must be declared as interventions wherever they touch a result.

### 5.10 L3/L4 discrimination — round-dimension scheme

L1/L2 are *a priori* (task-family split) and not inverted; L3/L4 are *process* properties observable only across
feedback rounds, operationalised **taxonomy-free**.

**Events (per model × task, over N rounds):** **A** — *activation* (≥1 candidate scored correct offline); **B** —
*locking* (final selected candidate correct).

**Derived statistics:** activation rate `P(A)`; locking rate `P(B)`; correction rate `P(B | A)`; L4-deficit
`1 − P(B | A)`; first-activation round; L3-deficit isolated via the A1 ablation.

**Six end-states** (each (model × task) run falls into exactly one):

| End-state | Start | Correct appears | Final | Reading |
|---|---|---|---|---|
| 1 | correct | — (never flips) | correct | L4 full (strong anti-interference) |
| 2 | correct | flips wrong | wrong | L4 deficit (misled into an error) |
| 3 | correct | flips + recovers | correct | L4 weak but recoverable |
| 4 | wrong | appears | correct | L3 + L4 full |
| 5 | wrong | appears | wrong | L3 present, L4 deficit (oscillation) |
| 6 | wrong | never appears | wrong | L3 absent (signal cannot activate) |

End-states 2/3 are the "flip-correct-to-wrong" phenomenon; the critic's false-positives double as a *natural L4
anti-interference stress test*.

### 5.11 Feedback-loop implementation

The round-dimension scheme is implemented as a bounded feedback–self-correction driver
(`src/run_feedback_loop.py`). For each (model, task): round 0 is a baseline solve; rounds 1..R inject the previous
answer plus the weak critic's gold-free feedback as an extra user message and re-solve *independently*. Tool results
are cached across rounds; the agent alone decides whether to revise.

**Hyperparameters (this probe):** R = 10 max feedback rounds; early-stop N = 3 (halt once the final answer is
unchanged for 3 consecutive rounds); feedback tier C; temperature = 0, seed = None. Zero-LLM scoring within the loop
(T1 rules for math / math500 / mmlu_pro / bfcl; finance-qualitative T2-judge rescue as a registered intervention).

### 5.12 Capability-layered dynamics model

Why a *directional* weak critic lifts accuracy even when near-noise — expressed as an estimable model.

**Statistical skeleton.** Latent mean `μ` (the L1/L2 intercept); a single observation `Y = μ + noise`. Three arms:
**A** no feedback → `E[Y_A] = μ`; **B** directionless noise → `E[Y_B] ≈ μ`; **C** directional weak critic →
`E[Y_C] = μ + Δ`. The **L3 existence claim** is `Δ = E[Y_C] − E[Y_B] > 0` — the contrast is **C vs B**, not C vs A
(the latter confounds "multiple rounds" with "directional signal").

**L3/L4 separation inside arm C.** Over the looping events (`A` = correct appears ≥ 1 round; `S` = round-0 correct;
`F` = final correct): `P_act = P(A)` (reachable ceiling), `r = P(A | ¬S)` (reversibility), `P_lock = P(F | A ∧ ¬S)`
(lock), `q_stay = P(F | S)` (anti-interference). Since `S ⊆ A`:

```
P_act = μ + (1 − μ)·r
final_acc = μ·q_stay + (1 − μ)·r·P_lock
locking_loss = P_act − final_acc
```

`P_act` is the primary "model ceiling" metric; `locking_loss` is the model's avoidable loss (correct within reach but
not locked). The evaluation target is the layered profile `model_score = (μ, P_act, r, P_lock, q_stay, cost(R))`.
(self-consistency numbers on existing arm-C data are in `docs/PHASE2_SUMMARY.md`.)

### 5.14 RSI loop stages (R0–R3)

| # | RSI moment | What we build / run | Success criterion |
|---|---|---|---|
| R0 | Error-set prior (information source) | existing weak critic + taxonomy, gold-free (§5.8) | `P_act` measurable and above single-sample μ |
| R1 | Stage A — reachability | error-set-guarded sampling inside the loop (§5.11) | `P_act` ↑ over the bare loop; EIR suppressed |
| R2 | Stage B — locking (EGTE) | three-role train-free evaluator reads each round's rationale → answer / abstain | lock-in rate ↑; `ECR/EIR > Acc/(1−Acc)` |
| R3 | Claim | error set as an effective RSI source | gains, with cost/token accounting as intermediate products |

R0/R1/R2 are **no-training and reversible**, so every stage can be aborted and re-run cheaply to bound cost.

### 5.15 Stage B evaluator — stability-based selection

**Directional hypothesis (H2).** After a bounded `n`-round budget, the answer sequence forms a near-reversible Markov
chain in which the correct value is a high-self-loop metastable attractor; a zero-gold Stage B evaluator selects the
most stable value and beats naive "take the last round", with the gain on activated-but-unlocked tasks.

- **H2a:** read-off selectors (mode / max self-loop) suffice; explicit stationary extrapolation adds nothing.
- **H2b:** mode concentration (top-1 share) is a strong lock-in signature (~6–14× higher on locked-correct than
  unlocked), doubling as a confidence / abstention signal.

**Offline anchors (gold-free, 4 C-arm trajectory files):** the correct value is the frequency mode in 86–98% of tasks;
the mode selector beats the last-round lock-in; when it fails the correct value is the competing 2nd mode in 33–57% of
cases. Selecting by critic `P(wrong)` (argmin) was *ineffective* (below last-round baseline) — the **stability** signal
is the superior gold-free selector. *(Full tables in `docs/PHASE2_SUMMARY.md` §13.)*

**Open question:** all four files are C-arm, so "the critic *forms* the new distribution" is not yet separated from the
model's own confidence — recompute mode concentration under A / A2 as a clean test.

### 5.16 Causal contrast (A/A2/A3 vs C) and the EGTE / Stage-B mechanism

**Question.** Does the weak critic's *directional* interference (arm C) concentrate probability mass on the correct
answer more cheaply than *i.i.d. sampling* (self-consistency)? Two pre-registered claims, at equal per-question sample
budget `n`: (1) `acc(C.freq-vote) > acc(A3.majority-vote)` (the core novelty, if true); (2) `acc(C.freq-vote) >
acc(C.last)` (voting beats final-round lock-in).

**Four arms** (same questions / models / `n`; only the perturbation source varies): see §5.5.

**Offline profiling of low-confidence errors (arm C).** Concentration (modal-share) separates correct from wrong by
2–3×; the wrong answers are overwhelmingly *flat* (no dominant mode — genuine uncertainty, not confident error), yet
the correct answer had already appeared in 60–78% of them (activation-without-lock = pure *selection* failures). The
sharp-wrong tail is a competence wall re-sampling cannot fix. **Negative result (recorded):** the critic's
`error_score` is anti-correlated with actual error, unusable as a selection signal — Stage B keys on a *stability*
signal instead.

**Stage-B / EGTE mechanism: stability gate + verifier escalation.**

- **B1 (stability gate, zero-API):** concentration ≥ τ → output the mode.
- **B2 (escalation, flat cases only):** a verifier scores the n already-sampled candidates and returns argmax
  (LLM-as-judge, or a light outcome-RM trained on the wrong bank).
- **Abstain:** sharp-wrong (or flat without activation) → conformal abstention.

**EGTE realisation (2026-10-21).** The Stage-B verifier is realised as the **three separated evaluator roles**: *distill*
(build-time, gold → `mechanism` + `check_procedure`), *check* (execution-time, gold-free `trigger`), *review*
(post-transition, evidence-anchored CUT / UNSURE). This is **not a PRM** — it assigns no scalar credit to the correct
path and performs no weight update; it only *eliminates* wrong moves. Step-level process reward remains deferred: the
signal concentrates in the final answer and the correct value is already in the candidate set.

---

## 6. Reproducibility and Implementation

The full reproducibility standard (three-tier reproduction, repository layout, seeds, config manifest, experiment log,
one-command reproduction) is specified in `docs/REPRODUCIBILITY.md`. Key invariants: all parameters from config (no
hard-coding); deterministic components fully reproducible; LLM sampling logged with explicit temperature + seed and ≥ 3
seeds per experiment; per-run `manifest.json` (hashes) under `results/`; evidence chain
`claim → experiment-log record → config + seed → trajectories → code version`.

### 6.1 Environment and compute

Apple M4 MacBook Air, 24 GB unified memory (no CUDA). **No local model loading** (local MLX / Ollama / llama.cpp
deprecated): Phase 1 runs all three mid-tier models on the Aliyun Token Plan; Phase 2 weak-tier models on a rented
Aliyun instance.

---

## 7. Budget and Timeline

Planning authority for phases, milestones, budget, and risk buffers is `docs/TIMELINE.md`. Order of magnitude: Phase 1
probe < $200 (budget tier < $50), Phase 2 feasibility ~$1.5k (≈ $300), Phase 3 full ~$10k (≈ $1.5–3k). Dominant cost
driver = API model × question × round cells. Nominal timeline ≈ 90 working days breakout; compute escalation through
free tiers → spot GPUs → budget API.

---

## 8. Contributions and Risk

### 8.1 Three contributions (layered)

1. **Error-set-driven RSI (headline).** An error set is an effective recursive-self-improvement information source:
   error-set-guided feedback produces a significant, attributable accuracy gain over directionless noise. Answers *"can
   a cheap, gold-free error signal actually improve the model?"*
2. **Error-Guided Test-Time Elimination (mechanism).** The gain decomposes into a reachability lever (Stage A, `P_act`,
   no training) and a test-time **elimination** lever realised as a three-role evaluator (*distill* / *check* /
   *review*) that removes wrong moves rather than scoring the correct path — bound to the per-round EIR/ECR dynamics
   and `ECR/EIR > Acc/(1−Acc)`. Answers *"where does the gain come from, and how do we push it further?"*
3. **Round-dimension measurement layer (enabling).** The activation / locking / correction observables
   (`μ, P_act, r, P_lock, q_stay, cost(R)`) are retained as the intermediate product that makes (1) and (2)
   measurable and reproducible. Answers *"how do we read the improvement, at what cost?"*

### 8.2 Risks and the informative negative result

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Proxy design unsound → no systematic change | medium | high | minimal design; rapid pre-experiment |
| Capability axes not clearly separable | medium | medium | fall back to direct curve comparison |
| No accuracy gain within N steps | high | low | activation–locking decoupling |
| Oscillation, no convergence | medium | medium | stopping criteria (threshold / max-round / no-improvement) |
| Weak-critic evidence has no discriminating power (98% FPR; reversed finance/mmlu) | high | high | recorded; re-derive evidence or accept critic as a pure direction hint |
| Weak critic under-powered (few wrong exemplars; 0–20 per leaf family) | medium | high | enlarge bank in Phase 2; keep deterministic gold-free features |

**Methodological stance.** Negative results are informative: if feedback makes a model increasingly wrong, that
reveals an absent or broken meta-cognitive loop — the more consequential diagnosis. The framework is robust to either
outcome.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.23 | 2026-10-21 | **Condensed to the EGTE backbone.** Retired §3.4 (cost–reliability prediction), §3.5 (three mathematical framings), §3.6 (three decouplings), §5.2 (Task-Bank Blueprint), §5.3 (experimental stages), §5.4 (tensor decomposition), §5.7 (Phase-1 go/no-go plan), §5.13 (RL redistribution correspondence — now a pointer to `docs/L3L4_RL_REDISTRIBUTION.md`); fold §5.16 back into §5; reconcile §5.5 to the A/A2/A3/C arms; RQ2 reworded off the removed framings. Surviving sections keep their numbers. Details moved to `PHASE1_SUMMARY.md` / `PHASE2_SUMMARY.md` / `TIMELINE.md` / `ERROR_TAXONOMY.md`. |
| 0.22 | 2026-10-21 | Sharpened the mechanism naming to **Error-Guided Test-Time Elimination (EGTE)** — a train-free, three-role evaluator (distill / check / review) that eliminates wrong moves, explicitly not a PRM (no scalar reward, no weight update). Re-anchored Abstract / §2 / §3.7 / §5.16 / §8.1; experiment path per `docs/PHASE2_SUMMARY.md` §14. |
| 0.21 | 2026-10-10 | Added §5.16 causal contrast (A/A2/A3 vs C); A3 = self-consistency (T=0.7 n=10; pass@k ↔ correct_appeared); FTR anchor; recorded flat-vs-sharp wrong profiling + critic error_score anti-correlation negative result; Stage-B B1/B2 mechanism. |
| 0.20 | 2026-10-10 | Added §5.15 directional hypothesis H2 (Stage B stability selection) with offline anchors (mode 86–98%; +0.5–4.3pp over `last`; mode concentration ~6–14× lock-in signature). |
| 0.19 | 2026-10-10 | Re-anchored to RSI: error-set prior + weak critic as the RSI information source; two-stage strategy bound to EIR/ECR dynamics (Liu & Meng 2026). Added §3.7, revised Abstract / §1 / §2 / RQ5-6 / §8.1; added §5.12 EIR/ECR bridge, §5.13 RSI reading, §5.14 R0–R3. |
| 0.18 | 2026-10-09 | Softened motivation per advisor feedback; novelty narrowed to the crossover + round-dimension measurement layer. |
| 0.17 | 2026-10-07 | §6.1 hardware/model-routing: local MLX/Ollama deprecated; weak tier via rented Aliyun instance. |
| 0.16 | 2026-10-07 | Added §2 core positioning + nearest-neighbour differentiation (Feedback Friction, overthinking, activation-probe). |
| 0.15 | 2026-10-07 | Marked Phase 1 complete; consolidated into `docs/PHASE1_SUMMARY.md`; removed `docs/PHASE2_PLAN.md`. |
| 0.14 | 2026-10-07 | Corrected §5.12 L3 activation semantics (`P_act = P(A)` ceiling vs `r = P(A | ¬S)` reversibility); decomposition `P_act = μ + (1−μ)·r`, `final_acc = μ·q_stay + (1−μ)·r·P_lock`; layered `model_score`. |
| 0.13 | 2026-10-06 | Added §5.12 capability-layered dynamics model; three-arm design (arm A reused from round 0). |
| 0.12 | 2026-10-06 | Added §5.11 feedback-loop implementation (R=10, N=3 early stop, tier-C, temp=0, independent re-solve, six end-states). |
| 0.11 | 2026-10-06 | Upgraded §3.1 to four layers (+L4); appended §5.8 Rev-3 exemplar retrieval; added §5.10 six end-states + §8.2 risk rows. |
| 0.10 | 2026-10-06 | Rewrote §5.8 to the weak critic (taxonomy prior + classifier, Top-3 over 19 leaves; cause/attention fields). |
| 0.9 | 2026-10-05 | Consistency pass: §5.1 / §5.3 / §5.7 / §6.1 aligned to Phase-1 reality. |
| 0.8 | 2026-09-29 | Rewrote §5.8 critique to rule-based metacognition (three gold-free signal layers). |
| 0.7 | 2026-09-29 | Revised §3.6 decoupling 1 + §5.4 (static tensor cannot invert L1/L2); added §5.10 L3/L4 round-dimension scheme. |
| 0.6 | 2026-09-29 | Added §5.9 three-tier scoring; renamed proxy to critique module. |
| 0.5 | 2026-09-29 | Added §5.7 Phase-1 execution plan (four feasibility checks, build-before-burn, no-human-labelling). |
| 0.4 | 2026-09-28 | Added §5.2 Task-Bank Blueprint (provisional). |
| 0.3 | 2026-09-27 | Phase-1 model tiers + task set revised. |
| 0.2 | 2026-09-26 | Restructured into academic experiment protocol; three-layer hypothesis, three framings, cost–reliability form, three decouplings. |
| 0.1 | 2026-09-26 | Initial working draft (internal). |

---

## Retired sections (v0.23 removal map)

Following `PROTOCOL.md` (historical continuity — superseded content is marked, not quietly dropped), the sections
removed in v0.23 and their authoritative homes:

| Removed section | Content | Now lives in |
|---|---|---|
| §3.4 cost–reliability prediction | extreme-value `Accuracy(c) = f(c; θ)`, shape `k` | `docs/PHASE1_SUMMARY.md`, `docs/WORKMAP.md` §6 |
| §3.5 three mathematical framings | stochastic approximation / Markov chain / sequential analysis | `docs/DECISION_LOG.md` (superseded) |
| §3.6 three decouplings | L1/L2 a-priori, activation vs locking, recognizing vs correcting | §3.1 / §3.7 / §5.10 (re-declared here) |
| §5.2 Task-Bank Blueprint | family × benchmark × layer × evaluator × token budget | `docs/TIMELINE.md`, `docs/ERROR_TAXONOMY.md`, `data/README.md` |
| §5.3 experimental stages | 4-stage signal→trajectory→convergence→cost | §5.14 (R0–R3) |
| §5.4 tensor decomposition | static tensor no-go for L1/L2 | `docs/ERROR_TAXONOMY.md`, §5.10 |
| §5.7 Phase-1 go/no-go | four feasibility checks | `docs/PHASE1_SUMMARY.md` |
| §5.13 RL redistribution | probability-redistribution correspondence | `docs/L3L4_RL_REDISTRIBUTION.md` |