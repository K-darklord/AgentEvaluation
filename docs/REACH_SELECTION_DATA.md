# Reach 与 selection：数据汇总与待解释的问题（2026-11-18；供多方一起推理机制）

本文件只汇总数据，不下机制结论。完整分表见 `REACH_SELECTION_DATA_TABLES.md`（脚本 `scripts/mechanism_tables.py` 生成）；检验结果的出处见 `CONTROLS_RESULTS.md`。BBEH 的结果读出后补入第 5 节。

## 1. 设定（一句话）
同一个模型既是 solver 也是 critic。每个 loop 从同一个 T=0 首答出发，最多 10 轮反馈，连续三次相同答案即停。**Reached**：出现过正确答案。**Selected**：出现次数最多的答案正确。反馈类型：reassuring（"没发现问题"）；generic doubt（五句固定的通用怀疑）；token-yoked generic doubt（通用怀疑一直跑到花掉 critique loop 在该题上的 token）；critique（critic 读题目和答案后写出针对性的怀疑）；九次独立采样（T=0.7，多数表决）。

## 2. 已由预设检验确立的事实
| 事实 | 证据 |
|---|---|
| 等 token 时，critique 的 reach 不多于通用怀疑 | qwen 新 800 题 348 对 363（等价检验通过，贴近界限）；deepseek 新 800 题 370 对 371（等价）；第一批 400 题 qwen 182 对 181、MiniMax 152 对 156 |
| critique 的 selected 高于九次采样 | qwen 新题 +27.2 [6.8, 47.2]；deepseek 新题 +29.6 [12.4, 47.8]；第一批题三个模型 +20.7、+23.1、+12.2（token 未对齐、未与 USC 比较，补充实验见 `EQUAL_TOKEN_SAMPLES_SPEC.md`） |
| critique 的 selected 高于安慰剂 loop：qwen 成立 | 新题：对 token-yoked +23.8 [5.9, 42.3]，对 reassuring +36.8 [17.4, 57.3] |
| 同一比较：deepseek 不成立 | 新题：对 token-yoked −7.2 [−23.9, 9.3]，对 reassuring −1.9 [−18.6, 15.3] |
| 两个模型之差（描述性） | 对 token-yoked +31.0 [5.9, 55.7]；对 reassuring +38.7 [12.8, 66.2] |
| "批评须读过答案"未确认 | qwen 新题：critique 减等 token 的 question-only +11.8 [−7.4, 29.4] |
| 同一条件重跑一次 | qwen 400 题：selected 变化 −2.7（critique）、−4.4（token-yoked） |

## 3. 五个格子的对照（事后整理；critique 对 reassuring）
| 格子 | 首答正确率 | reassuring：首答对的题丢掉 | reassuring：首答错的题到达 | critique：丢掉 | critique：到达 | critique − reassuring 的 selected（每格总数） |
|---|---|---|---|---|---|---|
| deepseek，第一批 400 | 28% | 5% | 14% | 8% | 30% | +12.5 |
| qwen，第一批 400 | 17% | 14% | 16% | 23% | 34% | +23.3 |
| MiniMax，第一批 400 | 20% | 14% | 14% | 18% | 22% | +5.3 |
| qwen，新 800 | 19% | 19% | 15% | 26% | 31% | +36.8 |
| deepseek，新 800 | 26% | 5% | 15% | 12% | 28% | −1.8 |

净差的四个来源（selected，critique 减 reassuring）：
| 格子 | 两个 loop 都到达的题 | 只有 critique 到达的题 | 只有 reassuring 到达的题 | 首答正确的题 |
|---|---|---|---|---|
| deepseek，第一批 400 | −6.5（33 题；.97 → .77） | +27.8（52 题，.53） | −5.0 | −3.8 |
| qwen，第一批 400 | +3.5（44 题；.59 → .67） | +31.8（69 题，.46） | −6.0 | −6.0 |
| MiniMax，第一批 400 | −2.0（33 题；.78 → .72） | +16.3（38 题，.43） | −6.3 | −2.7 |
| qwen，新 800 | +13.1（69 题；.57 → .76） | +41.9（132 题，.32） | −9.0 | −9.2 |
| deepseek，新 800 | −3.0（70 题；.74 → .70） | +25.7（99 题，.26） | −10.0 | −14.5 |
括号内：题数；"到达后选中的比例"（reassuring → critique，或只有 critique 时的比例）。

