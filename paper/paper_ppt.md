# Paper PPT — Slide Content & Layout (EGTE)

**Source of truth**: `paper/paper_outline.md` (seven-stage evidence chain) + `docs/PAPER_DRAFT.md`
(§2 roles/arms, §3 frozen standard, §4 results, §5 research questions). Aligned as of **2026-10-27**.

> **2026-10-27 restructure** — the deck is rebuilt on the *research-progression* scaffold drawn from the six
> reference slides: one `问题定义 → 贡献1·中间对象 → 贡献2·机制验证 → 贡献3·决策层 → 主表` ladder, each stage
> answering "what the study must answer" and leaving "a re-checkable deliverable". Slide order now follows that
> ladder, not the old bullet list.

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
*A train-free, three-role test-time elimination (distiller → critic → evaluator) that **excludes** wrong candidates from a recursively-refined error bank, instead of scoring the correct path.*

**Falsification strip** (bottom bar, deep navy)
- **One-sentence claim** — *Does answer-free error exclusion beat compute-matched sampling, and does the loop converge — surfacing correctness that self-consistency alone cannot reach?*
- **Failure criterion** — *if C3 does not systematically beat A3 on the hard slice (Δ_act ≤ 0 AND net Δ ≤ 0), the EGTE claim fails.*

**Key output** — the single question the rest of the deck must answer, gated by the failure criterion above.

---

## P2 — Research-progression ladder · [stage 1 — framing map]

**Breadcrumb**: `EGTE · 框架 · 研究推进顺序` · page 2

> mirrors reference image **研究框架.png** (three-column "研究推进顺序" table).

**Layout** — one three-column table, deep-navy header, zebra rows; bottom “retreat” note.

**Title** (deep navy, bold)
**The research-progression ladder — five stages, one evidence chain**

**Subtitle** (gray)
*The same EGTE topic, unfolded stage by stage; each stage answers one question and leaves one re-checkable deliverable.*

| Stage | What the study must answer | Deliverable of the stage |
|---|---|---|
| **问题定义** Problem definition | Where does prior work stop, and which failures still lack an *external* signal? | main question + literature boundary (a falsification criterion) |
| **贡献1 · 中间对象** Contribution 1 · intermediate object | Which process quantity must be observed separately — how is a *wrong-execution behaviour* distilled answer-free? | answer-free `mechanism` + `check_procedure` (L1/L2/L3) + minimal baseline |
| **贡献2 · 机制验证** Contribution 2 · mechanism verification | Why does it work, and which alternative explanations (sampling? scaffolding?) still hold? | interventions + ablations (`A/A2/A3/C3/A3C3`) + EIR/ECR stage-replacement |
| **贡献3 · 决策层** Contribution 3 · decision layer | Which real decisions does it change — when is `CUT/KEEP/UNSURE` trustworthy? | decision rule (elimination + mode) + risk-coverage boundary |
| **主表** Main table | Which contrasts jointly support the claim? | unified main table + support tables A/B/C |

**Bottom** (teal)
*Every stage must leave a re-checkable deliverable; where the evidence is insufficient, retreat to the previous stage.*

**Footer** (tiny gray)
P3–P7 below instantiate this ladder in order; P8–P9 test its boundary and fold the chain back to the claim.

---

## P3 — Problem definition: the error set as a test-time elimination information source · [stage 1 — gap & motivation]

**Breadcrumb**: `EGTE · 问题定义` · page 3

> mirrors reference image **04.jpg** (two-column "已有依据 / 研究单位需要明确").

**Layout** — left-right columns; left · green header "已有依据", right · deep-navy header "研究单位需要明确"; full-width bottom conclusion.

**Title** (deep navy, bold)
**Static accuracy confounds capability with framework artefacts**

**Subtitle** (gray)
*Candidate gap: which failures still lack an external gold-free signal, and can an error set supply it?*

**Left — 已有依据 (existing evidence)**
- Static single-shot accuracy confounds capability with evaluation-framework artefacts — a measured **26 pp spurious deficit** (FAB pilot).
- Intrinsic self-correction is unreliable (Huang et al. 2023); self-critic / self-refine models cannot reliably correct themselves without an external signal → external feedback is **necessary**.
- The "learn-from-mistakes" family is already occupied — Mistake Notebook, PRISM, Cliff, LANPO, Agent-R / TAPO / LEMMA.

