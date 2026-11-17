# 规格：批评内容的两个对照（v2.2，2026-11-15 23:15，先于任何全量运行）

> 状态：与 `TOKEN_YOKED_CONTROL_SPEC.md` 一起下达；下达后判据不再修改。v1（同日 22:25，存 `docs/_deprecated/20261115_v13_alignment/`）在外部意见后修订，修订时没有任何相关运行存在。改动：不再称"阶梯"，改为成对比较加性质表；供体批评按长度匹配；写明错配批评可能有害时如何解释；C2Q 增加长度报告、混淆标记与人工抽查；解释表改为"可以说 / 不能说"。
> 名称对照见 `INDEX.md` 第 2 节（A2P = generic-doubt loop，C2 = critique loop）。

## 1. 目的与读法

目的不是证明某一个因素单独起作用，而是把对"critique loop 到达更多"的替代解释逐个缩小。

五个条件在多个性质上同时变化，**不构成一维阶梯**。论文里只做成对比较，并附下面的性质表；不写"reach 在哪一级上升就说明哪个性质起作用"。

| 条件 | critic 调用 | 针对本题 | 读答案与推理 | 反馈由模型写成、每轮不同 | 总 token |
|---|---|---|---|---|---|
| A2P（generic-doubt） | 无 | 否 | 否 | 否 | 低 |
| A2PY（token-yoked） | 无 | 否 | 否 | 否 | 与 critique 对齐 |
| C2X（mismatched critique） | 无（复用已有批评） | 否 | 否 | 是 | 见 2.3 |
| C2Q（question-only critique） | 有 | 是 | 否 | 是 | 略低于 critique |
| C2（critique） | 有 | 是 | 是 | 是 | 基准 |

关于 critic 调用：调用只能通过它写给 solver 的文字起作用。若调用照常而文字被换成通用怀疑，solver 的输入与 generic-doubt loop 完全相同，温度 0 下轨迹也相同。所以不单独为"多一次调用"设对照；论文里把这一点写明。

三个新条件都只在 `qwen3.8-flash-payg` 上跑，同一 400 题，首答沿用 `experiments/rep200_A_qwen3.8-flash-payg/` 的第 0 轮。C2X、C2Q 的 solver 设置、提示词、停止规则（连续三次相同即停，最多 10 个反馈轮）与 critique loop 完全相同。

## 2. 条件 C2X：错配批评（论文名 mismatched-critique loop）

### 2.1 定义
- 每道题 q 配一道供体题 q'：同答案类型（选择题 / 开放题）、不同学科、**在冻结的 critique loop 里批评的平均长度处于同一三分位**、固定种子 20261115，不与自身配对。配对表 `experiments/hle400/t3/mismatch_map_qwen.json`（`scripts/make_mismatch_map.py`，只含题号）。配对后供体批评与本题批评的平均长度为 1,650 对 1,645 字符，平均条数 2.96 对 2.96。
- 第 r 个反馈轮，solver 收到的反馈 = 冻结的 qwen critique loop 在 q' 上第 r 轮的批评（`critic_direction`），用与 critique loop 相同的模板渲染。q' 的批评轮数不够时循环使用：取第 ((r−1) mod n) + 1 个有批评的轮次。
- 不调用 critic。轨迹里记录供体题号、所用轮次、渲染后反馈的字符数。

### 2.2 错配批评可能有害
别的题的批评可能把 solver 带偏。因此 critique 对 C2X 的差别（X1）可能来自"错配有害"，不一定来自"针对本题有益"。用 X2（C2X 对 A2P）区分：C2X 显著低于 A2P 时，判为"错配批评有害"，X1 不能单独归因于针对本题的好处。

