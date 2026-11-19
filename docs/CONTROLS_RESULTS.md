# 结果：token-yoked 与内容对照（qwen3.8-flash，400 题；2026-11-16 读出）

规格：`TOKEN_YOKED_CONTROL_SPEC.md` v2.1、`CONTENT_CONTROLS_SPEC.md` v2.2。读出脚本：`scripts/controls_readout.py`（两份规格的读出合在一个脚本里），输出 `experiments/hle400/t3/controls_readout.json`。读出在判分完成后进行一次；此前只看过运行健康度（`scripts/control_health.py`）。名称对照见 `INDEX.md` 第 2 节。

## 1. 运行与判分核对
- 三个条件各 400 题，无重复、无接口失败、无截断；首答与原首答 400/400 一致。
- token-yoked：总 token 38.00M，为 critique loop（36.22M）的 104.9%；触顶（100 轮）0 题。**对齐成立**。通用怀疑的内容与原 generic-doubt 运行在共有轮次上完全一致。
- 错配批评：1,647 轮反馈与冻结轨迹里供体题的批评逐字一致，供体全部符合配对表。
- 只读题目的批评：相邻两轮内容完全相同 0/1,892；critic 回退为中性句 4 轮（critique loop 为 10 轮）。
- 判分：执行 agent 把三个新条件写进了冻结的 `is_correct_t3_sidecar_rep.json`。核对后原有五个条件的内容逐字未变；已把新条件拆到 `is_correct_t3_sidecar_yoke.json` 与 `is_correct_t3_sidecar_ctrl.json`，并把冻结文件恢复为已提交的版本（合并版另存为 `is_correct_t3_sidecar_rep_with_controls_20261116.json`）。逐轮判分数与轨迹轮数一致；首答判分与原首答一致；同一候选答案在新旧条件间判分不同的有 3 个（共 2,211 个共有候选），按冻结规则保留。

## 2. 五个条件（reassuring loop 作参考）

| 条件 | reached | selected | conversion | 反馈轮数/题 | 候选数/题 | 改答比例 | token（solver + critic） | 反馈字符数 | 与题目的词汇重合 |
|---|---|---|---|---|---|---|---|---|---|
| reassuring | 123 | 90.8 | .74 | 4.24 | 2.11 | .40 | 15.2M | — | — |
| mismatched critique | 120 | 93.5 | .78 | 4.12 | 2.07 | .40 | 15.3M（+7.9M 为复用批评当初的成本） | 1,645 | .011 |
| generic doubt | 149 | 95.6 | .64 | 5.41 | 2.94 | .56 | 21.0M | 538 | .013 |
| question-only critique | 161 | 95.3 | .59 | 5.73 | 3.18 | .59 | 22.9M + 9.1M | 1,490 | .078 |
| token-yoked generic doubt | 181 | 92.0 | .51 | 16.66 | 4.49 | .45 | 38.0M | 537 | .011 |
| critique | 182 | 114.1 | .63 | 6.54 | 3.62 | .67 | 23.6M + 12.6M | 1,647 | .078 |

操纵检查成立：错配批评与题目的词汇重合（.011）与通用怀疑相同，远低于两种针对本题的批评（.078）；错配批评的长度与 critique 相同。只读题目的批评长度为 critique 的 90%，三条怀疑的占比 .99 对 .95，**未被标为与长度混淆**。只读题目的 critic 文本含 solver 下一答案的比例 79/1,096（7%）。

## 3. 预先写定的检验（reached，精确 McNemar）

| 检验 | 只有前者 / 只有后者 | p | Holm p |
|---|---|---|---|
| **Y1** critique 对 token-yoked（全部轮次） | 32 / 31 | 1.00 | 1.00 |
| Y1 辅口径（预算内的轮次，reached 174） | 35 / 27 | .37 | — |
| Y2 token-yoked 对 generic doubt | 42 / 10 | <.0001 | — |
| **X1** critique 对 mismatched | 72 / 10 | <.0001 | <.0001 |
| X2 mismatched 对 generic doubt | 9 / 38 | <.0001 | — |
| **Q1** critique 对 question-only | 48 / 27 | .020 | .041 |
| Q2 question-only 对 generic doubt | 34 / 22 | .14 | — |

## 4. 按规格的解释表得到的结论（限 qwen）

- **Y1 不显著、Y2 显著 →"与多花计算相容"。** 通用怀疑花掉同样多的 token 后到达 181 题，critique loop 182 题，不一致对 32/31。这不是功效不足造成的不显著：两个数字几乎相同。按规格，不写成"内容不重要"。
- **X1 显著，且错配批评显著低于通用怀疑 →"错配批评有害"一行**：按规格，X1 不能归因于"针对本题有益"。补充的参考比较（非预先写定）：错配批评与 reassuring loop 无差别（17/20；改答比例都是 .40，轮数 4.12 对 4.24）。更贴切的描述是 solver 把文不对题的批评当作没有反馈，而不是被带偏。由模型写成、较长、每轮更新这些形式本身没有带来 reach。
- **Q1 显著（校正后 p = .041），未被标为与长度混淆 →"读答案与推理带来了只读题目带不来的 reach"。** 但须连同 Y1 一起读：只读题目的批评 loop 停得更早（5.73 对 6.54 轮，总 token 为 critique loop 的 88%），而 Y1 表明 token 本身就能带来 reach，所以这 21 题的差别不能完全归于"读答案"。Q2 不显著（161 对 149）。

