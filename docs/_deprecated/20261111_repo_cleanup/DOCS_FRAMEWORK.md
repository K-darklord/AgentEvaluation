# Document System (Version 0.9)

> **Scope**: defines *which* documents exist, their register, how they are versioned, and how they map to the paper and code. It is itself part of the living-document system.
>
> **Two registers** (strict separation):
> - **Academic deliverables** — written for future reproducers and scholarly review; no process / discussion content.
> - **Process logs** — decisions, open questions, and working notes; never copied into the deliverables.
>
> **Repository home**: this AgentEvaluation repository is the canonical home of the research program; the separate `metacog-research/` drafting directory is superseded.

---

## 1. Core insight

Information was scattered across two places and has now been unified into this repository:

- **The source attachments** — RP outline + workmap + experiment summary + timeline + reproducibility standard (the *metacognition* vision);
- **The AgentEvaluation code** — `src/agent.py` / `src/evaluator.py` / `src/runner.py` + the existing `EVALUATION_STANDARD.md`, `CHANGELOG.md` (the *interference + evaluation* status quo).

---

## 2. Document inventory

### A. Academic deliverables (authoritative)

| Document | Register | Responsibility | Location |
|---|---|---|---|
| **RESEARCH_PLAN.md** | academic | experiment protocol (authoritative for research questions, method, experimental design, contributions, risks) | `docs/RESEARCH_PLAN.md` |
| **PHASE1_SUMMARY.md** | academic | Phase 1 (probe) results + Phase 2 plan (weak critic, six end-states, activation/locking, cost–reliability + risk) | `docs/PHASE1_SUMMARY.md` |
| **PHASE2_SUMMARY.md** | academic | Phase 2 (RSI) live summary — EGTE re-anchoring (§13), experiment path (§14: fix C → deepseek-first → glm/qwen + more families) | `docs/PHASE2_SUMMARY.md` |
| **PROTOCOL.md** | academic (governance) | change-propagation rules (which documents change when) | `PROTOCOL.md` |
| **REPRODUCIBILITY.md** | academic | top-venue reproducibility standard (three-tier, layout, seeds, config manifest, checklist) | `docs/REPRODUCIBILITY.md` |
| **TIMELINE.md** | academic | phases, milestones, budget, risk buffers | `docs/TIMELINE.md` |
| **EVALUATION_STANDARD.md** | academic | 3-tier scoring spec (T1/T2/T3) + finance-path detail | `docs/EVALUATION_STANDARD.md` |
| **ERROR_TAXONOMY.md** | academic | 19-leaf error taxonomy (leaf → literature anchor → rule → 6 middle axes) + L1–L4 separation | `docs/ERROR_TAXONOMY.md` |
| **INTERFERENCE_CAUSAL_TABLE.md** | academic (evidence) | INT-01…16 interference causal status | `docs/INTERFERENCE_CAUSAL_TABLE.md` |
| **EXPERIMENT_LOG.md** | academic (evidence) | per-run evidence index (config/seed/model/status/commit) | `docs/EXPERIMENT_LOG.md` |
| **WORKMAP.md** | academic | frontier literature map + proposal gap (52 sources; EGTE re-anchored) | `docs/WORKMAP.md` |
| **manuscript draft** | academic | full manuscript draft (EGTE definition, roles, objective, arms, scoring standard, results, research questions) | `docs/PAPER_DRAFT.md` |
| **paper skeleton** | academic | manuscript skeleton + three contribution claims + figure/table placeholders | `paper/paper_outline.md` |
| **paper deck** | academic | slide content & layout (P1–P8), aligned to the outline + draft | `paper/paper_ppt.md` |
| **data registry** | academic | dataset version / source / sha256 / license | `data/README.md` (to create) |
| **ARCHITECTURE.md** | academic (implementation) | code-architecture blueprint for the experiment-execution layer, sized to the Phase-3 workload | `docs/ARCHITECTURE.md` |
| **ablation matrix** | academic | ablations (rule out alternative explanations) | `configs/ablation/` (to create) |

### B. Process logs (not deliverables)

| Document | Register | Responsibility | Location |
|---|---|---|---|
| **DECISION_LOG.md** | process | decisions, open questions, working notes | `docs/DECISION_LOG.md` |
| **CHANGELOG.md** | process | engineering change record (what changed) | repo root |
| **budget tracker** | process | per-run API cost + cumulative | `docs/` (internal) |
| **compute notes** | process | hardware / engine / measured throughput | `docs/` (internal) |
| **FILE_AUDIT.md** | process | file-audit & doc-sync playbook (sync-on-push, periodic scan) | `docs/FILE_AUDIT.md` |

