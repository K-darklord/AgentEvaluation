# Error-Guided Test-Time Elimination (EGTE) — Paper Draft



---

## 1. EGTE: definition, roles, and the optimization objective

### 1.1 What EGTE is (asymmetric error exclusion)

EGTE (Error-Guided Test-Time Elimination) treats an **error set as an RSI information source** and  
optimizes an RSI **lower bound**. It does not train or prompt the model to  
*produce* the correct answer (the positive direction); it distills, from a gold-annotated **error  
bank**, a finite set of **generalizable wrong-execution behaviours**, and uses them to **EXCLUDE**  
wrong candidates at test time. 

The asymmetry is the load-bearing claim: the space of *wrong* moves reachable for a problem class is  
small, sparse, and checkable, while the space of correct derivations is dense and open-ended. Modeling  
"what goes wrong" (a few finite exclusion rules) costs far less than modeling "what is right" (a PRM  
that scores the correct direction), and is more robust because each rule is a *falsifiable check*, not  
a learned intuition. The distilled memory is **answer-free** — a class-level `mechanism` +  
`check_procedure` that never names a specific molecule / number / option — so it transfers across  
questions and across benchmark families and does not go obsolete: new errors keep feeding the bank,  
sharpening the same mechanisms instead of accumulating instance memory.

### 2.2 The strategy roles, and the quantity each optimizes

Three roles carry the strategy — the **distiller**, the **critic**, and the **evaluator** — plus  
two that frame them: the **solver** (generates) and the **scorer** (grades). Each role is a separate  
call; correctness lives in exactly the scorer.

| Role                             | When                          | Gold? | Produces                                                                | The quantity it optimizes                                 |
| -------------------------------- | ----------------------------- | ----- | ----------------------------------------------------------------------- | --------------------------------------------------------- |
| **distiller** (build)            | offline, over the error bank  | yes   | `mechanism` + `check_procedure` (class-level, answer-free)              | the generic exclusion rules both downstream roles consume |
| **critic** (front, in-loop)      | feedback loop                 | no    | directional correction; the trajectory that diverges the candidate pool | **activation** `P_act` ↑ at controlled **EIR**            |
| **evaluator** (back, offline)    | lock-in, on a transition only | no    | CUT / UNSURE / ANSWER lock (evidence-anchored)                          | suppress **EIR** (revert + lock), lock-in ↑                |
| **solver** (generation)          | generation                    | no    | candidate answer + CoT                                                  | (policy; not optimized here)                              |
| **scorer** (`scorer_LLM_rescue`) | final grading, all arms       | yes   | correctness verdict                                                     | (frozen; the only gold reader at grade time)              |

The evaluator's runtime closure is **check → review**, consuming the distiller's `mechanism` +  
`check_procedure`, with a `trigger` signature and per-transition `evidence` over the hidden CoT; it  
wakes only on an answer **transition**, never reads the target round's CoT at rest, and never sees the  
gold at runtime.

### 2.3 The single Objective: EIR and ECR on the two-state chain



```
final = init + corrected(ECR) − flipped(EIR)
```

- **EIR** (error induction rate) = P(correct → wrong) per round. Introduced  by the  
  **critic**: its perturbation buys activation, but the same perturbation can flip a correct  
  answer to wrong. 
- **ECR** (error correction rate) = P(wrong → correct) per round. Introduced by the **critic** too. The **evaluator does not raise ECR**; it only suppresses EIR, and  
  (i) *repairs* a misdirected transition by re-verifying against the distilled `check_procedure`, and  
  (ii) *recognizes* an already-activated correct answer and locks it before a later EIR event flips it.

Iteration is beneficial only while `ECR / EIR > Acc / (1 − Acc)`, with steady state  
`π* = ECR / (EIR + ECR)` and convergence `1 − EIR − ECR`. The two levers map one-to-one onto the two  
stages:

| Stage              | Role             | Knob                                | Target                             |
| ------------------ | ---------------- | ----------------------------------- | ---------------------------------- |
| **A** (activation) | critic (front)   | contain **EIR** at fixed activation | `P_act` ↑, EIR → 0                 |
| **B** (locking)    | evaluator (back) | suppress **EIR**                    | `ECR/EIR > Acc/(1−Acc)`, lock-in ↑ |

The objective is to make `final − init = corrected − flipped` **positive and stable** — to drive the  
loop into the stability region — rather than to maximize either stage in isolation. 

### 2.4 Four arms (causal contrast)