**Right — 研究单位需要明确 (what the study must fix)**
- Can an **error set** serve as a gold-free *test-time elimination* information source?
- Is *exclusion* (a few finite, falsifiable rules) cheaper and more robust than *scoring the correct direction* (a PRM)?
- Is the elimination **attributable to a real error mechanism**, not noise or a lucky re-sample?

**Bottom** (teal)
*Model "what goes wrong" (a few exclusion rules) rather than "what is right" — the asymmetry is the load-bearing claim.*

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
| **一致性** cross-question transfer | one archetype fires across questions **and** benchmark families | fires only on bank items it was distilled from |
| **未知状态** bank growth | L3 re-distills as the bank grows, not a frozen taxonomy | fixed taxonomy rejects new errors → mechanism goes stale |

**Bottom** (teal — continue condition)
*Continue condition: freeze the 7 L3 archetypes with their answer-free `check_procedure`, and confirm they fire consistently across families.*

**Footer** (tiny gray)
7 archetypes — `constraint_blind`, `descriptor_conflation`, `memory_substitution`, `procedure_truncation`, `sign_normalization_slip`, `retrieval_abort`, `format_nonconformance`.

---

## P5 — Contribution 2 · mechanism verification: arms + EIR/ECR · [stage 3 — intervention]

**Breadcrumb**: `EGTE · 贡献2 · 机制验证` · page 5

**Layout** — arm-contrast table (deep-navy header) + EIR/ECR condition strip + two hypothesis cards.

**Title** (deep navy, bold)
**The causal contrast what explains the effect — sampling, scaffolding, or error-set guidance?**

**Subtitle** (gray)
*All arms share the same solver base and scorer; they differ only in feedback/aggregation.*

| Arm | Definition | Role in the design |
|---|---|---|
| **A** | bare re-solve, T=0, single answer, zero intervention | floor — raw latent accuracy |
| **A2** | fixed neutral placebo, T=0, single answer | **placebo = no-distiller + no-critic-direction** — strips the whole error-set guidance (no mechanism, no direction); controls scaffolding and isolates the treatment |
| **A3** | self-consistency (Wang et al. 2022), T=0.7, N=10, i.i.d. majority vote | **independent-sampling baseline EGTE must beat** |
| **C3** | strong critic (in-loop) + evaluator `rubric_ce` (offline); **eliminator switch** isolates Stage B | treatment — Stage A (activation) + Stage B (lock) |
| **A3C3** | A3-seeded round-0, then the C3 loop | stacked (sampling + EGTE) |

**Additional controls** (same causal-contrast logic, kept separate from the fixed-solver arms)
- **Stronger-model control** (to run) — frontier solver **astra** (`gpt-6-astra`, 中转 smoke only), bare + A3: rules out "the base model is just weak; a larger model reaches the same without EGTE."
- **Compute-matched** — C3 (1× T=0 chain + critic + evaluator) uses **fewer** tokens than A3 (N=10 samples), so the C3 gain is *not* a compute artifact (EGTE is compute-cheaper).

**Bottom** (teal)
*`final = init + corrected(ECR) − flipped(EIR)` — iteration is beneficial only while `ECR / EIR > Acc / (1 − Acc)`.*

**Two hypotheses** (H1 / H2, each with support + failure)
- **H1 activation** — the strong critic lifts reachability vs A3: `P_act ≥ A3` at controlled EIR (↔ Q2 + Q5).
- **H2 mechanism** — the evaluator's elimination + mode lock beats a plain majority vote on the hard slice (↔ Q3 + Q4).

**Footer** (tiny gray)
Weak critic `C` is outdated (underperformed) — dropped, not in the final paper.

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
- **UNSURE** — evidence is weak, both answers survive.
- aggregation = **elimination + mode**; an all-UNSURE trace falls back to **mode**.

**Right — 同一比较条件 (same comparison terms)**
- same model + candidate answers.
- same data split.
- includes verification, sampling, and call cost.

**Bottom**
- **主判断 (main judgement)** — *does elimination + mode raise accuracy over a plain majority vote, at lower tokens per correct, with EIR suppressed and ECR retained?*
- **收缩结论 (shrink condition, teal)** — *if elimination + mode gives no stable gain, shrink the claim to diagnosis or mechanism discovery.*



---

## P7 — Main table design: main table + support tables · [stage 5 — synthesis]

