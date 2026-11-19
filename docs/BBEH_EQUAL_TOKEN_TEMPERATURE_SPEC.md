# 规格：BBEH 上的等 token 采样与 T=0.7 的 loop（qwen；v1，2026-11-19 14:35 写定，先于这两个条件的任何运行）

| 冻结记录（执行方在相应时刻填写并提交） | |
|---|---|
| 规格与读出脚本冻结（commit / tag `pre-bbeh-et-20261119`） | commit `9dd460f` |
| `scripts/bbeh_equal_token_readout.py` sha256 | `02818646268f3521c5fdca134d36547f27aca3a0cf518d4fa06e9e94300e47da` |
| 运行开始时间 | `2026-11-19 21:33:10 +0800` |
| 并发（运行记录） | A3Y 全程并发 120；GT7 并发 120 启动，`2026-11-19 22:58:12 +0800` 重启到并发 360 |
| `bbeh_sidecar_et.json` sha256 | 待填 |
| 读出时间与输出 sha256 | 待填 |

## 1. 目的

1. **补齐 token**：BBEH 上 critique loop 对九次采样的确认（B-A3，+46.1）没有对齐 token（采样 69.7M，critique 96.4M）。把采样续到同一预算，在等 token 下重做，并做与 HLE 相同的 reach / 转化检验（`E2_DECOMPOSITION_REGISTRATION.md`）。
2. **排除温度**：loop 在 T=0，采样在 T=0.7。新跑一条 T=0.7 的通用怀疑 loop，与等 token 采样温度相同、token 相同，唯一差别是"loop 还是独立采样"。

## 2. 两个新条件（qwen3.8-flash-payg，BBEH-hard 全部 800 题）

| 条件 | 做法 | 输出目录 | 判分 arm 名 |
|---|---|---|---|
| A3Y | 从已有九次采样（`b1_A3_hard`）续采，T=0.7，提示词与设置不变；累计采样 token（不含第 0 轮首答）≥ 预算即停，越界那次保留；最多 100 次采样。与 HLE 上 E2 的 A3Y 同一代码路径 | `experiments/b1_A3Y_hard_qwen3.8-flash-payg/` | `A3Y` |
| GT7 | 与 A2PY 完全相同（通用怀疑、显示上一轮答案、有保留许可、跑到预算、上限 100 轮），只把温度从 0 改为 0.7；第 0 轮沿用共享的 T=0 首答 | `experiments/b1_GT7_hard_qwen3.8-flash-payg/` | `GT7` |

预算：`experiments/hle400/t3/yoke_budget_bbeh_hard.json`（critique loop 的 solver 加 critic token，与 A2PY 同一文件）。

命令（在 `scripts/run_b1.sh` 加两个分支，其余参数由 `run()` 给出，不得改动）：

```bash
  A3Y)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export RESUME_TRAJ="$PWD/experiments/b1_A3_hard_${M}/${M}/loop_trajectories.jsonl"
    run A3 "b1_A3Y_hard_${M}" --temperature 0.7 --max-rounds 100
    ;;
  GT7)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    run A2P "b1_GT7_hard_${M}" --temperature 0.7 --max-rounds 100
    ;;
```

两个分支只用于 `hard`；`HIDE_PREVIOUS_ANSWER`、`DROP_KEEP_INSTRUCTION` 不得设置。

成本：A3Y 约 30M，GT7 约 100M（qwen）。

## 3. 健康检查（每个条件 16 题，只看运行统计，等确认后才跑全量）

- A3Y：每题采样数；累计 token / 预算；触顶题数；前九次采样与 `b1_A3_hard` 逐字相同的题数（应为 16）。
- GT7：每题轮数；累计 token / 预算；触顶题数；第 0 轮与 A2PY 逐字相同的题数（应为 16）；第 1 轮及以后的请求确实使用 temperature 0.7（贴出请求参数或日志一行）；第 1 轮答案与首答相同的题数。
- 两者：空答案数、截断数、接口失败数；每条轨迹带 `yoke_budget` 字段。

## 4. 判分

官方规则函数（与生成 `bbeh_sidecar.json` 的同一份脚本、同样的键规则），写入新文件 `experiments/hle400/t3/bbeh_sidecar_et.json`，格式 `{"arms": {"A3Y": {...}, "GT7": {...}}}`，每条轨迹每一轮都有判定（A3Y 含第 0 轮与前九次，与轨迹轮数逐题相等）。不调用任何接口。

## 5. 读出（`scripts/bbeh_equal_token_readout.py`，只执行一次）

候选：loop 用第 0 轮到最后一轮；采样用第 1 次到最后一次（不含首答）。selected、reached 定义同主实验。

**前置条件**：A3Y、GT7 的 solver token 总量各在预算总量的 95%–120% 之间，触顶不超过 40 题；某条件不满足，用到它的检验不作判定。

**确认性检验（Holm，三个 p 值检验，总 α = .05；符号翻转置换 10,000 次，双侧，方向须为正）**

| 检验 | 量 | 回答 |
|---|---|---|
| B-SC | selected(critique) − selected(A3Y) | BBEH 上第二句在等 token 下是否成立 |
| B-EC | 两者都 reached 的题上，selected(critique) − selected(A3Y) | 优势是否在于"选中" |
| T-1 | selected(GT7) − selected(A3Y) | 温度、token 都相同时，loop 是否仍优于独立采样 |

**等价判定 B-ER**：reached(critique) − reached(A3Y) 的 90% 区间在 ±33 之内（不进入 Holm）。

**描述性**：各比较的 reach / 转化拆分；GT7 − A2PY（loop 内部温度的作用）；critique − GT7；A3Y − 九次采样；每个条件每个答案的正确率、答对 / 答错后的重复率。

## 6. 措辞（事先写定）

| 结果 | 论文可写 |
|---|---|
| T-1 成立 | "温度和 token 都相同时，通用怀疑 loop 仍比独立采样选得更准：loop 的优势不来自温度" |
| T-1 不成立 | loop 对采样的优势不能与温度分开；第二句只写成"优于标准自洽投票（T=0.7）"，温度写进限制 |
| B-SC 成立 | BBEH 上第二句在等 token 下成立（第三个确认） |
| B-ER 与 B-EC 都成立 | 与 HLE 的登记措辞相同："token 相同时两者找到同样多的正确答案，loop 的优势在于让正确答案赢得投票" |
| B-SC 不成立 | BBEH 上第二句降级为"只对九次采样成立" |

## 7. 限制

单模型、单题集；T=0.7 改变答案长度与截断率，token 只按总量对齐；GT7 与 A3Y 的提示词不同（GT7 每轮带通用怀疑与上一轮答案），T-1 检验的是"loop 整体"，不区分记忆与提示。
