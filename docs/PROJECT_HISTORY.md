# 项目历史（合并文档，2026-11-11）

本文件合并了四份过程文档，原文保留在下方各节；合并前的原文件在 `docs/_deprecated/20261111_repo_cleanup/`。工程变更日志仍在根目录 `CHANGELOG.md`。当前状态与入口见 `docs/INDEX.md`。

## 0. 2026-10-28 至 2026-11-11：HLE-400 阶段（新增摘要）

- **10-28 至 11-02**：确定 HLE 400 题集（`scripts/build_hle_400_set.py`，文本题、按学科分层、种子 42）；跑 A / A2 / A3 / C3 四个条件；判分协议冻结（精确匹配 → 模型判定 → 争议复判与裁决），sidecar v2。
- **11-03 至 11-07**：mode/settle 的 None 计票 bug 修正；同模型 evaluator（Judge-R、Judge-R+、Judge-C）与似然比聚合；结论为"票数之外无可检出信息"。Judge-C 首次运行因 429 作废后全量重跑。
- **11-05 至 11-08**：bank-free critic（C2）预注册并运行，读出为"词表不可识别"；C2 的 hle_201 判分规则补充。
- **11-08 至 11-10**：扰动型安慰剂（A2′）预注册并运行；外部评审与独立评审推动：对称平局约定、自适应自洽采样基线、撤回"成本更低"主张。
- **11-10**：同成本自洽采样（补到 11 个样本）与 USC；发现并修复接口失败被写成答案的问题（A2′ 29 题等），全部整题重跑，sidecar v3。
- **11-11**：第二模型 qwen3.8-flash 复现完成，四条预注册检验全部成立；正式稿改为 ACL 模板（`paper/acl/`）；独立评审后修订；第三模型（glm-5.3）与人工审计预登记；仓库整理（本次）。

---

## 阶段史（原 HISTORY.md，2026-09-26）

### Project History

> This file preserves the **continuity** of the research program. Stages are never deleted; superseded results are marked, not removed. Every stage links to its surviving evidence.

> **Repository rename (2026-09-26).** This repository was formerly named **FinAgent** and is now **AgentEvaluation**, reflecting the metacognitive-evaluation program. The "FinAgent" era (Stage 0) is retained below as history, not deleted. Frozen experiment logs under `experiments/` keep their original absolute paths (`…/PycharmProjects/FinAgent/…`) as immutable evidence.

---

#### Stage 0 — Finance-agent evaluation pipeline ("FinAgent", renamed "AgentEvaluation")

**Period**: 2026-09-11 → 09-13
**Objective**: build a working financial-agent evaluation pipeline on real benchmark data.

What was built:

- Task schema + mini benchmark + FAB public loader (`src/benchmark.py`)
- Agents: rule-based / FinGPT / OpenAI / HuggingFace ReAct + EDGAR tools (`src/agent.py`)
- Main loop + trajectory recording (`src/runner.py`)
- 2-tier continuous scoring + dealbreaker (`src/evaluator.py`)

Milestones: `v0.1-skeleton` → `v2.1` (accuracy 8.3% → 34% via bug fixes).

**Status**: preserved as the finance **task-family module** of the current program.

---

#### Stage 1 — Evaluation-framework interference ("26pp spurious deficit")

**Period**: 2026-09-13 → 09-16
**Objective**: understand why the pipeline scored so low.

Core finding: evaluation-framework defects (tool design, call format, prompt, hyperparameters, judge bias) induced a measured **26pp spurious capability deficit** (34% → 60% on a 5-question validation set) — attributable to the framework, not the model.

Surviving evidence:

- `docs/INTERFERENCE_CAUSAL_TABLE.md` — INT-01…14 causal registry
- `docs/ADVISOR_SUMMARY_20260916.md` — stage report (bug vs. interference; three fairness principles)
- `docs/EVALUATION_STANDARD.md` — v2.3 scoring spec
- `experiments/20260916_int*` — INT-05 / 06 / 07 / 12 experiment records