## 5. selected（描述性，规格里不参与判定）

| 比较 | 差 | 95% 区间 | p |
|---|---|---|---|
| critique − token-yoked | +22.1 | [9.0, 35.8] | .002 |
| critique − mismatched | +20.6 | [6.5, 36.2] | .006 |
| critique − question-only | +18.7 | [4.9, 32.8] | .007 |
| critique − generic doubt（原有） | +18.5 | [3.9, 34.3] | .019 |
| token-yoked − generic doubt | −3.6 | [−14.2, 7.5] | .52 |

四个对照的 selected 都在 91–96 之间，与 reassuring loop（90.8）无差别；只有 critique loop 是 114.1。token-yoked 把 reach 从 149 提到 181，selected 却没有动（95.6 → 92.0），conversion 从 .64 降到 .51。

**这组数字的读法与限制。** 在 qwen 上，reach 可以用 token 买到，而 selected 的增益只出现在读了答案的批评里。但是：(i) 这些 selected 比较在规格里是描述性的，不是主检验；(ii) 五个比较共用同一次 critique loop 运行，不是五次独立的证实；(iii) qwen 是三个模型里 selected 增益最大的一个，只有这一个模型做了对照。它们把"critique 是否提高 selection"变成了一个值得用新题正式检验的假设（`MODEL_DEPENDENCE_SPEC.md` 的 P1），本身不构成确认。

## 6. 待办
- 只读题目的批评的 30 条人工抽查：`audit/controls_spotcheck_20261116/question_only_critic_spotcheck.xlsx`（待作者填写）。
- 论文改写（§4.1、摘要第一条、Discussion、附录 "Token-Yoked and Content Controls"）：待作者确认叙事后进行。

---

## 2026-11-17 Equal-token continuation (qwen) and token-yoked generic doubt (MiniMax)

Script: `scripts/equal_token_readout.py` → `experiments/hle400/t3/equal_token_readout.json`. Specs: `EQUAL_TOKEN_CONTROLS_SPEC.md` v4 §5, `TOKEN_YOKED_MINIMAX_ADDENDUM.md`. Read out once, after the audit of run statistics.

**Audit.** All three continued runs keep the earlier rounds byte-identical (400/400) and the earlier verdicts unchanged; no failed calls; frozen sidecars untouched. Token alignment (per question, up to the budget round) 1.043 / 1.048 / 1.086 of the critique loop's 36.22M; 7 reassuring-loop questions stop at 100 rounds short of budget (criterion ≤20). MiniMax token-yoked: 42.75M vs 40.36M (1.059), 0 at the cap.

**qwen, 400 questions, equal tokens per question** (critique loop: reached 182, selected 114.1)

| Feedback | Natural stop: reached / selected / tokens | Equal tokens: reached / selected | Critique vs it, reached (only critique / only control) | Critique − it, selected |
|---|---|---|---|---|
| Reassuring | 123 / 90.8 / 15.2M | 159 / 87.7 | E3 45/22, p=.007, Holm .020 | +26.4 [12.7, 41.8] |
| Mismatched critique | 120 / 93.5 / 15.3M | 166 / 96.8 | E2 37/21, p=.048, Holm .096 | +17.3 [3.9, 31.5] |
| Generic doubt | 149 / 95.6 / 21.0M | 181 / 92.0 | 32/31, p=1 | +22.1 [9.0, 35.8] |
| Question-only critique | 161 / 95.3 / 32.0M | 179 / 91.8 | E1 35/32, p=.81, Holm .81 | +22.3 [8.4, 36.8] |

- Every control reaches more when continued (38/2, 47/1, 42/10, 26/8; all p<.01); none selects more (−3.1, +3.3, −3.6, −3.5).
- Between controls at equal tokens: generic doubt ≈ question-only (24/22); both above reassuring (39/17, 36/16); mismatched in between (vs reassuring 25/18, p=.36).
- Exact matches only, critique − control: +11.9 [0.2, 23.6], +8.1 [−1.5, 17.8], +10.7 [−0.8, 21.8], +9.1 [−1.8, 19.8]; exact-match share of selected 0.60–0.64 in all five loops.
- Question-only strata: already over budget (135) critique 63 vs 67; continued (265) 119 vs 112.
- "All rounds" view gives the same pattern (question-only 187 reached at 1.236 of the tokens).

**MiniMax, 400 questions**

| Loop | Reached | Selected |
|---|---|---|
| Reassuring | 125 | 101.7 |
| Generic doubt | 128 | 102.3 |
| Token-yoked generic doubt | 156 (within budget 149) | 96.0 (98.3) |
| Critique | 152 | 106.9 |

Y1 critique vs token-yoked 21/25, p=.66 (within budget 25/22, p=.77). Y2 token-yoked vs generic doubt 39/11, p=.0001. Selected, critique − token-yoked +10.9 [−0.5, 22.3], p=.08 (exact matches only +7.2 [−2.0, 17.1]); token-yoked − generic doubt −6.3 [−17.4, 4.2].

