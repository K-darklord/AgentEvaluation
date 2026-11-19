# 论文数字清单（v17 改写用；2026-11-20 汇总，供作者确认）

**规则。** 正文与附录中的每个数字只取自下表列出的冻结读出输出（JSON），不从文档、聊天记录或旧版论文转抄。改写完成后，`docs/consistency_manifest.json` 按本清单重建，`scripts/check_manifest.py` 须 0 问题。区间均为题目级 bootstrap 95%（另注 90% 者除外）；p 为符号翻转置换检验（10,000 次），确认性检验附 Holm 校正后的 p。数字单位是"题"（800 题中的题数），不是百分比。

## 0. 数据来源（读出输出与哈希）

| 代号 | 读出输出（`experiments/hle400/t3/`） | sha256 前 12 位 | 读出脚本 | 内容 |
|---|---|---|---|---|
| R-ET400 | `equal_token_readout.json` | e3be1b3dd08b | `equal_token_readout.py` | 第一批 400 题：qwen 五种反馈等 token；MiniMax token-yoked |
| R-CTRL | `controls_readout.json` | 28127e2e25c4 | （controls 读出） | 第一批 400 题 qwen：token-yoked、错配、只看题目 |
| R-S1 | `selection_confirmation_readout.json` | d2a80dc3134c | `selection_confirmation_readout.py` | qwen 新 800 题：S1、S2、R1 |
| R-ADD | `selection_confirmation_addendum_readout.json` | 25f6cd52470a | `selection_confirmation_addendum_readout.py` | qwen 新 800：T-A3、T-Q（补判后） |
| R-DS | `selection_confirmation_ds_readout.json` | 1ba13dab0132 | `selection_confirmation_ds_readout.py` | deepseek 新 800（补判后） |
| R-TWO | `two_model_confirmation.json` | 66175c09393f | `two_model_confirmation.py` | 两模型差（描述） |
| R-V1 | `run_variance_readout.json` | 6e3c67a29da2 | `run_variance_readout.py` | 重复运行（补判后） |
| R-SCIPY | `stats_crosscheck.json` | 20832bbed0c3 | `crosscheck_stats.py` | SciPy 独立复算 |
| R-BB | `second_benchmark_readout.json` | 4be75883f4d2 | `second_benchmark_readout.py` | BBEH hard / easy |
| R-MEM | `memory_manipulation_readout.json` | 195858442672 | `memory_manipulation_readout.py` | 记忆操纵第一阶段 |
| R-E2 | `equal_token_samples_readout.json` | 930e5523b9c9 | `equal_token_samples_readout.py` | HLE 等 token 采样 + USC |
| R-BET | `bbeh_equal_token_readout.json` | d21af94d9e8e | `bbeh_equal_token_readout.py` | BBEH 等 token 采样 + T=0.7 loop |
| R-MECH | `mechanism_tables.json` | c6c4c3606c10 | `mechanism_tables.py` | 转移、保留率（描述） |
| R-B0 | `experiments/b0_A_qwen3.8-flash-payg/b0_scores.json` | eae9633f6585 | `score_b0.py` | 第二题集筛选（首答） |
| R-CRIT | `critic_doubts_by_correctness.json` | ec3f7be19100 | `critic_doubts_by_correctness.py` | critic 每轮怀疑数，按被批评答案的对错（描述） |
| R-SENS | `grading_key_sensitivity.json` | 172aff20587a | `grading_key_sensitivity.py` | 同一答案不同写法判定不一致时 E-SC 的敏感性（描述） |
| R-HA1 | `audit/human_audit_20261111/audit_final.json` | 0fbf92d28b27 | `human_audit_final.py` | 第一次人工核对 |

第一批 400 题上三个模型的主研究（论文第 4.1 节的观察、图 `fig:first`）沿用 v16 清单中已核对的数字，不在此重列。

## 1. 核心结果：同样的 token，采样找到更多，critique loop 选中更多（三格，全部确认）

