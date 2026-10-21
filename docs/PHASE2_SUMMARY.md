# Phase 2 Summary

**Document type**: Phase 2 (RSI) live summary — progress, anomalies, decisions, plan.
**Version**: 0.3 · **Date**: 2026-10-19
**Companion documents**: `PHASE1_SUMMARY.md` (§8 Phase 2 plan), `RESEARCH_PLAN.md` (§3.7 two-stage, §5.15 Stage B evaluator), `WORKMAP.md` (§0.2 two-stage + EIR/ECR bridge), `REPRODUCIBILITY.md` (config provenance).

> **Reading note (2026-10-19).** §1, §3, §4, §5, §6 and §7 items 1-11 below
> are **DEPRECATED** (kept verbatim for history); each carries an inline marker.
> The live protocol is §7 items 12-18, §8 (Phase-3 plan) and §12 (three-channel
> decoupling).

---

## 1. Status snapshot

> **DEPRECATED (2026-10-13 snapshot).** Superseded by §7 items 12-13 (settle =
> Stage A, non-settle 112-task target slice) and §12 (three-channel decoupling).
> Kept verbatim for history.

Phase 1 (probe) is complete: 3 mid-tier models × 250 tasks (5 families × 50) × up to 11 rounds
of weak-critic feedback, temperature = 0, single arm C. Phase 2 is in progress and asks the
*controlled* question: **does the weak critic (arm C) provide a real RSI gain over no-direction
sampling (arm A3)?**

Where we are (2026-10-13, updated):

- Phase-1 (250, 3 models) and new-set (aime/gpqa/bbh 144, 3 models) C/A3 trajectories are collected (§3).
- GPQA-Diamond is the sole discriminative set; the full 198 questions are pinned to a fixed,
  reproducible list (`data/processed/gpqa_198_tasklist.json`). deepseek A3 (051–198) + C (051–198)
  are run, but **without rationale** (see below).
- **Critical fix (2026-10-13): every C-arm run must emit `--rationale-mode`.** The transition
  self-report ("Reason:" line) is the Stage-B hook (§2.1, §5.5); `off` forfeits Stage B. Verified on
  deepseek (`reason_line` collects the per-transition rationale with the committed letter intact);
  glm needs `twostage` (no-commit, §4); qwen uses `reason_line`.
- **Difficulty: the current GPQA aggregate init ≈ 77% exceeds the hard-layer ceiling (70%, §6.2),**
  so the recent C/A3 GPQA numbers live on the *saturated* layer and cannot discriminate the arms.

Current priority: (1) per-question difficulty screening → hard layer (init ∈ [35%, 70%], §6.2);
(2) re-run C with rationale on the hard layer only; (3) compare the three dimensions (§2.3, §2.7) on
hard data. Do **not** run FAB yet.

---

## 2. Phase 2 objectives and design

### 2.1 Two-stage RSI