All arms share the same solver base model and are graded by the same scorer. They differ only in the  
feedback / aggregation treatment. `C3` is read as its default form: **critic (in-loop) +  
evaluator (offline)**.

| Arm    | Definition                                                                 | Identity / role in the design                           |
| ------ | -------------------------------------------------------------------------- | ------------------------------------------------------- |
| **A**  | bare re-solve, T=0, single answer, zero intervention                       | floor: raw latent accuracy (L1)                         |
| **A2** | fixed neutral placebo, T=0, single answer                                  | placebo control for scaffolding                         |
| **A3** | **self-consistency** (Wang et al. 2022), T=0.7, N=10, i.i.d. majority vote | the test-time scaling baseline EGTE must beat           |
| **C**  | weak critic, directional, T=0, frequency-vote                              | **outdated** — dropped (weak critic underperformed); **not in final paper** |
| **C3** | **strong critic (in-loop) + evaluator `rubric_ce` (offline)** = full EGTE  | the treatment: Stage A (activation) + Stage B (lock-in) |

The strong critic diverges the error source by activation (necessarily activating both correct and  
wrong candidates), and the offline evaluator reads that trajectory to *eliminate* wrong moves and lock  
a final answer. The evaluator is **never** run in-loop; the critic is **never** told the gold. The  
**headline causal contrast is the arms A / A2 / A3 / C3 / A3C3**; `C` (weak critic) is **outdated** — dropped, will **not appear** in the final paper — and was a Stage-A  
diagnostic probe (historical only).

### 2.5 The three core strategies, as implemented in `src/`

The three load-bearing roles are separate code paths, not prompt styles; each has its own
module, iron rules, and optimized quantity. (The **solver** — `agent.py`, generation — frames
them and is not optimized here.)

#### Distiller — `build_mechanism_levels.py` (+ `build_error_taxonomy.py`, `build_unified_taxonomy.py`)

