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

- [ ] **E2. C2 critic token 重放估计**
  从 C2 轨迹随机抽 50 个反馈轮（固定种子），用冻结配置（`StrongCritic.load(model, bank_free=True)`，同 `CRITIC_REASONING_BUDGET`）重放 critic 调用，记录 prompt / completion / reasoning tokens；外推到 2358 次；给 reasoning 的区间（同 C3 的处理）。同时记 prompt 字符数分布，与 C3 的 50 次对照（C3 已有 ≈16 M 的估计口径，沿用）。产出一张四列表（arm / 50 次均值 / 外推 / 区间）。

## 第 2 批（E1 完成后开，可并行）

- [ ] **E3. A2′ 扰动型安慰剂**（按 `A2PRIME_PERTURBING_PLACEBO_SPEC.md`）
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

## 不做
C1-free；abstaining critic；强模型 judge；任何聚合器/evaluator 新设计；为个案重开冻结数；看过结果后改 A2′ 模板或判读。

## 完成记录（agent 填写）
| 项 | 完成时间 | 结果一行 | 文件 |
|---|---|---|---|
| E1 | 2026-11-08 | 计数器改按轨迹事实计数（LLM_CRITIC_ARMS=C3/A3C3/C2），字段 `critic_calls_llm`（旧名别名保留）；重生成后 C3=2288、C2=2358、其余 0；C2 159/148/121 不变；diff 仅 cost_solver_only 6 格 | `scripts/t3_k3_adjudicate_and_recompute.py` |



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
