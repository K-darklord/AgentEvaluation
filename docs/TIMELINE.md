# Timeline

> Version 1.3 · 2026-10-07

---

## 1. Roadmap

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

## 2. Phase 1 — probe: end-to-end feasibility (COMPLETE → PHASE1_SUMMARY.md)

**Budget**: < $200. **Models**: 3 mid-tier via Aliyun Token Plan — deepseek-v4-flash-0731, qwen3.8-flash, glm-5.3; **no local model loading**; strong tier deferred to Phase 2/3. **Tasks**: 250 Qs — GSM8K 50 + MATH-500 50 + MMLU-Pro 50 + FAB 50 + BFCL 50 (L1:L2 = 3:2).

The authoritative Phase-1 plan (four feasibility checks, build-before-burn order, N=10 in 3-round
segments, no-human-labelling validation) is `docs/RESEARCH_PLAN.md` §5.7. Milestones:

- **Foundations (no API cost)** — capability-matrix definition + decomposition check against d1_baseline; per-domain error taxonomy + Top-K signal generator + prior-weighted update; validated by deterministic rules and outcome-based next-round improvement, not human labelling.
- **Multi-round feedback (N=10, 3-round segments)** — advance the loop in ~3-round segments; after each segment inspect activation/locking for signal-driven change before spending the next.
- **Analysis + decision** — L3/L4 discrimination from round-dimension events; fit cost–reliability curves (k classification); write the go/no-go report. pass → Phase 2; fail → adjust evaluator (template / K / prior) and rerun at most twice before reassessing direction.

---

## 3. Phase 2 — feasibility (planned; PHASE1_SUMMARY.md §8)

**Budget**: < $1,200. **Models**: mid tier (reused) + weak tier (qwen3.6-flash, glm-4.7-flash via rented Aliyun instance) + strong tier (strongest runnable, channel TBD). **Tasks**: core 5 families + hard-L1 (GPQA-Diamond) + a second light-FC family.

- **Prep (Day 4–6)**: unified model interface; control arms A / A2 / C; FC-carrier ablation; task-set expansion (difficulty-calibrated); weak-critic recalibration.
- **Main (Day 7–11)**: baseline (1 round) + evaluator feedback (5 rounds) across 8–10 models × 5–8 classes; daily data-integrity checks.
- **Ablations (Day 12–14)**: no-evaluator self-loop, random feedback, uniform prior, no voting, different K.
- **Analysis (Day 15–18)**: statistical comparison across arms; metric summaries; visualizations; phase report + decision.
  - all pass → Phase 3; partial (only specific tasks) → narrow scope, enter a reduced Phase 3; fail → analyze cause, consider a methodology paper.

---

## 4. Phase 3 — full experiment (Day 19–60)

**Budget**: < $8,000. **Models**: 12–15. **Tasks**: 12–15 classes, L2/L3 share ≥ 40%.

- **Prep (Day 19–25)**: deploy all models (open-source + API); prepare 12–15 task classes (incl. dynamically generated L3); complete the ablation matrix (8–10 arms); build the tensor-decomposition pipeline.
- **Experiment (Day 26–45)**: 12–15 models × 12–15 classes × (baseline + 8–12 feedback rounds); full ablation matrix; daily integrity checks.
- **Analysis (Day 46–60)**: tensor decomposition → latent dimensions; cost–reliability curve fitting (per model × task); ideal-upper-bound modelling + extrapolation validation; cross-task structural analysis; full report.

---

## 5. Writing & submission (Day 61–90)

- **Drafting (Day 61–75)**: Introduction, Related Work, Method (evaluator design + decoupling theory), Experiments, Results + Discussion, Conclusion + Limitations.
- **Revision (Day 76–85)**: internal review; extra analyses a reviewer might demand; language polish; format to the target venue template.
- **Submission (Day 86–90)**: appendix (full config tables + ablation details); code repository; submit.

---

## 6. Milestones and checkpoints

| Day | Milestone | Deliverable | Decision |
|---|---|---|---|
| 3 | Phase 1 done | probe report | proceed to Phase 2? |
| 18 | Phase 2 done | feasibility report | proceed to Phase 3? |
| 60 | Phase 3 done | full report | start writing? |
| 90 | submit | paper + appendix + code | submitted |

---

## 7. Buffers and risk response

| Risk | Response | Buffer |
|---|---|---|
| Phase 1 needs a rerun | 1–2 days for adjustment | Day 3–4 |
| Phase 2 model-deploy delay | rent Aliyun instance / resolve strong-tier channel | Day 4–6 |
| Phase 3 API over-budget | cut top API models' question load; replace with local large models | budget elasticity |
| Tensor decomposition unclear | fall back to direct curve comparison (2–3 days) | Day 46–48 |
| Writing lag | shrink to an 8-page workshop version | Day 76–80 |

---

## 8. Parallel work (while experiments run)

| Task | Window |
|---|---|
| Related-work draft | Phase-2 experiment window |
| Target-venue list | Phase-2 analysis window |
| GitHub repo scaffold | throughout |
| Figure templates | Phase-3 experiment window |

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Translated to English. |
| 1.1 | 2026-09-27 | Phase-1 probe revised: 4 models (weak local ×2, mid API ×2, strong deferred), tasks expanded to math/logic/finance 50 each. |
| 1.3 | 2026-10-07 | Phase 1 complete (all Aliyun, no local); Phase 2 plan consolidated in PHASE1_SUMMARY.md §8 (control arms, weak tier via rented Aliyun instance, strong tier TBD, task expansion, k/θ cost curves). |
| 1.2 | 2026-09-29 | Phase-1 probe re-scoped to an end-to-end feasibility loop (per RESEARCH_PLAN §5.7): 3 mid models via Aliyun, 250-Q probe set, N=10 feedback in 3-round segments, build-before-burn, no human labelling. |