**Reading.** (1) Reach: on two models, generic doubt given the critique loop's tokens reaches as many questions as the critique loop; on qwen a critique that never reads the answer does too. Reach is bought with tokens plus any feedback that makes the model change its answer; reassurance buys less. (2) Selected: extra tokens never raise it. On qwen the critique loop is ahead of all four equal-token controls by 17–26 questions (descriptive; all four comparisons share one critique run; smaller and mostly not separable from zero under exact matching). On MiniMax the margin is +10.9 with an interval that touches zero. The pre-specified test of (2) is S1 on 800 new qwen questions.

---

## 2026-11-17 Confirmation on 800 new questions (qwen) — `SELECTION_CONFIRMATION_SPEC.md` v1.1

Script: `scripts/selection_confirmation_readout.py` → `experiments/hle400/t3/selection_confirmation_readout.json`. Read out once, after all runs and scoring were complete.

**Audit.** 800/800 questions in each of five conditions (hle_401–hle_1200); 0 failed calls; 2 truncated rounds of 12,967 (token-yoked); scoring written to the new file `is_correct_t3_sidecar_confirm.json`, round counts match, first-answer verdicts identical across the five conditions; frozen score files untouched (verdict cache `astra_verdicts_rep.jsonl` only appended). Budget = logged solver + critic tokens of the new critique run on every question.

**4.1 Token alignment.** Token-yoked 69.24M vs critique 66.24M (1.045); 0 questions at the cap → aligned.

| Loop | Reached | Selected | Conversion | Tokens |
|---|---|---|---|---|
| First answer | 148 | 148.0 | — | 5.5M |
| Reassuring | 245 | 168.5 | .69 | 25.7M |
| Generic doubt | 287 | 183.2 | .64 | 36.3M |
| Token-yoked generic doubt | 363 | 181.5 | .50 | 69.2M |
| Critique | 348 | 205.3 | .59 | 66.2M |

**4.2 Confirmatory (selected).** S1 critique − token-yoked **+23.8 [5.9, 42.3], p=.008, Holm .008 → confirmed**. S2 critique − reassuring **+36.8 [17.4, 57.3], p=.0003, Holm .0006 → confirmed**.

**4.3 Equivalence (reached).** R1 critique − token-yoked −15, 90% interval [−32, +2], inside ±33 → **equivalent** (lower end one question from the bound; discordant 51/66, p=.20).

**4.4 Secondary.** Reached: critique vs reassuring 133/30, vs generic doubt 101/40, token-yoked vs generic doubt 102/26 (all p<.0001). Selected: critique − generic doubt +22.1 [4.4, 40.5]; token-yoked − generic doubt −1.8 [−15.8, 13.5]. Exact matches only: S1 +17.3 [1.4, 33.0], S2 +25.9 [8.2, 42.5], R1 −15 (90% [−31, +1]); exact-match share of selected .66–.67 in the four loops. Within budget: S1 +28.3 [10.4, 46.8], R1 −6 (90% [−24, +12]). Pooled 1,200 (exploratory): S1 +46.0 [23.0, 69.2], S2 +60.1 [35.0, 85.6].
By subject (new 800): selected difference critique − token-yoked positive in 8 of 8 subjects, − reassuring in 6 of 8 (negative: Computer Science −0.8, Engineering −1.0), − generic doubt in 6 of 8 (Humanities −3.3, Engineering −0.5). Reach vs token-yoked: critique ahead in 4 of 8; behind in Math 12/32 and Physics 3/9. By answer type: S1 +18.4 on exact-match questions, +5.5 on multiple choice.
Not in the spec, reported for transparency: by draw, S1 is +4.8 [−6.6, 17.5] on the first 400 new questions and +19.0 [5.9, 32.0] on the second; S2 +13.6 and +23.2.

**Verdict under 4.6 (first row):** on qwen, more tokens buy reach, not selection; critique that reads the answer raises selection. Limited to qwen.

**补记（2026-11-17 深夜，SciPy 独立复算）。** `scripts/crosscheck_stats.py`：不一致对、差值、精确 McNemar p 值完全一致；置换检验 p 值最大相差 0.0012；区间端点最大相差 1.3 题。R1 的 90% 区间按事先写定的做法（2,000 次重抽样）为 [−32, +2]；SciPy 用 10,000 次重抽样为 [−33, +3]；正态近似为 [−32.8, +2.8]。按写定的做法判定仍为"等价"，但下端落在界限上：可靠的是"critique 的 reach 不比 token-yoked 多"，"不比它明显少"则在边界上。

---

## 2026-11-18 Repeated runs (V1, `RUN_VARIANCE_SPEC.md`) — descriptive

Script: `scripts/run_variance_readout.py` → `experiments/hle400/t3/run_variance_readout.json`. qwen, first 400 new questions (hle_401–800), same inputs. Audit: 400/400 each, 0 failed calls, score file `is_correct_t3_sidecar_confirm_rerun.json` complete, first-answer verdicts identical to the first run, token-yoked rerun at 1.050 of budget.

| Loop | Run 1: reached / selected | Run 2: reached / selected | Selected, run 2 − run 1 | SD of that difference (sum over 400) | Same plurality answer |
|---|---|---|---|---|---|
| Critique | 179 / 98.5 | 175 / 94.8 | −3.7 | 5.8 | 49% of questions |
| Token-yoked generic doubt | 178 / 93.6 | 178 / 83.2 | −10.4 | 5.5 | 60% |

