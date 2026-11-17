# 主张—证据对照（v3，2026-11-15，对应 `paper/acl/main.tex` v15）

每条主张给出：论文位置、类别、数字、复算脚本。名称用论文的叫法；代码代号对照见 `docs/INDEX.md` 第 2 节。
数字的顺序一律是 deepseek-v4-flash、qwen3.8-flash、MiniMax-M2.5；每个模型 400 题。`a/b` 表示只有前一种方法答对（或到达）的题数 / 只有后一种的题数。

**类别**（与论文 §3 "What was fixed in advance" 一致）
- **确认性**：唯一的一项，第三模型上 critique loop 对 reassuring loop 的 selected 之差（P1）。
- **预先确定的次要检验**：各规格里写明判据的其余检验。
- **描述 / 探索**：没有预先确定判据的数字，包括三模型均值、conversion、来源拆分、与投票文献的对照。论文中均标明。

## A. Reach（§4.1）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| A1 | critique loop 到达的题多于 reassuring loop，三个模型都成立 | 预先确定（qwen：复现检验；MiniMax：S1） | reached 198/153、182/123、152/125；配对 52/7、69/10、38/11，均 p<.001 | `two_model_tables.py`、`third_model_readout.py` |
| A2 | critique loop 到达的题多于 generic-doubt loop | 预先确定（MiniMax：S2，差至少 15 且 p<.05） | reached 198/171、182/149、152/128；配对 39/12、49/16、37/13 | 同上 |
| A3 | generic-doubt loop 多于 reassuring loop 只在两个模型上成立 | 预先确定（MiniMax：S3 未满足） | 28/10、42/16、21/18（p=.75） | 同上 |
| A4 | A1、A2 在限定候选数、只计精确匹配时仍成立（MiniMax 在前 2 个候选时不显著） | 描述 | 前 2 个候选的 reached（reassuring/generic/critique/samples）：141/148/172/169、109/118/136/134、111/111/121/126；前 3 个：150/157/181/178、118/137/160/147、117/121/142/146；精确匹配：91/102/122/120、79/94/117/93、83/83/98/111 | 同上（表 6） |
| A5 | 第一个候选错时，第二个候选答对的比例 critique loop 不低于 generic-doubt loop | 探索 | 24% 对 15%（48/204、26/171）、24% 对 19%、16% 对 15% | `reach_quality_checks.py` |
| A6 | critique loop 与 9 个独立样本到达的题数相当，MiniMax 上样本更多 | 描述 | reached 198/190、182/171、152/173；配对 29/21、44/33、19/40（p=.009） | 主表脚本 |
| A10 | 结果不依赖开发阶段见过的题：400 题分三次抽取（50、150、200），后 200 题在运行协议冻结前没有跑过任何东西；只看后 200 题结论相同 | 事后分析，描述（规则先于计算写定） | 后 200 题：对 reassuring 27/2、35/5、20/3（前 200 题 25/5、34/5、18/8）；对 generic 18/6、19/7、17/8（前 200 题 21/6、30/9、20/5）；selected 之差 +7.2、+11.2、+6.6（前 200 题 +5.2、+12.0、−1.3） | `reach_by_draw.py` |
| A9 | reach 优势在各学科方向一致（三模型合计无一学科反向） | 事后分析，描述 | 对 reassuring（只有 critique / 只有 reassuring）：数学 73/12、计算机 12/2、生物医学 29/3、物理 14/3、人文社科 12/3、其他 9/4、化学 9/0、工程 1/1 | `reach_by_subject.py` |
| A7 | 三个模型上两种安慰剂 loop 都没有与 critique loop 对齐 token；对齐只在 qwen 上做了（见 A′） | 论文的解释限定 | — | §3、Limitations |

