# 执行 agent 工作清单（2026-11-08 下午起）

> 规则：每项"只填数、不改判读"；任何改动冻结文件的步骤先备份；每项完成在本文件勾选并写一行结果（数字 + 文件路径）。
> 遇到与规格冲突或口径不清的情况：停下来问，不自行取舍。
> 参考：`PAPER_CLOSEOUT_TASKS.md`（总表）、`A2PRIME_PERTURBING_PLACEBO_SPEC.md`、`C2_BANK_FREE_CRITIC_SPEC.md`、`HLE_SCORER.md` §1.2。

## 第 1 批（今天，串行，先做完再开第 2 批）

- [x] **E1. 计数器修复 + hle_201 规则 + 一次重生成**
  1. `scripts/t3_k3_adjudicate_and_recompute.py`：
     - critic 调用计数改为按轨迹事实：`LLM_CRITIC_ARMS={"C3","A3C3","C2"}`；`critic_calls_llm = Σ rounds[1:] 中 critic_direction 或 critic_fallback 非空`（仅对 LLM_CRITIC_ARMS），其他 arm 0；保留旧字段名 `critic_calls_unlogged` 作别名一版。
     - 加 hle_201 规则：两种形式（π/2^50·(C(50,25)² + 2Σ_{k=1}^{8}(−1)^k C(50,25−k)C(50,25−3k)) 与 π(50!)²/(4^25·25!)·Σ_{m=0}^{25} 1/((50−2m)! m! (m+25)!)）与 gold 精确相等 → True，理由 "exact rational equality with gold (Fraction)"；round-0 的 π·N/2^49 与 C2 r7 的 2^100 形式 → False（已有 astra 判决，不动）。
     - 把 C2（`experiments/hle400_C2/deepseek-v4-flash-payg/`）接入 ARMS。
  2. 备份 `is_correct_t3_sidecar_v2.json` / `t3_final_scores_v2.json` / `transition_metrics_v2.json` 为 `*.bak_20261108`，重生成。
  3. 验收：C2 mode 159、ceiling 198、final 148、settle 121；C3/A2/A3 所有数与 `HLE400_FROZEN_DATA.md` 一致；`critic_calls_llm` C3=2288、C2=2358、其余 0；`diff` 旧新三件套，只允许 hle_201 相关格与计数字段变化。把 diff 摘要贴进本文件。
  4. `python3 scripts/tie_and_adaptive_baselines.py` 与 `python3 scripts/judge_conditional_test.py` 各跑一次，确认输出与草稿 §3.1/§5.1/§6.3 的数一致：A3 随机 137.4、adaptive 136.5、C2 random 157.4、C3 random 150.5；Judge-R 相左 18/36=0.500、Judge-C 32/66=0.485 必须一致；**Judge-R+ 的行随覆盖变化，以当前输出为准，把整行贴进完成记录即可**（E4 补齐后再贴一次）。其余不一致即停、报。
  5. 产出 C2 的 MCQ/open 拆分（同 `by_answer_form` 口径），填到本文件。

- [x] **E2. C2 critic token 重放估计**（完成：≈23.2 M；prompt 2.6k + completion 7.2k/次，rt 区间 12.4–20.2 M）
  从 C2 轨迹随机抽 50 个反馈轮（固定种子），用冻结配置（`StrongCritic.load(model, bank_free=True)`，同 `CRITIC_REASONING_BUDGET`）重放 critic 调用，记录 prompt / completion / reasoning tokens；外推到 2358 次；给 reasoning 的区间（同 C3 的处理）。同时记 prompt 字符数分布，与 C3 的 50 次对照（C3 已有 ≈16 M 的估计口径，沿用）。产出一张四列表（arm / 50 次均值 / 外推 / 区间）。

## 第 2 批（E1 完成后开，可并行）

