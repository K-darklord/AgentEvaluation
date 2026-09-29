# Architecture Design — Scalable Experiment Execution

> Version 0.1 · 2026-09-27 · Status: Design (pre-implementation; no code yet)

---

## 1. Purpose and scope

This document is the **implementation blueprint** for the experiment-execution layer of the
metacognition research program. It is authored **up-front against the Phase-3 workload** so that
the pipeline does not need a second rewrite when the full matrix scales up.

**What this document is and is not:**

- It **defines** the target architecture: modules, interfaces, data flow, the SQLite task-queue
  schema, provider routing, and reproducibility guarantees.
- It is **not yet code**. Implementation is deferred until after (a) the current FAB merge is
  validated and (b) the near-term concurrency refactor is complete. The phased landing plan is in §10.
- The **experiment design** (what to run) is authoritative in `docs/RESEARCH_PLAN.md`; this document
  is authoritative for **how the runs are executed and stored**.

---

## 2. Design drivers (workload)

The architecture is sized to the Phase-3 full experiment, not to the current single-benchmark runs.

| Dimension | Phase 3 (full) |
|---|---|
| Models | **12–15** |
| Task classes (families) | **12–15** (L2/L3 ≥ 40%) |
| Feedback rounds per cell | baseline + **8–12** |
| Ablation arms | **8–10** |
| Seeds per run | **≥ 3** |

**Cell-count estimate** (Cartesian, worst case): `13 model × 13 class × 10 round × 9 arm × 3 seed ≈ 45,000`
experiment-configuration units — each multiplied by its probe question set (classes carry ~50–100
questions each). Independent of the exact factorisation, the workload is **millions of independent
probe runs**.

**Two hard constraints follow from this scale:**

1. **Throughput** — the current `src/runner.py` (`for task in tasks: agent.solve(task)` + an in-memory
   list written to CSV at the end) cannot express, let alone survive, this workload. Execution must be
   concurrent, persistent, and resumable.
2. **Cost** — the dominant cost driver is `API model × question × round` cells (nominal $8–10k top-tier).
   The scheduler must be cost- and rate-limit-aware, and every call must be metered.

---

## 3. Architecture overview

```
[Experiment Spec]   YAML: model×task×round×arm matrix + budget/rate guards
        │  Cartesian expansion
        ▼
[Task Generator]    emits independent probe tasks (one unit = one agent solving one question, one round)
        │  enqueue
        ▼
[Scheduler]         SQLite persistent task queue + dispatcher
        │            (global concurrency pool, provider routing, cost/rate aware, retry, checkpoint)
        ▼
[Executor]          agent.solve — provider-parameterized; local tier / API tier
        │  results
        ▼
[Artifact Store]    results/ + per-run manifest.json (hashes, config, seed, commit)
        │
        ▼
[Analysis]          tensor decomposition + cost–reliability curve fitting
```

The layering separates three concerns that the current code conflates: **what to run** (spec),
**how many at once** (scheduler), and **where each unit runs** (provider routing).

---

## 4. Core components

### 4.1 Experiment Spec (YAML)

Single source of truth for an experiment. Replaces the scattered inline constants in `src/config.py`.

```yaml
# configs/phase3_main.yaml  (illustrative shape)
experiment:
  name: phase3_main
  version: 1
models:
  - id: deepseek-v4-flash
    provider: hf-router
    model_name: deepseek-ai/DeepSeek-V4-Flash
    tier: api
  - id: qwen2.5-7b
    provider: local-ollama
    model_name: Qwen/Qwen2.5-7B-Instruct
    tier: local
task_families: [finance, math, commonsense, code, fact_qa, multi_hop, translation]
rounds: { baseline: 1, feedback: 10 }
ablation_arms: [main, no_proxy, random_feedback, uniform_prior, no_voting]
seeds: 3
budget: { max_usd: 8000, hard_stop: true }
rate: { global_rps: null, per_provider_max_concurrency: 8 }
```

### 4.2 Task Generator

Expands the spec Cartesian product into independent probe tasks. Each task is fully self-contained
(every field needed to execute + re-execute it), which is what makes parallelism and resumability trivial.

