# 规格：批评内容的两个对照（v1，2026-11-15 22:25，先于任何相关运行）

> 状态：作者决定"先把安慰剂相关的实验彻底做好"（2026-11-15 22:10）。本文件与 `TOKEN_YOKED_CONTROL_SPEC.md` 一起下达；下达后判据不再修改。
> 名称对照见 `INDEX.md` 第 2 节（A2P = generic-doubt loop，C2 = critique loop）。

## 1. 要拆开的东西

critique loop 与 generic-doubt loop 的差别不止"批评是否具体"。critic 的调用只能通过它写给 solver 的文字起作用（若调用照常而文字被换成通用怀疑，solver 的输入与 generic-doubt loop 完全相同，温度 0 下轨迹也相同），所以要拆的是这段文字的性质：

| 性质 | generic-doubt | 错配批评（C2X） | 只读题目的批评（C2Q） | critique |
|---|---|---|---|---|
| 由模型写成、较长、每轮不同 | 否 | 是 | 是 | 是 |
| 针对这道题 | 否 | 否 | 是 | 是 |
| 针对这个答案与推理 | 否 | 否 | 否 | 是 |

加上 token-yoked 对照（通用怀疑花同样多的 token），四个对照构成一条阶梯。reach 在哪一级上升，说明哪个性质在起作用。

三个新条件都只在 `qwen3.8-flash-payg` 上跑（理由同 `TOKEN_YOKED_CONTROL_SPEC.md` 第 2 节），同一 400 题，首答沿用 `experiments/rep200_A_qwen3.8-flash-payg/` 的第 0 轮。solver 设置、提示词、停止规则（连续三次相同即停，最多 10 个反馈轮）与 critique loop 完全相同。

## 2. 条件 C2X：错配批评（论文名 mismatched-critique loop）

- 每道题 q 配一道"供体题" q'：同答案类型（选择题 / 开放题）、不同学科、固定种子 20261115，不与自身配对。配对表 `experiments/hle400/t3/mismatch_map_qwen.json`（`scripts/make_mismatch_map.py` 生成，只含题号）。
- 第 r 个反馈轮，solver 收到的反馈 = 冻结的 qwen critique loop 在 q' 上第 r 轮的批评（`critic_direction`），用与 critique loop 相同的模板渲染（"A few possible error directions were inferred for this answer: …"）。
- q' 的批评轮数不够时循环使用：取第 ((r−1) mod n) + 1 个有批评的轮次，n 为 q' 上有批评的轮数。
- 不调用 critic。轨迹里记录供体题号与所用轮次。

## 3. 条件 C2Q：只读题目的批评（论文名 question-only critique loop）

- critic 与 critique loop 是同一模型、同一参数，但**看不到 solver 的答案和推理**，只看题目。
- 为使批评每轮不同（否则温度 0 下每轮文字相同，会混入"是否每轮更新"这一差别），critic 同时收到此前各轮已提出的怀疑的标签，并被要求不重复。
- system 提示词（在 critique loop 的 `SYSTEM_BANK_FREE` 上只改一处，其余逐字相同）：
  把 "At test time you inspect a solver's committed answer to a hard question and, using your own judgement of where answers to such questions typically go wrong, identify the most likely wrong direction(s) the answer exhibits."
  改为 "At test time you are shown a hard question, but not the solver's answer or reasoning, and, using your own judgement of where answers to such questions typically go wrong, identify the most likely wrong direction(s) an answer to this question would exhibit."
- user 提示词：
  ```
  Question:
  {question}

  The model's answer and reasoning are not shown to you.

  Suspicions already raised in earlier rounds (do not repeat them):
  {每行一个 id；第一轮写 "(none)"}

  Return a JSON object with exactly one key "directions": a list of 1 to 3 objects ranked most-likely first. Each object has three string fields:
    "id"        : a short label (at most 4 words) naming the kind of shortcoming
    "suspicion" : a past-participle clause (no leading 'the answer', no 'you may have') grounded in THIS question's specific pitfalls, still answer-free
    "check"     : a concrete gold-free self-check the solver can run to catch it
  Do not re-derive or re-solve the question. Output ONLY the JSON object.
  ```
- 渲染模板、失败处理（critic 调用失败 → 整题重跑，不回退）与 critique loop 相同。逐轮记录 critic 的 prompt / completion / reasoning token。

## 4. 运行规则与判分

与 `TOKEN_YOKED_CONTROL_SPEC.md` 第 3、4 节相同：先过 16 题健康度检查（只回报运行健康度，C2Q 另回报每轮怀疑条数分布与重复标签的比例）；含接口失败的轨迹整题重跑；不改提示词、不看中间对错。输出目录 `experiments/ctrl_C2X_qwen3.8-flash-payg/`、`experiments/ctrl_C2Q_qwen3.8-flash-payg/`；判分输出 `experiments/hle400/t3/is_correct_t3_sidecar_ctrl.json`（冻结口径，不新开争议复判）。