- [x] **E3. A2′ 扰动型安慰剂**（完成并判读：上限 170 vs C2 198，p=0.0001 → 内容有作用）（按 `A2PRIME_PERTURBING_PLACEBO_SPEC.md`）
  1. 实现 arm `A2P`（模板 critic，零 LLM 调用），五句通用 suspicion/check 写入代码常量。**（已批准跑前修订 2026-11-08，写入 spec §1）**

     **A2P 五句通用句 + 名（bank 原文 = C3 实际看到的去重词汇）**（`src/run_feedback_loop.py` 常量 `_A2P_ARCHETYPES`；每轮先抽 k，P(k=3)=.86 / P(k=2)=.11 / P(k=1)=.03，再从 5 个名中不放回抽 k 个，按 C3 多条格式渲染，零 LLM）：
     1. `constraint-blind decimation` — suspicion: "discounted a constraint or condition stated in the problem" / check: "re-read the problem statement, list every stated constraint, and confirm the answer satisfies each one"
     2. `descriptor/label conflation` — suspicion: "merged two distinct items or labels that should stay separate" / check: "list every distinct entity or label named in the problem and confirm none were merged or swapped"
     3. `procedure truncation / omission` — suspicion: "stopped short of completing every step the problem requires" / check: "enumerate the full sequence of steps the problem requires and confirm none were skipped or left unfinished"
     4. `retrieval-abort` — suspicion: "abandoned the recall or lookup of a needed fact before it was settled" / check: "confirm every fact or value used is actually stated, derived, or verifiably recalled rather than assumed"
     5. `format / precision non-conformance` — suspicion: "deviated from the requested output format or precision" / check: "re-read the requested output format and precision and confirm the answer conforms to it exactly"

     **跑前修订（2026-11-08，已批准并写入 spec §1）**：
     - **archetype = 5（非 7）**：7-archetype 词汇中 `memory_substitution`、`sign_normalization_slip` 无实例、从未进入任何 critic 调用；只用 5 个有实例的 bank 原文名，避免引入差异。
     - **随机源 = `zlib.crc32(task_id) ^ round_index`**（替代 `hash`，PYTHONHASHSEED 盐化不可复现；跨进程/跨平台确定）。
     - **方向数匹配 C2**：k 分布 86/11/3，不放回抽 k 个；模板 C3 多条格式；包装器 `_feedback_message`；summary 记 `k_draw_counts` + `archetype_draw_counts`。
     - **端点 + A-seeding**：`deepseek-v4-flash-payg`（payg，与 C2 同法）+ `A_SOURCE_TRAJ` 指向 `experiments/hle400_A/deepseek-v4-flash/loop_trajectories.jsonl`。
     - 代码已应用；单测通过：确定性 ✓、k 分布 3→86.2% / 2→10.8% / 1→3.0% ✓、无放回 ✓、名逐字 ✓、模板 C3 格式 ✓、无泄漏 ✓。

  2. smoke 5 题：dump 每轮反馈文本；验收：无题面/答案片段、五句逐字一致、`critic_direction[0].template == True`。
  3. 400 题全跑，`--out-dir hle400_A2PRIME`，其余参数与 C2 的 summary 逐字段一致（端点与 C2 同为 payg；记录在 summary）。
  4. 计分：T1→T2→T3 K=1→争议 K=3；新答案变体按 §1.2 人工裁决并追加规则表；三件套新增 `A2P`。
  5. 只填数到 `docs/A2PRIME_RESULTS.md`：上限、mode（对称约定 + recency）、final、settle、stay 不对称 + CI、switch 构成、均轮数、候选数、token；配对 McNemar：A2P vs C2 / vs A2 / vs A3（随机）。不写判读句——判读按 spec §5 由我来写。

- [ ] **E4. Judge-R+ 覆盖补齐**
  用 `recompute_evaluator_offline.freeze_switches` 在 freeze 空间重建 Q-CUT manifest；找出当前 `qcut_result.jsonl` 缺的 160 条 freeze 边；按原 Q-CUT prompt、N=2、同 thinking 设置、同锚定规则补判（先修流式/看门狗：流式累加 delta + 10 min 墙钟）；结果追加进 `qcut_result.jsonl`（加 `model`/`endpoint` 字段）。验收：`judge_conditional_test.py` 中 Judge-R+ 行 "edges with verdict" = 1201/1201、items 244/244；把新行贴到本文件。

- [ ] **E5. pairwise judge 第四行**
  把 `qcut_pairwise_result.jsonl`（302 行）映射成 `{task_id, from_r, to_r, verdict}`（`relation` → 新优/新劣/不定 的三值），加进 `judge_conditional_test.py` 作 `Judge-P`；报边级准确率、相左准确率（带 Wilson CI）、LR、覆盖。不做聚合穷举。

## 第 3 批（配额/人手允许时）

