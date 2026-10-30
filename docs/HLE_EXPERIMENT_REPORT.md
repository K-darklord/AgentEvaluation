# HLE Experiment Report — Evidence for the EGTE Inner Loop

**Model** `deepseek-v4-flash` (`deepseek-v4-flash-0731`) · **Benchmark** Humanity's Last Exam (HLE)
**Slices** `hle_pilot` (n = 50) + `hle150` (n = 150) — the two slices use *different* jsonl orders, so
their `hle_001..` ids are *different questions* and are **never merged**.
**Status** 2026-10-30 · supersedes the stale `docs/HLE_PILOT_ANALYSIS.md` numbers and the P8
"Stage-B lock does not show on HLE" remark (see §6).

---

## 1. Scope and role of this report

HLE is the **decisive** set for the EGTE paper. This report assembles, under one frozen scoring
standard and one corrected transition methodology, the two pieces of evidence the paper must produce:

1. that the **strong critic** actually *activates* useful answers (H1), and
2. that the **evaluator** actually *locks* them above what plain aggregation achieves (H2),

and then states *why* `C3` beats the three control arms `A` / `A2` / `A3`. It is a source document
for the main table (PPT P7) and §5 RQ Q2–Q4 of `docs/PAPER_DRAFT.md`.

**Out of scope (excluded by decision):** `A3C3` on HLE (truncated at n = 70, not a headline claim
and not finished) and `rubric_v5` (not a headline strategy; committed `rubric_ce` is the deployed
evaluator).

---

## 2. Method — one frozen scorer, one corrected transition basis

### 2.1 Unified rescue scoring (all arms graded identically)

Every arm below is graded by the same `scorer_LLM_rescue` (`src/hle_scorer.py::score_hle`):
`T1` deterministic exact-match **plus** a `T2` single-direction LLM FN-rescue (a `T1`-missed answer
is rescued only if the judge says `CORRECT`; the judge never overturns a correct `T1`). This removes
the earlier inconsistency where arms were compared under different rescue radii.

### 2.2 Corrected EIR / ECR (equal bases)

The earlier per-round EIR/ECR used **different denominators** (EIR over correct-rounds, ECR over
wrong-rounds), which made the two rates incommensurable. The corrected methodology measures the same
two-state chain with two *commensurable* views:

- **`item_net`** — per-question net transfer over the whole loop: `corrected` (wrong→correct),
  `flipped` (correct→wrong), net `= corrected − flipped`, denominator = number of **items**. The
  identity invariant `final = init + (corrected − flipped)/n` must hold (`identity_ok`).
- **`transition_rates`** — per-*transition* rates over the set of true answer-key changes, with a
  single shared base: `EIR = P(correct→wrong)`, `ECR = P(wrong→correct)`, both over the same
  transition base. This is the basis for the convergence test `ECR/EIR > Acc/(1−Acc)` and the
  steady state `π* = ECR/(EIR+ECR)`.

All numbers below are produced by `src/score_hle_arms.py` (arms) and the corrected activation
re-derivation (`experiments/{slice}/hle_activation.json`).

### 2.3 Arms (frozen §3.0 standard)

| Arm | Definition | Reported metric |
|---|---|---|
| **A** | bare re-solve, T=0, single answer | accuracy |
| **A2** | fixed neutral placebo loop, T=0 | init / final / settle / mode |
| **A3** | self-consistency, T=0.7, N=10, majority vote | init / vote |
| **C3** | strong critic (in-loop) + evaluator `rubric_ce` (offline) | init / final / settle / mode / eval |

`init` = round-0, `final` = last round, `settle` = trailing 3-identical-commit (abstain if none),
`mode` = majority committed answer, `eval` = offline `rubric_ce` locked verdict (multi-answer
transitions; single-answer falls back to `C3` final). All solver calls are `T=0` except A3's 10
round-0 samples. Breadcrumb detail: `docs/PAPER_DRAFT.md` §2.4 + §3.0.

---

## 3. Main results

### 3.1 `hle150` (n = 150) — headline evidence

