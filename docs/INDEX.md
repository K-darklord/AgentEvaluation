# 文档与数据索引（2026-11-11，与 `paper/acl/main.tex` 一致）

本文件是入口。凡与本文件或论文不一致的旧文档，以论文和本索引为准；过期文档已移入各目录下的 `_deprecated/`（移动清单：`docs/_deprecated/20261111_pre_submission/MOVE_LOG.json`）。

## 论文
| 内容 | 位置 |
|---|---|
| 正式稿（ACL 模板，LaTeX） | `paper/acl/main.tex`、`refs.bib`、`figs/`、`main.pdf` |
| 作图脚本 | `paper/acl/make_figs.py` |
| 主张—证据对照 | `docs/CLAIMS_REGISTRY.md` |
| 论文数字清单（可机读） | `docs/consistency_manifest.json` |
| 后续实验（不进论文） | `docs/NEXT_EXPERIMENTS_FOR_MAIN_CONFERENCE.md` |

## 冻结数据
| 内容 | 位置 |
|---|---|
| 主实验逐轮对错（deepseek，五个条件 + 首答） | `experiments/hle400/t3/is_correct_t3_sidecar_v3.json` |
| 主实验轨迹 | `experiments/hle400_{A2,A2PRIME,A3,C3,C2}/<model>/loop_trajectories.jsonl` |
| 自洽采样第 10–11 个样本及判分 | `experiments/hle400_A3_extra/`、`experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json` |
| universal self-consistency 输出 | `experiments/hle400/t3/usc_result.jsonl` |
| 第二模型（qwen）轨迹与判分 | `experiments/rep200_{A,A2,A2P,A3,C2}_qwen3.8-flash-payg/`、`experiments/hle400/t3/is_correct_t3_sidecar_rep.json` |
| 接口失败重跑清单 | `experiments/hle400/t3/api_failure_rerun_manifest.json` |
| judge 判决（Judge-R / R+ / C） | `experiments/hle400/t3/c3_rubric_ce.jsonl`、`qcut_result.jsonl`、`judge_c_verdicts_dashscope.jsonl` |
| 历史版本（v2 sidecar 等） | 仍在 `experiments/hle400/t3/`，仅供追溯，不再用于论文数字 |

## 复算脚本（只读冻结文件）
| 论文位置 | 脚本 |
|---|---|
| 表 2、表 3、表 4（两模型主表、匹配候选数、仅精确匹配、配对检验） | `scripts/two_model_tables.py` |
| 同成本比较、USC、两模型合并检验 | `scripts/cost_matched_readout.py` |
| 表 5（留存率）、recency 口径、提示条数分布 | `scripts/persistence_and_settle.py`；qwen 一侧见 `scripts/gen_replication_results.py` |
| 保守下界（并掉判对答案）、格式归一化 | `scripts/merge_correct_vote.py`、`scripts/vote_latex_normalized.py` |
| 自适应自洽采样、首轮修复/损伤、平局口径 | `scripts/tie_and_adaptive_baselines.py` |
| 弃答曲线、验证器模拟 | `scripts/selective_prediction.py`、`scripts/verifier_regimes.py` |
| 第 5 节 judge 审计 | `scripts/judge_conditional_test.py`（基于重跑前的 C3 轨迹，见 CLAIMS_REGISTRY 注） |

## 其他现行文档
| 内容 | 位置 |
|---|---|
| 项目历史（合并了 HISTORY / TIMELINE / EXPERIMENT_LOG / DECISION_LOG） | `docs/PROJECT_HISTORY.md` |
| 判分协议 | `docs/HLE_SCORER.md`（通用标准：`docs/EVALUATION_STANDARD.md`） |
| 错误词表来源 | `docs/ERROR_BANK_PROVENANCE.md` |
| 干扰因素与修复记录（代码注释中的 item 编号指向这里） | `docs/INTERFERENCE_CAUSAL_TABLE.md` |
| 变更传播规则、可复现性标准 | `PROTOCOL.md`、`docs/REPRODUCIBILITY.md`（均已加当前状态说明） |
| 工程变更日志 | `CHANGELOG.md` |

## 已归档（2026-11-11 仓库整理）
`docs/_deprecated/20261111_repo_cleanup/`（旧研究计划、工作图、架构、分类法、数据清单等）、`src/_deprecated/`（29 个未被引用的模块）、`scripts/_deprecated/`、`_deprecated/root_20261111/`（根目录杂项与旧 `output/`）、`experiments/_deprecated/backups_20261111/`。各目录内有 `MOVE_LOG.json`。

## 规格与预注册
`C2_BANK_FREE_CRITIC_SPEC.md`、`A2PRIME_PERTURBING_PLACEBO_SPEC.md`、`EVALUATOR_FINAL_DESIGN.md`、`REPLICATION_SPEC.md`、`COST_MATCHED_SC_AND_USC_SPEC.md`；结果：`REPLICATION_RESULTS.md`、`COST_MATCHED_SC_RESULTS.md`、`EVALUATOR_RESULTS.md`。

## 论文用名与内部代号
| 论文 | 代号 |
|---|---|
| Greedy | A |
| Reassuring placebo (RP) | A2 |
| Perturbing placebo (PP) | A2′ / A2P |
| Self-consistency (SC) | A3 |
| Bank critic (BC) | C3 |
| Free critic (FC) | C2 |

## 进行中
| 内容 | 位置 |
|---|---|
| 第三模型（glm-5.3）预登记规格 | `docs/THIRD_MODEL_SPEC.md` |
| 人工审计方案、标注表、抽样与分析脚本 | `docs/HUMAN_AUDIT_PLAN.md`、`audit/human_audit_20261111/`、`scripts/human_audit_sample.py`、`scripts/human_audit_analyze.py` |
| 评审后补充统计 | `scripts/review_fixes_stats.py` |

## 任务状态
执行 agent 的清单见 `EXEC_AGENT_WORKLIST.md` 末尾"第 8 批"。
