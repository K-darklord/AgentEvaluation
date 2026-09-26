# Project History

> This file preserves the **continuity** of the research program. Stages are never deleted; superseded results are marked, not removed. Every stage links to its surviving evidence.

> **Repository rename (2026-09-26).** This repository was formerly named **FinAgent** and is now **AgentEvaluation**, reflecting the metacognitive-evaluation program. The "FinAgent" era (Stage 0) is retained below as history, not deleted. Frozen experiment logs under `experiments/` keep their original absolute paths (`…/PycharmProjects/FinAgent/…`) as immutable evidence.

---

## Stage 0 — Finance-agent evaluation pipeline ("FinAgent", renamed "AgentEvaluation")

**Period**: 2026-09-11 → 09-13
**Objective**: build a working financial-agent evaluation pipeline on real benchmark data.

What was built:

- Task schema + mini benchmark + FAB public loader (`benchmark.py`)
- Agents: rule-based / FinGPT / OpenAI / HuggingFace ReAct + EDGAR tools (`agent.py`)
- Main loop + trajectory recording (`runner.py`)
- 2-tier continuous scoring + dealbreaker (`evaluator.py`)

Milestones: `v0.1-skeleton` → `v2.1` (accuracy 8.3% → 34% via bug fixes).

**Status**: preserved as the finance **task-family module** of the current program.

---

## Stage 1 — Evaluation-framework interference ("26pp spurious deficit")

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

## Stage 2 — Metacognitive evaluation (current)

**Period**: 2026-09-26 → present
**Objective**: redefine capability from single-shot accuracy into **cost–reliability + convergence**, and diagnose *which* capability a model lacks via an external meta-cognitive proxy.

- `docs/RESEARCH_PLAN.md` — experiment protocol
- `docs/REPRODUCIBILITY.md`, `docs/TIMELINE.md`, `docs/EXPERIMENT_LOG.md`
- `PROTOCOL.md` — change-propagation governance

**Continuity**: Stage 1's interference evidence is retained as the introduction motivation; the finance pipeline is retained as one cross-domain task family.

---

## Continuity rules (normative)

1. A stage is never deleted; it is only ever extended by a newer stage.
2. A superseded result is marked `superseded` and points to its replacement — never silently removed.
3. Any revision of a claim follows `PROTOCOL.md` §6 (evidence-chain integrity).

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.1 | 2026-09-26 | Recorded repository rename FinAgent → AgentEvaluation. |
| 1.0 | 2026-09-26 | Created; records Stages 0–2 and the continuity rules. |