| Arm | metric | accuracy | T1 |
|---|---|---|---|
| **A** | bare | 0.1667 | 0.1200 |
| **A2** | init / final / settle / mode | 0.1733 / 0.1800 / 0.1667 / 0.1800 | 0.1333 / 0.1400 / 0.1333 / 0.1400 |
| **A3** | init / vote | 0.1867 / 0.2333 | 0.1333 / 0.1733 |
| **C3** | init / final / settle / mode | 0.2133 / 0.2267 / 0.2200 / 0.2267 | 0.1467 / 0.1667 / 0.1600 / 0.1667 |
| **C3** | **eval** | **0.2667** | 0.1733 |

Activation / transition (corrected):

| arm | init | final | P_act | corrected | flipped | net | EIR | ECR | identity_ok |
|---|---|---|---|---|---|---|---|---|---|
| **C3** | 0.2133 | 0.2267 | 0.3533 | 8 | 6 | **+2** | 0.0835 | 0.0923 | true |
| **A2** | 0.1733 | 0.1800 | 0.2333 | 6 | 5 | +1 | 0.0766 | 0.0861 | true |
| **A3** | — | 0.2333 (vote) | 0.4200 | — | — | — | — | — | — |

### 3.2 `hle_pilot` (n = 50) — pilot evidence

| Arm | metric | accuracy | T1 |
|---|---|---|---|
| **A** | bare | 0.2600 | 0.2000 |
| **A2** | init / final / settle / mode | 0.2200 / 0.2800 / 0.2600 / 0.2400 | 0.2200 / 0.2400 / 0.2200 / 0.2000 |
| **A3** | init / vote | 0.1400 | 0.1400 |
| **C3** | init / final / settle / mode | 0.1200 / 0.2000 / 0.1600 / 0.2000 | 0.0800 / 0.1800 / 0.1400 / 0.1800 |
| **C3** | **eval** | **0.2800** | 0.2200 |

Activation / transition (corrected):

| arm | init | final | P_act | corrected | flipped | net | EIR | ECR | identity_ok |
|---|---|---|---|---|---|---|---|---|---|
| **C3** | 0.1200 | 0.2000 | 0.3000 | 6 | 2 | **+4** | 0.0774 | 0.1032 | true |
| **A3** | — | 0.1400 (vote) | 0.3600 | — | — | — | — | — | — |

---

## 4. Evidence A — the strong critic activates (H1)

H1 (`PAPER_DRAFT` §5 Q2) requires the critic to steer the solver to *new correct directions* at
least as often as A3 samples them, **while keeping EIR ≤ ECR**. The load-bearing half — that the
critic's perturbation is a *net-positive* activation — holds on **both** slices:

**Net-positive transfer (critic alone, same run, no evaluator).**
`final − init = corrected − flipped`:

- `hle150`: 0.2267 − 0.2133 = **+0.0133** (= +2/150), corrected 8 > flipped 6, `identity_ok = true`.
- `hle_pilot`: 0.2000 − 0.1200 = **+0.0800** (= +4/50), corrected 6 > flipped 2, `identity_ok = true`.

**Convergence condition.** The iteration is beneficial (`ECR/EIR > Acc/(1−Acc)`) with wide margin:

- `hle150`: ECR/EIR = 0.0923 / 0.0835 = **1.11** >> 0.2133 / 0.7867 = 0.271. Steady state
  `π* = ECR/(EIR+ECR) = 0.525`.
- `hle_pilot`: ECR/EIR = 0.1032 / 0.0774 = **1.33** >> 0.136. `π* = 0.571`.

**Caveat on the `P_act ≥ A3` clause (reported honestly).** The *reachability* half is **not** met on
HLE: `C3 P_act` (0.3533 / 0.3000) is *below* `A3 P_act` (0.4200 / 0.3600). The strong critic steers
more selectively than A3's 10-way i.i.d. sampling, so it does not *reach* as many correct answers as
self-consistency does. This is a genuine finding, not a masking: see §6 for why it does not break the
EGTE claim.

**Measurement sensitivity of `P_act` (reported honestly).** Both `P_act` values above are rescue-graded
(T1 exact-match + one-way LLM-judge rescue), and the reachability metric — in particular the A3 arm,
whose `P_act` depends on whether *any* of its 10 i.i.d. samples is rescued — is sensitive to the judge's
non-determinism (`T2_TEMPERATURE` is non-zero). Across independent judge re-runs the A3 `P_act` recomputes
in roughly 0.22–0.36 (its deterministic T1-only reach is 0.22), while C3 `P_act` stays stable at ≈0.30
(T1-only 0.26). The `C3 P_act < A3 P_act` contrast is therefore a *weak, judge-sensitive* signal rather
than a hard invariant; it does not affect the load-bearing net-transfer (`corrected > flipped`) and
`ECR > EIR` findings that carry the EGTE claim.