**[2026-11-18 15:50 作废] 本节 V1 的读出无效：第二次运行的判分中有 901 轮（A2PYr 807 轮、C2r 94 轮）的裁判调用失败后被记为"错误"，从未真正判分（见文末"判分事故"）。待补判后用同一脚本重读。以下数字仅留作记录。**

Selected, critique − token-yoked, on these 400 questions for the four pairings of runs: +4.8, +15.2, +1.2, +11.5 (mean +8.2). The spread across pairings (14 questions) is as large as the difference between the two draws of questions in the confirmation (+4.8 and +19.0). Run-to-run variation is independent across questions and is therefore already part of the question-level bootstrap interval of S1; S1 is not re-read.

## 2026-11-18 Screening of candidate second benchmarks (B0) — first answers only, preliminary scoring by the analyst

qwen, T=0 first answers, 0 failed calls. BBEH scored with the benchmark's own `evaluate.py`; GSM8K by numeric equality of the last boxed number; OlymMATH by the repository's string fallback only (its primary scorer `math_verify` is not installed here), so the OlymMATH figures are approximate.

- BBEH (35 per task, 805): 387 correct = 48.1%. By task: 10 tasks at 10–40% (multistep_arithmetic .11, nycc .11, geometric_shapes .17, sportqa .20, hyperbaton .23, temporal_sequence .23, zebra_puzzles .26, linguini .29, sarc_triples .29, shuffled_objects .34), 10 tasks at 40–80%, 3 tasks at ≥80% (time_arithmetic .80, object_counting .83, boardgame_qa .97).
- OlymMATH: EASY 87–92%, HARD 60–63% (100 each).
- GSM8K (200): 97.5%.


---

## 2026-11-18 判分事故：裁判调用失败被记为"错误"（三个判分文件作废，待补判）

**发现经过。** 2026-11-18 按规格读出了 qwen 附加检验（T-A3、T-Q）与 deepseek 新 800 题（D-S1、D-S2、D-A3、D-R1）。作者要求复查 deepseek 是否误判。复查发现 deepseek 新题上"裁判接受"的比例只有 2.1%–2.6%（第一批题为 15%–16%；qwen 两批题都是 8%–9%）。追查判分缓存 `astra_verdicts_confirm.jsonl`：18,874 条中有 8,106 条的 `served_model` 为 `ERR:PermissionDeniedError` 等接口错误，`c` 被写成 False。这些答案从未被裁判判过，却按"错误"计入。

**影响范围**（`scripts/audit_grader_errors.py`）。
| 判分文件 | 未判分的轮数 |
|---|---|
| `is_correct_t3_sidecar_confirm.json`（qwen S1：A、A2、A2P、C2、A2PY） | **0，未受影响**；S1、S2、R1 的读出有效 |
| `is_correct_t3_sidecar_confirm_rerun.json`（V1） | C2r 94，A2PYr 807 |
| `is_correct_t3_sidecar_confirm2.json`（qwen A3、C2Q、C2QY） | 314、134、166 |
| `is_correct_t3_sidecar_confirm_ds.json`（deepseek 六个条件） | 409、1961、2386、3194、4079、5698（约占裁判轮次的 65%） |
更早的判分缓存（第一批题、对照、等 token 续跑、MiniMax）没有这类错误条目。

**处理（在补判之前写定）。**
1. 上述三个文件的读出**全部作废**，不引用其中任何数字：T-A3、T-Q、D-S1、D-S2、D-A3、D-R1、两模型对比、V1。
2. 补判只做一件事：对缓存中 `served_model` 以 `ERR` 开头的条目重新调用裁判，其余条目与判分规则一律不动；然后重新生成这三个判分文件。
3. 三个读出脚本（`selection_confirmation_addendum_readout.py`、`selection_confirmation_ds_readout.py`、`run_variance_readout.py`、`two_model_confirmation.py`）自此冻结，补判后原样重跑。判据不变。
4. 论文附录如实写明：这三组数据因判分故障读过一次无效的结果，补判后重读。
5. 今后每次读出之前先运行 `scripts/audit_grader_errors.py`；判分脚本不得把接口错误写成判定。

---

## 2026-11-18 18:30 补判完成后的有效读出（取代上文作废的数字）

补判核对：`scripts/audit_grader_errors.py` 输出 OK（全部裁判轮次都有真实判定）；缓存 18,874 条全部来自裁判，接受 2,246 条（补判前 1,000 条）；未受影响的 `is_correct_t3_sidecar_confirm.json` 与缓存逐条一致、文件未改动；补判后没有任何一题的 selected 得分下降（只增不减，符合"只补判未判条目"）。读出脚本与第一次读出时相同（未改动），原样重跑。作废的读出保留为 `*_void_20261118.json`。

### qwen 附加检验（800 新题）
| Method | Last | Selected | Reached | Tokens |
|---|---|---|---|---|
| Nine samples | — | 178.1 | 329 | 52.0M |
| Question-only critique, natural stop | 186 | 191.4 | 303 | 58.1M |
| Question-only critique, equal tokens (1.084 of budget) | 182 | 193.5 | 333 | 71.8M |
| Critique | 207 | 205.3 | 348 | 66.2M |