**Status (continuity)**: *not discarded*. This stage becomes the **motivation** of the current program ("static accuracy is a bad metric"), and its unfinished experiments (INT-07 judge bias, INT-12 transparent budget) continue as the Phase-0 side track.

---

#### Stage 2 — Metacognitive evaluation (current)

**Period**: 2026-09-26 → present
**Objective**: redefine capability from single-shot accuracy into **cost–reliability + convergence**, and diagnose *which* capability a model lacks via an external meta-cognitive proxy.

- `docs/RESEARCH_PLAN.md` — experiment protocol
- `docs/REPRODUCIBILITY.md`, `docs/TIMELINE.md`, `docs/EXPERIMENT_LOG.md`
- `PROTOCOL.md` — change-propagation governance

**Continuity**: Stage 1's interference evidence is retained as the introduction motivation; the finance pipeline is retained as one cross-domain task family.

---

#### Continuity rules (normative)

1. A stage is never deleted; it is only ever extended by a newer stage.
2. A superseded result is marked `superseded` and points to its replacement — never silently removed.
3. Any revision of a claim follows `PROTOCOL.md` §6 (evidence-chain integrity).

---

#### Revision History

| Version | Date | Change |
|---|---|---|
| 1.1 | 2026-09-26 | Recorded repository rename FinAgent → AgentEvaluation. |
| 1.0 | 2026-09-26 | Created; records Stages 0–2 and the continuity rules. |

---

## 时间线与里程碑（原 TIMELINE.md，2026-10-21）

### Timeline

> Version 1.4 · 2026-10-07

---

#### 1. Roadmap

```
Phase 1: probe experiment      (3 days,  < $50)
    ↓ pass
Phase 2: feasibility           (2 weeks, ~ $1,200)
    ↓ pass
Phase 3: full experiment       (6 weeks, ~ $8,000)
    ↓ pass
Writing & submission           (4–6 weeks)
```

---

#### 2. Phase 1 — probe: end-to-end feasibility (COMPLETE → PHASE1_SUMMARY.md)

**Budget**: < $200. **Models**: 3 mid-tier via Aliyun Token Plan — deepseek-v4-flash-0731, qwen3.8-flash, glm-5.3; **no local model loading**; strong tier deferred to Phase 2/3. **Tasks**: 250 Qs — GSM8K 50 + MATH-500 50 + MMLU-Pro 50 + FAB 50 + BFCL 50 (L1:L2 = 3:2).

The authoritative Phase-1 plan (four feasibility checks, build-before-burn order, N=10 in 3-round
segments, no-human-labelling validation) is `docs/PHASE1_SUMMARY.md` (Phase-1 go/no-go plan). Milestones:

- **Foundations (no API cost)** — capability-matrix definition + decomposition check against d1_baseline; per-domain error taxonomy + Top-K signal generator + prior-weighted update; validated by deterministic rules and outcome-based next-round improvement, not human labelling.
- **Multi-round feedback (N=10, 3-round segments)** — advance the loop in ~3-round segments; after each segment inspect activation/locking for signal-driven change before spending the next.
- **Analysis + decision** — L3/L4 discrimination from round-dimension events; fit cost–reliability curves (k classification); write the go/no-go report. pass → Phase 2; fail → adjust evaluator (template / K / prior) and rerun at most twice before reassessing direction.

---

#### 3. Phase 2 — feasibility (planned; PHASE1_SUMMARY.md §8)

**Budget**: < $1,200. **Models**: mid tier (reused) + weak tier (qwen3.6-flash, glm-4.7-flash via rented Aliyun instance) + strong tier (strongest runnable, channel TBD). **Tasks**: core 5 families + hard-L1 (GPQA-Diamond) + a second light-FC family.

Execution order (see PHASE1_SUMMARY §8.7): **token metering → control arms → critic → weak tier + task expansion**. The control-arm trajectories are forward-compatible with Phase 3 and reused there, not re-run.