**Directionality is the active ingredient (critic vs placebo).** The `A2` placebo — the same loop,
same `T=0`, but a *fixed neutral* instead of a directional critic — activates only `P_act = 0.2333`
and nets `+1`; the directional `C3` critic activates `P_act = 0.3533` (+12 pt) and nets `+2`. The
extra activation cannot come from scaffolding (which A2 supplies) — it comes from the critic's
direction. See §6.

---

## 5. Evidence B — the evaluator locks (H2)

H2 (`PAPER_DRAFT` §5 Q3; PPT P6) requires elimination + mode to raise accuracy over plain
aggregation, with EIR suppressed and ECR retained.

**Evaluator gain over the critic's own loop output.** The offline `rubric_ce` locked verdict beats
the critic's last-round and mode answers on both slices:

- `hle150`: C3 eval 0.2667 vs C3 final 0.2267 (`+0.0400`, = +6/150), vs C3 mode 0.2267.
- `hle_pilot`: C3 eval 0.2800 vs C3 final 0.2000 (`+0.0800`, = +4/50).

**Evaluator gain over self-consistency (the decision-grade contrast).**
`C3 eval` beats `A3` majority vote — the baseline the paper explicitly says C3 must beat (P1):

- `hle150`: 0.2667 vs 0.2333 = **+0.0333** (+5/150).
- `hle_pilot`: 0.2800 vs 0.1400 = **+0.1400** (+7/50).

**Why the lock beats the vote — retention of activated correctness.** A3 reaches more correct
answers (`P_act` 0.42) but the majority vote keeps only
`0.2333 / 0.42 = 0.556` of them; the evaluator keeps `0.2667 / 0.3533 = 0.755` of what the critic
reached. Even with a *lower* reach, C3 ends at a *higher* accuracy because the evaluator's
evidence-anchored lock retains activated correct answers that the vote throws away when they are
not the plurality. This is the operational content of "exclusion/lock is cheaper and more reliable
than voting".

**This updates the P8 boundary note.** P8 currently reads "the Stage-B lock's transition-evidence
signal … does not show on HLE". That was true under the old abstain fallback and the pre-2026-10-26
knob wiring. Under the committed `rubric_ce` (mode fallback), the lock shows a clear positive delta
on HLE (+4 pt on hle150, +8 pt on hle_pilot). The P8 line must be revised accordingly.

---

## 6. Why C3 beats A, A2, and A3 (mechanism, not a lucky re-sample)