## A′. qwen 上的对照（§4.1 表 5、附录 G；详见 `CONTROLS_RESULTS.md`）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| K1 | 通用怀疑花掉与 critique loop 同样多的 token 后，到达的题相同：在 qwen 上 reach 的优势可由多花的计算解释 | **预先确定的主检验（Y1）**；token 对齐判据成立；限一个模型 | 181 对 182，不一致对 32/31，p=1；只计预算内轮次 174（35/27）；token-yoked 对通用怀疑 42/10，p<.001；总 token 为 critique 的 105%，触顶 0 题 | `controls_readout.py` |
| K2 | 为别的题写的批评不起作用：到达的题不多于 reassuring loop | 预先确定的主检验（X1）；按预先写定的读法为"错配有害，不能归因于针对本题有益"；与 reassuring 的比较为事后补充 | critique 对错配 72/10，p<.001；错配对通用怀疑 9/38；错配对 reassuring 17/20；reached 120 | 同上 |
| K3 | 只读题目的批评到达的题少于 critique loop；但它只花了 88% 的 token，差别不能全归于读答案 | 预先确定的主检验（Q1），Holm 校正后 p=.041；未被标为与长度混淆 | 48/27；reached 161；对通用怀疑 34/22（p=.14） | 同上 |
| K4 | critique loop 的 selected 高于每一个对照，四个对照的 selected 与 reassuring loop 无差别 | **描述性**（规格里不参与判定）；各比较共用一次 critique 运行；论文写为待检验的假设 | 对 token-yoked +22.1 [9.0, 35.8]；对错配 +20.6 [6.5, 36.2]；对只读题目 +18.7 [4.9, 32.8]；对照的 selected 为 92.0–95.6，critique 114.1 | 同上 |
| K5 | 假设：reach 由计算换来；critique 特有的贡献（如果有）在 selection，且需要读答案 | 假设，摘要末句与 Discussion "Two hypotheses"；正在用新题检验（`SELECTION_CONFIRMATION_SPEC.md`） | — | — |

## B. Selected（§4.2）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| B1 | 对 reassuring loop 的 selected 增益没有确立：第三模型上的确认性检验未满足 | **确认性（P1）** | MiniMax +5.2 [−6.9, 18.0]，p=.42 | `third_model_readout.py` |
| B2 | 另两个模型上的同一差值 | 预先确定（qwen）/ 描述（deepseek） | +12.4 [−1.6, 25.6]、+23.3 [8.8, 39.2] | `two_model_tables.py` |
| B3 | 三模型均值为正 | 探索 | +13.6 [5.1, 22.2] | `three_model_means.py` |
| B4 | 对 generic-doubt loop | 预先确定（MiniMax：P2 未满足） | +11.3 [−0.8, 23.7]、+18.5 [3.9, 34.3]、+4.6 [−8.4, 16.8]；均值 +11.5 [3.4, 20.1] | 同 B1–B3 |
| B5 | generic-doubt loop 对 reassuring loop 没有差别 | 描述 | +1.2、+4.8、+0.7；均值 +2.2 [−5.2, 9.8] | 同上 |
| B6 | 只计精确匹配时结论相同 | 描述 | +12.5 [0.8, 24.3]、+12.1 [−0.7, 24.8]、+1.4 [−8.6, 11.8]；均值 +8.7 [1.9, 15.8] | `selected_exact_only.py` |
| B7 | 检验效力有限（区间半宽约 12 题，对 13.6 题的效应约 57%） | 论文的限定 | — | §3 |
| B8 | conversion 在 critique loop 下更低 | 探索 | reassuring/generic/critique/samples：.95/.85/.79/.72、.74/.64/.63/.53、.81/.80/.70/.55；critique − reassuring：−.15 [−.21, −.09]、−.11 [−.20, −.03]、−.11 [−.20, −.03] | `search_not_verification.py` |
| B9 | 两种 loop 都到达的题上，critique loop 选中的不多于 reassuring loop；它的增益来自只有它到达的题（按结果拆分，不是因果分解） | 探索 | 都到达 146/113/114 题：129.6 对 140.0、82.3 对 84.8、90.6 对 95.3（均值 −5.9 [−10.9, −1.1]）；只有 critique 到达 52/69/38 题，其中选中 27.8/31.8/16.3；只有 reassuring 到达 7/10/11 题，选中 5.0/6.0/6.3 | 同上（表 5） |
| B10 | critique loop 的最后一个答案不如它的 plurality answer | 探索 | last − selected：−9.4、−2.1、−7.9；均值 −6.5 [−11.2, −1.8] | 同上 |