- **Prep (Day 4–6)**: token metering (prompt/completion/reasoning token counts, P2.0); control arms A / A2 / C (P2.1); FC-carrier ablation; task-set expansion (difficulty-calibrated); weak-critic recalibration.
- **Main (Day 7–11)**: baseline (1 round) + evaluator feedback (5 rounds) across 8–10 models × 5–8 classes; daily data-integrity checks.
- **Ablations (Day 12–14)**: no-evaluator self-loop, random feedback, uniform prior, no voting, different K.
- **Analysis (Day 15–18)**: statistical comparison across arms; metric summaries; visualizations; phase report + decision.
  - all pass → Phase 3; partial (only specific tasks) → narrow scope, enter a reduced Phase 3; fail → analyze cause, consider a methodology paper.

---

#### 4. Phase 3 — full experiment (Day 19–60)

**Budget**: < $8,000. **Models**: 12–15. **Tasks**: 12–15 classes, L2/L3 share ≥ 40%.

- **Prep (Day 19–25)**: deploy all models (open-source + API); prepare 12–15 task classes (incl. dynamically generated L3); complete the ablation matrix (8–10 arms); build the tensor-decomposition pipeline.
- **Experiment (Day 26–45)**: 12–15 models × 12–15 classes × (baseline + 8–12 feedback rounds); full ablation matrix; daily integrity checks.
- **Analysis (Day 46–60)**: tensor decomposition → latent dimensions; cost–reliability curve fitting (per model × task); ideal-upper-bound modelling + extrapolation validation; cross-task structural analysis; full report.

---

#### 5. Writing & submission (Day 61–90)

- **Drafting (Day 61–75)**: Introduction, Related Work, Method (evaluator design + decoupling theory), Experiments, Results + Discussion, Conclusion + Limitations.
- **Revision (Day 76–85)**: internal review; extra analyses a reviewer might demand; language polish; format to the target venue template.
- **Submission (Day 86–90)**: appendix (full config tables + ablation details); code repository; submit.

---

#### 6. Milestones and checkpoints

| Day | Milestone | Deliverable | Decision |
|---|---|---|---|
| 3 | Phase 1 done | probe report | proceed to Phase 2? |
| 18 | Phase 2 done | feasibility report | proceed to Phase 3? |
| 60 | Phase 3 done | full report | start writing? |
| 90 | submit | paper + appendix + code | submitted |

---

#### 7. Buffers and risk response

| Risk | Response | Buffer |
|---|---|---|
| Phase 1 needs a rerun | 1–2 days for adjustment | Day 3–4 |
| Phase 2 model-deploy delay | rent Aliyun instance / resolve strong-tier channel | Day 4–6 |
| Phase 3 API over-budget | cut top API models' question load; replace with local large models | budget elasticity |
| Tensor decomposition unclear | fall back to direct curve comparison (2–3 days) | Day 46–48 |
| Writing lag | shrink to an 8-page workshop version | Day 76–80 |

---

#### 8. Parallel work (while experiments run)

| Task | Window |
|---|---|
| Related-work draft | Phase-2 experiment window |
| Target-venue list | Phase-2 analysis window |
| GitHub repo scaffold | throughout |
| Figure templates | Phase-3 experiment window |

---

#### Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Translated to English. |
| 1.1 | 2026-09-27 | Phase-1 probe revised: 4 models (weak local ×2, mid API ×2, strong deferred), tasks expanded to math/logic/finance 50 each. |
| 1.3 | 2026-10-07 | Phase 1 complete (all Aliyun, no local); Phase 2 plan consolidated in PHASE1_SUMMARY.md §8 (control arms, weak tier via rented Aliyun instance, strong tier TBD, task expansion, k/θ cost curves). |
| 1.4 | 2026-10-07 | Phase 2 execution order revised: cost metering (P2.0) → control arms A/A2/C → critic → weak tier + expansion; control-arm data forward-compatible with Phase 3 (reuse, no re-run). |
| 1.2 | 2026-09-29 | Phase-1 probe re-scoped to an end-to-end feasibility loop (per RESEARCH_PLAN §5.7): 3 mid models via Aliyun, 250-Q probe set, N=10 feedback in 3-round segments, build-before-burn, no human labelling. |

