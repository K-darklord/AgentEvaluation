# Timeline

> Version 1.0 · 2026-09-26

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

## 2. Phase 1 — probe experiment (Day 1–3)

**Budget**: < $50. **Models**: 6 across three tiers (Qwen2.5-1.5B, TinyLlama-1.1B, Qwen2.5-7B, Llama-3.1-8B, GPT-4o-mini, Claude-3-Haiku). **Tasks**: math reasoning 20 Qs + logic puzzles 20 Qs (incl. L2–L3 level).

**Day 1 — environment + baseline**: build the experiment framework (code structure, config management, logging); deploy 4 local models (vLLM); configure API keys; run the 6-model × 40-Q baseline. *Acceptance*: baseline sanity (weak models clearly below strong).

**Day 2 — evaluator + feedback**: implement the minimal evaluator (round-1 error stats → Top-K feedback); run 6 models × 40 Qs × 3 feedback rounds; add a random-feedback control arm. *Acceptance*: all 4 rounds of outputs saved for every model × question.

**Day 3 — analysis + decision**: compute activation rate / first-activation round / locking rate; Fisher's exact test + visualization; write the phase report and decide.
- pass → prepare Phase 2; fail → adjust evaluator (template / K / prior) and rerun (1–2 days); fail twice → reassess direction.

---

## 3. Phase 2 — feasibility (Day 4–18)

**Budget**: < $1,200. **Models**: 8–10 (Phase-1 six + Mistral-7B, Gemma-2-9B + some GPT-4o). **Tasks**: 5–8 classes, 50–100 Qs each.

- **Prep (Day 4–6)**: unified model interface; deploy new local models; prepare 5–8 task classes (difficulty-calibrated); implement 6 ablation arms.
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
| Phase 2 model-deploy delay | local models first, API later | Day 4–6 |
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