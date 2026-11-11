# AgentEvaluation

Code, frozen scores and analysis for a placebo-controlled study of self-critique loops:
**where do the gains of "answer, criticize yourself, answer again" come from: iteration, pressure, or the
content of the critique, and do they show up in what a loop *reaches* or in what it *selects*?**

> Status (2026-11-11). The manuscript draft is in `paper/acl/` (ACL template). Two models are complete
> (deepseek-v4-flash, qwen3.8-flash) on 400 items of Humanity's Last Exam; a pre-registered run on a third
> model and a human audit of the scoring are in progress. Start from **`docs/INDEX.md`**.

## What is here

| Path | Content |
|---|---|
| `paper/acl/` | Manuscript (`main.tex`, `refs.bib`, figures, `make_figs.py`); `main.pdf` is the anonymous review build |
| `src/` | Experiment code: the revision loop and its conditions (`run_feedback_loop.py`), the critic (`strong_critic.py`), model access (`agent.py`, `config.py`), scoring (`hle_scorer.py`, `score_hle_arms.py`, `evaluator.py`), error-vocabulary distillation (`build_*`) |
| `scripts/` | Scoring pipelines, judges, and read-only analysis scripts that produce every number in the paper |
| `experiments/` | Run outputs. Small summary and score files are versioned; trajectories and judge verdicts are kept locally (see below) |
| `docs/` | Index, claims registry, pre-registered specifications, results, scoring protocol, project history |
| `audit/` | Human audit of the scoring (plan in `docs/HUMAN_AUDIT_PLAN.md`; annotation sheets are local only) |
| `data/` | Benchmark inputs (`data/raw/hle/` item sets; other benchmarks used only to distil the error vocabulary) |
| `_deprecated/`, `*/_deprecated/` | Superseded material from earlier phases, kept for traceability; nothing there is used by the paper |

## Conditions

| Paper name | Code | Feedback after the greedy first answer |
|---|---|---|
| Greedy | `A` | none |
| Reassuring placebo (RP) | `A2` | fixed sentence: no error direction found |
| Perturbing placebo (PP) | `A2P` | 1–3 templated suspicions, nothing is read, no model call |
| Bank critic (BC) | `C3` | 1–3 suspicions from a five-archetype error vocabulary |
| Free critic (FC) | `C2` | 1–3 suspicions in the critic's own words |
| Self-consistency (SC) | `A3` | none: independent samples at temperature 0.7 |

All loops share the greedy first answer, stop after three identical consecutive answers or ten feedback
rounds, and use one model as solver and critic.

## Reproducing the paper's numbers

The analysis scripts read frozen files only and never call a model.

| Paper | Script |
|---|---|
| Main table, candidate-matched and exact-match ceilings, paired tests (both models) | `scripts/two_model_tables.py` |
| Cost-matched self-consistency, universal self-consistency, pooled tests | `scripts/cost_matched_readout.py` |
| Persistence table, recency tie rule, suspicions per round | `scripts/persistence_and_settle.py` |
| Pooling bound, format-normalized vote | `scripts/merge_correct_vote.py`, `scripts/vote_latex_normalized.py` |
| Adaptive self-consistency, first-round repair and damage | `scripts/tie_and_adaptive_baselines.py` |
| Abstention curves, simulated external verifier | `scripts/selective_prediction.py`, `scripts/verifier_regimes.py` |
| Same-model judge audit | `scripts/judge_conditional_test.py` |
| Statistics added after review (bank critic against placebos, interactions, truncation, leak check) | `scripts/review_fixes_stats.py` |
| Figures | `paper/acl/make_figs.py` |

`docs/CLAIMS_REGISTRY.md` maps every claim in the paper to its evidence and states whether the analysis was
pre-specified; `docs/consistency_manifest.json` lists the paper's numbers with their sources.

**Data availability.** Per-round correctness (`experiments/hle400/t3/is_correct_t3_sidecar_*.json`) and
summary files are in the repository. Trajectories (`loop_trajectories.jsonl`) and judge verdicts are not
committed: they are large and contain benchmark questions. The scripts above need them; they will be released
with the paper.

## Running the experiments

```bash
pip install -r requirements.txt          # some scripts also use sympy, pyarrow and httpx
# create .env with the API keys read in src/config.py (TOKEN_PLAN_API_KEY, DASHSCOPE_API_KEY, ...)

# one condition
python3 src/run_feedback_loop.py --models <registry name> --task-set hle --arm C2 \
    --max-rounds 10 --early-stop 3 --rationale-mode off --temperature 0 --out-dir <name>

# all conditions for one model (greedy first answer, then the loops, then sampling)
MODEL=<registry name> bash scripts/run_replication.sh
```

Models are registered in `src/config.py`. Runs must follow the rules in the pre-registered specifications:
a trajectory containing a failed interface call is invalid and is rerun in full, and an error message never
counts as an answer.

## Scoring

Every answer of every round is scored once: truncated rounds are incorrect; otherwise exact match after
type-specific normalization; unmatched answers are judged by an independent model from a different provider;
disputed answer variants are adjudicated so that the same substance receives the same verdict in every
condition. Details: `docs/HLE_SCORER.md` (protocol), `docs/HLE400_FROZEN_DATA.md` (frozen files and versions).

## Documentation

`docs/INDEX.md` is the entry point. Pre-registered specifications: `C2_BANK_FREE_CRITIC_SPEC.md`,
`A2PRIME_PERTURBING_PLACEBO_SPEC.md`, `EVALUATOR_FINAL_DESIGN.md`, `REPLICATION_SPEC.md`,
`COST_MATCHED_SC_AND_USC_SPEC.md`, `THIRD_MODEL_SPEC.md`, `HUMAN_AUDIT_PLAN.md`. Project history, including
the earlier phases of this repository (a finance-agent evaluation pipeline, an interference study, and an
error-guided elimination design that the controls in the paper did not support), is in
`docs/PROJECT_HISTORY.md` and `CHANGELOG.md`.

## License

MIT (see `LICENSE`).
