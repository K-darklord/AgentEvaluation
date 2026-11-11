# Claims registry（v2，2026-11-11；对应 `paper/acl/main.tex`）

规则：论文中的每个数字都应能回指到本表一行；证据是冻结文件或只读冻结文件的脚本。状态分三类：**预先指定**（规格文档有日期、先于看数）、**探索性**（看数后提出）、**稳健性**（为回应质疑而加）。旧版（v1，按内部草稿编号）在 `docs/_deprecated/20261111_pre_submission/CLAIMS_REGISTRY_v1.md`。

## E. 证据源
| E | 内容 | 位置 |
|---|---|---|
| E1 | 逐轮对错（deepseek） | `experiments/hle400/t3/is_correct_t3_sidecar_v3.json` |
| E2 | 逐轮对错（qwen） | `experiments/hle400/t3/is_correct_t3_sidecar_rep.json` |
| E3 | 两模型主表与配对检验 | `scripts/two_model_tables.py` → `two_model_scores.json` |
| E4 | 同成本、USC、合并检验 | `scripts/cost_matched_readout.py`；`is_correct_t3_sidecar_A3extra.json`、`usc_result.jsonl` |
| E5 | 留存率、recency、提示条数 | `scripts/persistence_and_settle.py`；qwen：`scripts/gen_replication_results.py` → `REPLICATION_RESULTS.md` |
| E6 | 保守下界、格式归一化 | `scripts/merge_correct_vote.py`、`scripts/vote_latex_normalized.py` |
| E7 | 自适应自洽采样、首轮修复/损伤 | `scripts/tie_and_adaptive_baselines.py` |
| E8 | 弃答、验证器模拟 | `scripts/selective_prediction.py`、`scripts/verifier_regimes.py` |
| E9 | judge 审计 | `scripts/judge_conditional_test.py` → `_judge_audit_autogen.md`、`EVALUATOR_RESULTS.md` |
| E10 | critic token 回放 | `experiments/hle400_C2/token_replay_summary.json`、`experiments/hle400_C3/token_replay_summary.json` |
| E11 | 预注册与规格 | `C2_BANK_FREE_CRITIC_SPEC.md`、`A2PRIME_PERTURBING_PLACEBO_SPEC.md`、`EVALUATOR_FINAL_DESIGN.md`、`REPLICATION_SPEC.md`、`COST_MATCHED_SC_AND_USC_SPEC.md` |
| E12 | 判分协议与裁决 | `HLE_SCORER.md`、`k3_adjudication.json`、`scripts/gen_t3_sidecar_v3.py`、`scripts/gen_t3_sidecar_rep.py` |
| E13 | 切换文本分析（critic 是否递出答案） | `experiments/hle400/t3/r2w_w2r_switches_freezekey.jsonl`（重跑前的 C3 轨迹） |

