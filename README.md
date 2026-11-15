# AgentEvaluation

Code, frozen scores and analysis for a placebo-controlled study of self-critique loops
("answer, read a critique of your answer, answer again"). The study separates two outcomes: whether a correct
answer appears among a method's answers (**reached**) and whether the method's most frequent answer is correct
(**selected**).

> Status (2026-11-15). Complete: three models (deepseek-v4-flash, qwen3.8-flash, MiniMax-M2.5) on 400 questions
> of Humanity's Last Exam, and an audit of 100 scored answers. The manuscript is in `paper/acl/` (version 13).
> No further experiments are planned. Start from **`docs/INDEX.md`**.

## What is here

| Path | Content |
|---|---|
| `paper/acl/` | Manuscript: `main.tex` (anonymous review build), `main_preprint.tex` (author build), `refs.bib`, figures, `make_figs.py`, revision log |
| `src/` | Experiment code: the loop and its methods (`run_feedback_loop.py`), the critic (`strong_critic.py`), model access (`agent.py`, `config.py`), scoring (`hle_scorer.py`, `score_hle_arms.py`, `evaluator.py`) |
| `scripts/` | Scoring pipelines, judges, and read-only analysis scripts that produce every number in the paper (`scripts/README.md` lists them by purpose) |
| `experiments/` | Run outputs. Per-round correctness and summary files are versioned; trajectories and judge verdicts are kept locally (see below) |
| `docs/` | Index, claims registry, specifications written before the runs, results, scoring protocol, project history |
| `audit/` | Audit of the automatic scoring (plan and results in `docs/HUMAN_AUDIT_PLAN.md`; sheets with benchmark questions are local only) |
| `data/` | Benchmark inputs (`data/raw/hle/`; other benchmarks were used only to build the restricted critic's error vocabulary) |
| `_deprecated/`, `*/_deprecated/` | Superseded material from earlier phases, kept for traceability; nothing there is used by the paper |

## Methods

| Name in the paper | Code | What the solver receives after its first answer (temperature 0) |
|---|---|---|
| First answer | `A` | nothing |
| Reassuring loop | `A2` | a fixed sentence: no problem was found |
| Generic-doubt loop | `A2P` | one to three generic doubts drawn from five fixed sentences; nothing is read and no model is called |
| Critique loop | `C2` | one to three suspicions written by a critic (the same model) that has read the question and the solver's reasoning |
| Independent samples | `A3` | nothing: nine independent samples at temperature 0.7 |
| Restricted critic (appendix only) | `C3` | as the critique loop, with the critic limited to a vocabulary of five error types |

Every loop starts from the same first answer, runs for at most ten rounds of feedback and stops after three
identical consecutive answers. Documents written before 2026-11-13 use earlier names (RP, PP, FC, SC, BC);
`docs/INDEX.md` gives the correspondence.

## Reproducing the paper's numbers

The analysis scripts read frozen files only and never call a model.

| Paper | Script |
|---|---|
| Main table and paired comparisons, deepseek and qwen | `scripts/two_model_tables.py` |
| Main table and paired comparisons, MiniMax-M2.5; the tests fixed in advance for the third model | `scripts/third_model_readout.py` |
| Means over the three models | `scripts/three_model_means.py` |
| Conversion, where selected questions come from, last answer against plurality answer | `scripts/search_not_verification.py` |
| Repeat probabilities, first revision, whether the critic hands over answers | `scripts/three_model_appendix.py` |
| Robustness of reach: second candidates, question format | `scripts/reach_quality_checks.py` |
| Selected questions under exact matching | `scripts/selected_exact_only.py` |
| Sampling at equal cost, the model as selector (deepseek) | `scripts/cost_matched_readout.py` |
| Comparison with studies that find voting ahead of revision | `scripts/reconcile_with_voting_literature.py` |
| Bound on vote splitting | `scripts/merge_correct_vote.py` |
| Same-model judges | `scripts/section5_headroom.py`, `scripts/judge_conditional_test.py` |
| Audit of the scoring | `scripts/human_audit_final.py` |
| Figures | `paper/acl/make_figs.py` |
| All numbers at once | `scripts/check_manifest.py` (checks `docs/consistency_manifest.json` against script outputs and `main.tex`) |

`docs/CLAIMS_REGISTRY.md` maps every claim in the paper to its evidence and states which analyses were fixed in
advance and which are exploratory.

**Data availability.** Per-round correctness (`experiments/hle400/t3/is_correct_t3_sidecar_{v3,rep,rep3,A3extra}.json`)
and summary files are in the repository. Trajectories (`loop_trajectories.jsonl`) and judge verdicts are not
committed: they are large and contain benchmark questions. Most scripts above need them; they will be released
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
`COST_MATCHED_SC_AND_USC_SPEC.md`, `THIRD_MODEL_SPEC.md`, `HUMAN_AUDIT_PLAN.md`. These documents were written before the corresponding runs and use the working names of the
methods (RP, PP, FC, SC, BC); `docs/INDEX.md` maps them to the names in the paper. Project history, including
the earlier phases of this repository (a finance-agent evaluation pipeline, an interference study, and an
error-guided elimination design that the controls in the paper did not support), is in
`docs/PROJECT_HISTORY.md` and `CHANGELOG.md`.

## License

MIT (see `LICENSE`).