- [ ] **E6. 第二模型复现 —— 优先级提到 E3 之后立即、与 E4/E5 之前（耗时最长）**
  已备好：`docs/REPLICATION_SPEC.md`（预注册）、`data/raw/hle/hle_replication_200.json`（200 题四格分层，种子 20261108）、`scripts/probe_endpoints.py`（探测哪个端点/模型现在可用）、`scripts/run_replication.sh`（一条命令按 A → A2 → C2 → A2P → A3 顺序跑，A-seeding 自动指向该模型自己的 A 臂，resume 友好）。
  步骤：
  1. 在 Mac 上 `python3 scripts/probe_endpoints.py`。token-plan 已 429，所以预期可用的是 dashscope 上的 qwen（名字以探测结果为准）或 zhipu 上的 glm-5.3。
  2. 若可用的是 dashscope 的 qwen：在 `src/config.py` 加一个 `"qwen3.8-flash-payg"` 条目（model 用探测到的 id、base_url DASHSCOPE、key DASHSCOPE_API_KEY、thinking 预算与 deepseek 对齐：`thinking_budget 16384`，若模型不支持则记录）；若是 zhipu 的 glm-5.3：把 glm-5.3 条目的 base_url/key 改到 ZHIPU 或新建 `glm-5.3-zhipu`。选择与理由写进 `REPLICATION_SPEC.md` §1。
  3. `MODEL=<条目名> bash scripts/run_replication.sh 6`（后台 nohup，日志 `experiments/rep200_<MODEL>_run.log`）；第一段跑完**不分析**，直接 `MODEL=<条目名> TASKFILE=data/raw/hle/hle_replication_rest200.json bash scripts/run_replication.sh 6` 扩到 400（同 out-dir，resume 追加）。预先决定跑满 400；只在 400 上检验。与 E3 并行没有冲突（不同端点/模型）；如与 E3 争 payg 限速，E3 优先。
  4. 跑完按 spec §4 计分（新模型的答案变体人工裁决会多一些，预留），sidecar 写 `is_correct_t3_sidecar_rep.json`；结果只填 `docs/REPLICATION_RESULTS.md`。
  注意：A2P 分支在 `run_feedback_loop.py` 里必须对任意 `--models` 生效（检查 `_a2p_feedback` 不依赖 deepseek 专有字段）；A3 用 `--temperature 0.7`，脚本已写。
- [ ] **E7. C2 50 题 token-plan 重放**（配额恢复后）：报 mode/final 与 payg 运行的一致率。
- [ ] **E8. 冻结文档同步与归档**（E1 后任何时候）
  - `HLE400_FROZEN_DATA.md`：加上限行（154 / 190 / 191 / 198）、A3 随机平局与 A3-adaptive 注、evaluator 行指向 `EVALUATOR_RESULTS.md`、C2 行、critic_calls 字段说明。
  - `HLE_SCORER.md` §1.2：截断轮投票规则注 + hle_201 规则。
  - `EVALUATOR_FINAL_DESIGN.md` §4（± 聚合器规格错误记录）/§6（填 `_judge_audit_autogen.md`）；`EVALUATOR_FINAL_QCUT.md` 顶部 "Q-CUT = Judge-R+"。
  - `ERROR_BANK_PROVENANCE.md`：测试时 5 条词汇 + 去重取第一条实例的说明。
  - 中间方案文档（CEL / MPC / COV / QV-MPC / MOVE_PAIRWISE / CHECK_OUTCOME / lock_rule_study / 阈值 sweep / `BANK_FREE_CRITIC_PLAN.md`）移 `docs/_deprecated/`，顶部标 superseded。
- [ ] **E9. 图 F1–F6**（等我给图规格；数据源分别为 E1 三件套、`tie_and_adaptive_baselines.py`、`persistence_analysis.py`、`judge_conditional_test.py`、`selective_prediction.py`、`verifier_regimes.py`——后两个脚本由我今天归位到 `scripts/`）。

## 第 4 批（2026-11-10 起，按此顺序）