逐轮转移（答对后保持 / 答错后改对）：
| 格子 | reassuring | critique |
|---|---|---|
| deepseek，第一批 400 | .92 / .062 | .74 / .112 |
| qwen，第一批 400 | .78 / .066 | .59 / .122 |
| MiniMax，第一批 400 | .84 / .058 | .62 / .092 |
| qwen，新 800 | .75 / .073 | .49 / .144 |
| deepseek，新 800 | .88 / .071 | .62 / .144 |

其他观察：critic 每轮给出的怀疑数不随被批评答案的对错变化（qwen 2.96 对 2.96；deepseek 2.81 对 2.86）。deepseek 的 reassuring loop 比首答多选对 58 题（新 800），比九次采样多 31.5 题。

## 4. 待解释的问题
1. **是什么带来了 selection 的增益？** critique 相对安慰剂的净差来自四项（上表）。哪一项是"critique 的内容"起作用，哪一项只是"多作答几次"？
2. **为什么 qwen 有增益而 deepseek 没有？** 可见的差别：(a) deepseek 在 reassuring 下几乎不丢正确首答（5% 对 qwen 的 14%–19%），答对后保持的概率更高（.88–.92 对 .75–.78）；(b) 在两个 loop 都到达的题上，critique 使 qwen 的选中比例上升（.57 → .76），deepseek 不升或下降；(c) deepseek 首答正确的题更多，critique 在这些题上的损失更大。
3. **为什么只有 critique 才到达的题，选中比例在新题上明显低于第一批题？**（deepseek .53 → .26，qwen .46 → .32。）
4. **deepseek 在两批题上的净差为什么不同（+12.5 对 −1.8）？** 候选解释：抽样与运行波动（第一批题区间 [−1.6, 25.6]）；两批题运行相隔数周、接口通道不同。
5. **token-yoked 通用怀疑在 deepseek 上 selected 最高（261.5），在 qwen 上不高（181.5 对 reassuring 168.5、critique 205.3）。**为什么多花 token 对两个模型的 selection 作用不同？

## 5. 已在读出前写下的预测（BBEH，qwen）
见 `CONTROLS_RESULTS.md`"在读出 BBEH 之前写下的两个假说"。BBEH-hard 首答正确率约 25%。结果读出后补入本节。

## 6. 使用时的注意
第 3 节的全部数字是看过数据之后的整理，没有预设检验；各格子每个条件只运行一次（重跑的波动见第 2 节）；第一批题的 qwen、MiniMax 判分含少量争议复判，新题没有。

## 7. 候选解释框架与一项补充分析（2026-11-18 晚，事后）

**框架（另一位 agent 提出，`MECHANISM_HYPOTHESIS_20261118.md`）**：循环是有记忆的采样器；记忆让票集中；集中是好是坏取决于被重复的答案对不对。分析方的评估：与三条核心事实相容，可作为 Discussion 的解释；其中"selected ≈ P(正确票数 > 最强错误票数)"是定义而非证据；问题 4 的回答把每 400 题与每 800 题的数直接相比（折算后首答错的增益为 +16.3 对 +6.3）；"generic doubt 拿到 +22.1"应为 +14.7；"qwen 先升后降"比较的是不同反馈类型；"改为 critique of the question"不能成立（T-Q 的区间为 [−7.4, 29.4]）。

**停留优势（由转移表计算，1/(1−保持概率)，正确答案相对错误答案）**：qwen reassuring 1.6 倍、critique 1.4 倍；deepseek reassuring 2.9 倍、critique 1.8 倍；两个模型进入正确答案的概率在 critique 下都约翻倍。

**作者的质疑**：该框架不解释简单题——首答正确率高，但 critique 带来的偏移并不大。

**补充分析：记忆强度取决于模型对答案的把握（`scripts/confidence_strata.py`，800 新题）**。把握的度量在 loop 之外取得：九次独立采样中与 T=0 首答相同的次数；分层在计算前定为 0–3、4–6、7–9。下表为"loop 的多数答案仍是首答"的比例（首答正确 / 首答错误）与该层的 selected：