- **T-A3** critique − nine samples: **+27.2 [6.8, 47.2], p=.006, Holm .012 → confirmed** (exact matches only +25.0 [7.6, 44.3]).
- **T-Q** critique − question-only at equal tokens: **+11.8 [−7.4, 29.4], p=.21 → not confirmed**.
- Descriptive: reached critique vs samples 89/70; critique − question-only at equal tokens +15 (90% [−3, +32]); question-only at equal tokens − reassuring +25.0 [8.0, 42.6], − token-yoked generic doubt +12.0 [−3.4, 28.2]; samples − reassuring +9.6 [−8.1, 27.2].

### deepseek（800 新题）
Token alignment 1.046, 0 at cap. First answer correct 198 of 800.

| Method | Last | Selected | Reached | Conv. | Tokens |
|---|---|---|---|---|---|
| First answer | 205 | 198.0 | 198 | — | 9.8M |
| Reassuring | 252 | 256.2 | 291 | .88 | 42.7M |
| Generic doubt | 251 | 248.5 | 311 | .80 | 57.5M |
| Token-yoked generic doubt | 246 | 261.5 | 371 | .70 | 120.4M |
| Critique | 254 | 254.2 | 370 | .69 | 115.1M |
| Nine samples | — | 224.7 | 361 | .62 | 87.0M |

- **D-S1** critique − token-yoked: **−7.2 [−23.9, 9.3], p=.40 → not confirmed.**
- **D-S2** critique − reassuring: **−1.9 [−18.6, 15.3], p=.83 → not confirmed.**
- **D-A3** critique − nine samples: **+29.6 [12.4, 47.8], p=.0008, Holm .0024 → confirmed.**
- **D-R1** reached critique − token-yoked: −1, 90% [−16, +15], within ±27 → **equivalent** (43/44).
- Descriptive: reached critique vs reassuring 100/21, vs generic doubt 83/24, token-yoked vs generic doubt 82/22; critique vs samples 69/60. Selected: token-yoked − generic doubt +13.0 [−3.3, 29.0]; samples − reassuring −31.5 [−48.7, −13.7]; samples − token-yoked −36.8 [−53.8, −20.8]; reassuring − first answer +58.2. Exact-match share of selected .60–.65 in all six.
- Repeat probability after a correct / incorrect answer: reassuring .75/.64, generic doubt .64/.49, token-yoked .73/.61, critique .44/.29. First revision repaired/damaged: 40/18, 58/35, 47/31, 89/54.

### 两个模型在同一批 800 题上（描述性，非预设）
| Contrast (selected) | qwen | deepseek | qwen − deepseek | Mean of two |
|---|---|---|---|---|
| Critique − token-yoked | +23.8 | −7.2 | +31.0 [5.9, 55.7], p=.014 | +8.3 [−4.2, 21.2] |
| Critique − reassuring | +36.8 | −1.9 | +38.7 [12.8, 66.2], p=.004 | +17.4 [5.3, 29.7] |
| Critique − nine samples | +27.2 | +29.6 | −2.4 [−27.5, 22.6] | +28.4 [15.7, 41.5] |

### V1 重复运行（qwen，第一批 400 新题）
Critique: reached 179 → 177, selected 98.5 → 95.8 (−2.7). Token-yoked: 178 → 184, 93.6 → 89.2 (−4.4). 同一题两次运行多数答案相同的比例 49%、60%。critique − token-yoked 的四种配对：+4.8、+9.2、+2.2、+6.5（平均 +5.7）。

### 结论
1. Reach：等 token 时 critique 的 reach 不多于通用怀疑，三个模型成立（qwen 两批题、MiniMax、deepseek；deepseek 的等价检验有余量）。
2. Selection 对独立采样：两个模型在新题上都确认（+27.2、+29.6）。
3. Selection 对安慰剂：qwen 确认，deepseek 未确认（估计值接近零或为负）；两个模型之差显著（描述性）。
4. "批评须读过答案"：未确认。

### 探索性：按首答状态拆分（`scripts/repair_loss_split.py`，事后分析）
800 新题上，selected 相对首答的变化 = 修好的（首答错或被截断 → 选对）− 丢掉的（首答对 → 没选对）。

| | qwen | deepseek |
|---|---|---|
| 首答正确 / 错误或截断 | 149 / 651 | 205 / 595（其中截断 46） |
| Reassuring：丢掉 | 28.9（19%） | 10.7（5%） |
| Reassuring：修好 | 48.4（7%） | 61.8（10%，其中截断题 6.0） |
| Critique：丢掉 | 38.1（26%） | 25.2（12%） |
| Critique：修好 | 94.4（15%） | 74.5（13%） |
| Critique − reassuring：多修好 | +46.0 | +12.7 |
| Critique − reassuring：多丢掉 | −9.2 | −14.5 |
| 净差 | +36.8 | −1.9 |

单次采样（T=0.7）平均正确数：qwen 150.6，deepseek 207.6（首答 149、205）。deepseek 的 reassuring loop 强，不是因为首答被截断（只贡献 6 题）或首答偏弱，而是它在 reassuring 下几乎不丢已有的正确答案，同时把约一成的错误首答改对；这与第一批题一致（+32/400）。

