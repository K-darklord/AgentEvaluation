# 文档与数据索引（2026-11-15，与 `paper/acl/main.tex` v13 一致）

本文件是入口。凡与本文件或论文不一致的旧文档，以论文和本索引为准。过期文档在各目录的 `_deprecated/` 下，移动清单见各自的 `MOVE_LOG.json`。

**当前状态。** 三个模型（deepseek-v4-flash、qwen3.8-flash、MiniMax-M2.5）、400 道 HLE 题的实验全部完成，判分审计（100 条）完成，论文定稿为 v13。2026-11-15 决定不再追加实验。待办只剩投稿事务（见本文件末尾）。

## 1. 论文
| 内容 | 位置 |
|---|---|
| 正文源文件（匿名评审版 / 署名预印本） | `paper/acl/main.tex` / `paper/acl/main_preprint.tex`（后者只差作者栏与 AI 使用声明中的单复数） |
| 当前 PDF | `paper/acl/v13_anonymous.pdf`、`paper/acl/v13_preprint.pdf`（与 `main.pdf`、`main_preprint.pdf` 相同） |
| 参考文献、图、作图脚本 | `paper/acl/refs.bib`、`paper/acl/figs/`、`paper/acl/make_figs.py` |
| 修改记录（十轮审稿—修改、USC 选稿、其后的修改） | `paper/acl/REVISION_LOG.md`；各轮稿件与审稿提示在 `paper/acl/revision_loop/` |
| 旧版 PDF（v9–v12） | `paper/acl/_old/` |
| 主张—证据对照 | `docs/CLAIMS_REGISTRY.md` |
| 论文数字清单（可机读）与核对脚本 | `docs/consistency_manifest.json`、`scripts/check_manifest.py` |

## 2. 论文用名与代码代号
论文正文只用左列的名称；代码、数据文件和 11 月 13 日之前的文档用右两列。读旧文档时按此表对应。

| 论文（v13） | 代码 / 文件 | 旧文档里的叫法 |
|---|---|---|
| first answer（首答，温度 0） | `A` | Greedy |
| reassuring loop | `A2` | Reassuring placebo, RP |
| generic-doubt loop | `A2P`（目录名 `A2PRIME`） | Perturbing placebo, PP, A2′ |
| critique loop | `C2` | Free critic, FC, bank-free critic |
| independent samples（9 个；deepseek 另有第 10–11 个） | `A3` | Self-consistency, SC |
| restricted critic（仅附录 B 与 §4.5） | `C3` | Bank critic, BC |
| reached | `ceiling` / `reach` | ceiling、上限 |
| selected（平局随机下的期望得分） | `selected` / `sel` / `mode` | mode、majority |
| plurality answer | `mode` | majority answer |
| conversion = selected ÷ reached | `conversion` | — |
| last | `final` | final |
| repeat probability | `stay` | persistence、留存率 |
| grader（另一厂商的判分模型 gpt-6-astra） | `astra`、`T2`、`K1` | judge（判分意义上的） |
| judge（同模型裁判，仅 §4.5） | Judge-R = `rubric_ce`，Judge-R+ = `qcut`，Judge-C = `judge_c` | evaluator |

模型：deepseek-v4-flash（目录 `hle400_*`）、qwen3.8-flash（目录 `rep200_*`，名称沿用旧约定，实际为 400 题）、MiniMax-M2.5（目录 `rep3_*`）。

