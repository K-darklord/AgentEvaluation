# Paper PPT — Slide Content & Layout (EGTE)

**Source of truth**: `paper/paper_outline.md` (seven-stage evidence chain) + `docs/PAPER_DRAFT.md`
(§2 roles/arms, §3 motivation & setup, §4 results, §5 hypotheses). Aligned as of **2026-10-31**.

> **2026-10-27 restructure** — the deck is rebuilt on the *research-progression* scaffold drawn from the six
> reference slides: one `问题定义 → 贡献1·中间对象 → 贡献2·机制验证 → 贡献3·决策层 → 主表` ladder, each stage
> answering "what the study must answer" and leaving "a re-checkable deliverable".
>
> **2026-10-31 trim** — single story (EGTE as train-free test-time elimination); HLE-400 is the main
> evidence (bank never sees HLE); hypotheses remapped to the framework's H1 identifiable / H2
> mechanism-sensitive / H3 decision value; A2 is the irrelevant-change control for H2. Dropped: 26 pp
> FAB opener, RSI, weak critic C, astra, flip19, knobs, rubric_v5, support tables A/B, venue.

---

## Visual system (from the reference slides)

| Element | Treatment |
|---|---|
| Breadcrumb (top-left) | small muted text `EGTE · {module} · {contribution} · {layer}` |
| Page number (top-right) | small, right-aligned |
| Main title | large bold, deep navy `#1a3a5c` |
| Subtitle | gray `#888` |
| Table header | deep navy `#1a3a5c` (framework/main tables) or teal `#008B8B` (operational tables), white text |
| Table body | zebra striping `#f5f7f9` / `#ffffff`, no vertical rules (three-line table) |
| Two-column | left = "已有依据 / 被比较项", right = "研究单位需要明确 / 同一比较条件" |
| Bottom conclusion | teal/green `#2EAFAA` emphasis, matches header accent |
| Footer | tiny gray, references / working note |

---

## P1 — Title & the falsifiable main question · [stage 1 — main question]

**Breadcrumb**: `EGTE · Title` · page 1

**Layout** — title band (top), one-sentence falsifiable question (centre, large), falsification strip (bottom bar).

**Title** (deep navy, bold)
**Error-Guided Test-Time Elimination (EGTE)**

**Subtitle** (gray)
*A train-free, three-role test-time loop (distiller → critic → evaluator) that **excludes** wrong candidates using answer-free error mechanisms distilled from the model's own past errors — instead of scoring the correct path.*

**Falsification strip** (bottom bar, deep navy)
- **One-sentence claim** — *Can a model's own past errors, distilled into answer-free mechanisms, drive a gold-free test-time loop that recovers correct answers self-consistency finds but cannot hold — on harder problems the error bank has never seen?*
- **Failure criterion** — *if C3 does not systematically beat A3 on HLE-400 (paired McNemar not significant and Δacc ≤ 0), the EGTE claim fails.*

**Key output** — the single question the rest of the deck must answer, gated by the failure criterion above.

---

## P2 — Research-progression ladder · [stage 1 — framing map]

**Breadcrumb**: `EGTE · 框架 · 研究推进顺序` · page 2

> mirrors reference image **研究框架.png** (three-column "研究推进顺序" table).

**Layout** — one three-column table, deep-navy header, zebra rows; bottom "retreat" note.

**Title** (deep navy, bold)
**The research-progression ladder — five stages, one evidence chain**

**Subtitle** (gray)
*The same EGTE topic, unfolded stage by stage; each stage answers one question and leaves one re-checkable deliverable.*

