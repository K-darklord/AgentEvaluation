# 规格：在第二个模型上用新题确认 selection 的结论（deepseek；v1，2026-11-17 22:30，先于 deepseek 在新题上的任何运行）

> 来由：qwen 在 800 道新题上的确认性检验已通过（`CONTROLS_RESULTS.md`：S1 +23.8，S2 +36.8，R1 等价）。deepseek 在原 400 题上 critique 对 reassuring 的 selected 之差为 +12.4 [−1.6, 25.6]，未通过；对九次采样为 +20.7 [9.0, 32.4]。本规格在同样的 800 道新题上对 deepseek 做同一组检验。**选择 deepseek 而不是 MiniMax 的原因如实记录：** MiniMax 原 400 题上的差为 +5.2 [−6.9, 18.0]，预期难以检出，且成本高；这是在已知两个模型原始结果之后作出的选择，论文中写明。
> 名称同 `INDEX.md` 第 2 节。

## 1. 设计

- 模型：deepseek-v4-flash（与原 400 题运行相同的模型与设置）。
- 题目：qwen 已用的同一批 800 道新题（hle_401–hle_1200），不重抽、不剔除。两个模型因此在同一批题上成对。
- 条件：A、A2、A2P、C2、A3，然后 A2PY。A2PY 的预算由 deepseek 在新题上的 C2 运行生成（`yoke_budget_deepseek_confirm.json`，solver 加逐轮记录的 critic token），上限 100 个反馈轮。
- 判分：冻结口径，新文件 `experiments/hle400/t3/is_correct_t3_sidecar_confirm_ds.json`。只在全部跑完并判分后读出一次。

## 2. 读出（脚本 `scripts/selection_confirmation_readout.py` 加模型参数，判据与 qwen 相同）

- **token 对齐**：A2PY 总 token 在 C2 总量的 95%–120% 之间，触顶题不超过 40 道；不成立则 D-S1、D-R1 不作判定。
- **确认性检验（三个，Holm 校正，总 α = .05）**，题目级符号翻转置换检验（10,000 次），双侧，方向须与假设一致，bootstrap 95% 区间：
  - D-S1：selected(C2) − selected(A2PY) > 0。
  - D-S2：selected(C2) − selected(A2) > 0。
  - D-A3：selected(C2) − selected(A3) > 0。
- **reach 的等价性（D-R1，α = .05，单列）**：reached(C2) − reached(A2PY) 的 90% bootstrap 区间落在 ±27 题之内。界限按与 qwen 相同的规则得出：deepseek 原 400 题上 critique loop 比未对齐的通用怀疑多到达 27 题（198 对 171），800 题上相当于 54 题，取其一半。
- **描述性**：其余 reached 的不一致对；selected 的其余两两之差；只计精确匹配；预算内口径；每题轮数、候选数、改答比例、token；重复概率与"最后答案"；按学科与题型分层；两个模型在同一批 800 题上的平均（每题两个模型之和除以 2）的 S1、S2、A3 之差与区间，仅作描述。

## 3. 功效（按 deepseek 原 400 题的标准误估计，800 题上约 10 题）

| 检验 | 真实效应（800 题） | 检出概率（未校正） |
|---|---|---|
| D-S2 | 25 题（与原 400 题的 +12.4 相当） | 约 70% |
| D-S2 | 15 题 | 约 33% |
| D-A3 | 41 题（与原 +20.7 相当） | 约 98% |
| D-S1 | 无先验数据 | — |

## 4. 判定与论文处理

| 结果 | 论文处理 |
|---|---|
| D-S1、D-S2 成立，D-R1 等价 | "reach 靠 token、selection 靠 critique"写为在两个模型的新题上确认 |
| 部分成立 | 逐项如实报告，只把成立的写为确认 |
| D-S1、D-S2 都不成立 | 写明第二个模型上未确认；selection 对安慰剂的优势写为因模型而异，结论限于 qwen |
| D-A3 成立／不成立 | "优于独立采样"写为两个（或一个）模型的新题上确认 |

无论结果如何全部写入论文。
