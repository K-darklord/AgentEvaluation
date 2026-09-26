# Experiment Log

> Living document — one record per experiment (or per run, when runs must be distinguished). This is the **evidence index** for the paper: every claim must trace back to a record here (see `../PROTOCOL.md` §6).

**Record template** (from `REPRODUCIBILITY.md` §6):

```markdown
## [YYYY-MM-DD] {name}
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

## Existing experiments (finance / interference pilot)

| Date | ID | Experiment | Status | Evidence home |
|---|---|---|---|---|
| 2026-09-16 | INT-05 | max_steps 25→50 | confirmed (+6pp) | `experiments/20260916_int05_max_steps/` |
| 2026-09-16 | INT-06 | T2 trajectory 4000→20000 chars | minimal (+2pp) | `experiments/20260916_int06_context_length/` |
| 2026-09-16 | INT-07 | judge V4-Flash→V4-Pro | paused (cost) | `experiments/20260916_int07_judge_bias/` |
| 2026-09-16 | INT-12 | transparent budget + no fallback | planned | `experiments/20260916_int12_transparent_budget/` |
| 2026-09-16 | v3-full | 50-task full run | baseline 48% | `experiments/20260916_v3_50task_full/` |
| 2026-09-16 | v3-fix | interference-fixed run | 60% (5-Q validation) | `experiments/20260916_v3_interference_fix/` |

> These predate the current `configs/*.yaml` standard (configs were inline in `config.py`); their `EXPERIMENT.md` files remain the authoritative record. New experiments must follow the template above.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Created; indexed existing interference experiments. |