| Stage | What the study must answer | Deliverable of the stage |
|---|---|---|
| **问题定义** Problem definition | Where does prior work stop, and which failures still lack an *external, gold-free* signal? | main question + literature boundary (a falsification criterion) |
| **贡献1 · 中间对象** Contribution 1 · intermediate object | Which process quantity must be observed separately — how is a *wrong-execution behaviour* distilled answer-free? | answer-free `mechanism` + `check_procedure` + minimal baseline |
| **贡献2 · 机制验证** Contribution 2 · mechanism verification | Is the signal identifiable (H1), and does the key intervention beat an irrelevant change (H2)? | offline judge archetype hit rate + C3 vs A2 with attributed transitions + MCQ / open-form split |
| **贡献3 · 决策层** Contribution 3 · decision layer | Does the signal improve the decision on the same items at no higher cost (H3)? | C3 vs A3 on HLE-400 + eliminator on/off |
| **主表** Main table | Which contrasts jointly support the claim? | HLE-400 main table + mechanism table + ablation table |

**Bottom** (teal)
*Every stage must leave a re-checkable deliverable; where the evidence is insufficient, retreat to the previous stage.*

**Footer** (tiny gray)
P3–P7 below instantiate this ladder in order; P8–P9 test its boundary and fold the chain back to the claim.

---

## P3 — Problem definition: the error bank as a test-time elimination information source · [stage 1 — gap & motivation]

**Breadcrumb**: `EGTE · 问题定义` · page 3

> mirrors reference image **04.jpg** (two-column "已有依据 / 研究单位需要明确").

**Layout** — left-right columns; left · green header "已有依据", right · deep-navy header "研究单位需要明确"; full-width bottom conclusion.

**Title** (deep navy, bold)
**Self-consistency finds the right answer and loses it — what external signal can hold it?**

**Subtitle** (gray)
*Candidate gap: which failures still lack an external gold-free signal, and can the model's own past errors supply it?*

**Left — 已有依据 (existing evidence)**
- Under sampling + majority vote (Wang et al. 2022) the correct answer often **appears** in the candidate pool but is **not held** — test-time scaling activates it and the vote discards it.
- Intrinsic self-correction is unreliable (Huang et al. 2023); self-critic / self-refine models cannot reliably correct themselves without an external signal → external feedback is **necessary**; PRMs / verifiers supply one but need training and positive labels.
- The "learn-from-mistakes" family is already occupied — Mistake Notebook, PRISM, Cliff, LANPO, Agent-R / TAPO / LEMMA — all store instances or train on them.

**Right — 研究单位需要明确 (what the study must fix)**
- Can an **error bank** — the model's own past failures, distilled answer-free — serve as a gold-free, train-free *test-time elimination* information source?
- Does the bank **transfer**: distilled on in-family benchmarks, does it fire correctly on a harder family it has never seen (HLE)?
- Is the elimination **attributable to a real error mechanism**, not noise or a lucky re-sample?

**Bottom** (teal)
*Model "what goes wrong" (a few answer-free exclusion rules) rather than "what is right" — exclusion as the design choice; its transfer to unseen hard problems is the test.*

**Footer** (tiny gray)
[1] Huang et al. 2023; [2] Wang et al. 2022 (self-consistency); full 52-source map — `docs/WORKMAP.md`.

---

## P4 — Contribution 1 · intermediate object: the answer-free error mechanism · [stage 2]

**Breadcrumb**: `EGTE · 贡献1 · 中间对象` · page 4

> mirrors reference image **01.jpg** (three-line operational table: 核验维度 / 具体检查 / 容易遗漏的反例).

**Layout** — teal-header three-line table (no vertical rules), 3 columns; bottom "continue condition" + footer.

**Title** (deep navy, bold)
**The answer-free `mechanism` + `check_procedure` — an operational definition**

**Subtitle** (gray)
*The intermediate object that must be observed separately: class-level, never naming a molecule / number / option.*

| 核验维度 Check | 具体检查 Verify | 容易遗漏的反例 Counter-example |
|---|---|---|
| **定位** class-level | mechanism names only the *wrong operation/verb*, not instance answer text | extracts an instance number, yet claims "answer-free" |
| **充分性** gold isolation | the distiller is the **only** role that reads gold; runtime is gold-free | critic/evaluator covertly carry the answer (leakage) |
| **一致性** cross-family transfer | one archetype fires across questions **and** benchmark families — including HLE, which never entered the bank | fires only on bank items it was distilled from |
| **未知状态** bank growth | the archetype vocabulary is distilled from error data, not a fixed taxonomy | fixed taxonomy rejects new errors → mechanism goes stale |