- [ ] **N1. E6 复现收尾（最高优先，最长）**
  1. A3 第 200 题跑完后**不分析**，立即 `MODEL=qwen3.8-flash-payg TASKFILE=data/raw/hle/hle_replication_rest200.json bash scripts/run_replication.sh 6` 起第二段（同 out-dir，resume 追加；起跑前 `caffeinate -s`）。
  2. 第二段跑的同时，对第一段 200 题的五臂先做计分的**机械部分**（T1 → T2 → T3 K=1），K=3 与人工裁决等 400 题齐了一起做；不出任何 R1–R4 的数。
  3. 400 题齐后：K=3 + 新变体裁决 → `is_correct_t3_sidecar_rep.json` → `REPLICATION_RESULTS.md`（只填数：五臂 init/final/settle/mode（recency + 对称约定）、上限、stay 不对称 + CI、候选数、均轮数、token；配对 McNemar：C2 vs A3、C2 vs A2、C2 vs A2P、A2P vs A2 的上限与 mode）。
  4. 顺带核三项并写进结果：每臂截断率、`reasoning_tokens` 是否触顶 16384 的比例、round 0 与 A 臂逐字一致。
- [ ] **N2. TBD-4b C3 critic token**：与 E2 完全同法（50 次重放，种子 42，`StrongCritic.load(model, bank_free=False)`），外推 2288 次，给 rt 区间；更新 `_token_cost_autogen.md` 使 C2/C3 两行同一方法。
- [ ] **N3. E4 Judge-R+ 补齐**：freeze 空间重建 manifest，补 160 条边（流式 + 墙钟已修），重跑 `judge_conditional_test.py`，把新整行贴完成记录。
- [ ] **N4. E5 pairwise judge 第四行**（纯离线）。
- [ ] **N5. E8 冻结文档同步与归档**：按原 E8 清单；另加 `HLE400_FROZEN_DATA.md` 的 A2′ 行与 C2/A2′ 配对检验、`C2_BANK_FREE_CRITIC_SPEC.md` 补"方向数 86% vs 12%"的差异说明。
- [ ] **N6. E9 图**（规格如下，数据源脚本均已在 `scripts/`；输出 `paper/figs/F*.pdf` + 生成脚本 `scripts/make_figures.py`）
  - F1 双前沿：x = 臂（A, A2, A2′, A3, C3, C2），每臂两根柱：上限（浅）与选中（深；A3 用随机平局期望 + 129–145 区间须）。
  - F2 逐轮上限曲线：A2 / A2′ / C3 / C2，x = 轮次 0–10，y = 累计"出现过正确答案"的题数。
  - F3 stay 不对称：五臂 P(stay|correct) vs P(stay|wrong) 成对柱 + 比值与 CI。
  - F4 judge：三（四）个 judge 的"相左时判对率"点 + Wilson 区间，0.5 虚线，旁标"只用计数"的准确率。
  - F5 弃权曲线：覆盖率 vs 准确率，A2 / A3 / C3 / C2（+A2′）。
  - F6 验证器 regime：q vs 实现准确率，独立误差实线、相关误差虚线，A2 / A3 / C3 / C2。
- [ ] **N7. E7**（配额恢复后）C2 50 题 token-plan 重放。

## 不做
C1-free；abstaining critic；强模型 judge；任何聚合器/evaluator 新设计；为个案重开冻结数；看过结果后改 A2′ 模板或判读。

## 完成记录（agent 填写）
| 项 | 完成时间 | 结果一行 | 文件 |
|---|---|---|---|
| E1 | 2026-11-08 | 计数器改按轨迹事实计数（LLM_CRITIC_ARMS=C3/A3C3/C2），字段 `critic_calls_llm`（旧名别名保留）；重生成后 C3=2288、C2=2358、其余 0；C2 159/148/121 不变；diff 仅 cost_solver_only 6 格 | `scripts/t3_k3_adjudicate_and_recompute.py` |
| G5 | 2026-11-11 | 只报事实：定位到 `hle_261` A2 臂 round 1。final_answer 回显题目并附答案：`Minimum number of vertices in a family of bipartite graphs covering all edges of \(K_{35}\) is **181**.`（题目原文：`What is the minimum number of vertices in a family of bipartite graphs covering all the edges of the complete graph \( K_n \) where n = 35?`）；gold=`181`（answer_type=exactMatch, shape=int）；committed_answer=`181`；finish_reason=`stop`；trajectory `is_correct=true`；冻结 sidecar v3 `A2.hle_261[1]={c:true, s:"astra_true"}`（round0/round2 为 `t1`）。复核：按冻结 T1–T3 规则应判对——回显文本内确含正确值 `181`（与 gold 精确相等），T1 未对回显文本精确匹配、由 T2 astra judge FN 救回，属合法判对，非需纠正异常。 | `experiments/hle400_A2/deepseek-v4-flash/loop_trajectories.jsonl`、`experiments/hle400/t3/is_correct_t3_sidecar_v3.json` |