### 4.3 SQLite persistent task queue (chosen base)

Selected over Redis/Celery because it is a **zero-dependency, resumable, cross-process** queue that
keeps the reproducibility story local to the repo (no out-of-repo service). Schema:

```sql
CREATE TABLE tasks (
  task_id       TEXT PRIMARY KEY,      -- deterministic hash(model,family,question,round,arm,seed)
  model_id      TEXT NOT NULL,
  provider      TEXT NOT NULL,
  family        TEXT NOT NULL,
  question_id   TEXT NOT NULL,
  round_no      INTEGER NOT NULL,
  arm           TEXT NOT NULL,
  seed          INTEGER NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending',  -- pending|running|done|failed|api_failure
  retry_count   INTEGER NOT NULL DEFAULT 0,
  max_retries   INTEGER NOT NULL DEFAULT 3,
  payload       TEXT,                  -- JSON: rendered prompt + tool config
  result_ref    TEXT,                  -- path/token of stored trajectory
  cost_usd      REAL,
  latency_ms    INTEGER,
  error         TEXT,
  created_at    TEXT,
  updated_at    TEXT
);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_model_family ON tasks(model_id, family);
```

`status` transitions and an idempotent `task_id` (hash of the full cell) give **crash-safe resume**:
a re-run re-enqueues only `pending`/`failed` rows, never re-executes `done` cells.

### 4.4 Scheduler / Dispatcher

- **Global concurrency pool** sized by `per_provider_max_concurrency` (the physical rate-limit bound),
  not by benchmark or model count. This is the single shared budget across all levels of parallelism
  (task / benchmark / run).
- **Provider routing** (§7): model-fixed (fair comparison), failover, and cost/rate-aware strategies.
- **Retry with backoff + jitter** on transient/429; `api_failure` is a terminal state distinct from `failed`.
- **Budget guard**: `hard_stop: true` halts enqueueing once cumulative cost crosses the cap.

### 4.5 Executor (parameter-ized agent)

`agent.solve` becomes provider-parameterized rather than hard-coding `base_url`. A `ProviderRegistry`
holds `{base_url, api_key, model_list, rate_limit, cost_per_1k}`; the openai-compatible `chat.completions`
call is the universal transport, so "different platforms" reduce to different registry entries, not new
agent classes. Local tier (MLX/Ollama on the M4) and API tier (HF router / OpenAI / Anthropic) are both
registry entries routed by `tier`.

### 4.6 Artifact Store

Brings the current flat `output/*.jsonl|csv` up to the reproducibility standard:

```
results/<experiment>/<run>/
  manifest.json      # config hash, seeds, model list, git commit, timestamps, cost
  trajectories/      # one file per task_id
  judge_scores/
  analysis/
```

Each run maps to a git commit (`[EXP] name | config=… | seed=…`) per `PROTOCOL.md`.

### 4.7 Analysis

Tensor-decomposition pipeline (`T ∈ R^{M×T×E}` → PARAFAC/Tucker/PCA) and cost–reliability curve
fitting. Reads from the artifact store only — analysis never re-touches the LLM.

---

## 5. Key interfaces (stubs)

```python
# src/experiment/spec.py
@dataclass
class ExperimentSpec: ...
def load_spec(path: Path) -> ExperimentSpec: ...

# src/experiment/taskgen.py
def expand_tasks(spec: ExperimentSpec) -> Iterator[Task]: ...

# src/experiment/queue.py
class TaskQueue:
    def __init__(self, db_path: Path): ...
    def enqueue(self, tasks: Iterator[Task]) -> None: ...
    def claim_next(self, status: str) -> Task | None: ...
    def mark(self, task_id: str, status: str, *, result_ref=None, cost=None, error=None) -> None: ...

# src/experiment/scheduler.py
class Scheduler:
    def __init__(self, queue: TaskQueue, registry: ProviderRegistry, *, max_concurrency: int): ...
    def run(self) -> None: ...   # blocks until queue drains or budget hard-stop

# src/models/provider.py
class ProviderRegistry:
    def get(self, provider_id: str) -> Provider: ...
    def route(self, model_id: str, strategy: str) -> Provider: ...

# src/models/agent.py  (evolves from src/agent.py)
class ToolLoopAgent:            # was HuggingFaceAgent, now provider-injected
    def __init__(self, model_id: str, provider: Provider): ...
    def solve(self, task) -> AgentResult: ...
```

