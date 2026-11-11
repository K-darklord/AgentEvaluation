# Decision Log (process record — not a deliverable)

> This file records decisions, open questions, and process discussion that are **not** part of the academic deliverables. It is a working log for the author and future collaborators; it is not intended for the manuscript or supplementary material.

---

## 1. Resolved decisions

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

## 2. Open questions

1. **Interference in the main text** — standalone section ("why single-shot accuracy misleads") vs. intro figure + appendix registry. Pending Phase-0 evidence (INT-07/12 causal numbers).
2. **Phase-3 task-family list** — final 12–15 families beyond math / commonsense / code / factual-QA / multi-hop / translation / logic / finance.
3. **Strong-tier model list and API budget cap** — $100 / $500 / $1,000+ / uncapped.
4. **Target-venue priority** — Nature MI → TPAMI → NeurIPS ordering.
5. **Cloud GPUs** — whether to introduce before Phase 3 to scale local weak/mid-tier throughput.

---

## 3. Compute and budget discussion (working notes)

- **Hardware**: M4 MacBook Air, 24 GB unified memory, no CUDA. Local inference via MLX / Ollama / llama.cpp.
- **Local feasibility**: 0.5B–8B smooth; 14B marginal; 32B/70B infeasible.
- **Model routing**: weak/mid tiers local (free); strong tier budget API. The three-tier design and Mac capabilities are complementary.
  - *(superseded 2026-09-27/28)*: Phase 1 now loads **no model locally** — all three mid-tier models run on the Aliyun Token Plan; the Mac's local MLX/Ollama path is reserved for the Phase-2 weak tier.
- **API cost**: budget-tier scenario keeps the whole program within the low thousands of dollars; top-tier-API-heavy scenario reaches ~$10,000 for Phase 3 (see RESEARCH_PLAN §7).
- **Escalation ladder**: (1) free inference tiers (HF / Groq / Together / Replicate) → (2) spot cloud GPUs (RunPod / Lambda / Vast) → (3) offload to budget API.

---

## 4. Concurrency & parallelization (working notes)

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

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | Created; moved decision/process content out of the research plan. |
| 0.2 | 2026-09-26 | Resolved repository home (AgentEvaluation repo) and recorded the repo refactor; added license-choice open question. |
| 0.3 | 2026-09-26 | Recorded repository rename FinAgent → AgentEvaluation. |
| 0.4 | 2026-09-26 | Resolved license choice: MIT. |
| 0.5 | 2026-09-27 | Logged concurrency refactor status + future parallelization strategies (duration-basket scheduling, multi-API agents); deferred execution. |