### E1 diff 摘要（旧 `*.bak_20261108` vs 新）
- `t3_final_scores_v2.json`：6 处叶子全在 `cost_solver_only` —— `critic_calls_llm` 新增 ×5；`C2.critic_calls_unlogged` 0→2358。scores/paired/vs_shared_init/by_answer_form 全等。
- `k3_adjudication.json` / `is_correct_t3_sidecar_v2.json` / `transition_metrics_v2.json`：identical（0 diff）。hle_201 已在上版生效（k3 中 7 条 C2 override false→true：r1–r6 形式一、r8 形式二；round-0 π·N/2^49 与 r7 2^100 保持 false，未动），本版无新增格变化。
- `critic_calls_llm`：A/A2/A3=0，C3=2288，C2=2358（=2328+30）。
- C2 MCQ/open（by_answer_form）：mode 35/84 (0.4167) + 124/316 (0.3924)；final 30/84 + 118/316；settle 28/84 + 93/316。
- 对数 —— `tie_and_adaptive_baselines.py`：A3 随机 137.4 / adaptive 136.5 / C2 random 157.4 / C3 random 150.5，全对齐。`judge_conditional_test.py`：Judge-R 相左 18/36=0.500 ✓、Judge-C 32/66=0.485 ✓，两行与草稿/清单一致（勾 E1）；Judge-R+ 按当前覆盖取数（0.457 为新口径，非回退），完整行见下。

### Judge-R+ 完整行（当前覆盖，E4 补齐前；来源 `scripts/judge_conditional_test.py`）

- E1 边级准确率（非 UNSURE 决定性边）：140/232 = 0.603；决定性边 232/232 有裁决
- LR 三值 + 95% CI：CUT 0.72 [0.52, 0.99]；NO_CUT 1.90 [1.20, 3.02]；UNSURE 0.93 [0.06, 14.95]
- E3（dev 拟合 → test）：73 vs mode 76（+3 −6，McNemar p=0.508）
- E4（test 拟合 → dev）：72 vs mode 78（+5 −11）；LR dev/test：CUT 0.78/0.66、NO_CUT 1.72/2.04、UNSURE 0.96/0.92
- 相左准确率（judge 与 counts 不一致时）：53/116 = 0.457
- 穷举聚合（81 configs，in-sample all 400）：最大 156（+4 −2）@ ('node', 0.5, 0, 99)；≥155 配置数 32；跨半 best-on-dev→test (75,0,1) vs mode 76、best-on-test→dev (78,2,2) vs mode 78
- 覆盖 边/题：1041 边 / 242 题（freeze 全空间 1201 边 / 244 题；当前缺 160 边 / 2 题，E4 补到 1201/1201、244/244）


## 第 5 批（2026-11-10 下午）：同成本自洽采样 + USC

规格见 `docs/COST_MATCHED_SC_AND_USC_SPEC.md`（读出规则已预先写定，不得改动提示词与参数）。

| 编号 | 任务 | 规模 | 优先级 |
|---|---|---|---|
| S1 | A3 补第 10–11 个样本并按冻结协议判分 | 400 题 × 2 样本，约 10.3M token | 高，排在 E6 第二批 200 题之前或并行 |
| S2 | USC：6 个应用对象 × 400 次调用（A3 的 9/11 样本；C2、C3、A2、A2′ 轨迹） | 2400 次调用；其中 A3 的 11 样本一项依赖 S1 | 高；不依赖 S1 的 5 项可立即开始 |

注意：不改任何冻结文件；新数据写新目录/新文件；交付 `docs/COST_MATCHED_SC_RESULTS.md` 只报事实。


## 第 6 批（2026-11-11 上午）：v3 之后的收尾

背景：接口失败重跑已完成，`is_correct_t3_sidecar_v3.json` 已核对（各臂 0 条失败轮、长度一致）。以下为剩余项。