## 5. 读出（判据在此写定）

读出脚本 `scripts/content_controls_readout.py` 在数据到齐后由分析方编写，只实现本节。

**检验**（reached，精确 McNemar，双侧，α = .05）：
- X1：critique loop 对 C2X。X2：C2X 对 A2P。
- Q1：critique loop 对 C2Q。Q2：C2Q 对 A2P。
- 三个主检验 Y1（见 token-yoked 规格）、X1、Q1 各回答一个问题，分别报告原始 p 值，同时报告 Holm 校正后的 p 值；论文里的"显著"以校正后为准。
- 描述量：selected 之差（置换检验与 bootstrap 区间）、每题轮数与候选数、改答比例、token。

**功效**：与 Y1 相同量级。critique loop 对 A2P 现为 49/16；某个对照追回一半差距时，对应主检验的检出概率约 45%，追回四分之一时约 88%。不显著不等于差距消失，届时必须同时报告不一致对。

**判定**（限 qwen）：

| 结果 | 结论 | 论文措辞 |
|---|---|---|
| X1 显著，X2 不显著 | 批评的形式（由模型写成、较长、每轮更新）不带来 reach；批评必须针对本题 | "critique written for another question does not raise reach" |
| X1 不显著，X2 显著 | 形式本身带来了大部分 reach | 如实写明，§4.1 相应收窄：增益不能归于批评的具体内容 |
| Q1 显著 | 读答案与推理带来了只读题目带不来的 reach | "the critic's gain depends on reading the answer" |
| Q1 不显著，Q2 显著 | 针对题目的怀疑就够了，不需要读答案 | 如实写明；critique loop 的表述改为"针对题目的批评" |
| 其余组合，或主检验不显著而对应的第二项也不显著 | 没有定论 | 报告全部计数，不下结论 |

阶梯图：五个条件（A2P、token-yoked、C2X、C2Q、critique）的 reached 与 selected 并排画一张图，放附录。无论结果如何，五个条件全部报告。

## 6. 成本

C2X 约 24M token（只有 solver）；C2Q 约 36M（critic 不读推理，实际会更低）。加 token-yoked 的 36M，三项合计约 96M，另加判分调用。

## 7. 给执行 agent 的指令（原样转发）

```
任务 X1 / Q1（规格：docs/CONTENT_CONTROLS_SPEC.md，判据已冻结，只执行、不改判读）。与任务 Y1 可并行。

1. 代码：src/run_feedback_loop.py 新增两个 arm，其余逻辑（A 首答 seeding、solver 参数与提示词、--max-rounds 10 --early-stop 3、反馈渲染模板）与 C2 完全相同。
   - C2X：不调用 critic。读取 experiments/hle400/t3/mismatch_map_qwen.json 的 donor[task_id]；第 r 个反馈轮使用冻结轨迹 experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl 中供体题第 ((r-1) mod n)+1 个 critic_direction 非空的轮次（n 为该供体题此类轮次数），用 C2 的渲染函数生成反馈文本。轨迹记录 donor_task_id 与 donor_round。
   - C2Q：调用 critic，但 critic 只看题目。system 与 user 提示词按规格第 3 节逐字实现（system 只改规格写明的那一处）；"已提出的怀疑"取本题此前各轮 critic_direction 的 archetype_name。critic 调用失败不回退，整题重跑。逐轮记录 critic 的 prompt/completion/reasoning token。
2. 各先跑 16 题健康度检查（与 Y1 同一组题），只回报：完成/超时、截断率、每题轮数、token；C2Q 另回报每轮怀疑条数分布、与此前轮次标签重复的比例。不要计算或查看对错。回报后等待确认。
3. 确认后各跑全量 400 题：MODEL=qwen3.8-flash-payg，--temperature 0，输出目录 experiments/ctrl_C2X_qwen3.8-flash-payg/ 与 experiments/ctrl_C2Q_qwen3.8-flash-payg/，A_SOURCE_TRAJ 同 Y1。
4. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。
5. 判分：冻结口径（同 scripts/gen_t3_sidecar_rep.py），输出 experiments/hle400/t3/is_correct_t3_sidecar_ctrl.json（两个 arm 各一节）；不新开 K3 争议。
6. 完成后回报：轮数与 token 的描述统计、失败与重跑清单、文件路径。不要自行做 reach / selected 的比较。
7. 不提交 audit/ 下的标注表与 key.json；提交信息沿用 [P2.x] 编号。
```
