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