---

## 6. Data flow (end-to-end)

```
spec.yml → TaskGenerator → SQLite queue → [workers pull] → Executor(provider) →
  trajectory (per task_id) → Artifact store + manifest → Analysis (tensor/cost-fit)
        ▲                                                          │
        └────────── retry / resume (idempotent task_id) ◄─────────┘
```

A claim in the paper therefore traces: `claim → experiment-log record → config+seed → raw
trajectories → git commit`, unchanged from the evidence-chain convention in `docs/DOCS_FRAMEWORK.md` §5.

---

## 7. Provider routing (multi-platform)

- **Model-fixed (default)** — a model binds to one provider for the whole experiment. **Non-negotiable
  for model comparison**: provider variance (latency, backend version, rate-limit behaviour) would
  otherwise leak into the *model* dimension and corrupt the tensor decomposition.
- **Failover** — on provider 429/outage, reroute to an equivalent provider (engineering only, never
  for the comparison arms).
- **Cost-aware** — route cheap tiers first under a budget cap.

`model comparison` and `provider failover` are two distinct routing goals and are configured separately.

---

## 8. Reproducibility guarantees

- All parameters in YAML (no hard-coding); `config.py` retired as the parameter source.
- Explicit `temperature` (0 for the agent and judge) and `seed` per cell; each experiment run ≥ 3 seeds.
- Per-run `manifest.json` with config hash + git commit; idempotent `task_id` for resumability.
- Deterministic components (data processing, statistics, plotting) fully reproducible; LLM sampling
  logged with temperature and seed.

---

## 9. Relationship to current code (migration)

| Current | Target |
|---|---|
| `src/config.py` (inline constants) | `configs/*.yaml` + `ProviderRegistry` |
| `src/agent.py` (hard-coded base_url) | `src/models/agent.py` (provider-injected `ToolLoopAgent`) |
| `src/runner.py` (`for` loop, in-memory, CSV at end) | `src/experiment/{spec,taskgen,queue,scheduler}.py` |
| `src/evaluator.py` (serial loop + judge) | `src/judge/` + `src/analysis/` |
| `output/` (flat, gitignored) | `results/<experiment>/<run>/` + manifest |

This realises the migration already recorded in `docs/DOCS_FRAMEWORK.md` §6 (split
`src/{models,evaluator,experiment,analysis,judge,utils}/`, `config.py → YAML`).

---

## 10. Phased implementation plan

| Step | Scope | Trigger / gate |
|---|---|---|
| **P0** | `ProviderRegistry` + client factory + `configs/*.yaml` scaffolding | after merge validation |
| **P1** | SQLite `TaskQueue` + `Scheduler` (concurrency); `_DOCUMENT_CACHE` thread-safety fix | after P0 |
| **P2** | Multi-model parallel + provider routing (model-fixed / failover / cost) | after P1 |
| **P3** | Artifact store + manifest + tensor/cost analysis pipeline | Phase-2→3 boundary |

P0/P1 correspond to the near-term concurrency refactor already planned; P2/P3 are the multi-platform
scheduling and the Phase-3 analysis layer described in §3–§7.

---

## 11. Design decisions (logged)

| Decision | Choice | Rationale |
|---|---|---|
| Scheduling base | **SQLite persistent queue** | zero-dep, resumable, cross-process; keeps repro local to repo |
| Phase 1/2 concurrency | **thread pool** | `solve` is blocking I/O (GIL released); minimal change |
| Phase 3 scale | **persistent queue** | for-loop runner cannot resumable/retry at this scale |
| Multi-platform | **provider registry + router** | openai-compat transport ⟹ provider = registry entry |
| Model comparison fairness | **model-fixed provider** | isolate model dimension from provider variance |

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-27 | Initial architecture design (design only; no implementation). Sized to Phase-3 workload; SQLite queue; provider routing; phased landing plan. |