| B11 | **假设（不是结论）：reach 的增益是通用的，selected 的增益取决于模型** | 作者提出的假设，写在摘要末句与 Discussion "A hypothesis on models"；明确标为未确立 | 依据：三个模型上 reach 都显著提高，selected 的估计为 +12.4、+23.3、+5.2；MiniMax 上 critic 引出的新答案并不更常正确（16% 对 15%），reach 增益约为另两个模型的一半。反面：模型之间的差别都不显著（qwen − deepseek +10.8 [−8.8, 31.6]；qwen − MiniMax +18.0 [−0.2, 36.8]，p=.07；deepseek − MiniMax +7.2 [−11.2, 25.1]），数据分不清"效应因模型而异"与"同一效应加噪声" | `three_model_means.py` |
| B12 | selected 增益的算术拆分：reach 带来的部分减去 conversion 损失的部分；三个模型上 conversion 都吃掉 reach 收益的一半到四分之三 | 探索，恒等式而非因果分解 | reach 部分 +42.6、+43.6、+22.0；conversion 部分 −30.2、−20.3、−16.7；损失占比 71%、47%、76% | `three_model_means.py` |

## C. 没有 critic 时 loop 选什么（§4.3）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| C1 | 只是再问一次，selected 就比首答多（描述，未检验；首答是偏弱的基线） | 描述 | reassuring loop selected − 首答：32.0、21.8、20.7；deepseek 去掉 28 道首答被截断的题为 28.0；对单个样本的平均正确数（117.1/79.9/82.0）为 28.0、10.8、19.7 | 主表脚本；`three_model_appendix.py` |
| C2 | 答案正确时更容易被重复，所有方法都如此；critique loop 下两个概率都下降，比值上升 | 描述；比值检验为预先确定（qwen、MiniMax：S5 成立） | 重复概率 正确/错误/比值：deepseek .77/.54/1.4、.69/.41/1.7、.53/.25/2.1、.50/.28/1.8；qwen .68/.56/1.2、.51/.40/1.3、.46/.29/1.6、.36/.26/1.4；MiniMax .73/.59/1.2、.70/.54/1.3、.53/.37/1.5、.45/.26/1.7 | `three_model_appendix.py`；区间 `persistence_and_settle.py`、`third_model_readout.py` |

## D. 对独立样本（§4.4）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| D1 | critique loop 的 selected 多于 9 个样本的投票，虽然到达的题不更多 | 预先确定（qwen；MiniMax：S4 勉强成立） | +20.7 [9.0, 32.4]、+23.1 [9.6, 38.6]、+12.2 [1.0, 24.0]（置换 p=.051）；均值 +18.7 [10.7, 26.4] | 主表脚本、`three_model_means.py` |
| D2 | 把写法不同的正确答案并在一起计票后差距缩小（上界，用了参考答案） | 描述 | 13.0 [2.1, 23.8]、12.2 [−2.8, 27.3]、5.4 [−6.2, 17.3] | `merge_correct_vote.py`、主表脚本的 pooled 项 |
| D3 | 同成本（11 个样本，deepseek）下结论不变；USC 作选择器时差距的区间含 0 | 预先确定（R1 成立，R2 不成立） | 11 样本投票 138.2，critique 领先 +19.2 [7.0, 31.1]；USC 145，critique 领先 +12.4 [−0.7, 25.6]，p=.065 | `cost_matched_readout.py` |
| D4 | 与"投票优于顺序修改"的文献的差别来自读出方式（plurality 而非最后一个答案）与答案形式（开放式），不来自题目难度 | 探索 | last − 9 样本投票：+11.3 [−2.1, 24.2]、+21.0 [6.7, 36.5]、+4.3 [−9.2, 17.4]；单字母题（86）plurality 差 0.0、+6.2、+4.4；其余 314 题 +20.7、+16.9、+7.8；难度三层的每题优势 .03/.08/.09 | `reconcile_with_voting_literature.py` |

## E. 同模型 judge（§4.5、附录 G；仅 deepseek 的 restricted critic 轨迹）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| E1 | 三个同模型 judge 都没有把 plurality answer 改得更好 | 预先确定的设计（`EVALUATOR_FINAL_DESIGN.md`）；范围限定为一个模型、一种 critic | reached 192，selected 154，可改进空间 38（平局 10、差一票 11、更多 17）；1,199 次改答中 303 次影响对错（160 修好、143 改坏）；judge 准确率 .57、.59、.66；按 judge 改写后最好 154/156/155 | `section5_headroom.py`、`judge_conditional_test.py` |