---

## 实验记录索引（原 EXPERIMENT_LOG.md，2026-09-26）

### Experiment Log

> Living document — one record per experiment (or per run, when runs must be distinguished). This is the **evidence index** for the paper: every claim must trace back to a record here (see `../PROTOCOL.md` §6).

**Record template** (from `REPRODUCIBILITY.md` §6):

```markdown
#### [YYYY-MM-DD] {name}
- Config: configs/{file}.yaml
- Seed: {seed}
- Model: {model} @ commit {hash}
- Task: {class}, {n} questions
- Rounds: {n}
- Status: completed / failed / running
- Notes: …
- Git Commit: {hash}
- Log File: logs/{file}.log
```

---

#### Existing experiments (finance / interference pilot)

| Date | ID | Experiment | Status | Evidence home |
|---|---|---|---|---|
| 2026-09-16 | INT-05 | max_steps 25→50 | confirmed (+6pp) | `experiments/20260916_int05_max_steps/` |
| 2026-09-16 | INT-06 | T2 trajectory 4000→20000 chars | minimal (+2pp) | `experiments/20260916_int06_context_length/` |
| 2026-09-16 | INT-07 | judge V4-Flash→V4-Pro | paused (cost) | `experiments/20260916_int07_judge_bias/` |
| 2026-09-16 | INT-12 | transparent budget + no fallback | planned | `experiments/20260916_int12_transparent_budget/` |
| 2026-09-16 | v3-full | 50-task full run | baseline 48% | `experiments/20260916_v3_50task_full/` |
| 2026-09-16 | v3-fix | interference-fixed run | 60% (5-Q validation) | `experiments/20260916_v3_interference_fix/` |

> These predate the current `configs/*.yaml` standard (configs were inline in `src/config.py`); their `EXPERIMENT.md` files remain the authoritative record. New experiments must follow the template above.

---

#### Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Created; indexed existing interference experiments. |

---

## 决策记录（原 DECISION_LOG.md，2026-10-05）

### Decision Log (process record — not a deliverable)

> This file records decisions, open questions, and process discussion that are **not** part of the academic deliverables. It is a working log for the author and future collaborators; it is not intended for the manuscript or supplementary material.

---

#### 1. Resolved decisions

| Date | Decision | Outcome |
|---|---|---|
| 2026-09-26 | Paper architecture | **One single end-to-end paper**; the core contribution is metacognition. The evaluation-framework-interference work is the *pilot*, whose findings motivate the paper's "static accuracy is a bad metric" claim; how much of it enters the main text is decided later by evidence quality. |
| 2026-09-26 | Domain scope | **Cross-domain multi-task + finance retained.** Measuring metacognitive ability requires heterogeneous task families; finance (the retained finance pipeline + FAB) is one family and reuses the existing code. |
| 2026-09-26 | Execution mode | **Parallel**: build the multi-round feedback-loop probe (main track) while finishing interference experiments INT-07/12 (side track). |
| 2026-09-26 | Document language | English (facing the international community). |
| 2026-09-26 | Document register | Academic register only; process/decision content lives in this log, separated from the research plan. |
| 2026-09-26 | Analysis backbone | Capability-matrix **tensor decomposition** (model × task × error type), not pre-imposed L1/L2/L3. |
| 2026-09-26 | Repository home | **This AgentEvaluation repository** (code + research docs unified under `docs/`). The separate `metacog-research/` drafting directory is superseded. |
| 2026-09-26 | Repo refactor | Reorganized into `docs/`, `paper/`, `scripts/`, `docs/figures/`; added `PROTOCOL.md`, `docs/REPRODUCIBILITY.md`, `docs/TIMELINE.md`, `docs/EXPERIMENT_LOG.md`; un-ignored `experiments/` to keep it in the evidence chain. |
| 2026-09-26 | Repository rename | **FinAgent → AgentEvaluation** (directory, README title, env-var prefix `FINAGENT_* → AGENTEVALUATION_*`, SEC User-Agent, git remote). Historical "FinAgent" references are retained only in `docs/HISTORY.md` and this log. |
| 2026-09-26 | License choice | **MIT**. Rationale: permissive, widest compatibility, no copyleft obligation — the default for research code. Revisit only if patent grants matter (then Apache-2.0). |

