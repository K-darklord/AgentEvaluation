# scripts/

Names in the code are the working names: `A` first answer, `A2` reassuring loop, `A2P` generic-doubt loop,
`C2` critique loop, `A3` independent samples, `C3` restricted critic; `ceiling`/`reach` = reached,
`sel`/`mode` = selected, `fin` = last, `stay` = repeat probability, `astra` = the grader. See `docs/INDEX.md`.

Run everything from the repository root. Scripts in groups 1 and 2 read frozen files and never call a model.

## 1. Analyses reported in the paper
| Script | Produces |
|---|---|
| `two_model_tables.py` | Main table, paired comparisons, robustness of reach: deepseek, qwen (`two_model_scores.json`) |
| `third_model_readout.py` | The same for MiniMax-M2.5 and the tests fixed in advance, P1, P2, S1-S5 (`third_model_readout.json`) |
| `three_model_means.py` | Means over three models of the differences in selected questions (`three_model_means.json`) |
| `search_not_verification.py` | Conversion; where selected questions come from; last answer against plurality answer (`search_not_verification.json`) |
| `three_model_appendix.py` | Repeat probabilities, first revision, whether the critic hands over answers, first answers cut off (`three_model_appendix.json`) |
| `persistence_and_settle.py` | Intervals of the repeat probabilities (deepseek; `SIDECAR=` selects another file) |
| `reach_quality_checks.py` | Second candidates; reach by question format |
| `selected_exact_only.py` | Selected questions when only exact matches count (`selected_exact_only.json`) |
| `cost_matched_readout.py` | Eleven samples at equal cost; the model as selector (deepseek) |
| `reconcile_with_voting_literature.py` | Loop against vote under different read-outs, answer formats and difficulty |
| `merge_correct_vote.py` | Bound on vote splitting (deepseek) |
| `section5_headroom.py`, `judge_conditional_test.py` | Same-model judges (`section5_headroom.json`) |
| `human_audit_final.py` | Result of the scoring audit (`audit/human_audit_20261111/audit_final.json`) |
| `check_manifest.py` | Checks `docs/consistency_manifest.json` against the outputs above and `paper/acl/main.tex` |

## 2. Analyses from earlier versions, not in the current paper
`review_fixes_stats.py` (restricted critic against the placebo loops, interactions), `tie_and_adaptive_baselines.py`,
`selective_prediction.py`, `verifier_regimes.py`, `vote_latex_normalized.py`, `ceiling_at_matched_k.py`,
`paired_expected_score_tests.py`, `lr_vote.py`, `switch_contrast.py`, `gen_replication_results.py` (writes
`docs/REPLICATION_RESULTS.md`).

## 3. Scoring pipeline (writes the per-round correctness files)
| Script | Role |
|---|---|
| `recompute_evaluator_offline.py` | Answer identity (which answers count as the same candidate); imported by most analyses |
| `gen_t3_sidecar_v3.py`, `gen_t3_sidecar_rep.py`, `gen_t3_sidecar_rep3.py` | Per-round correctness for deepseek, qwen, MiniMax-M2.5 |
| `a2p_k1_sidecar.py`, `c2_k1_sidecar.py`, `s1_a3extra_k1_sidecar.py` | Grader pass for the generic-doubt loop, the critique loop and samples 10-11 |
| `t3_k3_adjudicate_and_recompute.py`, `t3_k3_recompute_v3.py` | Adjudication of disputed answers and recomputation |
| `recompute_evaluator_node.py`, `score_rubric_ce_readouts.py` | Read-outs of the first same-model judge |

## 4. Runs (call models; need API keys)
`run_replication.sh` (all methods for one model), `s1_a3_extra.py` (samples 10-11), `s2_usc.py`, `reparse_usc.py`,
`rerun_usc_stale.py`, `rerun_api_failures.py`, `judge_c.py`, `qcut_run.py`, `qcut_judge_v2.py`, `qcut_premise.py`,
`qcut_fill_result.py`, `e2_c2_critic_token_replay.py`, `e2_c2_critic_token_replay_qwen.py`,
`e2_c3_critic_token_replay.py` (critic token counts), `gate_16_candidates.py` (16-question run-health check for
third-model candidates), `probe_candidates.py`, `probe_endpoints.py`, `probe_thinking_budget.py`.

## 5. Data and audit preparation
`build_hle_400_set.py` (the 400 questions; seed 42), `build_hle_150_set.py` (earlier set);
`human_audit_sample.py`, `human_audit_make_sheets.py`, `human_audit_cas_checks.py`, `human_audit_milp_check.py`,
`human_audit_make_discussion.py`, `human_audit_analyze.py`.

`_deprecated/` holds scripts from earlier phases.