### 探索性：逐轮转移（`scripts/transition_table.py`，事后分析，800 新题）
| | 答对后保持 | 答对后改错 | 答错后保持 | 答错后改对 | 答错后改成另一个错答案 |
|---|---|---|---|---|---|
| qwen reassuring | .75 | .25 | .61 | .073 | .32 |
| qwen generic doubt | .62 | .38 | .44 | .100 | .46 |
| qwen token-yoked | .66 | .34 | .55 | .085 | .36 |
| qwen critique | .49 | .51 | .29 | .144 | .56 |
| deepseek reassuring | .88 | .12 | .65 | .071 | .28 |
| deepseek generic doubt | .82 | .18 | .51 | .084 | .41 |
| deepseek token-yoked | .86 | .14 | .63 | .063 | .31 |
| deepseek critique | .62 | .38 | .30 | .144 | .55 |

Critique 相对 reassuring 的逐轮效应在两个模型上几乎相同：答错后改对的概率都从约 .07 升到 .144；答对后保持的概率都下降 26 个百分点。两个模型的差别在安慰剂基线：deepseek 在 reassuring 下答对后保持 .88（qwen .75），且首答正确的题更多（205 对 149）。

### 在读出 BBEH 之前写下的两个假说及其预测（2026-11-18 18:50；BBEH 的 loop 数据已存在但尚未判分、未读出）
- **H-能力（作者的假说）**：用 critique 提高 selection 是模型的一种稳定能力。预测：qwen 在 BBEH-hard 上 critique 的 selected 高于 reassuring 与 token-yoked（B-S2、B-S1 为正，量级与 HLE 相近）。
- **H-状态（分析方由转移表提出）**：critique 的逐轮效应各模型相近，净收益取决于首答正确率与安慰剂下正确答案的稳定程度：正确答案越多、越稳，critique 的损失越大。预测：qwen 在 BBEH-hard（首答约 25%，接近 deepseek 在 HLE 上的 24.8%）上 critique 对 reassuring 的增益明显小于 HLE 上的 +18/400，可能接近零；critique 相对 reassuring"答错后改对"的概率仍约翻倍。
- 两个假说在 BBEH-easy 上预测相同：没有增益或为负。
- 判别：以 B-S2 的估计值为准。若其区间下限高于 0 且估计值不低于 HLE 新题上每 800 题 +36.8 的一半，支持 H-能力；若区间包含 0 且估计值低于该值的一半，支持 H-状态；其余情况不作判别。这一判别是探索性的，不改变 `SECOND_BENCHMARK_SPEC.md` 的任何检验。

### 探索性：首答答错的题上，到达之后发生了什么（`scripts/critic_path_diagnostics.py`，事后分析，800 新题；不含首答被截断的题）
| | qwen reassuring | qwen critique | deepseek reassuring | deepseek critique |
|---|---|---|---|---|
| 首答答错的题 | 651 | 651 | 549 | 549 |
| 其中到达正确答案 | 98 | 201 | 78 | 156 |
| 其中选中 | 48.4 | 94.4 | 55.8 | 68.5 |
| 到达后选中的比例 | .49 | .47 | .72 | .44 |
| 第一次答对后，下一轮仍对 | .57 | .38 | .73 | .39 |
| 之后各轮中答对的比例 | .42 | .38 | .62 | .40 |
| 到达但未选中时，多数答案是首答 | .39 | .62 | .29 | .66 |

Critic 的输出不随被批评答案的对错变化：每轮怀疑数 qwen 2.96 对 2.96，deepseek 2.81（答对）对 2.86（答错）。

读法：critique loop 在两个模型上的表现几乎相同（到达数翻倍；到达后选中约 .45；答对后下一轮仍对约 .38）。差别在 reassuring loop：deepseek 一旦在 reassuring 下答对就基本保持（.73，到达后选中 .72），qwen 则只有 .57 与 .49。因此 deepseek 上 critique 多到达的题被更低的"到达后选中比例"抵消（156×.44 对 78×.72），qwen 上没有这种抵消（201×.47 对 98×.49）。

**对"状态"假说的细化（2026-11-18 19:00，BBEH 尚未读出）**：预测 critique 是否提高 selection 的量，是 reassuring loop 在首答答错的题上"到达后选中的比例"。它高于 critique 下的该比例（两个模型都约 .45）越多，critique 的净收益越小。在 BBEH-hard 上：若 qwen 的 reassuring 该比例在 .5 左右，预测有增益；若在 .7 左右，预测没有增益。

### 探索性：到达后选中比例下降是构成变化还是 critique 的作用（`scripts/conversion_composition.py`，事后分析）
首答答错的题，按 reassuring 与 critique 哪个 loop 到达分组（括号内为到达后选中的比例）：

| | qwen：题数 / reassuring 选中 / critique 选中 | deepseek：题数 / reassuring 选中 / critique 选中 |
|---|---|---|
| 两个 loop 都到达 | 69 / 39.4 (.57) / 52.5 (.76) | 62 / 46.8 (.75) / 44.1 (.71) |
| 只有 critique 到达 | 132 / 0 / 41.9 (.32) | 94 / 0 / 24.3 (.26) |
| 只有 reassuring 到达 | 29 / 9.0 / 0 | 16 / 9.0 / 0 |