## 3. 冻结数据
| 内容 | 位置 |
|---|---|
| 逐轮对错，deepseek（A、A2、A2P、A3、C3、C2） | `experiments/hle400/t3/is_correct_t3_sidecar_v3.json` |
| 逐轮对错，qwen | `experiments/hle400/t3/is_correct_t3_sidecar_rep.json` |
| 逐轮对错，MiniMax-M2.5 | `experiments/hle400/t3/is_correct_t3_sidecar_rep3.json` |
| 独立采样第 10–11 个样本（deepseek） | `experiments/hle400_A3_extra/`、`experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json` |
| 轨迹（本地保存，不入库） | `experiments/hle400_{A,A2,A2PRIME,A3,C3,C2}/<model>/`、`experiments/rep200_*_qwen3.8-flash-payg/`、`experiments/rep3_*_minimax-m2.5/` 下的 `loop_trajectories.jsonl` |
| universal self-consistency 输出（2400 行） | `experiments/hle400/t3/usc_result.jsonl` |
| 同模型 judge 判决 | `experiments/hle400/t3/c3_rubric_ce.jsonl`、`qcut_result.jsonl`、`judge_c_verdicts_dashscope.jsonl` |
| 接口失败重跑清单 | `experiments/hle400/t3/api_failure_rerun_manifest.json`、`api_failure_rerun_qwen_manifest.json` |
| 分析脚本的输出（小文件，入库） | `experiments/hle400/t3/` 下的 `two_model_scores.json`、`third_model_readout.json`、`three_model_means.json`、`three_model_appendix.json`、`search_not_verification.json`、`selected_exact_only.json`、`section5_headroom.json` |
| 判分审计 | `audit/human_audit_20261111/`（`audit_final.json` 入库；标注表、题目、盲化密钥只在本地） |
| 历史版本（sidecar v1/v2、`_backup_*` 等） | 仍在 `experiments/hle400/t3/`，仅供追溯，论文不读 |

文件版本与判分规则的细节见 `docs/HLE400_FROZEN_DATA.md`（文首的"当前状态"一节）与 `docs/HLE_SCORER.md`。

## 4. 复算脚本（只读冻结文件，不调用模型）
| 论文位置 | 脚本 |
|---|---|
| 表 3（主表）、表 4（配对比较）：deepseek、qwen | `scripts/two_model_tables.py` |
| 表 3、表 4：MiniMax-M2.5；附录 E 的预先确定检验 P1、P2、S1–S5 | `scripts/third_model_readout.py` |
| 表 4 末列与图 3 的三模型均值 | `scripts/three_model_means.py` |
| §4.2 的 conversion、表 5（selected 的来源拆分）、last 与 selected 之差 | `scripts/search_not_verification.py` |
| §4.3 与附录 F 的重复概率表（表 7）、首轮修复/损伤、critic 是否直接给出答案、被截断的首答 | `scripts/three_model_appendix.py`（区间：`scripts/persistence_and_settle.py`、`scripts/third_model_readout.py`） |
| 附录 F 表 6（reach 的稳健性）中的第二候选质量、按题型拆分 | `scripts/reach_quality_checks.py`（其余列来自主表脚本） |
| 附录 F：只计精确匹配时的 selected | `scripts/selected_exact_only.py` |
| 附录 F：同成本采样（11 个样本）与 USC（deepseek） | `scripts/cost_matched_readout.py` |
| 附录 F："When does the loop beat the vote?" | `scripts/reconcile_with_voting_literature.py` |
| 附录 F：投票分裂的上界 | `scripts/merge_correct_vote.py`（deepseek）、`two_model_tables.py` 与 `third_model_readout.py` 的 pooled 项 |
| §4.5 与附录 G（同模型 judge） | `scripts/section5_headroom.py`、`scripts/judge_conditional_test.py` |
| 附录 D（判分审计） | `scripts/human_audit_final.py`（抽样 `human_audit_sample.py`，符号核验 `human_audit_cas_checks.py`） |
| token 用量 | 主表脚本（solver）；critic：`scripts/e2_c2_critic_token_replay*.py`（deepseek、qwen 为回放实测）、MiniMax-M2.5 为运行时记录 |
| 图 1–3 | `paper/acl/make_figs.py` |
| 全部数字的一次性核对 | `scripts/check_manifest.py` |

`scripts/README.md` 按用途列出 `scripts/` 下的全部脚本。