**Bottom** (teal — continue condition)
*Continue condition: freeze the 7 archetypes with their answer-free `check_procedure`, and confirm they fire on HLE.*

**Footer** (tiny gray)
7 archetypes — `constraint_blind`, `descriptor_conflation`, `memory_substitution`, `procedure_truncation`, `sign_normalization_slip`, `retrieval_abort`, `format_nonconformance` — each an answer-free `trigger` + `definition` + `check_procedure`. Distillation chain (L1/L2/L3) → Appendix A.

---

## P5 — Contribution 2 · mechanism verification: arms + EIR/ECR · [stage 3 — intervention]

**Breadcrumb**: `EGTE · 贡献2 · 机制验证` · page 5

**Layout** — arm-contrast table (deep-navy header) + EIR/ECR condition strip + three hypothesis cards.

**Title** (deep navy, bold)
**The causal contrast — what explains the effect: sampling, scaffolding, or error-bank guidance?**

**Subtitle** (gray)
*All arms share the same solver base model and scorer; solver, critic and evaluator are the same model; arms differ only in feedback/aggregation.*

| Arm | Definition | Role in the design |
|---|---|---|
| **A** | bare re-solve, T=0, single answer, zero intervention | floor — raw latent accuracy |
| **A2** | fixed neutral placebo loop, T=0, single answer | placebo — strips all error-bank guidance; controls scaffolding |
| **A3** | self-consistency (Wang et al. 2022), T=0.7, init = A round-0 + N-1 = 9 i.i.d. samples, majority vote over the 9 | **independent-sampling baseline EGTE must beat** |
| **C3** | strong critic (in-loop) + evaluator `rubric_ce` (offline), elimination + mode | treatment — activation (critic) + lock (evaluator) |
| **A3C3** (optional) | A3-seeded round-0, then the C3 loop | stacked (sampling + EGTE), reported if run |

**A-seeding (shared round-0 anchor).** A's deterministic T=0 answer is round 0 of A2 / A3 / C3 (no
round-0 drift); A3 = A-init + N-1 = 9 i.i.d. T=0.7 samples, majority-voted — A itself does not enter
the vote pool.

**Which contrast answers which hypothesis** (same items, same model, same scorer)
- **H2 key vs irrelevant** — C3 (error-bank-driven direction) vs A2 (same loop, content-free feedback): A2 is the irrelevant-change control.
- **H3 decision value** — C3 vs A3, paired McNemar; cost = total tokens of all role calls per correct, must not exceed A3.
- **Eliminator on/off** (ablation under H3) — inside C3: `off` = critic alone + mode lock; `on` = evaluator elimination + mode.
- **Bank-free critic** (optional strengthening of H2) — critic prompt without the archetype vocabulary.