| | 把握低（0–3） | 把握中（4–6） | 把握高（7–9） |
|---|---|---|---|
| qwen 题数（首答对 / 错） | 81 / 394 | 40 / 100 | 25 / 118 |
| qwen reassuring：仍是首答 | .46 / .42 | .88 / .86 | .96 / .98 |
| qwen critique：仍是首答 | .45 / .27 | .78 / .67 | .92 / .87 |
| qwen selected：reassuring → critique（首答对） | 58.1 → 52.9 | 37.0 → 34.0 | 24.0 → 23.0 |
| qwen selected：reassuring → critique（首答错） | 39.9 → 64.4 | 3.0 → 12.0 | 0.0 → 7.0 |
| deepseek 题数（首答对 / 错） | 85 / 299 | 43 / 88 | 70 / 114 |
| deepseek reassuring：仍是首答 | .69 / .48 | .95 / .80 | .99 / .97 |
| deepseek critique：仍是首答 | .54 / .28 | .93 / .69 | .96 / .91 |
| deepseek selected：reassuring → critique（首答对） | 78.3 → 67.8 | 42.0 → 40.5 | 69.0 → 67.5 |
| deepseek selected：reassuring → critique（首答错） | 37.8 → 47.3 | 9.0 → 9.0 | 1.0 → 3.5 |

读法：critique 是否推得动首答，主要看模型对它的把握，而不是它对不对。把握高时，critique 几乎推不动（对的 .92–.96，错的 .87–.91）；把握低时才推得动。critique 的收益几乎全部来自"把握低且首答错"的题（qwen +24.5，deepseek +9.5），损失来自"把握低且首答对"的题（qwen −5.2，deepseek −10.5）。deepseek 首答正确且把握高的题有 70 道，qwen 只有 25 道。

## 8. 在读出 BBEH 之前写下的预测（2026-11-18 21:50；BBEH 的运行已基本完成，尚未读出任何 reach / selected）

把握的度量与分层同第 7 节（九次采样中与首答相同的次数：0–3、4–6、7–9），用 BBEH 上的 A3 运行计算；读出脚本沿用 `scripts/confidence_strata.py` 的算法，只换数据。

- **P1（把握决定推不推得动）**：在 BBEH-hard 与 BBEH-easy 上，critique loop 结束时"多数答案仍是首答"的比例随把握单调上升；把握 7–9 的题上该比例不低于 .85，且首答对与首答错相差不超过 .10。
- **P2（收益的位置）**：BBEH-hard 上 critique 相对 reassuring 的 selected 增益，至少三分之二来自"把握 0–3 且首答错"的题。
- **P3（简单题）**：BBEH-easy 上 critique 相对 reassuring 的 selected 之差的绝对值不超过 12 题（240 题的 5%），即既无明显收益也无明显损失。
- **P4（校准）**：把握 7–9 的题上首答正确的比例，BBEH-easy 明显高于 BBEH-hard。
- 任何一条不成立都如实报告；P1 或 P2 不成立即视为该解释在第二个题集上未得到支持。

补充观察（HLE 新 800 题，事后）：把握 7–9 的题上首答正确的比例，qwen 为 25/143（17%），deepseek 为 70/184（38%）；把握 0–3 的题上为 81/475（17%）与 85/384（22%）。简单的"只在把握低时才用 critique"的策略用现有数据离线计算并不优于全程 critique（qwen 181.3 对 193.3，deepseek 236.1 对 235.6，均只计首答可解析的题），因为 qwen 在把握中、高的题上 critique 仍有净收益。

- **P5（定量外推，2026-11-18 22:00 补记，仍在 BBEH 读出之前）**：用 qwen 在 HLE 新 800 题上各格（把握分层 × 首答对错）critique 减 reassuring 的每题平均效应，乘以 BBEH-hard 各格的题数，得到 BBEH-hard 上的预测净差。每题平均效应（HLE，qwen）：把握低·首答对 −0.064，把握低·首答错 +0.062，把握中·首答对 −0.074，把握中·首答错 +0.090，把握高·首答对 −0.040，把握高·首答错 +0.059。预测值落在 BBEH-hard 实测净差（B-S2）的 95% 区间内，视为外推成立；否则不成立。同样的算法也用于 BBEH-easy（仅作描述）。
- **四类题的说法（作者与分析方讨论后的表述，待检验）**：把握高且对——critique 推不动，无得无失；把握高但错——critique 救不回来；把握低且错——收益的来源；把握低但对——损失的来源，损失多少取决于模型在没把握时自己守住正确答案的本事。critique 的净值 ≈（把握低且错的题数 × 修复率）−（把握低但对的题数 × 额外丢失率）。