## C. 主张
| C | 主张（论文位置） | 数 | 证据 | 状态 |
|---|---|---|---|---|
| C01 | 上限三级阶梯（摘要、§4.1、表 2） | deepseek 153 / 171 / 198；qwen 123 / 149 / 182 | E1–E3 | 描述性 |
| C02 | 上限：FC 对 RP | 52/7；69/10，均 p<0.001 | E3 | 预先指定（安慰剂对照；qwen 为 R2） |
| C03 | 上限：FC 对 PP | 39/12 p=0.0002；49/16 p<0.001 | E3 | 预先指定（A2′ 读出规则；qwen 为 R4） |
| C04 | 上限：PP 对 RP | 28/10 p=0.005；42/16 p<0.001 | E3 | 预先指定的对照，检验为探索性 |
| C05 | 上限在匹配候选数下保持（表 3） | k=2：33/9、37/19；k=3：35/11、41/18 | E3 | 稳健性 |
| C06 | 上限在仅精确匹配下保持（表 3） | 31/11 p=0.003；35/12 p=0.001 | E3 | 稳健性 |
| C07 | FC 与 9 样本自洽采样上限相当 | 198 对 190（29/21）；182 对 171（44/33） | E3 | 描述性 |
| C08 | 选中答案：FC 对 RP（§4.2、表 4、图 2） | +12.4 [−1.6, 25.6] p=0.08；+23.3 [8.8, 39.2] p=0.004；合并每模型 +17.9 [7.8, 28.5] p<0.001 | E3、E4 | 单模型检验为探索性；合并检验为探索性（事后） |
| C09 | 选中答案：FC 对 PP | +11.3 [−0.8, 23.7] p=0.07；+18.5 [3.9, 34.3] p=0.02；合并 +14.9 [5.3, 25.7] p=0.003 | E3、E4 | 同上 |
| C10 | 选中答案：FC 对 9 样本自洽采样 | +20.7 [9.0, 32.4] p<0.001；+23.1 [9.6, 38.6] p=0.002 | E3 | qwen 为预先指定（R1）；deepseek 的证伪检验原为 BC 而写 |
| C11 | 同成本（11 样本）下仍成立 | 138.2；+19.2 [7.0, 31.1] p=0.002 | E4 | 预先指定（COST_MATCHED R1） |
| C12 | 对 USC 未确立 | USC 145；+11.4 [−1.4, 24.8] p=0.09（n=396） | E4 | 预先指定（COST_MATCHED R2，未通过）；次要结果 |
| C13 | 保守下界 | deepseek +13.0 [2.1, 23.8]；qwen +12.2 [−2.8, 27.3]；合并 12.6 [3.2, 22.4] p=0.010 | E3、E4、E6 | 稳健性 |
| C14 | 压力本身不改善选择 | PP 对 RP：+1.2 p=0.84；+4.8 p=0.47 | E3 | 探索性 |
| C15 | RP 以约一半 token 与自洽采样持平 | +8.2 p=0.20；−0.2 p=0.99；token 24.6M 对 51.4M、15.2M 对 31.8M | E3 | 探索性 |
| C16 | error bank 无可识别贡献 | FC 对 BC：上限 23/17 p=0.43；选中 +6.5 p=0.32 | E3 | 预先指定（C2 读出规则） |
| C17 | BC 对自洽采样（原证伪检验） | +14.1 [2.5, 26.7] p=0.03 | E3 | 预先指定 |
| C18 | 最后一轮：deepseek 不优于安慰剂，qwen 优于 | 148 对 141（29/22 p=0.40）；112 对 89（48/25 p=0.010） | E3 | 探索性 |
| C19 | 盈亏判据 | 阈值 0.39 / 0.21；首轮修复/损伤见附录 E | E7、REPLICATION_RESULTS | 探索性 |
| C20 | 留存不对称（表 5） | FC 2.1 / 1.6；RP 1.4 / 1.2；qwen FC 区间下界 1.37 > RP 1.20 | E5 | qwen 为预先指定（R3） |
| C21 | critic 未直接递出答案；修对/改错近似对半 | 0/129；159 对 142 | E13 | 探索性（基于重跑前的 C3 轨迹） |
| C22 | 成本 | FC 约 61M、BC 约 66M（critic 为回放外推 23M、29M）；RP 24.6M；SC 51.4M | E3、E10 | 描述性；qwen 的 critic 未计量 |
| C23 | 同模型 judge 在票数之外无可检出信息（§5、表 6） | 分歧处准确率 18/36、53/116、32/66；跨半 76/73/71 与 73/72/77；81 规则 154/156/155 | E9 | 验收标准预先指定；"条件于票数"检验为探索性 |
| C24 | headroom 与 oracle | 37 = 11 + 10 + 16；1,201 switch；oracle 173；盲撤 149 | E9 | 描述性（重跑前的 C3 轨迹，上限 191） |
| C25 | 弃答、验证器模拟（附录 E） | 见附录 | E8 | 探索性 |
| C26 | BC 对两个 placebo 的选中答案（表 4，评审后补报） | +5.9 [−6.8, 18.5] p=0.34；+4.8 [−6.5, 16.4] p=0.43 | `scripts/review_fixes_stats.py` | 稳健性（不利于主张的对比） |
| C27 | 保守下界下对 11 样本自洽采样 | +9.3 [−2.1, 20.4] p=0.11 | E4 | 稳健性 |
| C28 | 模型间差异不显著（附录 E） | 选中 FC−RP：+10.8 [−8.8, 31.6]；最后一轮：+16.0 [−4.0, 38.0] | `scripts/review_fixes_stats.py` | 探索性 |
| C29 | 单样本准确率、截断率（§4.2、附录 C） | 单样本 117 / 80；deepseek 截断 6.4%–8.0%，首答截断 28 题；qwen 1 轮 | `scripts/review_fixes_stats.py` | 描述性 |
| C30 | critic 未直接递出答案（改用 Free critic 轨迹，取代 C21 的数字） | deepseek 修对 2/132、改错 2/100；qwen 17/159、16/132；修对/改错 165/135、229/193 | `scripts/review_fixes_stats.py` | 探索性 |
| C31 | Free critic 每轮 3 条质疑的比例 | deepseek 86%，qwen 95%；A2′ 的剂量分布取自 deepseek 并沿用于 qwen | `scripts/review_fixes_stats.py` | 描述性 |

注（2026-11-11 下午，独立评审后）：摘要与引言中对选择增益的表述已限定为"一个模型显著 + 合并检验"，并写明这些对比不在预注册检验内；参考文献 31 条，其中 5 条为评审后核对新增，5 条更新为正式发表版本。

## 已知不一致与待办
- 第 5 节（C23、C24）与 C21 基于 C3 重跑前的轨迹（3 题不同）。待执行 agent 对这 3 题补跑 judge 后重算，论文脚注已注明。
- USC 的 43 条过期记录待补跑（C12）。
- 论文附录 E 中 settle 的数字（135、134、117、121）中前两个由 `persistence_and_settle.py` 的同口径实现算出，待官方计分脚本按 v3 复核。
- qwen 与新增样本的判分未做新的争议复判（论文 Limitations 已写明）。