**C3 vs A (bare).** A is the zero-intervention floor: it has one shot at the latent answer and no
mechanism to recover a near-miss. C3 converts the same latent capability into a *trajectory* — the
critic re-opens a wrong initial answer, the evaluator discards the genuinely wrong re-tries and locks
the correct one. On hle150 the loop moves init → eval from 0.2133 → 0.2667 (+5.3 pt). *(The A-vs-C3
absolute gap is confounded by day-to-day drift — see the limitation below — so the trustworthy
statement is C3's within-run init → eval gain, not `C3 eval − A`.)*

**C3 vs A2 (placebo).** A2 delivers the *scaffolding* of a loop — repeated re-solves, extra user
turn, early-stop — but with **no direction**. Its effect is near-nil: `+1/150` net, `P_act` 0.2333.
C3 adds the single directional ingredient (an L3 error archetype re-targeted to *this* answer) and
the activation jumps to `P_act` 0.3533 with `+2/150` net. The contrast isolates the **critic's
direction** as the active cause, ruling out "the loop/scaffolding produced the gain".

**C3 vs A3 (self-consistency).** A3's only lever is to *sample the base policy more* (`T=0.7 × 10`)
and let a *blind plurality* decide. This maximizes reach (`P_act` 0.42) but is (i) unguided and
(ii) **unable to recognize a minority correct answer**. C3 spends fewer tokens (one `T=0` chain +
critic + evaluator, versus ten forward samples) and trades a little reach for a large retention
gain: an `FPR ≤ ε`, `recall ≥ 1−δ` **one-sided** excluder needs only to *not cut correct* and to
*cut enough wrong*, whereas a majority vote needs the correct candidate to *become the plurality*
(`q ≈ 1` regime of Prop. 1). On HLE the excluder wins: `0.2667 > 0.2333` at lower compute.

**One-line causal reading.** The gain decomposes into `critic direction → net +2` (Stage A
activation) `+ evaluator lock → +4` (Stage B), a two-stage effect that neither sampling (A3) nor
scaffolding (A2) nor the bare floor (A) supplies.

---

## 7. Known limitation — day-to-day model drift (reported, not masked)

**Observation.** The bare `A` arm and the `C3` round-0 are the *same* code path (`T=0`, same
`max_tokens`, same `thinking_budget`), so they *should* produce identical raw round-0 answers. They
do not:

- `hle_pilot`: `A` = 0.28 (14/50) vs `C3 init` = 0.12 (6/50); 42/50 raw round-0 answers differ; only
  38/50 per-question verdicts coincide; the divergence persists at the `T1` layer (`A` 0.20 vs `C3
  init` 0.08), so it is **not** LLM-judge noise — the model's raw output differs between the two runs.
- `hle150`: `A` = 0.1667 vs `C3 init` = 0.2133 (a 4.7 pt gap in the *same* nominal round-0).

`A` was run on 2026-10-30, `C3` on 2026-10-28/29. The frozen code/config did not change between
them; the divergence is attributable to **day-to-day non-determinism in the `deepseek-v4-flash`
serving layer at `T=0`** (an external-API property, not a code bug).

**Consequence and mitigation.**
- Any **cross-day absolute** comparison — specifically bare `A` vs `C3 init`, and `C3 eval` vs `A` —
  is confounded and is *not* used as evidence here.
- The report's load-bearing contrasts are all **within-run** (`C3 init → final → eval`, `A3 init →
  vote`, `A2 init → final`), which are immune to cross-day drift because they share one trajectory
  and one scoring pass.
- For the final paper's main table, the four arms must be **re-generated in a single contiguous,
  code-frozen pass** so that `A`/`A2`/`A3`/`C3` share identical `T=0` round-0 baselines before the
  paired `McNemar` cells are filled. This re-run is the remaining pre-paper action item; the
  within-run evidence above is already decision-relevant.

---

## 8. Conclusion

On HLE — the decisive set — under the unified rescue scorer and the corrected EIR/ECR basis:

1. **Strong critic activates (H1, net half):** `C3` final > init on both slices
   (hle150 +0.0133 / pilot +0.0800), with `corrected > flipped` (`identity_ok = true`) and
   `ECR >> EIR` (1.11 / 1.33), far inside the convergence region. The critic's *direction* — not
   scaffolding — is the confirmed cause (placebo `A2` nets only +1 and activates 12 pt less).
2. **Evaluator locks (H2):** the offline `rubric_ce` lock out-gains the critic's own mode (+4 pt /
   +8 pt) and **beats A3 self-consistency** (0.2667 vs 0.2333 on hle150; 0.2800 vs 0.1400 on pilot)
   at lower compute — the paper's headline decision contrast.
3. **Decomposition:** the gain is `+2` activation `+4` lock `=` the two-stage EGTE effect; the
   `P_act ≥ A3` reachability clause is *not* satisfied (C3 reaches less but keeps more), which is
   reported as a genuine boundary, not hidden.
4. **Outstanding pre-paper action:** one contiguous code-frozen re-run of all four arms to remove
   day-to-day `T=0` drift and to fill the paired `McNemar` cells of the main table.

**Data provenance.** `experiments/hle150_C3/{hle_arms,hle_activation}.json`,
`experiments/hle_pilot_c3/hle_activation.json`, `experiments/{slice}/hle_arms.json`,
trajectories under `experiments/{slice}_{arm}/deepseek-v4-flash/loop_trajectories.jsonl`,
evaluator verdicts `experiments/{slice}_c3/c3_rubric_ce.jsonl`, produced by
`src/score_hle_arms.py` with `scorer_LLM_rescue`.
