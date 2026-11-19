# 登记：等 token 下 loop 对采样的优势来自 reach 还是转化（2026-11-19 14:15 写定，UTC+8；先于 E2 判分文件的生成与任何 reached / selected 计算）

> 时间如实记录：写定时 E2 的续采与 USC 已跑完，**新增采样的裁判判分正在进行**（`astra_verdicts_confirm.jsonl` 在写入，约完成一半）；判分文件 `is_correct_t3_sidecar_confirm3.json` / `_confirm_ds2.json` 尚未生成，分析方与执行方都没有按题汇总过 A3Y 或 USC 的 reached / selected。写定时已知的只有前九次采样的结果（即已读出的 T-A3、D-A3）。本登记补充 `EQUAL_TOKEN_SAMPLES_SPEC.md` 第 3 节，不改其中的 E-SC、E-USC。

## 1. 依据（已有读出，恒等式拆分，描述性）

selected = reached × 转化。把 critique loop 对九次采样的差拆成两项（对称拆分：reach 项 = Δreached × 两者转化的平均；转化项 = Δ转化 × 两者 reached 的平均；两项相加等于总差）：

| 格子 | 总差 | reach 项 | 转化项 | 转化 |
|---|---|---|---|---|
| qwen HLE 新 800 | +27.2 | +10.7 | +16.5 | .541 → .590 |
| deepseek HLE 新 800 | +29.5 | +5.9 | +23.6 | .622 → .687 |
| qwen BBEH-hard | +46.1 | +28.4 | +17.7 | .630 → .661 |

三个格子的转化项都在 +17 到 +24 之间；reach 项随 token 差变化（BBEH 上 critique 多用 38% token）。由此登记假说：**等 token 时，reach 项消失，优势只剩转化项。**

## 2. 登记的检验（每个模型各一组，在 E-SC、E-USC 之外；与之一起做 Holm 校正，每组四个检验）

- **E-R（等价）**：reached(critique) − reached(A3Y) 的 90% bootstrap 区间落在 ±m 之内（qwen m = 33，deepseek m = 27，与 R1 / D-R1 相同）。
- **E-C（转化）**：在两种方法都 reached 的题上，selected(critique) − selected(A3Y) > 0；题目级符号翻转置换（10,000 次），双侧，方向为正。

A3Y 的 reached / selected 定义与九次采样相同（候选为第 1 次到最后一次采样，不含 T=0 首答）。

## 3. 措辞（事先写定）

| 结果 | 论文可写 |
|---|---|
| E-R 与 E-C 都成立 | "token 相同时，独立采样与 critique loop 找到同样多的正确答案；loop 的优势全部在于让正确答案赢得投票" |
| E-C 成立，E-R 不成立 | "loop 在共同找到的题上选得更准"；reach 的差另行报告 |
| E-C 不成立 | 不作机制主张；第 1 节的拆分只作描述 |

读出由 `scripts/equal_token_samples_readout.py` 实现，该脚本在判分文件生成后、任何计算前提交并记哈希。
