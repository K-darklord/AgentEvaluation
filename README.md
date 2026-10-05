# AgentEvaluation — Metacognitive Evaluation of Agent Capability

> Living document · 2026-09-26
>
> A financial-agent evaluation pipeline, now reorganized as the single source of truth for the metacognition research program. All research documents, the reproducibility standard, and the change-propagation protocol live alongside the code.

---

## What this repository is

1. **The evaluation pipeline** — real benchmark data across five task families (GSM8K, MATH-500, MMLU-Pro, FAB, BFCL) + tool-calling agents + trajectory recording + three-tier scoring (T1 rule / T2 LLM rescue / T3 multi-judge).
2. **The home of the research program** — single end-to-end paper whose core contribution is *metacognition*: an external meta-cognitive proxy redefines capability from single-shot accuracy into a cost–reliability curve + convergence class, and a model × task × error-type tensor decomposition localizes which capability a model lacks. The evaluation-framework-interference study (26pp spurious deficit) motivates "static accuracy is a bad metric".

---

## Repository structure

```
AgentEvaluation/
├── README.md                  # this index + reproduction guide
├── LICENSE                    # MIT
├── PROTOCOL.md                # change-propagation protocol (how documents stay consistent)
├── CHANGELOG.md               # engineering change log
├── requirements.txt
├── src/                       # working finance-agent pipeline (package)
│   ├── __init__.py
│   ├── benchmark.py           # task schema + mini benchmark + FAB loader
│   ├── agent.py               # RuleBased / FinGPT / OpenAI / HuggingFace (ReAct + EDGAR tools)
│   ├── runner.py              # run agent → trajectories + run summary
│   ├── evaluator.py           # 3-tier scoring (T1 rule / T2 LLM rescue / T3 multi-judge) + error taxonomy
│   └── config.py              # API keys / models / scoring config
├── configs/                   # experiment configs (Phase-1 YAML; scaffolded)
├── data/
│   ├── raw/                   # FAB public dataset (fab_public.csv)
│   └── processed/             # derived task banks (scaffolded)
├── docs/                      # academic deliverables + process logs (see index below)
│   ├── RESEARCH_PLAN.md       # experiment protocol (authority)
│   ├── REPRODUCIBILITY.md     # top-venue reproducibility standard
│   ├── TIMELINE.md            # phases, milestones, budget
│   ├── EVALUATION_STANDARD.md # 3-tier scoring spec (T1/T2/T3)
│   ├── INTERFERENCE_CAUSAL_TABLE.md
│   ├── EXPERIMENT_LOG.md      # per-run evidence index
│   ├── DECISION_LOG.md        # decisions + open questions (process)
│   ├── HISTORY.md             # stage history + continuity rules
│   ├── WORKMAP.md             # 4-dimension academic frontier map (evaluation / verification / optimization / inference scaling)
│   └── figures/
├── paper/                     # manuscript skeleton + drafts
├── experiments/               # per-experiment evidence (EXPERIMENT.md + data)
├── results/                   # results layout (raw_outputs / judge_scores / analysis / figures)
├── scripts/                   # dump_project.py (and future reproduce.sh)
├── logs/                      # per-run logs (auto-generated)
└── output/                    # working-pipeline run artifacts (gitignored)
```

---

## Documentation index

| Document | Purpose |
|---|---|
| [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) | Research questions, theoretical framework (3-layer capability hypothesis, 3 math framings, cost–reliability model), experimental design, contributions, risks |
| [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) | Three-tier reproducibility, repo layout, seed management, config manifest, ablation matrix, checklist |
| [docs/TIMELINE.md](docs/TIMELINE.md) | 3 phases (probe → feasibility → full) + writing, budget, milestones, risk buffers |
| [docs/EVALUATION_STANDARD.md](docs/EVALUATION_STANDARD.md) | 3-tier scoring spec (T1 rule / T2 LLM rescue / T3 multi-judge), 19-leaf error taxonomy |
| [docs/INTERFERENCE_CAUSAL_TABLE.md](docs/INTERFERENCE_CAUSAL_TABLE.md) | INT-01…14 interference causal status |
| [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) | Evidence index (every claim traces to a run) |
| [docs/DECISION_LOG.md](docs/DECISION_LOG.md) | Decisions, open questions, working notes (not a deliverable) |
| [docs/HISTORY.md](docs/HISTORY.md) | Project stage history (finance pipeline → interference → metacognition) + continuity rules |
| [docs/WORKMAP.md](docs/WORKMAP.md) | 4-dimension academic frontier map (33 sources): evaluation / verification / optimization / inference scaling → proposal positioning |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Implementation blueprint for the experiment-execution layer (SQLite task queue, provider routing, phased landing plan) |
| [PROTOCOL.md](PROTOCOL.md) | How every change propagates to all dependent documents |

---

## Quick start

```bash
pip install -r requirements.txt

# Mini benchmark (3 tasks, rule-based agent, no API key)
python -m src.runner

# Score and analyze
python -m src.evaluator
```

**Phase-1 models** (Aliyun Token Plan, no local model loading): `deepseek-v4-flash-0731`, `qwen3.8-flash`, `glm-5.3` — see `PHASE1_MODELS` in `src/config.py`. Weak / strong tiers are deferred to Phase 2+.
**Benchmarks** (5 families × 50 Qs = 250): GSM8K, MATH-500, MMLU-Pro, FAB, BFCL.

```bash
# Phase-1 baseline: 3 mid models (Aliyun Token Plan) over the 5-family 250-Q probe set
python -m src.phase1_baseline
```

The legacy finance pipeline (`AGENTEVALUATION_AGENT=hf AGENTEVALUATION_BENCH=fab python -m src.runner`) is retained as one task-family module. Outputs: `output/trajectories.jsonl` (full per-step trajectory), `output/run_summary.csv`, `output/results.csv`, `output/error_report.json`, accuracy charts.

---

## Evaluation (v3.0 — three-tier scoring)

Correctness is dispatched into three tiers by answer form: **T1** deterministic rule/symbol match (no LLM), **T2** LLM-assisted parse + judge rescue (`deepseek-v4-pro`, only on T1-missed rows, off by default via `T2_RESCUE_ENABLED`), **T3** multi-LLM voting (finance uses `max(T1, T2)` rubric coverage as an interim). Full spec: [docs/EVALUATION_STANDARD.md](docs/EVALUATION_STANDARD.md).

---

## Reproducibility and change governance

- **Reproduce**: see [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) §5 (one-command reproduction).
- **Change**: when direction or conclusions change, follow [PROTOCOL.md](PROTOCOL.md) — every dependent document is revised in the same change.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| — | 2026-09-16 | Prior evaluation pipeline README. |
| 2.5 | 2026-10-05 | Aligned README with current state: three-tier scoring, 5-family 250-Q task set, Phase-1 Aliyun models; removed legacy `fingpt`/FinGPT agent references. |
| 2.4 | 2026-09-27 | Added docs/ARCHITECTURE.md (experiment-execution architecture blueprint). |
| 2.3 | 2026-09-26 | Added docs/WORKMAP.md (English frontier map, migrated from the agent-eval workmap; 33 sources). |
| 2.2 | 2026-09-26 | Migrated pipeline code to src/ package; added configs/ results/ logs/ data/{raw,processed}/; added MIT LICENSE. |
| 2.1 | 2026-09-26 | Renamed repository FinAgent → AgentEvaluation (project title, env-var prefix, SEC User-Agent, git remote). |
| 2.0 | 2026-09-26 | Reorganized into the research-repository structure; added docs/ index, PROTOCOL.md, reproducibility standard. |