| 编号 | 任务 | 说明 |
|---|---|---|
| F1 | S1 判分 | `hle400_A3_extra` 的 800 个新答案走冻结协议 → `is_correct_t3_sidecar_A3extra.json`。同成本读出只差这一项。 |
| F2 | USC 补跑过期记录 | 重跑过的题其 USC 记录已过期：A3-9 4 题、A3-11 同 4 题、C2 1 题、C3 3 题、A2 2 题、A2′ 29 题（题号见 `api_failure_rerun_manifest.json`）。用新轨迹重跑这些行并替换。 |
| F3 | 官方计分表 v3 | 用官方计分脚本按 v3 重新生成各臂 final / settle / mode（`t3_final_scores_v3.json`），供核对 Table 2 的 settle 列。 |
| F4 | C3 三题的 judge 补跑 | hle_164、hle_179、hle_347 的 C3 轨迹已换新；对这三题的 switch 重跑 Judge-R / Judge-R+ / Judge-C，并更新 switch 清单，使第 6 节可按 v3 重算。 |
| F5 | qwen 复现修复 | 见前一批说明（61 题首答超时等）；完成后再判分。 |
| F6 | `hle400_A2` 提示词回显被判对的一轮 | 复核并记录处理结果。 |


## 第 7 批（2026-11-11 下午）：正式稿之后的收尾

状态：正式稿已成（`paper/acl/main.tex`，入口见 `docs/INDEX.md`）。第 5、6 批中已完成：S1 采样与判分、S2（除过期记录）、接口失败重跑与 v3 sidecar、qwen 五个臂及判分、`REPLICATION_RESULTS.md`。过期的过程文件已移入各 `_deprecated/` 目录（清单 `docs/_deprecated/20261111_pre_submission/MOVE_LOG.json`），请勿再往旧路径写文件。

| 编号 | 任务 | 说明 |
|---|---|---|
| G1 | 补跑过期 USC 记录 | A3-9 4 题、A3-11 4 题、C2 1、C3 3、A2 2、A2′ 29（题号见 `api_failure_rerun_manifest.json`）；替换 `usc_result.jsonl` 中对应行。 |
| G2 | C3 三题的 judge 补跑 | hle_164、hle_179、hle_347 的新轨迹：重跑 Judge-R / Judge-R+ / Judge-C，更新 switch 清单与 `r2w_w2r_switches_freezekey.jsonl`，然后重跑 `scripts/judge_conditional_test.py`。 |
| G3 | 官方计分表 v3 | 用官方计分脚本按 v3 生成 final / settle / mode（`t3_final_scores_v3.json`、`transition_metrics_v3.json`）。 |
| G4 | qwen 的 critic token 回放 | 同 deepseek 的做法，50 次回放，产出 `experiments/rep200_C2_qwen3.8-flash-payg/token_replay_summary.json`。 |
| G5 | `hle400_A2` 中 1 轮提示词回显被判对 | 复核并记录。 |

追加实验见 `docs/NEXT_EXPERIMENTS_FOR_MAIN_CONFERENCE.md`，待用户决定后另行下达。


## 第 8 批（2026-11-11 下午）：第三模型 + 收尾补跑

优先级从上到下。第 7 批的 G1–G5 并入本批，编号不变。

| 编号 | 任务 | 说明 |
|---|---|---|
| T1 | 第三模型 glm-5.3 | 严格按 `docs/THIRD_MODEL_SPEC.md`：先做 §3 的 16 题对齐门槛并回报（只报运行健康度），通过后再全量；§4 的运行保护与 critic token 逐次记录是硬要求；判分完成前不做任何对错预览。 |
| G1 | 补跑 43 条过期 USC 记录 | 见第 7 批。 |
| G2 | C3 三题的 judge 补跑 | 见第 7 批。 |
| G3 | 官方计分表 v3 | 见第 7 批。 |
| G4 | qwen 的 critic token 回放 | 见第 7 批。 |
| G5 | `hle400_A2` 提示词回显被判对的一轮 | 见第 7 批。 |

人工审计（`docs/HUMAN_AUDIT_PLAN.md`）由用户安排标注人，执行 agent 无需处理。


> **仓库整理提示（2026-11-11 14:40）**：根目录杂项、`output/`、29 个未被任何现行代码引用的 `src/` 模块、6 个旧脚本、若干旧文档已移入 `_deprecated/`（清单见各目录 `MOVE_LOG.json`，入口 `docs/INDEX.md`）。已静态检查：现行 `src/`、`scripts/`、`tests/` 中没有对被移动模块的引用。若确需其中某个文件，请移回原处并在此文件注明，不要在 `_deprecated/` 内直接运行。`.gitignore` 已加入 `audit/` 下的标注表与对照表、`usc_result.jsonl`、`astra_verdicts*.jsonl`。
