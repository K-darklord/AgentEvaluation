# 第三模型（glm-5.3）确证性实验：预登记规格

状态：2026-11-11 定稿，先于任何 glm 的 HLE-400 数据。执行方：TRAE 执行 agent；分析：Claude 离线。
目的：对论文 `paper/acl/main.tex` 中目前属于探索性的主张"生成式批评在安慰型 loop 之上改善选中的答案"做一次预先指定的确证性检验，并把上限阶梯扩到第三个模型。

## 1. 为什么选 glm-5.3（事先写明）
- 与 deepseek、qwen 不同厂商；同一能力档位。
- 论文的盈亏判据预测首答准确率越高、批评对选择的帮助越小，所以不选明显更强的模型；该预测留给后续工作。
- 若 glm-5.3 无法通过 §3 的对齐门槛，停止并报告，由用户决定替代模型；**不得**在看到任何对错结果后更换模型。

## 2. 题目与条件
- 题目：论文的 400 题（`data/raw/hle/hle_400_new.jsonl`；两段题单 `hle_replication_200.json` + `hle_replication_rest200.json`）。
- 条件：A（贪心首答）、A2（安慰型）、A2P（扰动型，模板，零 LLM）、C2（Free critic，critic = glm-5.3）、A3（9 样本，T=0.7）。不跑 C3。
- 常量与主实验一致：max_rounds 10、early_stop 3、rationale off、T=0（A3 为 0.7）、A-seeding（各 loop 共用 A 臂首答）、`CRITIC_HOLD_ON_REPEAT=0`。
- A2P 的条数分布沿用 0.86 / 0.11 / 0.03（与 qwen 相同，不按 glm 重新拟合）。
- 运行：`MODEL=<glm 注册名> bash scripts/run_replication.sh`，输出目录前缀改为 `rep3_`（请给脚本加 `TAG` 参数，默认值不变）。

## 3. 开跑前的对齐门槛（只看运行健康度，不看对错）
在 A 臂前 16 题上检查：
- thinking 预算：reasoning_tokens ≤ 16384，max_tokens = 16384 + 8192；若 glm 的接口不支持 `thinking_budget`，记录实际可用的等价设置。
- 截断率（finish_reason = length）≤ 15%；reasoning_content 非空。
- 已知风险：glm 的隐藏推理可能写满预算（见 `src/run_feedback_loop.py` 关于 glm 的注释）。若截断率 > 15% 且无法通过预算设置解决 → 停止并报告。
- 端点：glm-5.3 目前只注册在 token plan；若配额不足，先注册按量付费条目再跑，逐条记录端点。

## 4. 运行保护（必须）
- 接口失败不写记录、稍后重试；连续 5 次失败即停；任何含失败轮的轨迹不算完成。
- 报错文本不得进入答案键，也不计入"连续 3 次相同"。
- **critic 调用逐次记录 token**（prompt / completion / reasoning），写入轮记录的新字段，供成本核算；不再靠回放外推。
- 全部跑完后报告：每臂题数、失败轮数（应为 0）、截断率、平均 reasoning token、首答是否各臂一致。

## 5. 判分
与 qwen 相同：截断 → 错；精确匹配；astra K=1（按题 + 答案缓存）；沿用已有裁决规则。输出 `experiments/hle400/t3/is_correct_t3_sidecar_rep3.json`。论文中会写明这是缩减协议。

## 6. 预先指定的检验
全部在 400 题上，一次性读出；选中答案 = mode / vote，平局随机的期望得分；配对符号翻转置换检验（10,000 次）+ 95% bootstrap 区间；二值结果用精确 McNemar。

| 级别 | 检验 | 成立标准 |
|---|---|---|
| **P1（唯一主检验）** | C2.mode − A2.mode（选中答案） | 差 > 0 且 95% 区间不含 0 |
| P2（次检验） | C2.mode − A2P.mode | 同上 |
| S1 | 上限 C2 对 A2 | 方向相同且 p < 0.05 |
| S2 | 上限 A2P 对 C2 | A2P 至少低 15 题且 p < 0.05 |
| S3 | 上限 A2P 对 A2 | 方向相同且 p < 0.05 |
| S4 | C2.mode − A3.vote（9 样本） | 差 > 0 且区间不含 0 |
| S5 | 留存不对称 C2 > A2 | C2 的区间下界 > A2 的点估计 |

描述量（不设阈值）：首答准确率、每题候选数、换答案率、留存率、最后一轮、首轮修复/损伤、单样本准确率、各臂 token（含实测的 critic token）。

## 7. 读出规则（预先写定）
- **P1 成立** → 论文保留"到达 + 选择"的主线，把 glm 的 P1 作为确证性结果写入摘要；三个模型的合并估计作为探索性结果报告。
- **P1 不成立（区间含 0）** → 论文改为以到达率为唯一 headline；选择一节写成"在一个模型上显著、预先指定的确证性检验未通过"。
- **P1 方向为负且区间不含 0** → 如实报告为相反结果，并撤回选择方面的主张。
- S1–S3 中任一不成立 → 在结果节与 Limitations 各写一次，不改主实验的任何数字。
- 不因任何结果回头修改 deepseek 或 qwen 的判读；不换模型重跑到成立；判分完成之前不做任何基于精确匹配的预览。

## 8. 交付
五臂轨迹（`experiments/rep3_{A,A2,A2P,C2,A3}_<model>/`）；sidecar；`docs/THIRD_MODEL_RESULTS.md`（只填数与运行健康度，不做结论）。分析由 `scripts/two_model_tables.py` 的三模型版本完成。

## 9. 成本估计
solver 约 5 个臂 × 400 题，按 qwen 的量级约 90–110M token，critic 约 20–30M。