更正上一节的读法：deepseek 在 critique 下"到达后选中比例"从 .72 降到 .44 主要是构成变化（只有 critique 才到达的 94 题只有 .26 被选中），在两个 loop 都到达的题上该比例基本不变（.75 对 .71）。模型间 38.7 题的差距：新到达的题 17.6；共同到达的题 15.8；首答正确的题上少丢 5.3。

### 作者确认的核心叙事（2026-11-18 20:37）
1. 找到正确答案靠 token，不靠 critique（三个模型，预设检验）。
2. 在选中正确答案上，critique loop 优于对独立采样投票（两个模型新题确认；待补等 token 采样与 USC 的稳健性）。
3. 对安慰剂 loop，critique 的 selection 增益因模型而异（qwen 有，deepseek 无）。
机制解释作者有疑虑，暂不作为结论；事后切分到此为止，只做 BBEH 读出与第一批题三个模型的回溯核对。

---

## 2026-11-18 22:50 BBEH 读出结果（`SECOND_BENCHMARK_SPEC.md`；脚本 `second_benchmark_readout.py`，冻结于 c201f2a，执行一次，输出 sha256 4be75883…）

审计：两组题六个条件全部完成，0 失败调用；判分与官方函数抽查约 1,400 轮零分歧；token 对齐 1.043（hard）、1.044（easy），无题触顶。

### BBEH-hard（800 题，首答正确 263）
| Method | Last | Selected | Reached | Conv. | Tokens |
|---|---|---|---|---|---|
| Reassuring | 359 | 379.9 | 465 | .82 | 48.1M |
| Generic doubt | 370 | 388.9 | 510 | .76 | 57.4M |
| Token-yoked generic doubt | 291 | 371.9 | 576 | .65 | 100.6M |
| Critique | 357 | 390.5 | 591 | .66 | 96.4M |
| Nine samples | — | 344.4 | 547 | .63 | 69.7M |

- **B-S1** critique − token-yoked：**+18.6 [−3.3, 41.4]，p=.10 → 未确认。**
- **B-S2** critique − reassuring：**+10.6 [−11.3, 33.5]，p=.35 → 未确认。**
- **B-A3** critique − nine samples：**+46.1 [25.8, 67.1]，p=.0001，Holm .0003 → 确认。**
- **Reach**：critique − token-yoked +15，90% 区间 [−2, +34]，界限 ±33 → **没有定论**（上端未低于 +33）；不一致对 61/46，p=.18。
- 描述性：reached critique 对 reassuring 150/24、对 generic doubt 128/47、token-yoked 对 generic doubt 97/31、critique 对 samples 95/51。Selected：critique − generic doubt +1.6 [−21.2, 25.0]；token-yoked − generic doubt −17.0 [−35.8, 1.1]；samples − reassuring −35.5 [−54.2, −16.0]；reassuring − first answer +116.9。答对后重复 / 答错后重复：reassuring .72/.38，generic .65/.29，token-yoked .70/.48，critique .45/.16。
- 按任务（critique − reassuring）：10 个任务中 7 个为正；hyperbaton +10.7，zebra_puzzles −7.0。

### BBEH-easy（240 题，首答正确 195）——描述性
Selected：reassuring 222.5，generic doubt 227.5，token-yoked 226.5，critique 223.8，nine samples 225.5。critique − reassuring +1.3 [−5.2, 8.3]；− token-yoked −2.7 [−8.5, 2.8]；− samples −1.7 [−9.3, 6.0]。

### 登记的预测（按原文判定）
| 预测 | 结果 | 判定 |
|---|---|---|
| 18:50 两个假说 | B-S2 = +10.6，区间含 0，低于 18.4 | 按写定的判别：支持"状态"，不支持"能力" |
| P1（hard） | 多数答案仍是首答：把握 0–3 / 4–6 / 7–9 = .27 / .74 / .92（单调；≥ .85）；把握高时首答对 .97、首答错 .86，相差 .108 | **不成立**（"相差不超过 .10"一项差 .008） |
| P1（easy） | .11 / .90 / .97；把握高时 .98 对 .86（首答错仅 7 题） | 不成立（同一项） |
| P2（hard） | 把握低且首答错的题贡献 +5.7，占净差 10.6 的 53% | **不成立**（要求至少三分之二） |
| P3（easy） | 差的绝对值 1.3 | 成立 |
| P4 | 把握高的题里首答正确：easy 162/169（96%），hard 109/197（55%） | 成立（登记时未给阈值） |
| P5（hard） | 预测净差 +20.9，实测 +10.6 [−11.3, 33.5] | 成立（区间很宽）；easy 上预测 −6.1，实测 +1.3 [−5.2, 8.3]，不在区间内 |

**按登记的规则，P1、P2 不成立，该解释在第二个题集上未得到支持。** 定性上"把握越高越推不动"在 BBEH 上很明显，但登记的两项定量判据没有达到；收益并不集中在把握低的题上（把握中、首答错 +10.3；把握高、首答错 +6.0；把握中、首答对 −9.0）。

### 结论
1. critique 优于九次采样：在 BBEH 上再次确认（三次新数据确认：qwen HLE、deepseek HLE、qwen BBEH）。
2. critique 优于安慰剂 loop：BBEH 上未确认（方向为正）。三次检验中只有 qwen 的 HLE 一次确认。
3. 等 token 时 reach：HLE 上三个模型相当；BBEH 上没有定论（critique 多 15 题）。
4. 易题上 critique 没有可见的收益或损失。