| | qwen HLE 新 800 | deepseek HLE 新 800 | qwen BBEH-hard 800 | 来源 |
|---|---|---|---|---|
| critique loop：找到 / 选中 | 348 / 205.3 | 370 / 254.2 | 591 / 390.5 | R-E2、R-BET |
| 等 token 采样：找到 / 选中 | 385 / 180.0 | 397 / 229.0 | 611 / 356.5 | R-E2、R-BET |
| 等 token 采样每题平均次数 | 18.75（中位 13） | 17.21（中位 12） | 21.16 | 同上 |
| 采样 token 占预算 | 118.1% | 115.3% | 112.9% | 同上 |
| **选中：critique − 等 token 采样** | **+25.3 [4.4, 46.5]，Holm .028** | **+25.2 [7.8, 41.8]，Holm .008** | **+34.0 [13.8, 55.0]，Holm .003** | E-SC / B-SC |
| **两者都找到的题上** | **+26.8 [9.0, 44.9]，Holm .008（290 题）** | **+32.0 [17.6, 46.4]，Holm .0006（323 题）** | **+35.4 [16.0, 54.0]，Holm .002（540 题）** | E-C / B-EC |
| **critique − USC** | **+22.3 [1.5, 43.1]，Holm .030**（USC 183.0） | **+19.2 [2.0, 37.1]，Holm .039**（USC 235.0） | 未做 | E-USC |
| 找到：critique − 等 token 采样 | −37，90% [−58, −18]（界限 ±33：无定论） | −27，90% [−45, −8]（±27：无定论） | −20，90% [−39, −1]（±33：不等价） | E-R / B-ER |
| 找到的不一致对（critique 独有 / 采样独有） | 58 / 95，p = .003 | 47 / 74，p = .018 | 51 / 71，p = .085 | 同上 |
| 拆分：找到项 / 转化项 | −19.6 / +44.8 | −17.1 / +42.3 | −12.4 / +46.5 | 同上 |
| 采样从九次加到等 token：找到 / 选中 | +56 / +1.9 | +36 / +4.4 | +64 / +12.0 [−0.4, 24.2] | 同上 |

稳健性（描述）：只计精确匹配，E-SC +28.6 [10.2, 47.5] / +17.2 [2.8, 31.6]，E-USC +41.3 / +23.6（R-E2）。按题型（R-E2）：开放题（599）E-SC +24.3 [7.8, 39.7] / +19.8 [5.7, 33.6]；选择题（201）+1.0 [−11.5, 13.4] / +5.4 [−3.0, 13.9]。

未等 token 时（九次采样，作为历史检验报告）：T-A3 +27.2 [6.8, 47.2] Holm .012；D-A3 +29.6 [12.4, 47.8] Holm .0024；B-A3 +46.1 [25.8, 67.1] Holm .0003（R-ADD、R-DS、R-BB）。

## 2. 第一句：找到靠 token

| 比较（等 token） | 找到之差，90% 区间 | 界限 | 判定 | 来源 |
|---|---|---|---|---|
| qwen HLE 新 800：critique − token-yoked 通用怀疑 | −15 [−32, +2]（SciPy：[−33, +3]） | ±33 | 等价（贴边，正侧稳） | R-S1、R-SCIPY |
| deepseek HLE 新 800 | −1 [−16, +15] | ±27 | 等价 | R-DS |
| qwen 第一批 400：critique − 通用怀疑（等 token） | +1 [−11, 14] | — | 描述 | R-ET400 |
| qwen 第一批 400：critique − 只看题目 / 错配 / 安抚（等 token） | +3 [−10, 17] / +16 [4, 29] / +23 [9, 36] | — | 描述 | R-ET400 |
| MiniMax 第一批 400：critique − token-yoked | 156 对 152，不一致对 21/25，p = .66；之差 90% [−15, 7] | — | 描述 | R-ET400 |
| qwen BBEH-hard：critique − token-yoked | +15 [−2, +34] | ±33 | 无定论 | R-BB |

token：qwen HLE critique 66.2M、token-yoked 69.2M（104.5%）；deepseek 115.1M、120.4M；BBEH 96.4M、100.6M（104.3%）。

## 3. 第三句：critique 对安慰剂 loop 的选中优势是有条件的

