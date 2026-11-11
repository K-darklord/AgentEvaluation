# File Audit & Doc-Sync Playbook

**Document type**: process · **Version**: 1.0 · **Date**: 2026-10-07
**Companion**: `PROTOCOL.md` (change propagation), `DOCS_FRAMEWORK.md` (document inventory).

---

## 1. Purpose

This playbook records the *habits and rules* that keep the repository internally consistent as the
research program moves. It exists because drift accumulates silently: documents stop matching code,
filenames go stale, and dependencies lag the implementation. The rules below are normative; the
findings section (§5) is a historical log of the 2026-10-07 audit.

---

## 2. Rule 1 — Sync on every push

Every time a functional change is committed and pushed, the author must update dependent materials
in the **same** change, not a later one. The trigger is any of:

- **A conclusion changes** (numbers, claims, results) → update `RESEARCH_PLAN` claims, `PHASE1_SUMMARY`
  results/§7, `WORKMAP` gap, and any figure/table that cites the old number.
- **A method/config changes** (model tier, channel, scoring, task family) → update
  `EVALUATION_STANDARD`, `REPRODUCIBILITY`, `config.py`, and the module config (`configs/*.yaml`).
- **A file is added/removed/renamed** → update `README` index, `DOCS_FRAMEWORK` inventory, `PROTOCOL`
  document graph, and `requirements.txt` if the change adds/removes a dependency.
- **A dependency changes** → update `requirements.txt` **and** confirm nothing else imports the removed
  package (grep the repo before removing).

## 3. Rule 2 — Periodic scan (checklist)

Before a milestone commit / tag, or on request, run this sweep and fix every item found:

1. **Names**: every file/dir name reflects its current role (no typos, no superseded stage names).
2. **Version/date headers**: each deliverable's header and Revision History are current.
3. **Cross-references**: `README` index ↔ `DOCS_FRAMEWORK` inventory ↔ `PROTOCOL` graph list the same
   authoritative documents.
4. **Dependencies**: `requirements.txt` matches the union of `import`/`from` in `src/` + `scripts/`;
   no dead (local-inference) or missing (`pyyaml`, `openai` pin) packages.
5. **Dead code**: any class/function/config left over from a superseded stage (grep its symbol; if the
   only references are its own definition + a legacy branch, remove it).
6. **Legacy scaffolds**: config files / entrypoints for an earlier architecture that was never shipped.

## 4. Rule 3 — Single source of truth

- Any fact lives in exactly one authoritative document; everywhere else references it.
- Duplicated facts (the same number/decision described in two files) are a defect — merge to one and
  reference it.
- Stage history (`HISTORY.md`) and engineering history (`CHANGELOG.md`) are **append-only**; superseded
  results are marked superseded, never silently rewritten or deleted.
- Experiment evidence under `experiments/` is the paper's reproducibility chain; prune it only after
  confirming no downstream claim/`EXPERIMENT.md` points at it.

## 5. Findings log — 2026-10-07 audit

Root causes observed (each produced a class of drift):

1. **Channel migration not propagated** — HF router → Aliyun Token Plan was recorded in `CHANGELOG`
   and `config.py`, but `PHASE1_SUMMARY` §7/§9 still said the run used "HF router (free tier)", and
   `configs/fab_baseline.yaml` still named the HF model id `deepseek-ai/DeepSeek-V4-Flash`. Lesson:
   channel/model changes must touch every doc that names the endpoint.
2. **Deprecated local route left in code + deps** — the FinGPT local-LoRA path (`src/agent.py`
   `FinGPTAgent`, `src/config.py` `FINGPT_*`, `src/runner.py` `fingpt` branch) stayed after local
   loading was abandoned, so `requirements.txt` kept `torch/transformers/peft/...`. Lesson: when a
   route is abandoned, remove the code *and* the dependency in the same change.
3. **New authoritative doc not registered** — `PHASE1_SUMMARY.md` became the Phase-1+Phase-2 authority
   but was missing from `README`, `DOCS_FRAMEWORK`, and `PROTOCOL`. Lesson: a new deliverable must be
   registered in all three indexes immediately.
4. **Stale facts in the graph** — `PROTOCOL` still said "scoring methodology (2-tier)" after the
   3-tier re-scope, and `INT-01…14` after the range grew to `INT-16`. Lesson: a re-scope updates the
   governance graph, not just the spec.
5. **Layer count not propagated** — the capability hypothesis went 3-layer → 4-layer (L1–L4); `README`
   still described "3-layer". Lesson: a conceptual rename/re-number must be grepped repo-wide.
6. **Naming drift** — `configs/fab_baseline.yaml` describes a FAB-only multi-seed baseline that the
   final 5-family / temperature-0 probe superseded. Lesson: rename/remove a config the moment the
   experiment it drives is re-scoped.

Fixed in the 2026-10-07 batch (commit `7d47469`, tag `phase1-docs-alignment-v0.17`): requirements,
README, PHASE1_SUMMARY, TIMELINE, RESEARCH_PLAN §6.1, DOCS_FRAMEWORK, PROTOCOL.

Resolved in the follow-up cleanup batch: `CHANGELOG.md` Phase-1 entries added; FinGPT local path
(`agent.py`/`config.py`/`runner.py`) removed; `configs/fab_baseline.yaml` removed; superseded
`d1_baseline_*` runs archived to `experiments/archive/superseded_d1_baseline_20261007.tar.gz`
(one-off scripts kept in `src/` per continuity).

## 6. Remaining debt (pending)

No outstanding items as of 2026-10-07. The last entry — `src/experiment.py` + `configs/*` scaffolding —
was removed after confirmation (2026-10-07); the now-unused `pyyaml` dependency went with it.
