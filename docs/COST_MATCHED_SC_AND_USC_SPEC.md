# 同成本自洽采样 + Universal Self-Consistency（USC）规格

状态：2026-11-10 定稿，**读出规则在任何新数据产生前写定**。执行方：TRAE 执行 agent。
目的：回应两份审稿意见——(a) 自洽采样（A3）比 critic 臂少用 token；(b) 开放题上按字符串计票对独立样本不利，应补 USC 基线。
原则：**USC 只是一个被评价的选择方法，不参与判分**——它选出哪个答案，由它决定；这个答案对不对，只由冻结的 T1–T3 判分（sidecar）决定。USC 的输出不得用于修改、补充或复核任何对错标签。不改任何冻结文件；新数据全部写新目录/新文件；判分沿用冻结协议；不看结果调参数。

## 0. 成本口径（已由冻结数据算出，执行 agent 无需重算）

| 臂 | solver | critic | 合计 |
|---|---|---|---|
| A3（贪心首答 + 9 样本） | 51.3M（首答 5.1M + 9 × 5.135M） | 0 | 51.3M |
| C2 Free critic | 38.13M | 23.17M（回放外推） | 61.30M |
| C3 Bank critic | 37.05M | 28.98M（回放外推） | 66.03M |

与 C2 同成本：(61.30 − 5.1) / 5.135 = 10.9 → **N = 11**；与 C3 同成本：(66.03 − 5.1) / 5.135 = 11.9 → **N = 12**。
主方法是 C2，Bank critic 不是主要结论，因此只对齐 C2：A3 **补 2 个样本**（第 10、11 个，合计 11 个），约 10.3M token。C3 与 11 样本比较时注明其成本高约 8%。

## 1. 任务 S1：A3 补 2 个样本

- 题目：冻结的 400 题，全部。
- 设置与原 A3 完全一致：同一提示词、temperature 0.7、thinking 16384 + margin 8192、同一模型权重。优先用原 A3 的端点（`deepseek-v4-flash`）；若配额不足改用 `deepseek-v4-flash-payg`，必须在结果里写明，并报告与原 9 样本的对齐统计（平均 reasoning token、截断率、无提交率）。
- 输出：`experiments/hle400_A3_extra/<model>/loop_trajectories.jsonl`，记录格式同原 A3，`round` 取 10、11。**不要写入或改动 `experiments/hle400_A3/`。**
- 判分：对这 800 个新答案走冻结协议（T1 → astra → k3 争议复判 → 按答案变体裁决；"同一实质同一判决"，已有裁决变体直接沿用）。输出 `experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json`，格式同 sidecar v2（每题 2 条 `{c, s}`）。**不要改 `is_correct_t3_sidecar_v2.json`。**
- 冒烟：先跑 10 题 × 2 样本，确认记录格式、截断率与原 A3 相近，再全量。

## 2. 任务 S2：USC

USC（Chen et al., 2023）：把同一题的多个回答交给模型，让它选出"与多数最一致"的那一个。

- 模型：与 solver 相同（deepseek-v4-flash，同一 thinking 预算），temperature 0。**不看标准答案。**
- 输入：题目 + 各回答的**最终答案文本**（`final_answer`，不含推理）。截断轮（`finish_reason == "length"`）和空答案不进入列表。
- 顺序：每题用 `crc32(task_id)` 做种子随机打乱，**所有臂同样处理**（避免 loop 臂借用时间顺序）。
- 提示词（固定，不得改动）：

  ```
  I have generated the following responses to the question: {question}

  Response 1: {answer_1}
  ...
  Response K: {answer_K}

  Evaluate these responses. Select the most consistent response based on majority consensus.
  Start your answer with "The most consistent response is Response X" (without quotes).
  ```
- 解析：取 "Response X" 的 X；解析失败或 X 越界 → 重试 1 次；仍失败 → 该题回退为普通投票结果，并计数上报。
- 应用对象（每个都是 400 次调用）：
  1. A3 的 9 个样本；
  2. A3 的 11 个样本（1–11）；
  3. C2 轨迹的全部轮次；
  4. C3 轨迹的全部轮次；
  5. A2 轨迹的全部轮次；
  6. A2′ 轨迹的全部轮次。