Offline, over the gold-annotated error bank; the only role that reads gold. A distillation chain — each level re-distills the one beneath it, and the vocabulary is iteratively refined as the bank grows, not a fixed taxonomy:
- **L1** (`build_behavior_leaves.py``) — one instance-level wrong-operation `mechanism` per
  errored (model, task) pair.
- **L2** (`build_mechanism_levels.py`) — clusters one solver model's L1 mechanisms into ≤8
  benchmark-level classes by the shared *wrong verb*; each class gets an answer-free `mechanism`
  (verb phrase), a differential gold-free `check_procedure`, and a `trigger` (question-type +
  committed-answer signature).
- **L3** — each L2 class is mapped into one cross-benchmark wrong-execution **archetype**; the archetype vocabulary is **distilled from the current error data, not fixed a priori**, and grows/refines as more (model, family) errors enter the bank. The present snapshot is
  (`build_mechanism_levels.ARCHETYPES`): `constraint_blind`, `descriptor_conflation`,
  `memory_substitution`, `procedure_truncation`, `sign_normalization_slip`, `retrieval_abort`,
  `format_nonconformance`.

A freeze step writes `level3_bank_{model}.json` — one answer-free entry per class (`definition`
= a past-participle suspicion clause, plus `check_procedure`, `trigger`, and de-identified
`examples`). Iron rules: **per-model banks** (never pool models), **never name** a molecule /
number / option / answer text. `build_unified_taxonomy.py` is a parallel detector-first 8-leaf
scheme kept only for the cross-family block-diagonality audit, not for runtime.

#### Strong critic — `strong_critic.py` (`StrongCritic`); weak fallback `egte_critic.py` (`Level3Critic`)

Gold-free, exec-time (`feedback(question, answer, family, reasoning)`). Reads the **question**, the
**committed answer**, the solver's hidden CoT (a 6000-char reasoning budget, truncated only when
longer) and the full answer-free L3 vocabulary. Against that vocabulary the LLM *reasons which
archetype(s) this specific answer most likely violates* — i.e. it re-targets the feedback to the
committed answer — then emits 1–3 grounded past-participle `suspicion`s, each with an
instance-specific `check` naming the exact step/value/assumption to re-verify (still answer-free).
On LLM/parse failure it falls back to `Level3Critic`:
deterministic TF-IDF retrieval, single direction, probability-free, "possible" never "confident".
Iron rules: never read gold; never emit a probability; never name the correct answer / option /
question-specific content. This is the **activation** source — it deliberately diverges the
candidate pool and therefore carries both **EIR** and **ECR**.

#### Evaluator — `stage_b_evaluator.py` (`rubric_cut` / `rubric_ce` / `rubric_v5`; *not yet final*)

Offline, never in-loop, never sees gold. Consumes the transition view (only *non-settled* tasks).
For each answer **switch edge**, a three-dimension judge scores `contradiction / error /
disconnection` (0–10) over the transition's reasoning (full hidden CoT); `error` is backlinked
against the answer-free L3 bank, and any dim ≥ 6 must carry open evidence else it is zeroed.
`rubric_ce` gates the CUT on `max(contradiction, error)`, dropping the direction-agnostic
`disconnection` (which fires on both DERAIL and REPAIR). Each switch → `CUT` (revert to old) or
`UNSURE` (keep both); aggregation = **elimination + mode**, with an all-UNSURE trace falling back to
`mode` (an honest abstention is **not** the current fallback). **Not final:** `rubric_ce` and
`rubric_v5` (rev 5) are still under comparison — `rubric_v5` is a structured judge separating an
*evidence* axis (old/new support, error with backlink-verified quotes) from a *reflection* axis
(confidence), in which only a backlinked error may CUT/KEEP, else UNSURE. (Reliable **abstention**
detection is hard for the current model and may be out of scope.) Offline scoring is normal accuracy
(locked == gold). This role is the **EIR** suppressor — it reverts misdirected transitions and locks
already-activated correct answers, retaining the ECR the critic re-surfaced.

The three evaluator strategies (all `elimination + mode`; they differ only in the judge structure, the decision rule, and the tie handling):

| Knob | `rubric_cut` (rev4) | `rubric_ce` (2026-10-25) | `rubric_v5` (rev5) |
| --- | --- | --- | --- |
| Judge structure | 3-dim `disconnection/contradiction/error` (0–10) over the transition CoT | same 3-dim judge | evidence axis (`old/new_support`, `error_*` w/ backlinked quotes) vs reflection axis (`confidence`) |
| Evidence gate | any dim ≥ 6 needs open evidence, else zeroed | same | backlink-verified quotes required |
| Decision rule | `CUT` iff `max(3 dims) ≥ cut_bar` | `CUT` iff `max(contradiction,error) ≥ cut_bar` (drops `disconnection`) | `CUT`/`KEEP` iff a side's backlinked conclusion ≠ its answer label (deterministic, no threshold) |
| Verdicts emitted | `CUT` / `UNSURE` | `CUT` / `UNSURE` | `CUT` / `KEEP` / `UNSURE` |
| all-UNSURE fallback | `mode` | `mode` | `mode` |
| surviving tie-break | `directional` | `directional` | `directional` |

Here `directional` = on a surviving-mode tie, lock whichever tied answer the judge's confident verdicts preferred more often (`CUT` prefers its old/left answer, `KEEP` prefers its new/right answer); with no confident preference, abstain.

The elimination → mode lock carries three further knobs (wired in `_elimination_mode_lock`, rev 8),
ablating *how* the per-run survive-scores fold into a locked answer:

1. **KEEP vote (`keep`, rubric strategies only).** A clean transition — all three dims 0 — reads as
   `KEEP` (new side survives, old side drops) when `keep` is on; off, it stays `UNSURE`.
   (`rubric_v5` has its own conclusion-mismatch `KEEP`, so `keep` is N/A there.)

2. **half-vote / fold (`vote_mode`).** Each run folds its two flank survive-scores (from its left and
   right switches) into one multiplier, and `UNSURE` casts a half vote or none:
   - `max` — fold = max(flanks), `UNSURE` = 0.5 (conservative: a run dies only if *both* flanks kill it);
   - `min` — fold = min(flanks), `UNSURE` = 0.5 (aggressive: a run dies if *either* flank kills it);
   - `0` — no half vote (`UNSURE` inert), fold = max over the hard 0/1 `CUT`/`KEEP` flanks.

3. **vote unit (`weight_by`).** `round` — every round of a run casts one vote (unit = round count);
   `fragment` — every maximal run casts one vote (unit = 1).

A verdict maps to survive-scores `CUT` = old 1.0 / new 0.0, `KEEP` = old 0.0 / new 1.0, `UNSURE` =
both w; the non-`None` answer with the highest total weight locks, and a tie is broken
`directional`ly (above) or abstains.

The scorer is **`scorer_LLM_rescue`**: `T1` deterministic exact-match (routed by answer form), `T2`  
LLM one-way FN rescue (re-reads only the committed final answer, never the CoT, never overturns a  
correct T1), `T3` multi-LLM voting / human review of contested rows. See `docs/EVALUATION_STANDARD.md`  
§0.

---

## 3. Experimental results — deepseek-v4-flash, all benchmarks except FAB

> **STATUS — all `§3` numbers are INVALID and must not be cited.** The §3.1 table mixes a fresh
> **A2** run (2026-10-20/21, *after* the deepseek GPQA thinking fix of 2026-10-18) with stale or
> missing comparison arms: **C** was run 2026-10-08/15 (pre-fix, and its GPQA slice used a different
> `rationale_mode`), **C3** has no full `new`/`gpqa` run, and the **A3**-deepseek run dir is empty.
> This makes A2's init look artificially highest across benchmarks — an artifact, not a placebo
> effect. **Plan: re-run all arms under the frozen standard in §3.0, then refill §3.1.**

**Model** `deepseek-v4-flash` (`deepseek-v4-flash-0731`). **Arms** A (bare, T=0) · A2 (fixed neutral  
placebo) · A3 (self-consistency, T=0.7, N=10) · A3C3 (A3-seeded round-0, then the C3 loop) · C3 (strong critic in-loop + evaluator `rubric_ce`  
offline). **Benchmarks** GSM8K, MATH-500, MMLU-Pro, BFCL, AIME, BBH, GPQA-Diamond (all non-FAB).  
FAB (finance) is a single deferred decision-only run, excluded by design.

### 3.0 Frozen per-arm runtime standard (every re-run must follow this)

| Arm                              | solver `T` | samples | aggregation                    | feedback                  | grader               |
| -------------------------------- | ---------- | ------- | ------------------------------ | ------------------------- | -------------------- |
| **A** (floor)                    | 0          | 1       | single answer                  | none                      | `scorer_LLM_rescue`  |
| **A2** (placebo)                 | 0          | 1       | fixed neutral placebo loop     | `A2_PLACEBO_FEEDBACK`     | `scorer_LLM_rescue`  |
| **A3** (self-consistency)        | 0.7        | 10      | i.i.d. majority vote (tie→1st) | none                      | `scorer_LLM_rescue`  |
| **C** (weak critic) — **outdated, not in final paper**  | 0          | 1       | frequency vote                 | weak critic (directional) | `scorer_LLM_rescue`  |
| **C3** (treatment)               | 0          | 1       | `rubric_ce` elimination + mode | strong critic (in-loop)   | `scorer_LLM_rescue`  |

Common frozen fields for **every** arm: `max_tokens = 8192` (`REASONING_BENCH_MAX_TOKENS`),
`rationale_mode = off`, `max_rounds = 10`, `early_stop_n = 3`, model `deepseek-v4-flash-0731`,
`seed = None`. `T = 0.7` applies **only** to A3's 10 i.i.d. round-0 samples; every other solver call
(all arms, including C3's feedback rounds) is deterministic `T = 0` — see `run_feedback_loop.py`
round-0, which runs A3C3's round-0 vote at `T>0` and the remaining loop at `T=0`.

**A3C3 (A3-seeded C3)**: run **contiguously with A3** (share A3's single run — no separate A3 pass) — A3's `T=0.7, n=10` i.i.d. majority vote becomes A3C3's
round-0 committed answer — then continue with the **C3 loop** (`T=0`, `max_rounds=10`,
`early_stop_n=3`). I.e. A3C3 = A3's round-0 vote + C3's feedback loop, run in the same pass as A3.

**Per-arm metrics for the §3.1 comparison:**

| Arm      | reported metrics                        |
| -------- | --------------------------------------- |
| **A**    | accuracy (single `T=0` sample)          |
| **A2**   | `init` · `final` · `settle` · `mode`      |
| **A3**   | `init` · `final`                        |
| **A3C3** | `init` · `final` · `settle` · `mode` · `evaluator` |
| **C3**   | `init` · `final` · `settle` · `mode` · `evaluator` |

- `init`      = accuracy of the round-0 committed answer.
- `final`     = accuracy of the **last** committed answer (end of the loop).
- `settle`    = accuracy of the **early-stop** answer — a trailing run of 3 identical committed
  answers (`early_stop_n = 3`); a loop that never settles abstains (scored as not-correct).
- `mode`      = accuracy of the **majority** committed answer across the whole loop (ties → latest
  appearance) — the round-level analogue of A3's i.i.d. vote.
- `evaluator` (C3 / A3C3) = accuracy of the offline evaluator's locked answer (strategy TBD — `rubric_ce` vs `rubric_v5` still being compared).

### 3.1 Cross-benchmark arm accuracy

| Benchmark    | n   | A (bare T=0) | A2 (placebo)  | A3 (SC vote)  | C3 (strong + `rubric_ce`) |
| ------------ | --- | ------------ | ------------- | ------------- | ------------------------- |
| GSM8K        | 50  | —            | 100% (50/50)  | 100% (50/50)  | 98% (49/50)               |
| MATH-500     | 50  | —            | 96% (48/50)   | 88% (44/50)   | 86% (43/50)               |
| MMLU-Pro     | 50  | —            | 94% (47/50)   | 94% (47/50)   | 94% (47/50)               |
| BFCL         | 50  | —            | 100% (50/50)  | 100% (50/50)  | 100% (50/50)              |
| AIME         | 50  | —            | 100% (50/50)  | 88% (44/50)   | 94% (47/50)               |
| BBH          | 44  | —            | 93% (41/44)   | 95% (42/44)   | 93% (41/44)               |
| GPQA-Diamond | 198 | —            | 86% (171/198) | 77% (152/198) | 81% (161/198)             |

Arm **A** (bare re-solve, T=0) is pending a clean T=0 re-run — its column is left empty for now.  
Arm **A2** reports the final committed answer of the fixed-neutral-placebo loop (T=0, rationale off).  
GPQA-Diamond pools the 50-item new slice and the 148-item gpqa_051-198 slice (A2 = 44 + 127 / 198).  
Benchmarks with no arm-to-arm separation will be dropped from the final paper.



## 4. Analysis data (flip19 + HLE — strategic probes, not benchmarks)

The flip19 slice and the HLE pilot are analysis probes for optimizing and reasoning about the  
strategy, not evaluation benchmarks. They are kept because only these items show enough answer  
transitions (flips) to quantify EIR / ECR and to inspect the mechanism.

### 4.1 flip19 (n = 19, the answer-transition slice)

19 items (across phase1 / new / gpqa) on which the arm-C loop produced an answer flip. EIR / ECR are  
per-round transition rates on the {correct, wrong} chain.

**Item list** (task id + prompt opening, grouped by source slice):

- **phase1** (`n=5`): `math500_010` ("The expression $2\cdot3\cdot4\cdot5+1$ is equal to 121…"), `math500_021` ("Evaluate $(1+2i)6-3i$."), `math500_027` ("In how many ways can $7$ people sit around a round table…"), `mmlu_pro_033` ("Find the amount to be paid each month in order to pay off…"), `mmlu_pro_047` ("Which of the following would yield the greatest net return…")
- **new** (`n=9`): `aime_018` ("A point $P$ is chosen in the interior of $\triangle ABC$…"), `aime_021` ("Three circles, each of radius $3$, are drawn with centers at $(14,92)$…"), `aime_044` ("Three $12$ cm $\times 12$ cm squares are each cut into two pieces $A$ and $B$…"), `gpqa_009` ("Which of the following molecules has C3h symmetry?…"), `gpqa_016` ("How many of the following compounds will exhibit optical activity?…"), `gpqa_028` ("(S)-4-hydroxycyclohex-2-en-1-one is treated with tert-Butyldimethylsilyl chloride…"), `gpqa_031` ("toluene is treated with nitric acid and sulfuric acid, forming product 1…"), `gpqa_048` ("cyclohexanone was treated with bromine, forming product 1…"), `gpqa_049` ("Sigmatropic rearrangement is a class of pericyclic reactions…")
- **gpqa** (`n=5`): `gpqa_095` ("3,3,6-trimethylhepta-1,5-dien-4-one is treated with 1 equivalent of meta-chloroperbenzoic…"), `gpqa_103` ("Which sequence of reactions from the following options would lead to the high-yield…"), `gpqa_109` ("Consider a bound system of two nucleons (NN) in a 1S0 state…"), `gpqa_163` ("We would like to dissolve (at 25°C) 0.1 g Fe(OH)3 in 100 cm3…"), `gpqa_167` ("Calculate the amount of non-Gaussianity (nG) in the Schrödinger cat state…")

| arm                    | n  | init  | final | EIR   | ECR   |
| ---------------------- | -- | ----- | ----- | ----- | ----- |
| A3C3, CoT-corrected    | 19 | 0.737 | 0.684 | 0.226 | 0.324 |
| A3C3, no-CoT (pre-fix) | 19 | 0.842 | 0.632 | 0.322 | 0.341 |
| C3, CoT-corrected      | 19 | 0.632 | 0.632 | 0.208 | 0.263 |
| C3v2 (old)             | 19 | 0.632 | 0.684 | 0.176 | 0.303 |

### 4.2 HLE pilot (n = 50, scorer-graded)

| line                   | init | final        | definition                                          |
| ---------------------- | ---- | ------------ | --------------------------------------------------- |
| A3 (self-consistency)  | 0.12 | 0.14 (7/50)  | N=10 @ T=0.7, majority vote                         |
| C3 strong-critic alone | 0.12 | 0.14 (7/50)  | strong critic last round, no evaluator              |
| C3 + `rubric_ce`       | 0.12 | 0.20 → 0.24 (12/50) | strong critic + offline evaluator, mode fallback; knob-optimized (`keep`+`fragment`) |
| C3 + `rubric_v5`       | 0.12 | 0.06 (3/50)  | strong critic + offline evaluator, mode fallback (pre-fix: was abstain) |

Activation (reachability): A3 16/50, C3 15/50. Head-to-head (A3 vote vs C3 full): 4 C3 saves  
(hle_028, hle_032, hle_038, hle_040), 1 C3 loss (hle_013) — net +3.

> `rubric_v5`'s `0.06 (3/50)` was scored under the old **abstain** fallback; after 2026-10-26 the
> fallback is **mode** (matching `rubric_ce`), so this number is stale and needs a re-run.
>
> Knob ablation (2026-10-26, offline re-derivation — no new LLM): re-scoring the committed `rubric_ce`
> verdicts under the three Stage-B knobs (`keep`, `vote_mode`, `weight_by`) on the rescuable slice
> (`correct_appeared ∧ ≥2 candidates`, n=11) lifts C3 + `rubric_ce` from its committed 10/50 (0.20) to
> **12/50 (0.24)**. The +2 decomposes: (i) **+1 from the rev-8 rewrite** (survive-score `fold=max` +
> directional tie-break replacing the hard-delete + abstain rule; on `hle_025` it rescues the
> once-flashed correct `142` that the old code deleted to no-survivors); (ii) **+1 from the
> `keep ∧ fragment` interaction** (`weight_by=fragment` lifts only when `keep=on`). `vote_mode` (the
> UNSURE half-vote) has no effect on this slice. flip19 (`rubric_ce`, n=5) is invariant across all
> three knobs (0.800 everywhere).

## 5. Research questions (Q1–Q5)

1. **Signal generalization (distiller → critic).** Does the distiller's answer-free `mechanism` +
   `check_procedure` give the strong critic a signal that *generalizes* — i.e. it fires on the right
   archetype across questions and benchmark families, rather than only on the bank items it was
   distilled from?

2. **Directional exploration (critic → solver), evidenced by transitions.** Does the strong critic
   actually steer the *solver* toward new (correct) directions — and is this established by transition
   evidence (the committed-answer trajectory plus the critic's per-transition rationale), not by
   aggregate accuracy alone? Concretely: does the critic activate a correct answer at least as often as
   A3's i.i.d. sampling (`P_act` ≥ A3), while keeping EIR from exceeding ECR (else the strong critic
   needs re-tuning)?

3. **Exclusion and abstention (evaluator).** Does the evaluator receive a signal strong enough to
   (a) exclude definitively-wrong candidates without cutting a correct one, (b) stay `UNSURE` when the
   evidence is weak, and (c) lock the most *sticky* state (the settled tail or the mode) rather than a
   transient answer? Is its current cut bar too conservative or too aggressive?

4. **Is the selection mechanism itself evidenced?** Beyond the final number: does the *transition
   evidence chain* — solver trajectory + critic feedback + evaluator CUT/UNSURE decisions — trace, per
   question, *why* a wrong candidate was excluded and the correct one retained, so the elimination is
   attributable to a real error mechanism rather than to noise or a lucky re-sample?

5. **A3 vs C3 by question type.** Is the advantage question-type dependent — A3 a strong
   *multiple-choice* vote, whereas C3's critic + evaluator applies more broadly (open-ended /
   derivational answers, where a plain majority vote is ill-defined)? Could C3 close the gap further by
   reasoning over the *similarity* between candidate answers (not yet introduced)?