The core claim to establish: **the error set is an effective RSI information source**, expressed as
two train-free stages (aligned with the paper's "EIR suppression vs ECR enhancement"):

| Stage | Mechanism | Observable | Target |
|---|---|---|---|
| **A** (activation) | error-set sampling + weak-critic directional feedback | activation rate `P_act` | raise the reachable ceiling |
| **B** (locking) | external weak evaluator excludes unreasonable states (transition-level) | lock-in rate | hold an activated answer to final |

These beat passive sampling only if the weak critic adds information beyond `pass@k`; the claim is
tested against the arm ordering **A3 (no-direction sampling) ≤ C (noisy critic) ≤ C\* (oracle
verifier)** as `C > A3`.

### 2.2 Control arms

| Arm | Feedback | Temperature | Early stop | Sampling |
|---|---|---|---|---|
| A | none (bare re-solve) | 0 | — | single |
| A2 | form placebo ("No confident error direction…") | 0 | — | single |
| A3 | none (i.i.d.) | 0.7 | none | N = 10, majority vote |
| C | weak-critic directional (cause + attention) | 0 | N = 3 consecutive correct | single chain |
| C\* | oracle verifier | — | — | best-of-N ceiling |

A / A2 / C keep temperature = 0; **A3 is the only T > 0 arm** (the best-of-N / majority-vote
passive lower bound). A3 baseline is frozen: `temperature = 0.7`, `N = 10`, no feedback, no early
stop, independent sampling.

### 2.3 Three independent comparison dimensions (no cross-dim mixing)

1. **Activation** — `P_act` / `ceiling`.
2. **Final single answer** — round-0 vs last-round (`@1`).
3. **Vote / mode** — majority-vote over the trajectory (C mode ≡ A3 vote).

C must be compared to A3 **separately on each** dimension. C-round-0 and A3-@1 are the *same
quantity* (first answer, before feedback): if they systematically diverge on a family it can only be
temperature / prompt / scorer drift, never a treatment effect — this is the first diagnostic to run
on any "C below A3" surprise.

### 2.4 Headroom three buckets (mutually exclusive, `n = never + headroom + locked`)

| Bucket | Definition | Stage B? |
|---|---|---|
| `locked` | correct activated **and** held to final | no (already locked) |
| `headroom` | correct activated **but not locked** | **yes — sole Stage-B target** |
| `never` | correct never appears | no (excluded — dirty denominator) |

### 2.5 EIR/ECR bridge (Liu & Meng 2026)

`reversibility r = 1 − ∏(1 − ECR)`; stability region `ECR / EIR > Acc / (1 − Acc)`. Kept distinct
from the macro `P_act` / lock-in rate; linked via `r`.

### 2.6 Cost / token metering

Phase 2 is the first phase with a token/cost axis (Phase 1 predates the metering instrumentation).
`configs/model_prices.csv` + `data/processed/model_token_usage.csv` + `src/cost_table.py`.
The k/θ cost curve (sampling budget vs gain) is a Phase-2 planning input.

### 2.7 Three claims (headline) + proof direction + sample size (2026-10-19)

The whole Phase-2 question reduces to three claims, one per comparison dimension (§2.3). Do **not**
collapse them — different effect sizes, different sample needs. The reachability chain is
**A < C ≤ A3** (A = T=0 single no-feedback; C = critic-perturbed T=0; A3 = T=0.7, N=10 i.i.d.).

| # | Claim | Dimension | Direction |
|---|---|---|---|
| 1 | C activation > A activation, but ≤ A3 activation | `P_act` | A < C ≤ A3 |
| 2 | C settle (Stage A) > A3 vote | settle acc vs vote acc | superiority |
| 3 | C Stage B abstains more on non-activated answers | meta (`UNSURE`) | superiority |

**Claim-1 strategic corollary (deferred to Phase 3).** Because C `≤` A3 on activation (A3 samples
more widely), the optimal pipeline is **A3's majority vote as the round-0 answer, then continue C's
feedback loop from there** — the weak critic refines an already-strong seed instead of re-deriving
from T=0. Phase 3 tests whether this hybrid reaches the highest final accuracy.

**Claim-3 is Stage B's meta-cognition, not a third accuracy mechanism.** The only additive value
Stage B holds over Stage A is the *abstain* channel: where the correct answer never activated (the
`never` slab, §2.4), C can emit `UNSURE` instead of committing a guess — A3's majority vote must
always commit to one option. It is graded orthogonally to accuracy (§7 item 15): `ANSWER:` accuracy
vs `UNSURE` metacognition.

Sample sizes will be recomputed against these new directions before the next collection pass.

### 2.8 假设三元组（支持证据 / 失败判据，2026-10-19）

把 §2.7 的三 claim 映射到七阶段框架的阶段 4「H1 可识别 / H2 机制敏感 / H3 决策价值」三层可证伪假设，每条配失败判据，避免确认偏误：

| 假设 | 支持证据（什么结果支持它） | 失败判据（什么结果削弱它） | 对应 claim |
|---|---|---|---|
| **H1 可识别**：弱 critic 能在 A 与 A3 之间提升可达性 | 硬层上 `P_act(A) < P_act(C) ≤ P_act(A3)`，且非饱和层 | `P_act(C) ≤ P_act(A)`（C 无增益）；或 `P_act(C) > P_act(A3)`（推翻 A3 上限）；或只在饱和层（init > 70%）有差 | Claim 1 |
| **H2 机制敏感**：settle 锁定优于投票 | `settleAcc(C) > voteAcc(A3)`，且分差随 Stage-A 关键改动而变 | `settleAcc(C) ≤ voteAcc(A3)`；或改无关项也产生同等分差 | Claim 2 |
| **H3 决策价值**：Stage-B abstain 有决策价值 | 未激活答案上 `UNSURE(C)` 的覆盖率 / 正确率 > A3 的强制 commit | abstain 不带来净收益；或成本 > 收益 | Claim 3 |

H3（abstain）作用在未激活 slab 上，是 Claim 1 可达性的补集；它独立于 H1/H2 记分，但只有 H1 的激活边界先定下来，H3 的决策价值（何时该 abstain）才可定义。

---

## 3. Data inventory

> **DEPRECATED.** All entries below used the old `reason_line` / `twostage` /
> `rationale off` protocol; the current Stage-B non-settle resampling uses the §12
> three-channel (`transition`) protocol. Kept for directory history only.

| Run | Dir | Arm / scope | Model coverage | Status |
|---|---|---|---|---|
| C phase 1 | `experiments/feedback_loop_20261006_173715/` | C, 5 families × 50 | deepseek / glm / qwen | stored; bfcl + mmlu_pro scorer/prompt drift (see §4) |
| C new (deepseek) | `experiments/feedback_loop_C_20261008/` | C, aime/gpqa/bbh 144 | deepseek | clean |
| C new (glm/qwen) | `experiments/feedback_loop_C_new_20261011/` | C, 144, `emit_rationale=true` | glm / qwen | qwen clean; glm contaminated (no-commit, §4) |
| A3 phase 1 | `experiments/experiments/a3_phase1_20261010_t0.7/` | A3, skip_finance | deepseek / glm / qwen | clean |
| A3 new | `experiments/experiments/a3_new_20261010_t0.7/` | A3, 144 | deepseek / glm / qwen | clean |
| GPQA-198 A3 | `experiments/a3_gpqa_full_deepseek_20261013/` | A3, gpqa 051–198 | deepseek | clean (A3 needs no rationale) |
| GPQA-198 C | `experiments/c_gpqa_full_deepseek_20261013/` | C, gpqa 051–198, `rationale off` | deepseek | **needs re-run with rationale** |
| GPQA-198 C (001–050) | `experiments/c_gpqa_001_050_deepseek_20261013/` | C, gpqa 001–050, `rationale off` | deepseek | **stopped 36/50, needs re-run with rationale** |
| GPQA C rationale smoke | `experiments/c_smoke_rationale_20261013/` | C, gpqa 3, `reason_line` | deepseek | rationale collection verified ✓ |

---

## 4. Data anomalies (flagged)

> **DEPRECATED (mostly resolved).** #1 bfcl and #2 mmlu_pro are resolved via
> offline re-score / rerun; #3 glm no-commit and #5 cross-model protocol mismatch
> are superseded by §12 three-channel decoupling. Kept as historical anomaly log.

All three "C systematically below A3" surprises were traced to **measurement / rubric drift**, not a
real C deficit. Marked so that no downstream analysis trusts cross-version `is_correct` fields.

| # | Anomaly | Root cause | Fix |
|---|---|---|---|
| 1 | **bfcl** C < A3 | C arm (20261006) stored `is_correct` from the old buggy `_score_bfcl`; A3 (20261010) used the fixed version. Same raw `final_answer` verbatim, scored opposite. | Offline re-score with current `_score_bfcl` → deepseek/glm C bfcl = 50/50 = A3. **No rerun.** |
| 2 | **mmlu_pro** C < A3 | C arm lacked the "respond ONLY the option letter" prompt → model emitted prose → `_extract_mcq_letter` returns None → judged wrong; A3 had the prompt. | **Rerun** phase-1 mmlu_pro 3 models × 50 with the prompt. |
| 3 | **glm new-set C** degraded (naive 65.3%, corrected 81.9%) | `emit_rationale=true` induced glm `no-commit` (feedback rounds emit pure "Reason:" prose, drop the answer). Naive score 65.28%; offline re-score with carry-forward + unicode-minus fixes (on-disk `loop_summary.corrected.json`) recovers to 81.94% — but still **11 pp below init (93.1%)** with 19 "misled" state-2 tasks, so the transition/final data remain contaminated. | **Rerun** glm new-set C (144) with decoupled answer/rationale collection, `emit_rationale` kept (§6.4). |
| 4 | **deepseek GPQA no-commit divergence (C=16, A3=7, overlap=5)** | Sampling-temperature path artifact, not a treatment effect: `temp=0` (C) and `temp=0.7` (A3) no-commit on a *different* task set. Neither `reason_line` nor `enable_thinking` fixes it (see note after the temp=0 block). | Annotate no-commit tasks before any A3-vs-C commit-rate comparison; never read A3 > C on them as the weak critic hurting. |
| 5 | **cross-model rationale-protocol mismatch** | glm C uses `twostage` (two-call answer/reason decoupling) while deepseek/qwen C use `reason_line` (single call + "Reason:" tail): different prompt structures and call counts across models, so cross-model C comparison is unsound. | Defer to Phase 3: standardize rationale collection to ONE protocol and re-run all C arms to quantify the difference (see §7). |

Cross-run stored `is_correct` is **not trustable across scorer/prompt versions**; comparisons must
first align prompt + scorer + re-score offline or rerun.

**temp = 0 round-0 non-determinism (sampling-level limitation, closed).** A glm-5.3 GPQA probe
(20× round-0 per question, no feedback) shows round-0 answers drift even at `temperature = 0`, but
*only on fragile near-tie questions*:

| question | seed = None | seed = 42 |
|---|---|---|
| gpqa_001 (stable, gold `B`) | `B` ×20 | `B` ×20 |
| gpqa_014 (fragile, gold `D`) | `D`×10 `B`×5 `A`×1 `Looking`×2 prose×1 | `D`×14 `B`×1 `A`×1 `Looking`×3 prose×1 |
| gpqa_019 (fragile, gold `D`) | `D`×12 `A`×6 `C`×2 | — |

Three stacked causes: (1) argmax float-flip on near-equal logits — stable questions (gpqa_001) are
fully deterministic (20/20); (2) server-side reasoning randomness is only *partially* anchored by
`seed` (`seed = 42` shifts `D` 10→14 but does not reach 100%); (3) `no-commit` is a
temperature/seed-agnostic co-occurring artifact (3–4/20 responses fold the answer into `Looking` /
prose rather than a commit line).

Impact / mitigation: on a single run fragile questions form a high-variance zone for C vs A3, but the
drift is random *per question*, not a systematic bias toward either arm — at the ≥ 100-question hard
layer (§6.3) it averages out and C / A3 are affected symmetrically. Recorded as a limitation; **no
further per-model probes** are planned. A residual C < A3 on large sets would indicate genuine
non-robustness, not drift.

**deepseek GPQA no-commit is a temperature-path artifact, not a C-nightmare.** The C arm (temp=0) no-commits on 16 GPQA tasks; A3 (temp=0.7) on 7, with only 5 in common (gpqa_072/089/091/122/148). The 11 C-only tasks (gpqa_070/077/082/095/103/121/127/128/146/167/186) are ones where A3 *can* commit — but rarely (1–7/10 rounds) and mostly to the wrong letter (only gpqa_103/121/167 vote correct). Two A3-only tasks (gpqa_065/116) no-commit at temp=0.7 yet commit under temp=0. Neither `reason_line` (re-states "answer only, no explanation" every feedback round) nor `enable_thinking=true` fixes the C no-commit: enabling thinking routes the CoT into hidden `reasoning_content` but never terminates it (gpqa_070 → 61k-char CoT, `finish_reason=length`, empty `content`). **Consequence:** the lower A3 no-commit count is a sampling-temperature difference, NOT evidence that C's weak critic harms; any A3-vs-C commit-rate comparison must annotate these no-commit tasks and must not read A3 > C on them as a treatment effect.

---

## 5. Findings so far

> **Finding 4 is DEPRECATED** -- it reports the old `reason_line`-era headroom
> (~2-3 questions); the current non-settle target slice is 112 tasks (§7 item 13).
> Findings 1-3 remain historical context.

1. **`C-mode ≡ A3-vote` is the wrong reading.** "Mode" and "vote" are both *frequent-answer*
   selectors, but they act on **different sampling distributions**: C is weak-critic *perturbed*
   adaptive sampling (a trajectory, non-i.i.d.), A3 is *isotropic* i.i.d. sampling. Equating them
   assumes away Claim 1 (§2.7). C carries a trajectory structure — and thus the Stage-B transition
   hook — that A3 lacks. No clean `A3 >> C` cell survives §4, but no significant `C >> A3` cell
   exists either at n ≤ 198 on the saturated layer.

2. **Three-way split (clean discrete data).** The only C >> A3 cell with `.1`-level separation is
   `deepseek × GPQA` (act 47>44, fin 43>38 @1, mode 46>44). All other benchmarks are parity; there is
   no clean A3 >> C cell.

3. **Benchmark saturation is the binding constraint.** aime / bbh / mmlu_pro are saturated
   (init > 80%, act ≈ fin). **GPQA is the only discriminative set** (init ~76%, non-trivial
   act − fin gap).

4. **True Stage-B headroom is small.** After correcting the glm contamination and letting the mode
   selector lock what it can, the residual activated-but-unlocked headroom is ~2–3 questions
   (deepseek `aime_044 = 864`, `gpqa_031 = D`; qwen `bbh_0019 = F`). Mode already locks most
   activated-unlocked cases (deepseek 5/7, qwen 2/3). The raw pool number (37 discrete headroom) is
   inflated by glm's contaminated no-commit run and must not be used for Stage B.

5. **`emit_rationale` is the Stage-B hook.** The transition log (`A_t → A_{t+1}` with self-reported
   rationale) is the unique information C has that A3 pass@k lacks; dropping it forfeits Stage B.
   (See §6.4.)

---

## 6. Decisions (2026-10-12)

> **DEPRECATED (2026-10-12 decisions).** Historical; the current plan lives in
> §7 items 12-18 and §8 (Phase-3 plan, 2026-10-17). Kept for provenance.

1. **FAB postponed.** Run FAB only once, after the core conclusion is established.
2. **Difficulty layering.** Saturated questions (init ≳ 70%, act ≈ fin) = "easy": keep archived, do
   not rerun, only assert `C ≥ A3`. Differentiated questions (init ∈ [35%, 70%] **and** act > fin
   with a gap) = "hard": the core target, the only layer worth re-running / expanding.
3. **Question-selection principles.** (a) *Reproducible* — a deterministic difficulty-screening rule
   + question-ID list committed to `configs/` + `REPRODUCIBILITY.md` (not random sampling; random
   seeds introduce uncertainty). (b) *Differentiated difficulty* — layer by init score so the hard
   layer alone has act − fin gap. (c) *No token explosion* — fab/finance run once; hard layer uses
   closed-book, light-token sets (GPQA / AIME / MMLU-Pro), target **≥ 100 hard questions** for
   statistical power.
4. **Keep `emit_rationale`, fix collection.** The transition is the Stage-B breakthrough; the fix is
   to **decouple answer-commit from Reason-rationale** (answer follows the same commit rules as
   rationale-free rounds — mmlu_pro letter-only, aime boxed — with the rationale on a separate tail
   "Reason:" line; `_split_rationale` splits only the tail), not to remove rationale emission.

---

## 7. Next steps (2026-10-13, updated)

> **Items 1-11 are DEPRECATED** (2026-10-13 hard-layer plan, superseded by items
> 12-18 and §12). **Items 12-18 remain CURRENT** -- the live decision set
> (settle = Stage A, non-settle 112-task slice, Stage-B output/scoring, glm/None fix).

1. **Per-question difficulty screening** (offline, zero token cost): compute per-question round-0
   init from existing C/A3 data; keep only `init ∈ [35%, 70%]` AND `act > fin` gap → the hard layer
   (§6.2). Commit threshold + question-ID list to `configs/` + `REPRODUCIBILITY.md`.
2. **Re-run C with rationale on the hard layer only**, per model: deepseek `--rationale-mode
   reason_line`, qwen `reason_line`, glm `twostage`. A3 does not need rationale (no trajectory).
3. **Re-run the three-way comparison (§2.3, §2.7) on hard + rationale-clean data**: `Δ_act`,
   `mode(C) vs vote(A3)`, and net final; feed the activated-but-unlocked slice to the Stage-B
   transition-locking operator design (§2.1).
4. **Deferred (saturated controls, no longer blocking):** the 2026-10-12 "rerun glm new-set C 144" and
   "rerun phase-1 mmlu_pro" are archived saturated sets (§6.2); bfcl stays offline re-score only. They
   re-enter only if the hard-layer discriminative question requires them.
5. **Phase 3 — C at `temperature = 0.7` ablation.** Re-run C at `temp=0.7` (matching A3's temperature, so feedback is the only arm variable) to test whether it clears the temp=0 no-commit basin and to observe C's round-level dynamics under sampling. This is an ablation, not the Phase-2 protocol.
6. **Phase 3 — Stage-B no-commit handling (keep round-0 sampling fixed).** Do not change first-round sampling. Treat no-commit as a special case of Stage-B's non-mode scenario: after committing the mode on mode-clean tasks, take the remaining non-mode tasks, run transition analysis on them (which should surface the "no answer" case), then re-sample so the task yields at least one committed answer. Acceptance hypothesis: the re-sample strategy must beat the mode-on-non-mode baseline score on those non-mode tasks.
7. **Transition evaluation (Stage B) must beat the mode baseline to be meaningful.** The mode (trajectory majority) is a zero-cost selector; Stage-B transition evaluation is only worth its cost if it beats mode on the non-mode slice. Beating mode is the acceptance criterion for the Stage-B operator, not a secondary check.
8. **Candidate optimal strategy (future): A3-lock → C-continue → mode → Stage-B fallback.** A3 (temp=0.7) first locks round-0 into a committed answer (escaping the temp=0 no-commit basin), then C runs the weak-critic feedback loop from that round-0 start, the trajectory mode is taken, and only the non-mode remainder (incl. no-commit) enters Stage-B transition evaluation. Recorded as the likely-optimal A3⊕C composition to validate in Phase 3.
9. **Activation undercount is a `reason_line` extraction artifact, not a real activation gap.** Re-extracting each round's answer from `final_answer` (bypassing the polluted `committed_answer`) recovers activation on GPQA 051–198 from 125 → 131 (+6); phase-1 (−1) and new-set (+1) are already clean. The residual "never" set on GPQA is dominated by no-commit: several never-flagged tasks carry the gold letter in their own trajectory (gpqa_077/094/116/128/146 …). Confirm-and-repair before reading any activation number off reason_line data.
10. **"Settled" ≠ "final": settle = 3 identical consecutive answers (the early-stop trigger); `final` is the last round even when nothing converged.** Full-set settle split (deepseek, 442 voteable tasks — math/math500/mmlu_pro 150 + aime/gpqa/bbh 144 + gpqa051-198 148):
    - settled ≈ 92% (409/442) with settled-accuracy ≈ 91.8% (376/409);
    - non-settled ≈ 8% (33/442) — of which ≈ 20 truly activated (the Stage-B target) and ≈ 13 never-ish (mostly gpqa reason_line no-commit).
11. **Two task types — the Phase-3 selector decision.**
    - (a) Voteable (MCQ / numeric, a canonical answer key exists → can vote & compare A3): **A3 (temp=0.7) locks round-0 → C weak-critic loop → if non-settled, enter Stage-B transition evaluation.**
    - (b) Non-voteable (finance / bfcl: free-form or JSON, no vote; C has no settle anyway): **C → Stage-B directly.**
    - glm finance no-commit is a rationale-protocol artifact (twostage vs reason_line mismatch), expected fixable by the Phase-3 unified-protocol re-run — not a capability deficit. bfcl's negative C gain is suspect (§4 #1 scorer drift + ~90% saturation) and is deferred until Stage-B is built to see whether the same operator rescues it.
    - **Answer-form coverage for C-value validation (2026-10-18).** C 的价值用跨答案形式的实验佐证：
      选择（letter MCQ：gpqa / mmlu_pro / bbh-letter）、数值（math500 / bbh-num / aime-integer）、
      推理（aime 多步数学 / bbh 逻辑链）、文本（自由文本解答）。前三种本期 Stage-B 已覆盖；
      文本 = FAB 定性。FAB 因 token 消耗大，**延后到第三阶段补**（与 §6 #1、§8 一致），
      本期 Stage B 不跑 finance。bfcl 为 function-calling（结构化 JSON/AST 调用），非文本答案形式。

> --- **Items 12-18 below are CURRENT (2026-10-16 onwards).** ---

12. **Stage A = settle (decision locked, 2026-10-16).** The Stage-A selector is the early-stop settled
    answer (3 identical consecutive committed answers), NOT the trajectory mode and NOT the last round.
    Settled beats `final` on all three models (key = `_early_stop_key`, pipeline-consistent; this
    supersedes item 10's approximate deepseek-only split):

    | model | n voteable | settle rate | settle acc | final acc | settle-final |
    |---|---|---|---|---|---|
    | deepseek | 442 | 88.2% (390) | 96.9% | 87.8% | +9.1 pp |
    | glm | 294 | 79.9% (235) | 89.4% | 76.2% | +13.2 pp |
    | qwen | 274 | 92.7% (254) | 96.1% | 92.7% | +3.4 pp |

    Settle locks 80-93% of tasks at 89-97% accuracy for zero extra cost, pushing Stage B onto a small
    hard slice. Cross-model caveat: deepseek carries an extra gpqa051-198 block (148) that glm/qwen lack,
    glm's new-set is no-commit contaminated, and qwen's mmlu_pro rerun is 30/50 -- the direction
    (settle > final) is robust but per-slice numbers are not strictly comparable across models.

13. **Stage-B target slice = the non-settled remainder (112 unique tasks).** Per model: deepseek 52,
    glm 59, qwen 20 (union = 112). Composition by activation status: **79 activated-only** (correct answer
    appeared in every non-settle model -- the direct lockable target), **29 never-only** (correct never
    appeared -- needs Stage-B re-sampling), **4 mixed**. The 29 never-only are dominated by deepseek
    gpqa051-198 `reason_line` no-commit (23 of 29 gpqa; 19 are >gpqa_050, the extraction-artifact
    fake-never from item 9), so the true lockable-only headroom is larger than the never count suggests.
    Stage-B acceptance baselines on this slice (must beat the zero-cost mode): deepseek 36.5% / glm 78.0%
    / qwen 55.0%; activated ceiling (lock everything that ever appeared correct) 50% / 90% / 70%.

---



14. **settle 优化属于 Stage A，不是 Stage B (2026-10-16).** settle-locked-wrong (模型自信收敛但答案错误)
    在调用时没有任何可观测信号能触发 Stage B —— 没有 gold 时无法判断该题应否进入 Stage B。这是 settle 这一个
    选择器自身的极限, 属于 Stage-A 的策略优化空间 (更保守的 settle / 收紧 streak 阈值或置信门槛), 不是 Stage-B
    transition evaluation 的职责。因此 Stage-B 目标切片**严格定义为非 settle 的余集** (item 13 的 112 题),
    settle-wrong 不退入 Stage B。之前 'activated ∩ Stage-A 错题' 的新口径作废。

15. **Stage B 的双输出与两套正交评分 (2026-10-16).** Stage-B evaluator 的合法结论只有两类:
    - `ANSWER: <X>` —— 从 transition 修剪中锁定一个候选答案;
    - `UNSURE` (abstain) —— 判定模型无法可靠锁定, 承认 '不会'.
    相对 gold 的评分是**两个互不混算的正交维度** (仅离线, 用于验证 evaluator 是否带来增量价值):

    **维度 1 — 正常判分 (accuracy).** 与普通打分器一致, 只问对错: `ANSWER == gold` → correct;
    答错 或 abstain (未作答) 都记为 not-correct。

    **维度 2 — metacognition (额外评估).** 独立于 accuracy, 评估 evaluator 能否从 activation 状态
    识别出「模型 (在本题轨迹上) 没有正确答案」的元认知能力, 判据是 answer/abstain 行为是否匹配激活真值:
    - **activated** (gold 出现过, 存在可锁的正确答案) → 期望输出 ANSWER (而非 UNSURE);
    - **never** (gold 从未出现, 轨迹里没有正确答案) → 期望诚实输出 UNSURE (承认不会, 避免幻觉)。

    两个维度单独报告: accuracy 反映锁答案的对错; metacognition 反映「是否识别出模型没答案」的能力,
    后者正是纯 sampling (A3) 完全不具备、而 Stage B 独有的增量价值所在。

    Evaluator 架构 (两层, RSI 递归):
    1. **Evaluator 重构 prompt** (程序侧): 把 transition 视图 (candidates + commit 时间线 + rationale)
       重构成一道 '元选择题', 不输入原题、不输入 gold;
    2. **调用目标模型回答 (RSI, 自递归)**: 目标模型 sequential 读每个 rationale, 对每个相邻 pair
       依据 rationale 判「是否同一 state」, 构建修剪状态链, 再对链上每个真实 transition 判合理性;
    3. **Evaluator 出 verdict**: 依据模型输出的修剪状态链/路径 (MC = state chain/path, 非 Monte Carlo
       采样) 汇总出 `ANSWER:` 或 `UNSURE`.

---

16. **glm rationale fragment bug (twostage second-call budget, 2026-10-16).** 已记录, 待 Stage-B
    设计定型后修复 —— 先按用户决策用 deepseek + qwen 的完整 rationale 推进 Stage B, 回头再修 glm,
    修复的 token 需求以 Stage-B 对 rationale 的实际消费为准。

    - **现象**: glm C-arm (`twostage`) 的 `rationale` 字段 503 条中仅 217 (43%) 是完整句子, 其余是
      `'I'` / `'Wait'` 单字符 fragment。
    - **根因**: twostage 的第二 call (独立收集 transition self-report) 用
      `TWOSTAGE_RATIONALE_MAX_TOKENS = 512` 的紧凑预算强制短句; glm 是 reasoning 模型, hidden CoT 吃掉
      了这 512 token, 可见 rationale 只剩首字符。`agent.py` L950 注释早已记录该行为
      ('folds the reason into a one-character fragment ("I", "Wait")')。
    - **对照**: deepseek (`reason_line`, 10-15 重跑) 260/260、qwen (`reason_line`, 10-16) 264/264 的
      rationale 全部完整、零 fragment —— 非全局问题, 是 glm twostage 特有。
    - **修复方向**: 提高 twostage 第二 call 的可见预算 (对齐 REASONING_BENCH_MAX_TOKENS 或加独立开关),
      让 CoT 之后仍有余量输出完整句。

17. **deepseek / qwen C-arm 的 `None` 态是运行时伪影，不是「模型主动弃权」(2026-10-16).** 核验 Stage-B
    状态空间时发现：完整状态空间里的 `None` 态在 deepseek/qwen 上均无 rationale，与「None→None 每个
    rationale 不同」的前提冲突。两类根因：

    - **deepseek token-cap 截断 (bug，非预算问题)**: 71 轮 (26/148 题) `completion_tokens ==
      reasoning_tokens == 8192`（`REASONING_BENCH_MAX_TOKENS` 上限），答案在 hidden CoT 中被打断成散文
      fragment，既无 clean letter 也无 `Reason:` rationale。用户定性——「token 上限这种情况也应该要
      输出 rationale，这不是预算的问题」——属收集逻辑 bug，与 glm item 16 同根（reasoning 模型 hidden
      CoT 吃掉可见预算，截断可见 answer+rationale）。修复须保证 CoT 之后仍预留可见 token 输出答案与 rationale。
    - **qwen API failure**: 15 轮 (5/146 题) `api_failure=True, completion_tokens=0`，`committed_answer =
      'LLM error: Connection error.'`。用户决定：**重跑这些任务**。
    - **影响**: `None` 态会污染 metacognition 评分（never→期望 UNSURE）；Stage-B 正式跑须在干净数据上，
      即先修 token-cap 收集逻辑 + 重跑 qwen 失败题。

18. **Stage-B 输出架构 / 状态空间泛化 / rationale 预算待决 (2026-10-16).** 与用户方案讨论确认：

    - **输出架构 (模型判状态链 + evaluator 出 verdict)**: ① 目标模型 sequential 读每个 round 的 rationale；
      ② 对每个相邻 pair (k,k+1) 依据 rationale 判「是否同一 state」（非选择题里「逻辑没变、仅表述微调」
      即合并，后一个为准）；③ 据此构建修剪后的**状态链/路径 (MC = state chain/path)**；④ 同步/随后对链上
      每个保留下来的真实 transition 判合理性；⑤ evaluator 依据这条修剪状态链做**最终 verdict**
      （`ANSWER: <label>` / `UNSURE`）。verdict 是 evaluator 的最终输出。注：**MC = 状态链/路径，不是
      Monte Carlo 多次采样**。→ 修正 item 15：无 MC 采样层，模型输出 per-transition 判断 + 修剪状态链。

    - **无采样层 (澄清)**: evaluator **没有**「多次采样/多数表决」环节，verdict 单次、依修剪状态链直接得出。
      多数采样只存在于：① A3（纯 sampling baseline）；② 未来混合策略（先 A3+C）；③ C 的 no-commit 情形
      （可能用采样激活到一个答案，属后续设计，非 evaluator 机制）。

    - **状态空间泛化**: 状态按 1,2,...,n 索引（对应 round），状态值 ∈ {选项字母 A-D、文字答案、一段论述、
      None}，不写死 A/B/C/D。transition 记录对任意答案 token 通用。

    - **同一 state 判定 (通用)**: 模型判「是否同一 state」的依据是 **rationale 的逻辑是否改变**，而非
      字符串/字母相等。逻辑没变 → 同一 state（合并，以后一个为准）；逻辑变了 → 真 transition。
      选择题里两者等价：正常轨迹「逻辑没变 ⟺ 字母相同」；若「字母变了但 rationale 逻辑没变」（或反之），
      说明轨迹逻辑本身有问题——这是**不一致信号**，evaluator 应捕获上报，而不是简单按字母切开。
      非选择题里字符串不等不代表逻辑变，只能靠 rationale 判定（对应原「合并规则」）。

    - **rationale 预算 / twostage (待决)**: deepseek/qwen 的 reason_line 是否全部迁到 twostage 解耦，
      留待后期决定；当前**先补齐缺失 rationale + 重跑受影响任务**（deepseek 截断 26 题、qwen 失败 5 题）。

19. **新协议重跑：旧 non-settle 归零 + Stage-A settle 优化方案（暂不处理，2026-10-19）.**

    实测 deepseek 旧 non-settle 全集（item 13 的 52 题）用新协议（三通道解耦 + `committed_answer`
    独立通道 + `transition` rationale）重跑，已跑 19 题全部 settle（`settled_ans` 全非空），non-settle
    余集归零。

    - **根因（旧 non-settle 为何归零）**: 旧判定的 non-settle 主体是「假 non-settle」——旧协议 commit
      提取失败（`candidates=0`、纯 no-commit），无 commit 即无 3 连、`settled_ans` 只能判 None；新协议
      修好 commit 提取后这些题重新 settle（例 gpqa_121：旧 candidates=0 → 新 1、settle=D）。非模型变乖，
      而是采集协议修复挤掉了假 non-settle 的水分。

    - **Stage-A settle 语义缺陷（暂不处理、后期优化）**: 现 settle 唯一判据是「末尾 3 连」，不校验
      「全程稳定 / 是否锁错」。典型 gpqa_070：r1/r2 commit 正确 D（仅 2 连、未触发 early stop）→ 被
      feedback 干扰 D→C→A 横跳 8 轮 → 末尾 A A A settle=错误 A；「先对后错、锁错」被 settle 判定掩盖为
      「稳定收口」。

    - **候选优化（记录、暂不处理）**: 「链路太长」的多轮横跳题追加采集 rationale，用于 settle 稳定性/
      置信判断；更保守的 settle（收紧 streak 阈值 / 加置信门槛）同属 Stage-A 优化空间（item 14）。




---

## 8. Phase 3 plan（按证据链阶段重组，2026-10-17）

> 把 §7 中散落的 Phase-3 动作（items 5–8）以及 item 16（glm fragment）、item 17（None 态）重组成七阶段框架的阶段 5（机制）/ 6（决策）/ 7（稳健性）三段执行序。原 items 细节保留，此处给出重组后的 ordering 与验收判据。

### 8.1 阶段 5｜机制验证（对应 H2：transition rationale 是真实信号）

先把信号做干净，再验证「关键改动 > 无关改动」：

1. **协议统一（先于一切 Stage-B 对照）**：三模型 rationale 协议从 `reason_line` vs `twostage` 统一为单一协议（item 5）；修 glm twostage fragment（item 16：提高第二 call 可见预算）与 deepseek token-cap 截断（item 17：保证 CoT 之后仍预留可见 token 输出 answer + rationale）；重跑受影响任务（deepseek 26 题、qwen 失败 5 题）。
2. **None 态补采闭环**：确认 `None→X / X→None / None→None` 三迁移均采到干净三段式 rationale（transition 模式已加入 None 分支）。
3. **干预对照（H2 判据）**：只改交给 evaluator 的 rationale / signal（Original / 去掉 rationale / 替换为无关 rationale），看 verdict 是否按预期变化；关键改动分差必须 > 无关改动分差，且「字母变而逻辑未变」的不一致信号被捕获上报（item 18）。

### 8.2 阶段 6｜决策验证（对应 H3：锁定收益在同等条件下优于强基线）

1. **固定分母公平对比**：在非 settle 余集（item 13 的 112 题，headroom 桶已排除 never）上，比 Stage-B 锁定 vs settle / mode / A3 强基线的 accuracy。
2. **两套正交评分同时报告**（item 15）：accuracy（ANSWER 对错）+ metacognition（never 是否诚实 abstain）；后者是 A3 完全不具备、Stage B 独有的增量——这是 H3 决策价值的核心。
3. **以「beat mode」为验收判据**（item 7）：Stage B 只在非 mode 切片上运行，必须 beat 零成本 mode 才值得额外成本；同时报告样本量、不确定区间、token 成本。

### 8.3 阶段 7｜稳健性（边界）

1. **跨条件复现**：12–15 模型、跨题型（启发自 §9 四方向题库），验证 H1–H3 是否仍成立。
2. **成本-收益对照**：settle（零成本）vs Stage B（额外推理成本）的开销-收益曲线，确认「收益覆盖成本」。
3. **失败案例清单**：主动搜集「settle-locked-wrong」「no-commit」「不一致 transition」最差分组的典型样本；明确结论对哪些模型 / 题型失效。
4. **协议豁免**：glm 若无完整 rationale，先按 deepseek / qwen 推进，glm 修复的 token 需求以 Stage-B 对 rationale 的实际消费为准（item 16）。

### 8.4 待定（候选，非本期提交）：confidence-only 对照臂

「仅自报置信度」这条简单解释（框架阶段 5.3 排他表一行）不进入 Claim 1–3（已由 A3 采样基线覆盖），只作为**元认知维度**（Stage B 的 answer / abstain 评分）的对照——需等 metacognition 评分定型后再设计，故留待 Phase 3 后半段另行拍板。

---

## 9. Benchmark directions (reference for future scaled validation)

Four benchmark families, recorded as the long-term reference pool for scaling validation once the
GPQA hard layer is locked down. Each is chosen for **verifiability** (closed-form answer / executable)
plus a **generation–verification gap** (model can generate but not reliably hold), matching the
self-improvement literature's convention.

| # | Direction | Representative benchmarks | Signal shape | Representative works |
|---|---|---|---|---|
| 1 | Math reasoning (numeric closed-form) | GSM8K, MATH-500, AIME-2024/2025, Minerva, Olympiad-Bench, MIT Integration Bee | free-generation, verifiable → richest transition signal | R-Zero, LADDER, ReST, Mind the Gap |
| 2 | Code (executable verification) | HumanEval, MBPP, LiveCodeBench | executable, binary pass/fail | Z1 (test-time scaling), Reflexion |
| 3 | Graduate-level MCQA | **GPQA Diamond (core)**, MMLU-Pro | 4-option letter commit; 25% guessing floor | Z1, DeepSeek-R1, most reasoning-model reports |
| 4 | Multi-step / general & verifiable game tasks | BBH, Winogrande, CommonsenseQA, Sudoku, Countdown | structured; Sudoku/Countdown have gen-verification gap | PASR, Reflect-Retry-Reward, Mind the Gap |

Current status: the *saturated* repeat sets (aime/bbh/mmlu_pro) stay archived for the "C ≥ A3" control
conclusion only (§6.2); **GPQA Diamond is the sole discriminative + headroom carrier** and is the focus
of the hard-layer expansion (§7.1). Directions 1/2/4 are recorded for later, larger-scale validation.

---

## 10. Open questions

- Is current benchmark difficulty sufficient? GPQA is the only discriminative + headroom set; harder
  questions are needed to build a ≥ 100-question hard layer.
- How to source reproducible harder questions deterministically (no random sampling)?
- Quantifying the weak critic's gain requires all three effect sizes — Δ_act > 0, Δ_lock > 0, and
  net Δ accuracy — under the A2 ≈ A3 placebo control.
- `no-commit` (feedback-induced commitment withdrawal) is a behavioral side-effect observation; note
  but do not treat as a core object until its effect on final answers is verified separately.

---

## 11. Provenance

C-arm scoring uses the fixed `commit, don't scan` contract with carry-forward commitment and
`_early_stop_key` robust extraction per family. A3 uses `temperature = 0.7`, `N = 10`, majority
vote. Cross-version `is_correct` fields are not trustable (see §4). Anomalies and corrections are
logged in `project_memory.md` (Lessons Learned) and this document.


---

## 12. Stage-B signal decoupling: three-channel collection + CoT cap (2026-10-19)

**Decision (supersedes the `reason_line` in-content split).** For every Stage-B (non-settle)
trajectory, collect and store THREE decoupled channels instead of one merged content stream:

| Channel | Source | Code field |
|---|---|---|
| hidden CoT | `reasoning_content` (native endpoint field, streamed) | `reasoning_content` |
| answer | committed visible answer (answer-only first call) | `committed_answer` |
| feedback rationale | self-report via a SEPARATE side-channel call | `rationale` |

The three are natively decoupled. They must NOT be merged back into a single trailing "Reason:" line —
the `reason_line`/`json` in-content split was the fragile source of the glm no-commit collapse
(§4 item 3); `twostage`/`transition` already collect the rationale as a separate call and are the
target of record.

**Thinking is ON, always (correction).** Earlier `total_reasoning = 0` was NOT "thinking off".
The pre-10-14 non-streaming `_call_llm_text` read only `_extract_content(message)` and never captured
`reasoning_content`; `AgentResult` had no `reasoning_content`/`finish_reason` then. Thinking stayed on
at model default the whole time (no model has `enable_thinking: False`; `enable_thinking` defaults to
`None` and is never propagated to `extra_body`). The 10-14 streaming switch merely started RECORDING
the hidden CoT the endpoint was already producing.

**CoT cap is two orthogonal mechanisms (both required):**
1. (generation) thinking budget + content window: `thinking_budget < max_tokens`, reserve
   `REASONING_CONTENT_MARGIN` visible tokens (industry: Anthropic `budget_tokens < max_tokens`).
2. (read-side) tail sampling: `_cot_tail` recovers the answer-relevant end of CoT.

A CoT cap is net-positive, not just cost control: the Detection–Extraction Gap (2604.06613) shows
models commit the answer early then over-think, so truncating 70–78% of serial generation raises
accuracy; Fractured CoT (2505.12992) reaches the same conclusion.

**The self-report rationale is a WEAK signal.** Visible-channel rationales can be post-hoc
rationalizations (Turpin et al. 2023; Arcuschin et al. "Implicit Post-Hoc Rationalization"; Young
2603.26410: 55.4% thinking–answer divergence). hidden CoT is the primary signal; the self-report is a
readable annotation only.

**Stage-B fusion order:** CoT = primary (did reasoning actually change), answer = commit fact,
self-report = annotation.

**NEW signal (2026-10-19):** the Stage-B model additionally checks hidden-CoT <-> self-report
CONSISTENCY; mismatch is itself a feature for the stage evaluator — evidence of post-hoc
rationalization (the model "says" a reason that its own CoT does not support).

**Open — glm/qwen CoT control.** `thinking_budget=8192` currently exists only on deepseek. glm
re-derives the full problem in hidden CoT until ANY cap (config L113-119); budget alone does not fix
glm — the known mitigation is question-stem truncation (`_RATIONALE_QUESTION_MAX_CHARS=300`, INT-25).
The glm/qwen CoT-cap strategy (budget vs stem-truncation vs early-commit) needs a small experiment
before generalization. deepseek non-settle is the first target, then glm/qwen.


**Consistency = probability (refinement, 2026-10-19).** The Stage-B consistency check is an
LLM-judged probability c in [0,1] (not binary), matching the MC self-review's probabilistic framing.
c weights each transition in the lock decision: c=1 reproduces today's mechanism (the self-report
rationale taken at face value); c<1 down-weights the transition (evidence of post-hoc rationalization)
and biases toward CUT / abstention. The judge compares each per-transition self-report rationale
against the target round's hidden-CoT tail.

**Consistency mechanism -- final design (2026-10-19).** The c signal is a Likert 0-10
judged by the target model itself (RSI self-adjudication), mapped to c = score / 10 in [0,1].

**Why not the stationary distribution.** `pi = pi P` exists and is unique only for an
irreducible, aperiodic chain. The state chain is a one-way DAG (time advances, no return
edges), so it is NOT irreducible and has NO stationary distribution. The correct MC
quantity is the ABSORPTION probability (`(I-Q)^-1 R` for a general absorbing chain), which
for this LINEAR non-branching chain collapses to a prefix product: the survival
probability of state r_k is `S(k) = prod_{i<=k} c_i`, where c_i is the consistency of the
i-th transition edge. A Monte Carlo edge-survival simulation (each edge survives w.p. c_i)
converges to the same analytic value, so it doubles only as a sanity check.

**Lock rule (three clauses).**
1. survival: `S(k) = prod_{i<=k} c_i`; a fragment (a maximal run of surviving edges) has
   probability `prod_{k in F} c_k`.
2. main fragment = the fragment with the MOST surviving edges (ties broken by higher
   fragment probability); the locked answer candidate is the highest-S(k) state inside
   that fragment.
3. UNSURE (abstain) when no fragment survives (all edges cut) OR the candidate state /
   fragment probability is below the answer threshold.

c=1 on every edge reproduces the current mechanism exactly (S(k)=1, one full fragment, no
down-weighting), so this is a strict generalization, not a new mechanism.

**Hyperparameters (heuristic initial values; scanned on the offline validation set after
the first smoke).** t_keep (edge-cut threshold) = 0.5; t_answer (abstain threshold) = 0.5.
Both tunable from measured results.

---

## 13. Related work & positioning: Error-Guided Test-Time Elimination (EGTE, 2026-10-21)

### 13.1 Framing (this project's contribution)

The RSI loop optimizes a **lower bound**, not the objective. It does not train or prompt the
model to *produce* the correct answer (the "positive" direction); it distills, from a
gold-annotated **error bank**, a finite set of **generalizable wrong execution behaviors** and
uses them to **EXCLUDE** at evaluation time. The asymmetry is the point:

- **Error vs correctness is asymmetric information.** The space of *wrong* moves reachable for
  a problem class is small, sparse, and checkable; the space of correct derivations is dense and
  open-ended. Modeling "what goes wrong" (a few finite exclusion rules) costs far less than
  modeling "what is right" (a PRM that scores the correct direction), and is more robust because
  each rule is a falsifiable *check* rather than a learned *intuition*.
- **The memory is an answer-free mechanism + check_procedure**, distilled at the class level
  (never naming a specific molecule/number/option), so it transfers across questions and across
  benchmark families, and does **not** go obsolete — new errors from new questions/models keep
  feeding the bank, sharpening the same mechanisms instead of accumulating instance memory.

This is **Error-Guided Test-Time Elimination (EGTE)** (错题集泛化): analogous to a student who
derives, from gold-marked mistakes, a short list of *"for this class of problem, here are the
moves to rule out"* — the wrong answer is excluded, not the right one selected.

### 13.2 Three-role closed loop — distill / check / review (mechanism / check_procedure / trigger / evidence)

| Role | When | Gold? | Produces | Consumes |
|---|---|---|---|---|
| **distill** (build) | offline, over the error bank | yes | `mechanism` + `check_procedure` (class-level, answer-free) | gold answer + wrong answer + prompt |
| **check** (execute) | online, per task | no | cheap `trigger` signature (question-type + committed answer) | `trigger` |
| **review** (post-transition) | after an answer **transition** only | no | CUT / UNSURE / ANSWER lock (rubric judge, evidence-anchored) | `mechanism` + `check_procedure` + `evidence` over the transition's hidden CoT |

Errors green-lit at review re-enter the bank, closing the loop. The evaluator only wakes on
transition (the cheap-path decision) — it never reads the target round's CoT at rest.

### 13.3 Related work (closest → farthest to the error-exclusion idea)

| Work | arXiv | Core mechanism | Overlap with ours | Gap vs ours |
|---|---|---|---|---|
| **PRISM** | [2606.09078](https://arxiv.org/html/2606.09078) | PRMs are biased by step-label imbalance; FP steers Best-of-N/decoding toward flawed reasoning, FN only slows it → train to **reduce false positives** | the asymmetric FP/FN framing (eliminate false credit) | operates at *reward-accuracy* level; we move the asymmetry into *what to learn* (named exclusion rules), not just *how to train the RM* |
| **Cliff** | [2609.02817](https://arxiv.org/html/2609.02817) | locate the **first mistake**, then assign negative advantage to the whole suffix ("cliff") | negative-after-first-error = penalize wrong direction | numeric reward shaping; no *named, reusable* exclusion mechanism, no answer-free memory |
| **Mistake Notebook Learning** | [2512.11485](https://arxiv.org/html/2512.11485) | training-free persistent KB of **abstracted error patterns**, batch abstraction + empirical validation | closest to our "robust non-obsolete 错题集": abstracted (not instance) error memory | in-context / batch-level guidance merged via RAG; ours is an *evaluator-side* check_procedure with evidence anchoring, closed over a transition-triggered verifier |
| **LANPO** | [2510.16552](https://arxiv.org/pdf/2510.16552) | reward-agnostic reflection (intra-sample) + **relevant abstraction** (distill generalizable lessons, inter-sample) | the generalizable-lesson abstraction matches our `mechanism` field | abstraction feeds *policy optimization* (exploration guiding); we feed it to a *frozen-weight evaluator* for exclusion at review time |
| **Agent-R** | [2501.11425](https://arxiv.org/pdf/2501.11425v3.pdf) | MCTS recovers correct trajectories from erroneous ones; model-guided first-error-step critique | reverse-engineers *where* the model errs, from gold | splices full *correct* continuations (trains recovery); we distill only the *exclusion rule*, no answer/CoT replay |
| **TAPO** | [2606.18844](https://arxiv.org/html/2606.18844) | micro-reflective trajectories: keep erroneous prefix, insert diagnosis + corrected reasoning | error-driven distillation anchored in the learner's own prefix | constructs a *corrective* trajectory for reward; we construct a *check procedure* for lock/abstain |
| **LEMMA** | [2503.17439](https://arxiv.org/html/2503.17439v1) | error-type grounded mistake augmentation → (wrong + reflection + correct) SFT | systematic error-type analysis of model mistakes | fixed taxonomy; ours is distilled *class-level behavior*, taxonomy-free and cross-benchmark |
| **ThinkPRM / SCoRe / R3 / VSI / Double-Checker** | [2504.16828](https://arxiv.org/html/2504.16828) · [2409.12917](https://export.arxiv.org/pdf/2409.12917) · [2505.24726](https://arxiv.org/html/2505.24726v1) · [2603.21558](https://arxiv.org/html/2603.21558) · [2506.21285](https://arxiv.org/html/2506.21285v2) | generative/scalar PRMs, self-correction RL, verify-reasoning-not-answer | all accept "process supervision beats outcome" | all train a *positive* (correctness) signal; the error-as-exclusion regime is the missing framing |

### 13.4 Position: what is (to our knowledge) not yet done

Every ingredient above exists in isolation, but the **synthesis** we are building — *EGTE, i.e.
lower-bound optimization via answer-free mechanism+check_procedure distillation, closed over a
transition-triggered, evidence-anchored self-review verifier (weak critic → rubric judge →
activation+locking), with the solver and the three evaluator roles as SEPARATE calls* — is not,
to our knowledge, published as a single system. Three claims carry the novelty:

1. **Asymmetry as an objective**, not just an RM-metric detail (PRISM stops at FP reduction).
2. **Answer-free, cross-benchmark exclusion rules** as the durable memory (vs instance-anchored
   reflection in SCoRe/R3/Agent-R, and vs in-context notes in MNL/LANPO).
3. **The three-role distill / check / review closure** (`mechanism` / `check_procedure` /
   `trigger` / `evidence`) with the evaluator consuming only distilled checks at transition time
   — the explicit "robust, non-obsolete check memory" the RSI loop accumulates.

**Open question to verify against the literature before claiming:** whether any 2025-2026 work
explicitly phrases process supervision as "minimize the *error* bound via elimination" rather
than "maximize correct-step probability". This is the market-separator to cite (or to occupy).

---

## 14. Re-anchored experiment path (EGTE, 2026-10-21)

> Supersedes §7 next-steps. One decisive change after the A2 forensics (§4/§5): **C (and A3) must
> be re-run with the content-margin truncation fix before any C-vs-A2/A3 comparison is valid.**
> The ladder is then **deepseek-first → glm/qwen replication → more task types**.

### 14.1 Fix C first — recover the true round-0 accuracy

- **Finding** (A2 forensics): A2 gpqa init (84.46%, post-fix) vs C (76.35%, pre-fix) is confounded.
  C's round-0 `committed_answer` was a length-truncated raw CoT (`completion_tokens=8192`,
  `finish_reason=length`) scored wrong, while A2 emitted a clean letter (`stop`). 84.46% is the real
  round-0 precision; C and every pre-2026-10-18 baseline were suppressed by the truncation bug.
- **Action**: re-run C (and A3, for the T>0 comparison) on the same 148-gpqa slice
  (gpqa_051–198) with the `REASONING_CONTENT_MARGIN` fix; then re-derive the hard layer
  `init ∈ [35%, 70%]` from TRUE (post-fix) init — the old difficulty screening was built on
  truncated init and is itself contaminated.

### 14.2 deepseek-first EGTE ladder — close the loop on ONE model

Get the full distill → check → review mechanism working end-to-end on deepseek before any
cross-model / cross-type expansion:

1. **distill** — gpqa error bank → `mechanism` + `check_procedure` (v3.0 three-role prompt; smoke
   3 first, then the full 49 gpqa entries).
2. **check** — wire `trigger` into the cheap path; wake the evaluator only when the answer starts
   to transition (the A-plan: never read the round's CoT at rest).
3. **review** — rubric judge (disconnection/contradiction/error) consumes `check_procedure` +
   `evidence` over the transition's hidden CoT → CUT / UNSURE.
4. **Gate**: EGTE must show a train-free test-time gain over the strong selectors (mode / A3-vote)
   on the deepseek hard slice *before* replication is attempted.

### 14.3 Replicate on glm / qwen

- After deepseek EGTE is green end-to-end, port the same distill → check → review to glm and qwen
  (fix glm `twostage` rationale fragment first, item 16; unify the rationale protocol, item 5).
- Explicitly test **cross-model transfer** of the distilled mechanisms: answer-free mechanisms should
  transfer; the check is whether a glm/qwen-specific error bank is even needed, or whether deepseek's
  mechanisms already carry.

### 14.4 Breadth — more task types

- Extend the error bank beyond gpqa to mmlu_pro / bbh (MCQ) and aime (numeric) to test the
  "cross-benchmark exclusion rules" claim (§13.4 novelty #2). This is where answer-free mechanisms
  are pushed past a single family.

### 14.5 Ordering rationale

- deepseek-first: single-model closure de-risks the mechanism before the cross-model × cross-type
  matrix explodes cost. Same discipline as §9.1: **run in segments, callback on failure.**