**Bottom** (teal)
*`final = init + corrected(ECR) − flipped(EIR)` (per-round) — iteration is beneficial only while `ECR / EIR > Acc / (1 − Acc)`; whole-loop `P_act` / `P_flip` are the per-item counterparts used in the main table and the eliminator ablation. Under A-seeding, `P_act_init` = correct at round 0 (from A) vs `P_act_loop` = correct first committed at round ≥ 1 (the critic's activation).*

**Three hypotheses** (framework stage 4; each with support + failure)
- **H1 identifiable** — on C3's wrong rounds, the critic's gold-free archetype hits the archetype an independent gold-visible offline judge assigns, above a permutation baseline (20-item human spot check of the judge). *Fails if* hit rate is at baseline or one archetype fires regardless.
- **H2 mechanism-sensitive** — (i) C3 > A2 on the same items; (ii) C3's wrong→correct transitions are preceded by a suspicion, A2's by none (`critic_direction = None`); (iii) the gain persists on open-form items where the A3 vote collapses. *Fails if* C3 ≈ A2 or the gain is MCQ-only.
- **H3 decision value** — C3 > A3 (paired McNemar) at no higher tokens per correct. *Fails if* not significant or cost exceeds A3.

---

## P6 — Contribution 3 · decision layer: the evaluator's fair comparison · [stage 4 — decision]

**Breadcrumb**: `EGTE · 贡献3 · 决策层` · page 6

> mirrors reference image **02.jpg** (two-column "三种选择器 / 同一比较条件").

**Layout** — left-right columns: left = "三种裁决" (three verdicts), right = "同一比较条件" (fixed comparison terms); bottom main-judgement + shrink-conclusion.

**Title** (deep navy, bold)
**`CUT / KEEP / UNSURE` — a fair elimination-vs-vote comparison**

**Subtitle** (gray)
*The evaluator wakes only on an answer transition; it never reads gold, never runs in-loop.*

**Left — 三种裁决 (three verdicts)**
- **CUT** — a definitively-wrong candidate is reverted to the old answer.
- **KEEP** — a clean transition keeps the new answer.
- **UNSURE** — not eliminated this time; both answers survive (no abstention promised).
- aggregation = **elimination + mode**; an all-UNSURE trace falls back to **mode**.

**Right — 同一比较条件 (same comparison terms)**
- same model, same 400 items, same scorer for every arm.
- eliminator on vs off compared on the same C3 trajectories.
- cost counted over all role calls (solver + critic + evaluator) vs A3's N samples.

**Bottom**
- **主判断 (main judgement)** — *does C3 beat A3 on the same items at no higher cost (H3), and does elimination + mode add over the critic-alone lock without cutting correct candidates (false-CUT rate)?*
- **收缩结论 (shrink condition, teal)** — *if elimination + mode gives no stable gain over the critic-alone lock, the claim shrinks to critic activation and mechanism discovery.*

---

## P7 — Main table design: main table + ablation table · [stage 5 — synthesis]

**Breadcrumb**: `EGTE · 主表设计` · page 7

> mirrors reference image **03.jpg** (three-column "主表与支撑表" structure).

**Layout** — teal-header table, columns = 表 / 行·比较对象 / 列·必须回答; bottom constraint sentence.

**Title** (deep navy, bold)
**EGTE's main table and ablation table**

**Subtitle** (gray)
*The main table answers the decision effect on HLE-400; the mechanism table answers H1/H2; the ablation table says which stage carries the gain. Numbers filled after the frozen re-run.*

| Table | Row — comparison object | Column — must answer |
|---|---|---|
| **主表 · HLE-400** Main · selection quality | A / A2 / A3 / C3 (A3C3 not run) | Acc; settle; tokens per correct (all roles); per-round EIR / ECR; `P_act_init` / `P_act_loop`; McNemar exact (paired vs A3) |
| **机制表 (H1/H2)** Mechanism | C3 wrong rounds (judge-labelled); C3 vs A2; MCQ vs open-form | archetype hit rate vs permutation baseline (H1); paired acc C3 vs A2, attributed-transition rate, gain by answer form (H2) |
| **消融表** Ablation (under H3) | C3 eliminator off / on; (bank-free critic) | Acc delta; `P_flip`; false-CUT rate |
| **来源表** Bank provenance | bank-source benchmarks vs evaluation target | which (model, benchmark) errors built the bank; HLE never in bank |
| **动机表 (stage 3)** Motivation | A / A2 / A3 on the bank-source benchmarks | simple routes near ceiling there; unexplained failures concentrate on HLE (`P_act(A3)` vs A3 acc) |

**Bottom** (teal)
*The claim's reach is bounded by the paired result on HLE-400, the cost, and the bank-provenance separation.*

**Footer** (tiny gray)
Numeric cells withheld pending the full HLE-400 re-run under the frozen standard (`docs/PAPER_DRAFT.md` Appendix C).

---

## P8 — Robustness & limitations · [stage 6 — boundary]

**Breadcrumb**: `EGTE · 稳健性 · 边界` · page 8

**Layout** — existence-claim strip (top) + boundary list + explicit failure-case list.

**Title** (deep navy, bold)
**Where the claim holds — and where it fails**

**Subtitle** (gray)
*An existence claim: an unoptimized instantiation already yields the gain; each role has measurable headroom.*

- **Existence claim** — distiller / critic / evaluator are first instantiations, not optimized ones. Headroom is quantified by the gap between current EIR/ECR and the threshold `Acc/(1−Acc)`: critic EIR can be lowered, evaluator retention of wrong→correct can be raised.
- **Transfer evidence** — the bank is distilled from in-family benchmarks, never from HLE; the HLE-400 result is therefore the cross-family, cross-difficulty test.
- **Cost** — C3 total consumption (all role calls) vs A3, stated separately from failure conditions.
- **For whom it holds** — HLE-400 split by answer type (MCQ vs open-ended); worst subgroup reported.
- **Where it fails** — locked-wrong (early stop on a wrong answer), no-commit, inconsistent transitions; correct candidates cut (false-CUT rate).
- **Boundary (teal)** — single solver model (deepseek-v4-flash), n = 400; reliable abstention out of scope (UNSURE = not eliminated); no stronger-model comparison (claim is same-model + external bank; frontier solver = future work).

**Bottom** (teal)
*The claim's boundary is one model, one hard family, and an unoptimized pipeline — each a stated direction for improvement, not a hidden assumption.*


---

## P9 — Conclusion: the evidence chain folds back · [evidence correspondence]

**Breadcrumb**: `EGTE · 收束 · 证据链` · page 9

> mirrors reference image **05.jpg** (wrap-up "每课题 → 中间对象 / 关键机制对照 / 最终评价").

**Layout** — four-row mapping table; each conclusion traces to one evidence type.

**Title** (deep navy, bold)
**One evidence chain, four evidence types**

**Subtitle** (gray)
*Every conclusion maps to a single evidence type — motivation, mechanism, decision, or boundary.*

| Conclusion | Evidence type | Key contrast |
|---|---|---|
| self-consistency activates correct answers but does not hold them | motivation | `P_act(A3)` vs A3 vote accuracy |
| the critic's suspicion identifies the actual error (H1) and the error-bank direction, not the scaffold or the vote, drives the correction (H2) | mechanism | archetype hit rate vs baseline; C3 vs A2 + attributed transitions; open-form split |
| error-guided elimination beats sampling on the same items at no higher cost (H3) | decision | C3 vs A3 on HLE-400; eliminator on vs off |
| a bank distilled in-family transfers to an unseen harder family; the pipeline is an unoptimized existence proof | boundary | bank provenance vs HLE; EIR/ECR headroom |

**Bottom** (teal)
*The strength of the contribution is bounded by how many alternative explanations the contrasts rule out.*

**Footer** (tiny gray)
Fig 1–3 + Tab 1–4 (below) are the deck's cross-slide index.

---

## Key figures / tables (cross-slide index)

- **Fig 1** (P3): one EGTE cycle — offline distillation → online elimination.
- **Fig 2** (P4): the three-role EGTE pipeline (distiller / critic / evaluator) over the EIR/ECR stability diagram.
- **Fig 3** (P6): transition-evidence chain on one HLE trajectory (critic suspicion → answer change → verdict).
- **Tab 1** (P5): control arms `A / A2 / A3 / C3 (/ A3C3)`.
- **Tab 2** (P7): bank provenance vs evaluation target.
- **Tab 3** (P7): HLE-400 main table (accuracy, settle, cost, EIR/ECR, P_act, McNemar).
- **Tab 4** (P7): mechanism table (H1 hit rate vs baseline; H2 C3 vs A2, attribution, answer-form split) + ablation (eliminator on/off).