- 输出：`experiments/hle400/t3/usc_result.jsonl`，每行 `{task_id, arm, n_responses, order:[原始 round 序号…], selected_round, raw_output, parse_ok, prompt_tokens, completion_tokens, reasoning_tokens}`。
- 判对错：**不需要新判分**——被选中的那一轮的对错直接取 sidecar（A3 新样本取 A3extra）。被选中的轮若为截断轮按冻结规则记错（按上面的输入规则不应出现）。
- 冒烟：每个应用对象先跑 10 题，检查解析成功率 ≥ 95% 再全量。
- 成本：记录 USC 自身的 token，并入对应臂的总成本单独列出。

## 3. 分析（由 Claude 离线完成，执行 agent 只需交付数据）

对每个比较报告：期望得分差（平局随机，解析精确期望）、95% bootstrap 区间、配对符号翻转置换检验 p。

## 4. 读出规则（预先写定）

主比较（**指定主方法为 C2 Free critic 的 mode**）：

- **R1 同成本投票**：C2.mode 对 A3 的 11 样本普通投票。
- **R2 同成本 USC**：C2.mode 对 A3 的 11 样本 USC。
- 次要：C3.mode 对 A3 的 11 样本（投票、USC；注明 C3 成本高约 8%）；USC(C2 轨迹) 对 USC(A3 11 样本)；A3 上限随 N 的变化（9/11）。

判定：
- R1 与 R2 的差的 95% 区间**都不含 0** → "同成本下选择优势成立"，稿子保留"selects more correct answers than self-consistency"，数字换成同成本的。
- R1 成立、R2 不成立 → "优势来自计票方式；对带语义选择的自洽采样无优势"，选择一节按此改写，论文重心移到上限与对照。
- R1 不成立 → "同成本下选择与自洽采样相当"，撤回选择优势的主张。
- 无论哪种，上限、对照、评估器三部分结论不受这组实验影响。

不做的事：不用 astra 做等价聚类或选择（astra 只用于判对错，保持测量与方法分离；2026-11-10 决定）；不因结果调整 N、提示词、输入内容或平局规则；USC 只跑一次。

## 5. 交付清单

- `experiments/hle400_A3_extra/…/loop_trajectories.jsonl`（400 题 × 2 样本）
- `experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json`
- `experiments/hle400/t3/usc_result.jsonl`（6 个应用对象 × 400）
- `docs/COST_MATCHED_SC_RESULTS.md`：端点、截断率、对齐统计、USC 解析失败数、各部分 token；**只报事实，不做结论**。

## 6. 修订记录（2026-11-10 16:30，USC 运行中、尚未做任何对错统计）

检查运行中数据时发现两处实现问题，属于实现与规格不符的修正，不涉及提示词、参数或读出规则：

1. **解析过宽**。`parse_selection` 在找不到完整句式时退而匹配正文里第一个 "Response N"；当模型推理写满预算、思考内容漏进可见输出或被截断时，会把推理中随口提到的编号当成选择并记为 `parse_ok=True`。修正为：只接受完整句式 `most consistent response is Response N`，取**最后一次**出现；可见输出被截断（completion 达上限）一律算解析失败；去掉宽松回退。已有记录用 `raw_output` 离线重解析，不需重新调用；重解析后变为失败的题按规格重试 1 次，仍失败回退普通投票。
2. **接口错误不得写成结果**。当前实现在接口异常时把该题直接回退为普通投票（token 记 0）；S1 把 `api_failure` 的样本也记为已完成。配额耗尽时这会把基线结果悄悄换成投票结果或空样本（与 11 月 5 日 Judge-C 的 429 事故同类）。修正为：接口异常不写记录、稍后重试；连续 5 次接口异常即停止并报告；`api_failure` 的样本不算完成、必须重采；每条记录写入实际使用的端点名。
3. 端点：token plan 与按量付费为同一模型权重。配额不足时切到 `deepseek-v4-flash-payg` 续跑，结果文件中逐条记录端点，并报告两段的对齐统计（平均 reasoning token、截断率）。