| 检验 | qwen HLE 新 800 | deepseek HLE 新 800 | qwen BBEH-hard | 来源 |
|---|---|---|---|---|
| critique − token-yoked 通用怀疑 | **+23.8 [5.9, 42.3]，Holm .008，确认** | −7.2 [−23.9, 9.3]，未确认 | +18.6 [−3.3, 41.4]，p = .10，未确认 | S1 / D-S1 / B-S1 |
| critique − 安抚 | **+36.8 [17.4, 57.3]，Holm .0006，确认** | −1.9 [−18.6, 15.3]，未确认 | +10.6 [−11.3, 33.5]，未确认 | S2 / D-S2 / B-S2 |
| 只计精确匹配：S1 / S2 | +17.3 [1.4, 33.0] / +25.9 [8.2, 42.5] | −4.9 / +4.1 | — | R-S1、R-DS |

- 两模型之差（描述，R-TWO）：critique − token-yoked 的 qwen − deepseek +31.0 [5.9, 55.7]；critique − 安抚 +38.7 [12.8, 66.2]。
- qwen 第一批 400（R-ET400）：critique 选中 114.1；等 token 时安抚 87.7、错配 96.8、通用怀疑 92.0、只看题目 91.8；critique − 各项 +26.4 [12.7, 41.8]、+17.3 [3.9, 31.5]、+22.1 [9.0, 35.8]、+22.3 [8.4, 36.8]。
- MiniMax 第一批 400：critique − token-yoked 选中 +10.9 [−0.5, 22.3]（R-ET400）。
- 只看题目的 critique（qwen HLE 新 800，R-ADD）：T-Q critique − 只看题目（等 token）+11.8 [−7.4, 29.4]，未确认。
- qwen HLE 新 800 按两批题（描述，R-S1）：S1 +4.8 / +19.0。重复运行（R-V1，前 400 新题）：四种配对 +4.8、+9.2、+2.2、+6.5。

## 4. 温度（BBEH-hard，R-BET）

| | 选中 | 来源 |
|---|---|---|
| T-1：T=0.7 通用怀疑 loop − 等 token 采样 | +11.6 [−9.6, 31.6]，p = .27，**未确认** | R-BET |
| loop 内换温度：T=0.7 − T=0（描述） | −3.9 [−22.5, 15.9] | R-BET |
| T=0 通用怀疑 loop − 等 token 采样（描述） | +15.4 [−2.4, 33.7] | R-BET |
| critique − T=0.7 通用怀疑 loop（描述） | +22.5 [−0.9, 44.4] | R-BET |

各条件选中：critique 390.5，T=0 通用怀疑 371.9，T=0.7 通用怀疑 368.0，等 token 采样 356.5，九次采样 344.4。

## 5. 机制（全部描述性，写在讨论里）

**保留率（BBEH-hard，R-BET；答对后保留 / 答错后保留）**：critique .45 / .16；T=0 通用怀疑 .70 / .49；T=0.7 通用怀疑 .69 / .47；等 token 采样（相邻两次相同）.60 / .39；九次采样 .58 / .33。每个答案的正确率：critique .305、通用怀疑 .306 / .305、等 token 采样 .296。

**critic 每轮怀疑数不随答案对错变化**（R-CRIT；被批评的答案正确 / 错误）：qwen HLE 2.96 / 2.96（962 / 3,804 轮）；deepseek HLE 2.81 / 2.86（1,046 / 3,093 轮）；qwen BBEH 2.94 / 2.95（1,573 / 3,958 轮）。注意：提出三条及以上怀疑的轮次占 84%–97%，这个量接近饱和，只能说明 critic 不会因为答案对了就少提怀疑，不能说明它的内容不含对错信息。（旧文档中的 BBEH 2.92 / 2.94 来自另一种计数，不引用。）

**记忆操纵（qwen BBEH-hard，R-MEM）**：操纵检查通过（第 1 轮与首答相同 .41 对 .50，不一致对 71/143，p < .001）；NM-2 显示上一轮答案 − 不显示 +12.4 [−6.0, 30.9]，p = .20，**未确认**；拆分找到项 −10.0、转化项 +22.4（描述）；400 题上可见性 +6.4 [−6.4, 19.3]，许可 +2.0 [−10.3, 14.1]。

