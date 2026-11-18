# 规格：等 token 的独立采样与 universal self-consistency（qwen、deepseek，800 新题；v1，2026-11-18 21:10，先于这两项的任何运行）

> **时间顺序如实记录。** 九次采样的检验（qwen 的 T-A3、deepseek 的 D-A3）已读出并通过（`CONTROLS_RESULTS.md`：+27.2、+29.6）。作者指出该比较没有对齐 token（九次采样只用了 critique loop token 的 76%–79%），也没有与 universal self-consistency 比较。本规格在那之后写定；写定时新题上没有超过九次的采样，也没有任何 USC 的运行。已读出的检验不因本规格改变。
> 做法沿用第一批题上 deepseek 的同类分析（`COST_MATCHED_SC_AND_USC_SPEC.md`，脚本 `scripts/s2_usc.py`、`scripts/cost_matched_readout.py`）。

## 1. 两个条件

- **A3Y（等 token 采样）**：从已有的九次采样接着采（temperature 0.7，提示词与设置不变），每题采到"各次采样的累计 token（prompt + completion，不含 T=0 首答）≥ 该题预算"为止，越界的那一次保留；每题最多 100 次采样。预算与 token-yoked 对照相同：qwen 用 `yoke_budget_qwen_confirm.json`，deepseek 用 `yoke_budget_deepseek_confirm.json`（critique loop 在该题上的 solver 加 critic token）。九次采样已超过预算的题不再采。已有的九次采样原样保留，不得改动。
- **USC**：对每题，把 A3Y 的全部采样答案交给同一模型，由它选出"最一致的回答"（Chen et al., 2023）。提示词、解析规则、失败处理与 `scripts/s2_usc.py` 完全相同（只接受完整句式、取最后一次出现；截断视为解析失败；接口错误不写入记录）。解析失败的题按 A3Y 的多数答案计（与第一批题的处理一致；若第一批题的处理不同，以第一批题为准并回报）。

## 2. 判分

冻结口径（截断 > 精确匹配 > 裁判 > K3 规则不触发）。新增采样逐轮判分；USC 选出的答案取被选中那一次采样的判定。输出新文件：qwen `is_correct_t3_sidecar_confirm3.json`（节 A3Y：全部采样；节 USC：每题一项，含被选中的采样序号），deepseek `is_correct_t3_sidecar_confirm_ds2.json`。**判分脚本不得把裁判接口错误写成判定；读出前运行 `scripts/audit_grader_errors.py` 的同类检查。**

## 3. 读出（脚本 `scripts/equal_token_samples_readout.py`，数据到齐后编写，只实现本节）

每个模型各自一组，两个检验，Holm 校正，总 α = .05；题目级符号翻转置换检验（10,000 次），双侧，方向须与假设一致；bootstrap 95% 区间。
- **token 对齐**：A3Y 的采样总 token 在预算总量的 95%–120% 之间，采满 100 次仍未到预算的题不超过 40 道；不成立则两个检验不作判定。
- **E-SC**：selected(critique) − selected(A3Y 的多数答案) > 0。
- **E-USC**：selected(critique) − USC 选出答案的正确数 > 0。
- 描述性：A3Y 对九次采样的 selected 之差；USC 对 A3Y 多数答案之差；reached；只计精确匹配；每题采样数；USC 解析失败数；对 reassuring 与 token-yoked 通用怀疑的 selected 之差；按题型（开放题、选择题）分别报告。

## 4. 判定与论文处理

| 结果 | 论文处理 |
|---|---|
| E-SC、E-USC 都成立 | "critique loop 在 selection 上优于独立采样"写为：等 token 且换成模型自选共识后仍成立 |
| E-SC 成立，E-USC 不成立 | 写为"优于对独立采样的多数表决；让模型自选共识后差距不再能确立" |
| E-SC 不成立 | 该结论降级：只对九次采样成立，token 对齐后未确认 |

两个模型分别报告，全部写入论文。

## 5. 给执行 agent 的指令（原样转发）

```
任务 E2（规格：docs/EQUAL_TOKEN_SAMPLES_SPEC.md，判据已冻结，只执行、不改判读）。
模型 qwen3.8-flash-payg 与 deepseek-v4-flash-payg，题目为 800 道新题（hle_401–hle_1200）。并发 120–240。

1. A3Y：给 A3 增加"续采到预算"模式（可仿照 A2/C2Q 的 RESUME_TRAJ + YOKE_BUDGET_FILE）。
   - 读入已有 conf_A3 轨迹的全部轮次，原样作为前半段，不得改动。
   - 已花 token = 第 1–9 次采样的 prompt_tokens + completion_tokens 之和（不含第 0 轮的 T=0 首答）。
   - 已花 >= 预算：不再采；否则继续采样（temperature 0.7，提示词与设置同 A3），每采一次累计，
     累计 >= 预算即停，越界的那一次保留；每题最多 100 次采样。记录 yoke_budget、yoke_cum_tokens、yoke_hit_cap。
   - 预算：qwen 用 experiments/hle400/t3/yoke_budget_qwen_confirm.json，
     deepseek 用 experiments/hle400/t3/yoke_budget_deepseek_confirm.json。
   - 输出 experiments/conf_A3Y_{模型}/，不得改动 conf_A3 目录。
2. USC：用 scripts/s2_usc.py 的提示词、解析规则与失败处理（不得改动），对每题把 A3Y 的全部采样答案
   （第 1 次到最后一次）交给同一模型选出最一致的回答。输出 experiments/hle400/t3/usc_confirm_{qwen,deepseek}.jsonl，
   字段与 usc_result.jsonl 相同。解析失败的处理与第一批题相同，并回报失败题数。
3. 健康度检查：A3Y 在前 16 题上先跑，回报每题采样数、累计 token / 预算、触顶题数、截断率、
   前九次与 conf_A3 逐字相同的核对；USC 在前 16 题上回报解析成功率与 token。不看对错。回报后等待确认。
4. 含 api_failure 的采样只重采该次；报错文本不得写成答案。
5. 判分：冻结口径；新文件 is_correct_t3_sidecar_confirm3.json（qwen）与 is_correct_t3_sidecar_confirm_ds2.json
   （deepseek），各含 A3Y（前九次的判定从已有判分文件原样抄入，只判新增采样）与 USC 两节
   （USC 每题一项：{"c": 被选中采样的判定, "s": 同上, "selected_round": 序号, "parse_ok": bool}）。
   裁判接口报错时重试，仍失败则不写入缓存、不生成判分文件并报错退出；不得把接口错误写成判定。
6. 完成后回报运行统计与文件路径。不要计算任何 reach / selected。
7. 不提交 audit/ 下的文件；提交信息沿用 [P2.x] 编号。
```