**Breadcrumb**: `EGTE · 主表设计` · page 7

> mirrors reference image **03.jpg** (three-column "主表与支撑表" structure).

**Layout** — teal-header table, columns = 表 / 行·比较对象 / 列·必须回答; bottom constraint sentence.

**Title** (deep navy, bold)
**EGTE's main table and support tables**

**Subtitle** (gray)
*The main table answers decision effect; the support tables explain why the signal works. Structure to be filled after the frozen re-run.*

| Table | Row — comparison object | Column — must answer |
|---|---|---|
| **主表 · 选择质量** Main · selection quality | A / A2 / A3 / C3 / A3C3 | Acc; tokens per correct; EIR; ECR; McNemar exact (paired) |
| **支撑表 A · 信号质量** Support A · signal quality | weak discriminator / independent verifier (critic trigger) | AUROC, AUPRC, annotation agreement — is activation attributable to the error set? |
| **支撑表 B · 干预机制** Support B · intervention mechanism | original / key intervention / irrelevant intervention | paired EIR/ECR deltas, confidence intervals, question type |
| **支撑表 C · 稳健性** Support C · robustness | model (12–15) / task family / evidence format | cross-distribution gain and failure range |

**Bottom** (teal)
*The claim's reach is bounded by the paired result, cost, and cross-dataset stability.*

**Footer** (tiny gray)
Numeric cells are withheld here pending the full re-run under the frozen §3.0 standard (`docs/PAPER_DRAFT.md`).

---

## P8 — Robustness & limitations · [stage 6 — boundary]

**Breadcrumb**: `EGTE · 稳健性 · 边界` · page 8

**Layout** — robustness matrix (cross-model × task-family) + explicit failure-case list.

**Title** (deep navy, bold)
**Where the claim holds — and where it fails**

**Subtitle** (gray)
*Boundary conditions, cross-condition reproduction, and cost–benefit.*

- **Cross-condition reproduction** — cross-model (12–15) × cross-task-family + a stronger frontier solver (rules out "the base model is just weak").
- **Cross-benchmark transfer** — the L3 error bank is distilled from prior errors, **not** HLE; the HLE pilot's net +3 (4 saves vs 1 loss, p = 0.375) is **motivation / pilot** evidence only, not decision-grade transfer evidence — distinct from the Stage-B-lock boundary below.
- **Cost–benefit** — settle is free vs the Stage-B evaluator cost.
- **Explicit failure cases** — settle-locked-wrong, no-commit, inconsistent transitions.
- **Boundary (teal)** — the Stage-B lock's transition-evidence signal is question-type-dependent: it shows on one slice but **not on HLE**; Phase 3 must test whether the transition rationale transfers across families, not just within a slice.

**Bottom** (teal)
*The claim's boundary is where the transition evidence stops transferring across question types.*

**Footer** (tiny gray)
Robustness matrix = outline Tab 4.

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
| static accuracy confounds capability with framework artefacts | motivation | measured 26 pp spurious deficit |
| answer-free error mechanisms exclude wrong candidates, not score the right path | mechanism | distiller/critic/evaluator, EIR vs ECR |
| elimination + mode lock beats a plain majority vote | decision | C3 vs A3 on the hard slice |
| distillation transfers to HLE as pilot-only motivation (net +3, p = 0.375); only the Stage-B lock's evidence stays question-type-bound | motivation / pilot | one slice vs HLE |

**Bottom** (teal)
*The strength of the contribution is bounded by how many alternative explanations the contrasts rule out.*

**Footer** (tiny gray)
Fig 1–3 + Tab 1–4 (below) are the deck's cross-slide index.

---

## Key figures / tables (cross-slide index)

- **Fig 1** (P3): capability curve → self-improvement engine (reframe).
- **Fig 2** (P4): the three-role EGTE pipeline (distiller / critic / evaluator) over the EIR/ECR stability diagram.
- **Fig 3** (P6): Stage-B evaluator pruned state chain → `CUT / KEEP / UNSURE`.
- **Tab 1** (P5): control arms `A / A2 / A3 / C3 / A3C3`.
- **Tab 2** (P5): two hypotheses (H1 activation / H2 mechanism) + falsification criteria.
- **Tab 3** (P7): accuracy and EIR/ECR across arms on the hard slice.
- **Tab 4** (P8): robustness matrix (cross-model × task family).