**登记的预测（R-BB 附带，`CONTROLS_RESULTS.md`）**：P1 不成立（把握高时首答对 .97、错 .86，差 .108 > .10）；P2 不成立（53%，要求 ≥ 2/3）；P3、P4 成立；P5 hard 成立、easy 不成立。

## 6. 题集与范围

- 第二题集筛选（qwen 首答，R-B0）：BBEH 805 题 48.1%（10 个任务 10–40%，10 个 40–80%，3 个 ≥ 80%）；GSM8K 200 题 97.5%；OlymMATH EASY 97%、HARD 72%（`b0_scores.json`，OlymMATH 用官方判分器 math_verify）。`CONTROLS_RESULTS.md` 第 146–148 行的 EASY 87–92%、HARD 60–63% 是分析方当时只用字符串回退判分的初步数字，不引用。
- BBEH-hard：10 个任务 × 80 题，首答正确 263；BBEH-easy：240 题，首答正确 195，所有 loop 选中 222–228，critique − 安抚 +1.3 [−5.2, 8.3]（R-BB）。
- HLE 新 800 题首答正确：qwen 148，deepseek 198。

## 7. 判分的可靠性

- 第一次人工核对（R-HA1）：100 条与自动判分一致 93 条（直接比对 53/53，符号核验 12/12，讨论裁决 28/35）；自动判对的 71 条中 6 条人工判错，自动判错的 29 条中 1 条人工判对；按条件 critique 3/16（3 条都在 qwen，共 4 条）。
- 第二次人工核对：分流 P1 60 / P2 17 / P3 23；符号核验 17 条中 16 条等价；**标注未开始**。
- 判分事故（2026-11-18）：判分缓存 18,874 条中 8,106 条为接口错误被记为错误；涉及三个判分文件，补判后 `audit_grader_errors.py` 输出 OK；作废的读出全部重做，S1 的判分文件未受影响。
- E2 与 BBEH 判分复核：裁判判过的轮次全部有真实判定（qwen 14,051、deepseek 12,056）；BBEH 为规则判分，所有条件同一答案判定一致（9,526 键，0 冲突）。
- 同一答案不同写法判定不一致的敏感性（R-SENS，E-SC）：qwen 8,664 个答案键中 20 个、deepseek 8,464 个中 19 个判定不一致（各涉及 20 / 19 题）；按多数、任一判对即对、全部判对才对三种方式统一后，E-SC 为 qwen +27.3 / +27.8 / +27.8，deepseek +25.7 / +24.7 / +23.7，区间都不含零（原样 +25.3 / +25.2，与 R-E2 逐位相同）。
- SciPy 独立复算（R-SCIPY）：精确量完全一致；区间端点最大差 1.28 题；置换 p 最大差 .0012。

## 8. 进论文前要处理的问题

1. ~~OlymMATH 数字不一致~~ 已解决（2026-11-20）：`score_b0.py` 用官方判分器 math_verify，论文引用 97% / 72%。
2. ~~两组数字只在文档里~~ 已解决（2026-11-20）：`critic_doubts_by_correctness.py`、`grading_key_sensitivity.py` 写成正式脚本，输出见 R-CRIT、R-SENS。
3. **第二次人工核对未完成**：论文附录的判分可靠性一节，等它的结果。
4. ~~只看题目的 critic 抽查表~~ 已完成（2026-11-20，`QONLY_SPOTCHECK_RESULTS.md`）：泛泛而谈 0/30；明确给出或指向答案 5/30，边界 2/30（作者标注 6/30，AI 助手复核同意 28/30）。
5. **`CONTROLS_RESULTS.md` 里有作废的段落**（V1 旧读出、判分事故前的读出），已标注作废；改论文时只按本清单取数。
6. **措辞上的三处约束**：qwen HLE 的 R1 是贴边等价，写明正侧稳；T-1 未确认，温度写进限制；E-R / B-ER 都不是"等价"，只能写"采样找到的更多"，不能写"找到一样多"。
