# 收口任务清单 v2（2026-11-08，v5 草稿之后；token 预算已恢复）

> 原则不变：不改任何冻结文件的规则；新 arm 一律先写 spec 再跑；判读规则在看数前写死；每个新 arm 走完整
> T1→T2→T3→K=3 计分（新答案变体按 `HLE_SCORER.md` §1.2 人工裁决）。
> 口径：freeze-key；A3 平局随机化 300 次；主比较用对称约定；dev 偶 / test 奇。

## A. 新实验（有预算才做；按价值排序）

| # | arm / 实验 | 回答什么 | 设计要点（spec 待写，模板 = `C2_BANK_FREE_CRITIC_SPEC.md`） | 预注册判读 | 规模 |
|---|---|---|---|---|---|
| **A1** | **A2′ 扰动型安慰剂** | critique 的内容有没有作用，还是任何结构化扰动都够 | critic 不读答案、不读 CoT；每轮从 5 个 archetype 名随机抽 1 个，套固定模板生成"you may have <archetype> … To check: re-verify the step most likely affected"；其余与 C2/C3 完全一致（never silent、同轮数、同早停、同预算）；无 LLM critic 调用 | 主终点上限：A2′ ≥ C2 − 5 → 内容无作用（主语改为"结构化扰动 + 序列计数"）；A2′ ≤ C2 − 15 且 p<.05 → 具体内容有作用；次终点 mode（对称约定）、stay 不对称 | 400 题，solver 调用 ≈ C2 量级，无 critic 成本 |
| **A2** | **第二模型复现** | 单模型限制 | qwen3.8-flash（或 glm-5.3）；同 400 题中按 id 分层抽 200；跑 A / A2 / A3 / C2（+A2′ 若 A1 已跑）；同循环常量；计分同协议 | 复现对象两条：C2.mode > A3.vote（对称约定）；三 judge 不做，只复现 §6 的"计数 vs 相左"检验需要 judge……改为只复现 §5：C2 vs A3、上限 C2 vs A2、持久性不对称 | 200 题 × 4–5 臂 |
| A3 | **C1-free 自我批评** | critic 是否必须是独立调用（成本） | solver 单次调用：先写 1–3 条针对上一轮答案的具体怀疑 + check，再重解；无 critic 调用；其余同 C2 | 上限与 mode 相对 C2 的差；若 ≈ C2 → 成本主张可部分恢复 | 400 题；**仅在 A1 显示内容有作用时才跑** |
| A4 | abstaining critic | 预防侧 | 自一致性门控（N=2 对换一致才发）| mode vs C2，R→W 数 | 留 future work，不排期 |

执行顺序：A1 立即（spec → smoke 5 题 → 400 题 → 计分）；A2 与 A1 并行（不同模型、不同配额池）；A3 等 A1 结果。

## B. 数据归位（无依赖，立即并行）

| # | 任务 | 验收 |
|---|---|---|
| B1 (TBD-3b) | hle_201 规则入 `t3_k3_adjudicate_and_recompute.py`；重生成三件套含 C2（159 / 198）；C2 MCQ/open；重跑 `tie_and_adaptive_baselines.py` 对数 | 冻结文件与草稿 §5.1 逐格一致 |
| B2 (TBD-4) | C2 critic token：重放 50 次 bank-free 调用外推 2 358 次，给 rt 区间 | §5.1 C2 行无占位 |
| B3 (TBD-5) | Judge-R+：按 freeze 空间重建 manifest，补 160 条边（≈320 次），重跑 `judge_conditional_test.py` | §6.3 三行覆盖 1201/1201 或脚注 |
| B4 (TBD-18) | pairwise judge（`qcut_pairwise_result.jsonl`）过 `judge_conditional_test.py` 作第四行 | 边级准确率、相左准确率、LR |
| B5 (TBD-13) | selective prediction 用冻结 vote/mode；A3 平局随机化；AUROC bootstrap | §5.5 去 provisional |
| B6 (TBD-14) | `verifier_regimes.py`：对称 q、不对称 (s,p)、相关误差（q 随候选数/难度下降）三组 | §5.6 表 + F6 |
| B7 (TBD-15) | 配额恢复后 C2 50 题 token-plan 重放，报 mode/final 一致率 | §8 一句 |
| B8 (TBD-7/8) | 冻结文档同步（FROZEN_DATA：上限行、evaluator 行、tie 规则与 A3-adaptive 注；SCORER：截断投票注 + hle_201；EVALUATOR_FINAL_DESIGN §4/§6；QCUT 头；PROVENANCE 5 条注）；中间方案文档移 `_deprecated/` | docs/ 顶层只剩论文引用文件 |

## C. 人工与写作

| # | 任务 | 要点 |
|---|---|---|
| C1 (TBD-11) | 100 题人工双标 κ | 分层：仅 critic arm 到达的题、T2 救回与 K=3 判决、MCQ/open；标注者盲于 arm |
| C2 (TBD-2) | 引用 | 加 adaptive-consistency、universal self-consistency、self-preference judge 三条线 |
| C3 (TBD-6) | 图 F1–F6 | F2 逐轮上限曲线新加 |
| C4 (TBD-9/17) | outline / PPT 同步 v5；术语表进 §3 | — |
| C5 | A1（及 A2）结果回填：§1 Findings、贡献 2、§5.1 表、§5.4、§7 H1、§8 | 判读按 spec，不改叙述框架以外的东西 |
| C6 (TBD-10) | 格式与第二 agent 只读冻结文件的数字终审 | 所有以上完成后 |
| C7 | 文字门控（`~/PycharmProjects/academic/paper-skills/paper-writing-skill`）：机械门（em-dash 已清至 ≈0、intensifier、被动语态、冗词）→ 语义门 S1–S31 → 独立 red-team（评审 agent 不看作者自评）；每节出 grep 命中清单与修复记录 | 文字定稿前 |
| C8 | 下一轮独立评审改用 `paper-review-skill` 的 ML 清单（inference-time method 行：matched-call 基线、多模型家族、held-out 任务）+ validity-threats 表，champion/adversary 两栏输出 | E6 结果回填后 |
| C9 | 引言与摘要对照 `Research-Paper-Writing-Skills` 的范式（从挑战开场 / 观察驱动）重写一版，与当前"两种读法"版并列由 PI 选 | 可立即 |

## D. 已关闭

- 端点对齐（§8 已用 `endpoint_caveat_alignment.json` 关闭，仅剩 B7 重放）
- C2 persistence + CI（T6 已落笔）
- C3 critic token（≈16 M，区间 9–20 M）
- 三 judge 覆盖口径（1201 边 / 244 题）