## F. 判分与审计（附录 C、D）
| ID | 主张 | 类别 | 数字 | 脚本 |
|---|---|---|---|---|
| F1 | 抽查 100 条判分，93 条与审计结论一致；自动判对的 71 条中 6 条应为错，自动判错的 29 条中 1 条应为对 | 审计方案预先写定（`HUMAN_AUDIT_PLAN.md`）；讨论裁决一路不是独立判断，论文已写明 | 直接比较 53/53，符号核验 12/12，讨论裁决 28/35 | `human_audit_final.py` |
| F2 | 只计精确匹配的结果不依赖 grader（见 A4、B6） | 描述 | — | — |

## G. 其他附录数字
| 内容 | 数字 | 脚本 |
|---|---|---|
| token（百万）：reassuring/generic/critique/samples | 24.6/31.8/61/51.4、15.2/21.0/36/31.8、21.3/24.3/40/44.7（MiniMax 的 critic 为 10.6M；v13 及之前误写为 15.4M / 合计 45，是把 reasoning token 重复计入） | 主表脚本（solver）+ critic 回放或运行记录 |
| 首轮修复/损伤 | deepseek 17/7、22/13、45/20；qwen 30/13、40/18、47/29；MiniMax 21/13、26/12、27/29 | `three_model_appendix.py` |
| critic 文本含下一答案（变好 / 变坏） | 2/132、2/100；17/159、16/132；13/115、16/98 | `three_model_appendix.py` |

## 选题与此前运行的披露（附录 F "Choice of benchmark, earlier runs, and how the questions were drawn"）
目的是让读者能判断 benchmark 和题目是否按结果挑选。附录如实列出：
- 此前六个 benchmark 上 deepseek-v4-flash 的首答正确率：AIME 47/50、GPQA-Diamond 41/50、BBH 40/44、MMLU-Pro 43/50、MATH-500 45/50、BFCL 45/50，合计 89%。
- **此前在这些 benchmark 上也跑过 loop**（deepseek）：早期 critic loop（另一种 critic，无安慰剂）在 GPQA-Diamond 148 题上首答 76%–78% → 末答 81%（两次运行），在 AIME+GPQA+BBH 144 题上 85% → 90%；reassuring loop（设置已改）在同一 148 题上 84% → 86%，同一 144 题上 96% → 94%，另 200 题上 97% → 97%。两组运行的推理预算和判分不同，没有算过 reached / selected，generic-doubt loop 与本文的 critique loop 从未在这些 benchmark 上跑过。论文不从中下任何结论。来源：`experiments/_deprecated/{feedback_loop_C_20261015_175552,c_gpqa_full_deepseek_20261013,feedback_loop_C_20261008,feedback_loop_A2_20261021_000317,feedback_loop_A2_20261020_232545,feedback_loop_A2_20261020_231648}/loop_summary.json`。
- 400 题分三次抽取，没有题目被剔除；见 A10。
- generic-doubt loop 与 critique loop 的规格和判据写于各自运行之前；在 400 题上按冻结协议跑过的每个方法和模型都在论文里。

## 不在论文中的结果
- **按 token 截断 critique loop 的事后分析**（`budget_matched_reach.py`，规则见 `REVIEW_RESPONSE_PLAN.md` A 项）：算过，结果是截断到安慰剂 loop 的预算后 critique loop 不再到达更多。作者判断这一比较方法不成立（安慰剂 loop 自行停止，截断只缩短 critique loop，不能说明安慰剂 loop 多花 token 会怎样），决定不写入论文，改由 token 对齐的安慰剂实验（`TOKEN_YOKED_CONTROL_SPEC.md`）回答；该实验结果不论方向都写入论文。同一脚本里"每轮首次出现正确答案的比例"也一并不写入，以免只留有利的一半。脚本与输出文件保留在仓库。
- restricted critic（C3）对两种安慰剂 loop 的比较、模型 × 方法的交互：`review_fixes_stats.py`，论文只在附录 B 提及 restricted critic。
- 弃答曲线、模拟验证器、自适应采样：`selective_prediction.py`、`verifier_regimes.py`、`tie_and_adaptive_baselines.py`，为早期版本的分析，v15 未使用。
- "模型保留首答的倾向"的观察、GPQA 与蒸馏阶段的数据：作者决定不写入。

## 已知的未决事项
见 `docs/INDEX.md` 第 8 节。
