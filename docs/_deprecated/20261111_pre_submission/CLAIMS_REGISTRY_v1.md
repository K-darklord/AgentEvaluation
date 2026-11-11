# Claims registry（按 scientific-agent-skills / scientific-writing 的 evidence-binding 规范）

> 每条论文主张 = 一个 C-ID；证据 = 冻结文件或可重跑脚本（E-ID）；状态 = 预先指定（protocol 文档有日期记录，先于看数）/ 探索性（看数后提出）/ 事后鲁棒性（为回应审稿而加，结论不依赖它）。
> 规则：草稿中任何数字若不能回指到这里的一行，就不能进正文。终审（TBD-10）按本表逐条核。

## E. 证据源
| E | 内容 | 位置 |
|---|---|---|
| E1 | 冻结逐轮正误 sidecar v2（含 C2） | `experiments/hle400/t3/is_correct_t3_sidecar_v2.json` |
| E2 | 冻结 winner 准确率 / 配对 / 成本 / 答案形式 | `experiments/hle400/t3/t3_final_scores_v2.json` |
| E3 | 平局敏感性、随机化配对、A3-adaptive、逐轮曲线、对账、端点统计 | `scripts/tie_and_adaptive_baselines.py` |
| E4 | 持久性（stay、run-3、retention、CI） | `scripts/persistence_analysis.py` → `docs/PERSISTENCE_MECHANISM.md` |
| E5 | 三 judge 审计（混淆、LR、E1–E4、条件于计数、穷举） | `scripts/judge_conditional_test.py` → `docs/_judge_audit_autogen.md` |
| E6 | 弃权曲线、AUROC | `scripts/selective_prediction.py` |
| E7 | 验证器 regime 模拟 | `scripts/verifier_regimes.py` |
| E8 | 轨迹级 26 特征对照 | `scripts/switch_contrast.py` |
| E9 | 端点对齐 | `endpoint_caveat_alignment.json`（执行 agent E3 产物） |
| E10 | token 账（solver 冻结；critic 重放估计） | `t3_final_scores_v2.json` cost + `token_replay_summary.json` |
| E11 | 预注册协议（带日期） | `C2_BANK_FREE_CRITIC_SPEC.md`、`EVALUATOR_FINAL_DESIGN.md` §5、`A2PRIME_…_SPEC.md`、`REPLICATION_SPEC.md`、outline 的证伪边界 |
| E12 | 计分协议与裁决 | `HLE_SCORER.md` §1.2、`k3_adjudication.json`、`HLE400_T3_SECOND_AUDIT.md` |

## C. 主张
| C | 主张（草稿位置） | 数 | 证据 | 状态 |
|---|---|---|---|---|
| C01 | 上限：A2 154 / A3 190 / C3 191 / C2 198（§5.1） | 同左 | E1, E3 | 描述性 |
| C02 | 上限 C3 vs A2 配对 47/8 p=8e-8；C2 vs A2 50/7 p=4e-9 | 同左 | E3 | 预先指定的对照（A2 为预注册安慰剂） |
| C03 | C2.mode vs A3.vote，对称约定：157.4 vs 137.3，p 中位 0.004，97% 抽签显著 | 同左 | E3 | 检验预先指定（证伪边界）；**对称约定为审稿后加入的分析口径**（事后，保守方向） |
| C04 | C3.mode vs A3.vote 对称约定 150.7 vs 137.3，p 0.076；方法原规则 154 vs 137.4，p 0.030 | 同左 | E3 | 同 C03；C3 不作主张 |
| C05 | A2.mode vs A3.vote 不显著（p 0.27） | 同左 | E3 | 描述性 |
| C06 | A3-adaptive 136.5，36.0 M tokens；C2 vs adaptive p 0.001 | 同左 | E3 | **事后**（审稿后加入的成本匹配基线） |
| C07 | recency 规则贡献 −0.9 / +3.5 / +1.6 | 同左 | E3 | 事后鲁棒性 |
| C08 | 单步 ECR₁/EIR₁：A2 17/7、C3 38/19、C2 45/20；阈值 0.39 | 同左 | E3 | 探索性（§5.3 的解释框架） |
| C09 | stay 不对称 A3 1.6 / C3 1.5 [1.3,1.8] / C2 1.9 [1.6,2.2] / A2 1.25 | 同左 | E4 | 描述性；C2 vs C3 的"区间重叠"用于预注册读出 |
| C10 | run-3 复合 2.3；count-3 锁定 107/110 vs A3 单次 18/53；retention .94/.80/.80/.72 | 同左 | E4 | 描述性 |
| C11 | 归一化器拆分：正确→正确转移改 key 27%（critic 臂）/16%（A2） | 同左 | E3 | 描述性，限制 |
| C12 | 可回收 37 = 平局 11 / 差 1 票 10 / ≥2 票 16；oracle 173 / 165 / 盲撤 149 | 同左 | E5 | 描述性 |
| C13 | 三 judge 边级 0.577 / 0.571 / 0.663；LR 与 CI | 同左 | E5 | E1–E4 **预先指定**（EVALUATOR_FINAL_DESIGN §5） |
| C14 | 预注册 ± 聚合 dev→test：76 / 77 / 71（mode 76） | 同左 | E5 | 预先指定 |
| C15 | 条件于计数：相左时 0.500 / 0.475 / 0.485（Wilson CI） | 同左 | E5 | 探索性（核心解释，审稿前提出） |
| C16 | 三角色 NB、logistic in-sample 150、穷举 ≤156 跨半归零 | 同左 | E5 | 事后鲁棒性 |
| C17 | C2 vs C3 读出：上限 198 ≥ 191−5；不对称区间重叠 → "不可识别" | 同左 | E1, E4, E11 | **预先指定**（spec 日期早于 C2 运行） |
| C18 | C2 方向数 3 条占 86%，C3 12% | 同左 | 轨迹（E3 脚本可加） | 描述性，限制 |
| C19 | 弃权曲线与 AUROC | 同左 | E6 | 探索性 |
| C20 | 验证器 regime（独立 / 不对称 / 相关） | 同左 | E7 | 探索性模拟 |
| C21 | 26 特征 AUC 0.43–0.59 无稳定 | 同左 | E8 | 探索性 |
| C22 | 端点对齐四项 | 同左 | E9 | 描述性 |
| C23 | 成本：solver 37.05 / 38.13 / 24.66 / 51.32 M；C3 critic ≈16 M；C2 critic [E2 待] | 同左 | E10 | 描述性 |
| C24 | 计分：22 条裁决 + C2 21 条（7 对 / 4 错 / 11 既有规则） | 同左 | E12 | 协议 |
| C25 | 方向数 k 分布、A2′ 结果 | [待] | 待 | 预先指定（A2PRIME spec） |

## 多重性声明（草稿 §4 需有对应句）
- 选择规则：三条（final / settle / mode）均在协议中列出、无主次；正文报全部三条；主结论用 mode 时注明 Bonferroni ×3 后 C2 仍 p<0.02，C3 否。
- judge：三种 framing 均报告；没有挑选。
- 平局：对称约定为主；方法原规则并列。