---

## 3. Versioning and iteration rules

- **Semantic versioning** `vX.Y`: X = structural change (new phase / contribution), Y = content revision.
- **Fixed header** on every deliverable: version + date + status.
- **Git discipline**: one commit per experiment (`[EXP] name | config=… | seed=…`); milestone tags (`exp-{phase}-{date}`).
- **Single source of truth**: any fact is defined in exactly one document and referenced elsewhere; reconcile conflicts immediately.
- **Change propagation**: governed by `PROTOCOL.md`; a change to any fact must be propagated to all dependent documents in the same revision.

---

## 4. Document → paper/code mapping

| Document | Paper landing | Code landing |
|---|---|---|
| RESEARCH_PLAN | Method + Experiments | `configs/` design rationale |
| PROTOCOL | (governance) | — |
| REPRODUCIBILITY | Appendix + Supplementary | `README` + `scripts/reproduce.sh` |
| TIMELINE | (planning) | — |
| EVALUATION_STANDARD | Method (scoring) | `src/evaluator.py` |
| INTERFERENCE_CAUSAL_TABLE | Introduction motivation | Appendix evidence |
| EXPERIMENT_LOG | Appendix reproducibility evidence | `experiments/` |
| WORKMAP | Related Work | — |
| paper skeleton | full manuscript skeleton | — |
| data registry | Appendix data statement | `data/README.md` |
| ablation matrix | Experiments tables | `configs/ablation/` |
| DECISION_LOG | — (internal) | — |

---

## 5. Evidence-chain convention

Every claim that feeds the paper must be traceable:

```
claim (paper) → experiment-log record → config + seed → raw trajectories → code version (git commit)
```

- A claim without an experiment-log record is not allowed in the manuscript.
- A result figure/table cites its experiment-log ID and git commit.
- Raw artifacts live under `results/` (target) / `experiments/` (current) with a per-run manifest.

---

## 6. Pending migrations

1. Migrate the workmap HTML/PDF → `docs/WORKMAP.md` under version control.
2. Add a `LICENSE` file (license choice is a process decision — see DECISION_LOG).
3. ~~Migrate the flat finance pipeline into `src/`~~ — **done (2026-09-26)**: `src/` now holds `benchmark.py`, `agent.py`, `runner.py`, `evaluator.py`, `config.py`. Remaining: split into `src/{models,evaluator,experiment,analysis,judge,utils}/` and convert `config.py` → YAML as the Phase-1 framework matures.
4. Create `configs/*.yaml`, `results/`, `logs/`, and `data/raw|processed/` scaffolding.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-26 | Initial document system. |
| 0.2 | 2026-09-26 | Introduced the academic/process register separation. |
| 0.4 | 2026-09-27 | Registered docs/ARCHITECTURE.md (experiment-execution implementation blueprint). |
| 0.3 | 2026-09-26 | Aligned to the AgentEvaluation repository (canonical home); added PROTOCOL / TIMELINE / EXPERIMENT_LOG / EVALUATION_STANDARD / INTERFERENCE_CAUSAL_TABLE to the inventory; updated pending migrations. |
| 0.6 | 2026-10-07 | Registered PHASE1_SUMMARY.md as the authoritative Phase-1 + Phase-2 summary; WORKMAP now 36 sources (no longer pending). |
| 0.5 | 2026-10-05 | EVALUATION_STANDARD re-scoped to 3-tier; added ERROR_TAXONOMY.md to the inventory; INTERFERENCE_CAUSAL_TABLE range extended to INT-16. |
| 0.7 | 2026-10-07 | Registered FILE_AUDIT.md (file-audit & doc-sync playbook) in the process-logs register. |
| 0.8 | 2026-10-21 | Re-anchored WORKMAP (52 sources) and registered PHASE2_SUMMARY.md; named the mechanism Error-Guided Test-Time Elimination (EGTE). |
| 0.9 | 2026-10-27 | Registered `docs/PAPER_DRAFT.md` (manuscript draft) and `paper/paper_ppt.md` (slide deck); fixed stale header version (0.7 → 0.9). |