### 2.3 不做 live 版本与"只调用、丢弃输出"的条件，及 token 的记法
外部意见建议让 critic 现场为供体题生成批评，使调用次数和 token 也对齐。本规格不做：现场生成的批评与冻结轨迹里的批评出自同一 critic、同一题目，分布相同，solver 看到的输入没有差别，只是多花约 12M token。进一步说，critic 在温度 0 下对同一输入（供体题及其当时的答案与推理）会给出同一段批评，现场调用得到的就是冻结轨迹里的那段文字。同理不设"critic 照常调用但输出丢弃"的条件：solver 的输入与 generic-doubt loop 逐字相同，温度 0 下得到的就是 A2P 的轨迹，这个条件只会测到接口的运行间波动。
token 表里 C2X 按"solver token + 所用供体批评当初的生成成本（每次 4,816 token）"记账，并注明这部分是复用而非现场调用。

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
- 渲染模板与 critique loop 相同。**critic 失败的处理也与 critique loop 相同**（v2.2 更正，见文末）：critic 调用失败或返回空的怀疑列表时重试一次，仍失败则该轮改用中性句 "No confident error direction was found for this answer."，并记 `critic_fallback=True`；不因此整题重跑。solver 调用失败仍按规则整题重跑。逐轮记录 critic 的 prompt / completion / reasoning token，以及渲染后反馈的字符数与怀疑条数。
- 不为凑长度而改提示词（那会使它与 critique loop 的 critic 在更多地方不同）。改为事后报告并预先写定标记规则：若 C2Q 渲染后反馈的平均字符数低于 critique loop 的 70%，或三条怀疑的轮次占比与 critique loop 相差超过 15 个百分点，则 Q1 在论文中标为"与反馈长度混淆"。
- **人工抽查**：全量跑完后按固定种子抽 30 条 C2Q 的批评（不带任何对错信息），由作者逐条判三项：是否与同题此前轮次重复；是否泛泛而谈（换一道题也成立）；是否含有答案。另用现有的字符串检查统计"批评文本含 solver 下一答案"的比例。结果写入附录；不参与判定。

## 4. 运行规则与判分

与 `TOKEN_YOKED_CONTROL_SPEC.md` 第 3、4 节相同：先过 16 题健康度检查（只回报运行健康度，C2Q 另回报每轮怀疑条数分布与重复标签的比例）；含接口失败的轨迹整题重跑；不改提示词、不看中间对错。输出目录 `experiments/ctrl_C2X_qwen3.8-flash-payg/`、`experiments/ctrl_C2Q_qwen3.8-flash-payg/`；判分输出 `experiments/hle400/t3/is_correct_t3_sidecar_ctrl.json`（冻结口径，不新开争议复判）。

## 5. 读出（判据在此写定）

读出脚本 `scripts/content_controls_readout.py` 在数据到齐后由分析方编写，只实现本节。

**检验**（reached，精确 McNemar，双侧，α = .05）：
- X1：critique loop 对 C2X。X2：C2X 对 A2P。
- Q1：critique loop 对 C2Q。Q2：C2Q 对 A2P。
- 三个主检验 Y1（见 token-yoked 规格）、X1、Q1 分别报告原始 p 值和 Holm 校正后的 p 值；论文里的"显著"以校正后为准。三个都报告，不只报显著的。
- 描述量：selected 之差（置换检验与 bootstrap 区间）、每题轮数与候选数、改答比例、token、各条件反馈长度与条数的分布。
- 操纵检查（描述，不参与判定）：(i) 反馈与题目的相关程度——反馈文本与题目文本的词汇重合率（去停用词后的 Jaccard），五个条件分别报告，预期 C2X 明显低于 C2Q 与 critique；(ii) 反馈长度与条数；(iii) 每轮改答比例；(iv) 每题候选数；(v) 各条件总 token。C2X、C2Q 不做 token 对齐（对齐需要改停止规则，而何时停止本身是反馈的效果）；token 只作为检查量报告，token 这一替代解释由 Y1 单独回答。

**功效**：与 Y1 相同量级。critique loop 对 A2P 现为 49/16；某个对照追回四分之一差距时主检验的检出概率约 88%，追回一半时约 45%。不显著不等于差距消失，届时必须同时报告不一致对与区间，不写"无效果"。

**解释表**（限 qwen；成对比较，不拼成一条因果链）：

| 结果 | 可以说 | 不能说 |
|---|---|---|
| Y1 显著 | reach 优势不只是多花 token | 不能说是批评的内容单独起作用 |
| Y1 不显著，Y2 显著 | 与"多花计算"相容 | 不能说内容不重要 |
| Y1 不显著，Y2 不显著 | 没有定论 | — |
| X1 显著，X2 不显著 | 为别的题写的批评替代不了本题的批评；批评的形式本身没有带来 reach | 不能完全排除供体批评的误导 |
| X1 显著，C2X 显著低于 A2P | 错配批评有害 | 不能把 X1 归因于针对本题的好处 |
| X1 不显著，X2 显著 | 批评的形式（模型写成、较长、每轮更新）就带来了大部分 reach | 不能说针对本题没有用 |
| Q1 显著（且未被标为与长度混淆） | 读答案与推理带来了只读题目带不来的 reach | 若被标为混淆，只能说两者有差别，不归因于读答案 |
| Q1 不显著，Q2 显著 | 针对题目的怀疑带来了大部分 reach | 不能说读答案完全没有用 |
| 其余组合 | 没有定论，报告全部计数 | — |

