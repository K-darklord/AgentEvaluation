# Change-Propagation Protocol

> Living document · v1.0 · 2026-09-26
>
> This protocol governs how the repository stays internally consistent when the research direction changes or new experimental conclusions revise prior views. It is **normative**: every change must follow it.

---

## 1. Purpose and principles

1. **Single source of truth.** Every fact (a claim, a number, a decision, a method) is defined in exactly one authoritative document; all other documents reference it. Duplicated facts are prohibited.
2. **Propagation is mandatory.** When a fact changes, every document that derives from it must be revised in the same change, or explicitly marked superseded with a pointer. No silent divergence.
3. **Traceability.** Every revision is logged (Revision History / CHANGELOG / DECISION_LOG) and linked to evidence (`experiment-log record → config + seed → trajectories → git commit`).
4. **Review gate.** Structural changes (direction, method, contribution) require explicit review before execution; content revisions (numbers, wording) may proceed and are logged.
5. **Historical continuity.** Earlier research stages are preserved and never deleted; superseded results are marked, not removed. The stage history and continuity rules live in `docs/HISTORY.md`.

---

## 2. Trigger taxonomy

| Code | Trigger | Example |
|---|---|---|
| **T1** | Direction / scope change | change of research question, paper architecture, domain, benchmark substrate |
| **T2** | Conclusion change | a new experiment result revises a prior claim (e.g. the "26pp" figure is not reproduced at full scale) |
| **T3** | Method / model / config change | proxy design, model tiers, task families, metrics, scoring |
| **T4** | Process decision | venue, budget cap, repository home, compute/GPU, timeline |

---

## 3. Document graph (authoritative nodes)

| Document | Authoritative for | Depends on |
|---|---|---|
| `docs/RESEARCH_PLAN.md` | research questions, method, experimental design, contributions, risks | — |
| `docs/REPRODUCIBILITY.md` | reproducibility standard (seeds, configs, layout, checklists) | — |
| `docs/EVALUATION_STANDARD.md` | scoring methodology (2-tier, dealbreaker, error taxonomy) | — |
| `docs/INTERFERENCE_CAUSAL_TABLE.md` | interference evidence (INT-01…14 causal status) | `experiments/` |
| `docs/TIMELINE.md` | phases, milestones, budget | RESEARCH_PLAN |
| `docs/WORKMAP.md` | frontier literature map | — |
| `docs/EXPERIMENT_LOG.md` | per-run evidence index | `experiments/`, `configs/` |
| `docs/DECISION_LOG.md` | decisions, open questions, working notes | — |
| `docs/DOCS_FRAMEWORK.md` | the document system itself | — |
| `docs/HISTORY.md` | project stage history + continuity rules | — |
| `paper/` | manuscript (downstream of all) | all of the above |
| `CHANGELOG.md` | engineering changes | git |
| `README.md` | index / reproduction guide | all of the above |

---

## 4. Propagation matrix

| Trigger | Primary document(s) | Downstream revisions (in order) |
|---|---|---|
| **T1** direction | RESEARCH_PLAN (§0, §3, §4) + DECISION_LOG (log rationale) | WORKMAP (rescan frontier) → TIMELINE (rescale) → paper skeleton → README (index view) |
| **T2** conclusion | `experiments/<exp>/EXPERIMENT.md` + EXPERIMENT_LOG | INTERFERENCE_CAUSAL_TABLE (status) → RESEARCH_PLAN (claims / contributions / risks) → paper (affected section) → DECISION_LOG (note) |
| **T3** method | RESEARCH_PLAN (§3, §5) | REPRODUCIBILITY (new artifact / parameter) → EVALUATION_STANDARD (if scoring changes) → code → TIMELINE → EXPERIMENT_LOG |
| **T4** decision | DECISION_LOG | RESEARCH_PLAN / TIMELINE (if plan-affecting) → README (if structure changes) |

---

## 5. Revision procedure

1. **Identify** the primary change and its trigger code.
2. **Update** the primary authoritative document first.
3. **Propagate** to every downstream document per §4.
4. **Bump versions** and append to each document's Revision History.
5. **Reconcile** the evidence chain (§6) so every revised claim still points to a valid record.
6. **Commit** with a message naming the trigger and the documents touched, e.g. `[T2] revise 26pp claim after INT-12 | RESEARCH_PLAN, INTERFERENCE_CAUSAL_TABLE, paper`.

---

## 6. Evidence-chain integrity

A change to any claim invalidates downstream artifacts that depend on it. On any T2 (conclusion) change:

- re-run or re-derive the affected figures/tables, or explicitly mark them stale;
- if a conclusion is reversed, **do not delete** the old record — mark it superseded and point to the new experiment-log record;
- the manuscript must never cite a number whose experiment-log record no longer exists.

---

## 7. Failure modes this protocol prevents

- **Drift** — RESEARCH_PLAN updated, but paper and TIMELINE still describe the old design.
- **Orphaned claims** — a figure survives whose underlying experiment was disproven.
- **Forked truth** — the same fact stated differently in two documents.
- **Lost rationale** — a direction change with no record of why (needed for review rebuttals).

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Initial protocol. |