---

#### 2. Open questions

1. **Interference in the main text** — standalone section ("why single-shot accuracy misleads") vs. intro figure + appendix registry. Pending Phase-0 evidence (INT-07/12 causal numbers).
2. **Phase-3 task-family list** — final 12–15 families beyond math / commonsense / code / factual-QA / multi-hop / translation / logic / finance.
3. **Strong-tier model list and API budget cap** — $100 / $500 / $1,000+ / uncapped.
4. **Target-venue priority** — Nature MI → TPAMI → NeurIPS ordering.
5. **Cloud GPUs** — whether to introduce before Phase 3 to scale local weak/mid-tier throughput.

---

#### 3. Compute and budget discussion (working notes)

- **Hardware**: M4 MacBook Air, 24 GB unified memory, no CUDA. Local inference via MLX / Ollama / llama.cpp.
- **Local feasibility**: 0.5B–8B smooth; 14B marginal; 32B/70B infeasible.
- **Model routing**: weak/mid tiers local (free); strong tier budget API. The three-tier design and Mac capabilities are complementary.
  - *(superseded 2026-09-27/28)*: Phase 1 now loads **no model locally** — all three mid-tier models run on the Aliyun Token Plan; the Mac's local MLX/Ollama path is reserved for the Phase-2 weak tier.
- **API cost**: budget-tier scenario keeps the whole program within the low thousands of dollars; top-tier-API-heavy scenario reaches ~$10,000 for Phase 3 (see RESEARCH_PLAN §7).
- **Escalation ladder**: (1) free inference tiers (HF / Groq / Together / Replicate) → (2) spot cloud GPUs (RunPod / Lambda / Vast) → (3) offload to budget API.

---

#### 4. Concurrency & parallelization (working notes)

> Status: engineering warm-up for Phase 1; recorded for later, NOT executed now.

### Current state (done)
- Serial-to-parallel refactor completed and smoke-tested:
  - `agent.py`: `_DOCUMENT_CACHE` -> `threading.local()` (thread-safe; 12 threads no cross-talk).
  - `runner.py`: `ThreadPoolExecutor` task-level parallelism + failure isolation (`AGENTEVALUATION_CONCURRENCY`, default 6).
  - `evaluator.py`: parallel scoring via `_score_one_row` + `ThreadPoolExecutor`.
- 10-task stress test @ concurrency 6: 10/10 done, 0 API failures, wall-clock 6:44 (serial ~ 21 min), ~3.2x speedup. Single-task latency unchanged (min 30s / mean 128s / max 339s).
- Bottleneck is tail variance, not throughput: a wave's wall-clock equals its slowest task (the "bucket" effect), so speedup stays well below the concurrency factor.

### Future directions (defer until more real questions are added)
1. **Duration-tagged basket scheduling**: tag each question with its expected duration, group near-duration tasks into a basket, and run them concurrently — reduces the tail/bucket penalty by keeping wave-mates close in runtime (load-balance by predicted latency instead of FIFO batching).
2. **Multi-API agents**: route different questions to different API-backed agents (distinct endpoints/accounts), raising the total concurrency ceiling by spreading rate limits.
3. Open follow-up: sweep concurrency (6/8/12/16) to locate the HF-router rate-limit knee before any full-scale run.

---

#### Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | Created; moved decision/process content out of the research plan. |
| 0.2 | 2026-09-26 | Resolved repository home (AgentEvaluation repo) and recorded the repo refactor; added license-choice open question. |
| 0.3 | 2026-09-26 | Recorded repository rename FinAgent → AgentEvaluation. |
| 0.4 | 2026-09-26 | Resolved license choice: MIT. |
| 0.5 | 2026-09-27 | Logged concurrency refactor status + future parallelization strategies (duration-basket scheduling, multi-API agents); deferred execution. |