论文呈现：附录一节 "Token-Yoked and Content Controls"，含性质表、成对比较表（五个条件的 reached、selected、token、反馈长度；各对比较的不一致对与 p 值）、抽查结果。无论结果如何，五个条件全部报告。§4.1 "Is it only more tokens?" 与相邻段落按解释表重写。关键句预先写定：
"The token-yoked control matches total tokens, not the critic call. The content controls vary question-specificity and access to the answer; they are reported as pairwise contrasts, not as a single causal ladder."

## 6. 成本

C2X 约 24M token（只有 solver）；C2Q 约 36M（critic 不读推理，实际会更低）。加 token-yoked 的 36M，三项合计约 96M，另加判分调用。

## 7. 给执行 agent 的指令（原样转发）

```
任务 X1 / Q1（规格：docs/CONTENT_CONTROLS_SPEC.md v2，判据已冻结，只执行、不改判读）。Y1 先启动；X1 / Q1 可随后并行。

1. 代码：src/run_feedback_loop.py 新增两个 arm，其余逻辑（A 首答 seeding、solver 参数与提示词、--max-rounds 10 --early-stop 3、反馈渲染模板）与 C2 完全相同。
   - C2X：不调用 critic。读取 experiments/hle400/t3/mismatch_map_qwen.json 的 donor[task_id]；第 r 个反馈轮使用冻结轨迹 experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl 中供体题第 ((r-1) mod n)+1 个 critic_direction 非空的轮次（n 为该供体题此类轮次数），用 C2 的渲染函数生成反馈文本。轨迹记录 donor_task_id、donor_round、渲染后反馈的字符数。
   - C2Q：调用 critic，但 critic 只看题目。system 与 user 提示词按规格第 3 节逐字实现（system 只改规格写明的那一处）；"已提出的怀疑"取本题此前各轮 critic_direction 的 archetype_name。critic 失败的处理与 C2 完全相同：重试一次，仍失败则该轮用 A2_PLACEBO_FEEDBACK 并记 critic_fallback=True（v2.2 更正）。逐轮记录 critic 的 prompt/completion/reasoning token、渲染后反馈的字符数与怀疑条数。
2. 各先跑 16 题健康度检查（与 Y1 同一组题），只回报：完成/超时、截断率、每题轮数、token；两者都回报渲染后反馈的字符数分布；C2Q 另回报每轮怀疑条数分布、与此前轮次标签重复的比例。不要计算或查看对错。回报后等待确认。
3. 确认后各跑全量 400 题：MODEL=qwen3.8-flash-payg，--temperature 0，输出目录 experiments/ctrl_C2X_qwen3.8-flash-payg/ 与 experiments/ctrl_C2Q_qwen3.8-flash-payg/，A_SOURCE_TRAJ 同 Y1。
4. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。
5. 判分：冻结口径（同 scripts/gen_t3_sidecar_rep.py），输出 experiments/hle400/t3/is_correct_t3_sidecar_ctrl.json（两个 arm 各一节）；不新开 K3 争议。
6. 完成后回报：轮数与 token 的描述统计、失败与重跑清单、文件路径。不要自行做 reach / selected 的比较。
7. 不提交 audit/ 下的标注表与 key.json；提交信息沿用 [P2.x] 编号。
```

## 更正记录

**v2.2（2026-11-15 23:15）。** v2.1 写的是"C2Q 的 critic 失败 → 整题重跑，不回退"，并称这与 critique loop 相同。核对代码后发现不同：critique loop（C2）在 critic 重试一次仍失败时，该轮回退为中性句并记 `critic_fallback=True`（qwen 的冻结运行里有 10 个这样的轮次，占 0.4%）。为使 C2Q 与 C2 只在规格写明的地方不同，改为相同的处理。另一个理由是温度 0 下 critic 的失败可能是确定性的，整题重跑会反复失败。更正时只有 16 题健康度检查在运行，没有全量运行，也没有查看任何对错。回退轮次的数量在读出时报告。
