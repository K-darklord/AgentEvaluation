# 规格：第二个题集 BBEH 上的推广检验与易题对照（qwen；v1，2026-11-18 09:40，先于 BBEH 上任何 loop 的运行）

> 名称同 `INDEX.md` 第 2 节（A 首答，A2 reassuring，A2P generic-doubt，C2 critique，A3 九次独立采样，A2PY token-yoked generic-doubt）。
> 本规格写定时，BBEH 上只有首答筛选（B0）的数据，没有任何 loop 或采样的数据。

## 1. 题集是怎么选出来的（如实记录，论文附录照此披露）

1. **候选与筛选规则。** 候选题集三个：BBEH、OlymMATH、GSM8K（CorrectBench 因取不到测试数据、判分口径过粗而在筛选前放弃）。筛选只跑 qwen 的首答（T=0）。筛选前定下的规则：首答正确率 10%–40% 视为"有空间"，80% 以上视为"饱和"，其余不自动开跑、另行商定。**这条规则在筛选数据产生之前确定，但当时只记录在作者与分析方的对话里（2026-11-17），没有写入仓库；写入仓库的时间是本文件。**
2. **筛选结果**（分析方初步判分，`CONTROLS_RESULTS.md`）。BBEH 每个任务抽 35 题共 805 题，首答正确 48.1%；OlymMATH EASY 约 87%–92%、HARD 约 60%–63%（各 100 题，官方判分器未安装，数字为近似）；GSM8K 200 题 97.5%。
3. **看到筛选结果之后作出的决定**（事后决定，须披露）：
   - GSM8K 与 OlymMATH 不再运行：前者与 OlymMATH EASY 已饱和，没有可观察的空间；OlymMATH HARD 居中且每档只有 100 题。
   - BBEH 整体落在两个区间之外。它的 23 个任务难度差别很大，因此把同一条规则用到任务一级：筛选样本上首答正确率 10%–40% 的 10 个任务作为"难任务"，80% 以上的 3 个任务作为"易任务"；40%–80% 的 10 个任务不运行。
4. **防止选择偏差的做法。** 任务按筛选样本选定；检验用的题从这些任务**没有用于筛选**的题里另抽，筛选用过的题不进入任何检验。23 个任务在筛选样本上的首答正确率全部列入附录。

| 组 | 任务（筛选样本上的首答正确率） |
|---|---|
| 难任务（10 个） | multistep_arithmetic .11，nycc .11，geometric_shapes .17，sportqa .20，hyperbaton .23，temporal_sequence .23，zebra_puzzles .26，linguini .29，sarc_triples .29，shuffled_objects .34 |
| 易任务（3 个） | time_arithmetic .80，object_counting .83，boardgame_qa .97 |
| 不运行（10 个） | buggy_tables .46，causal_understanding .51，object_properties .51，boolean_expressions .57，disambiguation_qa .60，spatial_reasoning .66，word_sorting .69，dyck_languages .71，web_of_lies .74，movie_recommendation .77 |

## 2. 设计

- 模型 `qwen3.8-flash-payg`。
- 题目：每个任务从未用于筛选的 165 题中按固定种子 20261118 抽 80 题。难任务 10 × 80 = **800 题**（BBEH-hard）；易任务 3 × 80 = **240 题**（BBEH-easy）。抽出后不得重抽、不得剔除。
- 条件：A、A2、A2P、C2、A3，然后 A2PY（预算取自本题集上 C2 的运行，solver 加逐轮记录的 critic token，上限 100 个反馈轮）。两组题都跑全部六个条件。
- loop 的设置、停止规则、token 上限、critic 提示词、五句通用怀疑与 HLE 运行完全相同。solver 的提示词只在答案格式上按 BBEH 的要求调整（与 B0 首答所用的格式说明相同），不得做其他改动，不得调参。
- **判分（只用规则）。** 每一轮的最终答案用 BBEH 官方 `evaluate.py` 的 `evaluate_correctness(回答, 参考答案)` 判定，原样使用。不使用任何模型裁判，不设争议复判。
- **候选答案的同一性。** 一轮答案的键 = 官方 `preprocess_sample` 的输出；该输出能解析为数值时，键取数值。键相同即同一候选。截断或空答案没有键，不算候选。
- 判分输出新文件 `experiments/hle400/t3/bbeh_sidecar.json`：`{"arms": {arm: {task_id: [{"c": bool, "k": 键或 null}, ...每轮一项]}}}`，两组题在同一文件。运行期间不查看对错。

## 3. 读出（脚本 `scripts/second_benchmark_readout.py`，数据到齐后编写，只实现本节）

量的定义与论文相同：reached = 任一候选正确；selected = 出现次数最多的候选正确（并列时取期望）。

### 3.1 BBEH-hard（800 题）：确认性检验
- **token 对齐**：A2PY 总 token 在 C2 总量的 95%–120% 之间，触顶题不超过 40 道；不成立则 B-S1、B-R1 不作判定。
- **三个检验，Holm 校正，总 α = .05**；题目级符号翻转置换检验（10,000 次），双侧，方向须与假设一致；题目级 bootstrap 95% 区间：
  - **B-S1**：selected(C2) − selected(A2PY) > 0。
  - **B-S2**：selected(C2) − selected(A2) > 0。
  - **B-A3**：selected(C2) − selected(A3) > 0。
- **reach（单列，α = .05）**：reached(C2) − reached(A2PY) 的 90% bootstrap 区间。界限沿用 HLE 新题的 ±33 题（800 题上的 ±4.1 个百分点）。区间在界内 → 相当；完全在界外 → 有差别；其余 → 没有定论。鉴于 HLE 上该检验下端贴近界限，同时单独报告上端：上端低于 +33 即"critique 的 reach 不多于等 token 的通用怀疑"。
- **描述性**：其余 reached 的不一致对与 selected 之差；每题轮数、候选数、改答比例、token；重复概率、第一次修改的修好/改坏、最后答案；按 10 个任务分别报告三个 selected 之差的方向。

### 3.2 BBEH-easy（240 题）：只作描述
各条件的 reached、selected、最后答案；selected(C2) 减首答、减 A2、减 A2PY、减 A3，附区间；第一次修改的修好/改坏。**事先写下的预期**：首答多数已对时，critique loop 的 selected 不高于 reassuring loop 与首答，可能更低。不设检验。

### 3.3 功效
BBEH 上没有先验数据。若标准误与 HLE 新题相近（800 题上约 9–10 题），真实差 27 题时单个检验的检出概率约 80%，20 题时约 55%。

### 3.4 判定与论文处理

| BBEH-hard 的结果 | 论文处理 |
|---|---|
| B-S1、B-S2 成立，reach 相当或 critique 不多 | "reach 靠 token、selection 靠 critique"写为在第二个题集上确认 |
| 部分成立 | 逐项如实报告，只把成立的写为确认 |
| B-S1、B-S2 都不成立 | 写明在第二个题集上未确认；结论的范围限于 HLE，并讨论题型差别 |
| B-A3 成立／不成立 | "优于独立采样"在第二个题集上确认／未确认 |

BBEH-easy 无论结果如何都报告，用来说明结论的适用范围（首答正确率低的题）。全部结果写入论文。