## 5. 规格（预先写定，之后不改）与结果
| 内容 | 规格 | 结果 |
|---|---|---|
| critique loop（C2） | `C2_BANK_FREE_CRITIC_SPEC.md` | 论文 §4.1 |
| generic-doubt loop（A2P） | `A2PRIME_PERTURBING_PLACEBO_SPEC.md` | 论文 §4.1 |
| 同模型 judge | `EVALUATOR_FINAL_DESIGN.md` | `EVALUATOR_RESULTS.md`（论文 §4.5 的数字以 `section5_headroom.py` 为准） |
| 第二模型 qwen | `REPLICATION_SPEC.md` | `REPLICATION_RESULTS.md` |
| 同成本采样与 USC | `COST_MATCHED_SC_AND_USC_SPEC.md` | `COST_MATCHED_SC_RESULTS.md` |
| 第三模型 MiniMax-M2.5 | `THIRD_MODEL_SPEC.md`（§10 选型，§11 读出） | `THIRD_MODEL_RESULTS.md` |
| 判分审计 | `HUMAN_AUDIT_PLAN.md`（含最终结果） | 论文附录 D |

规格文件用的是当时的名称（RP、PP、FC、SC、BC），对应关系见第 2 节。规格文件不为统一名称而改写。

## 6. 其他现行文档
| 内容 | 位置 |
|---|---|
| 项目历史 | `docs/PROJECT_HISTORY.md`（§0 是 HLE-400 阶段的时间线） |
| 判分协议 | `docs/HLE_SCORER.md`；通用标准 `docs/EVALUATION_STANDARD.md` |
| restricted critic 的错误词表来源 | `docs/ERROR_BANK_PROVENANCE.md` |
| 干扰因素与修复记录（代码注释里的 INT 编号指向这里） | `docs/INTERFERENCE_CAUSAL_TABLE.md` |
| 执行 agent 的任务清单（已全部结束，留作记录；代码注释引用其中的条目编号） | `docs/EXEC_AGENT_WORKLIST.md` |
| 变更传播规则、可复现性标准（早期阶段写成，文首有说明） | `PROTOCOL.md`、`docs/REPRODUCIBILITY.md` |
| 工程变更日志 | `CHANGELOG.md` |

## 7. 已归档
- 2026-11-15：`docs/_deprecated/20261115_v13_alignment/`（追加实验的方案 `NEXT_EXPERIMENTS_FOR_MAIN_CONFERENCE.md`，已决定不做）。
- 2026-11-11：`docs/_deprecated/20261111_repo_cleanup/`、`docs/_deprecated/20261111_pre_submission/`、`src/_deprecated/`、`scripts/_deprecated/`、`_deprecated/root_20261111/`、`experiments/_deprecated/`、`paper/_deprecated/`（v6 之前的 Markdown 稿）。
- 早期阶段的数据（GPQA、错误词表蒸馏等）在 `experiments/_deprecated/` 与 `experiments/l0_distill_v1/`，论文不使用。

## 8. 投稿前待办（都需要作者决定或操作）
1. 通读 `paper/acl/v13_preprint.pdf` 并批注。
2. 讨论裁决表里是否有一条"建议 correct、裁决 incorrect"：已保存的 `discussion_adjudication.xlsx` 里没有这样的行，需作者核对；若确有，附录 D 的一句话要改。
3. 作者单位（预印本作者栏目前只有姓名与邮箱）。
4. 提交与推送：当前改动均未提交。`scripts/human_audit_cas_checks.py` 含 12 条 HLE 参考答案的转写，是否公开需决定。
5. 论文写明预先确定的规格随材料公开：规格文件为中文，匿名投稿用的代码链接需去除身份信息（仓库名、`CHANGELOG.md` 中的邮箱、`.idea/` 等）。
6. ARR：确认 2027 年 1 月周期的截稿日与预印本政策；按实际情况填写 AI 使用与 checklist。