## 记忆操纵，第一阶段（qwen，BBEH-hard；规格 `MEMORY_MANIPULATION_SPEC_v3_1.md`，冻结 `b15bbb4` / tag `pre-memory-runs-20261119`；读出 2026-11-19 11:02，输出 sha256 `19585844…`，读出只执行一次）

审计：判分文件轮数与轨迹逐题相等（G-NM 800 题 14,085 轮，G-KI 400 题 6,550 轮）；首答判定与 A2PY 逐题相同；同一题同一键在所有条件下判定一致（9,161 个键，0 冲突）；无键的轮 9 / 6，均判错；token 为预算的 104.3%，无触顶。规则判分，不涉及接口。

| 条件（通用怀疑，等 token） | n | reached | selected | 转化 | 每题候选 | 第 1 轮与首答相同 |
|---|---|---|---|---|---|---|
| A2PY：显示上一轮答案，有保留许可 | 800 | 576 | 371.9 | .65 | 4.38 | .50 |
| G-NM：不显示，无许可 | 800 | 592 | 359.5 | .61 | 4.96 | .41 |
| G-KI：显示，无许可（400 题） | 400 | 284 | 174.5 | .62 | 5.09 | .41 |
| 九次采样 | 800 | 547 | 344.4 | .63 | 3.90 | — |

- **操纵检查：通过。** 第 1 轮与首答相同 .41 对 .50（不一致对 71/143，p < .001），方向为"无记忆时重复更少"。
- **NM-2（唯一确认性检验）selected(A2PY) − selected(G-NM)：+12.4 [−6.0, 30.9]，p = .20 → 未确认。**
- reached：A2PY 对 G-NM 不一致对 35/51，p = .11。
- 400 题子集（描述）：许可 +2.0 [−10.3, 14.1]；可见性 +6.4 [−6.4, 19.3]；合计 +8.4 [−4.6, 21.4]。
- 对九次采样（描述）：A2PY +27.5 [7.1, 46.7]；G-NM +15.0 [−4.6, 34.0]；G-KI（400 题）+14.4 [−0.3, 28.2]。
- 按事先写定的规则：**"记忆买集中"从论文撤下；loop 优于采样的原因写为未知；第二阶段不跑。** 不得写成"记忆无用"：区间上限为 +31。

## E2：等 token 采样与 USC（qwen、deepseek，HLE 新 800 题；规格 `EQUAL_TOKEN_SAMPLES_SPEC.md` + `E2_DECOMPOSITION_REGISTRATION.md`；脚本 sha256 `aca86c07…`，输出 sha256 `930e5523…`，读出只执行一次）

审计：判分轮数与轨迹逐题相等；前九次判定与已有文件逐字相同；裁判判过的 14,051 / 12,056 轮全部有真实判定（无接口错误）；USC 解析失败 3 / 21（按 s2_usc.py 的回退处理）。token：等 token 采样为预算的 118% / 115%，触顶 1 / 10 题（达标；采样多花的 token 对采样有利，检验因此偏保守）。

| | qwen 选中 / 找到 | deepseek 选中 / 找到 |
|---|---|---|
| critique loop | 205.3 / 348 | 254.2 / 370 |
| 等 token 采样（每题中位 13 / 12 次） | 180.0 / 385 | 229.0 / 397 |
| USC（在等 token 采样上） | 183.0 | 235.0 |
| 九次采样 | 178.1 / 329 | 224.7 / 361 |

| 检验（每个模型 Holm 三项） | qwen | deepseek |
|---|---|---|
| E-SC critique − 等 token 采样 | **+25.3 [4.4, 46.5]，Holm .028，确认** | **+25.2 [7.8, 41.8]，Holm .008，确认** |
| E-USC critique − USC | **+22.3 [1.5, 43.1]，Holm .030，确认** | **+19.2 [2.0, 37.1]，Holm .039，确认** |
| E-C 两者都找到的题上 | **+26.8 [9.0, 44.9]，Holm .008，确认**（290 题） | **+32.0 [17.6, 46.4]，Holm .0006，确认**（323 题） |
| E-R 找到：critique − 等 token 采样 | −37，90% [−58, −18]，界限 ±33 → 没有定论 | −27，90% [−45, −8]，界限 ±27 → 没有定论 |

- 描述：等 token 时采样找到的正确答案**多于** critique loop（不一致对 58/95，p = .003；47/74，p = .018），选中的却少 25 题。拆分：qwen 找到项 −19.6、转化项 +44.8；deepseek −17.1、+42.3。
- 描述：采样从九次加到等 token，找到 +56 / +36 题，选中只 +1.9 / +4.4。
- 描述：只计精确匹配，E-SC +28.6 / +17.2，E-USC +41.3 / +23.6；按题型，收益在开放题（599 题：+24.3 / +19.8），选择题上接近零（+1.0 / +5.4）。
- 描述：deepseek 上 token-yoked 通用怀疑 − 等 token 采样 +32.4 [16.3, 48.8]；qwen 上 +1.5 [−13.5, 16.5]。
- 按登记措辞（E-C 成立、E-R 不成立）：可写"loop 在共同找到的题上选得更准"；reach 的差另行报告。
