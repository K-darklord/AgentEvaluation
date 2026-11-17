# 附页：token-yoked generic-doubt control 在 MiniMax-M2.5 上（2026-11-16 20:30，先于任何相关运行）

> 状态：**作者已确认实施（2026-11-16 20:31）**（约 40M token）。判据沿用 `TOKEN_YOKED_CONTROL_SPEC.md` v2.1，一字不改；本页只写与 qwen 不同的地方。

## 目的
qwen 上，通用怀疑花掉同样多的 token 后到达的题与 critique loop 相同（181 对 182）。本页检验这是否只是 qwen 的特点。MiniMax 是现有数据里通用怀疑最不起作用的模型（通用怀疑的 reach 与 reassuring loop 无差别，128 对 125），所以它是对"reach 来自计算"最不利的一个检验。

## 与 qwen 版本的不同
- 模型 `minimax-m2.5`，原 400 题，首答沿用 `experiments/rep3_A_minimax-m2.5/`。
- 预算文件 `experiments/hle400/t3/yoke_budget_minimax.json`（已生成：400 题合计 40.4M；critic token 用轨迹里逐轮记录的实际值，2,251 次调用全部有记录）。
- 输出目录 `experiments/yoke_A2PY_minimax-m2.5/`；判分输出新文件 `experiments/hle400/t3/is_correct_t3_sidecar_yoke_minimax.json`。
- MiniMax 的通用怀疑每轮约 1.2 万 token，高于 qwen，预计需要的轮数更少；上限仍为 100。

## 读出
与 `TOKEN_YOKED_CONTROL_SPEC.md` 第 5 节相同：先查 token 对齐（95%–120%，触顶不超过 20 题）；Y1（reach，critique 对 token-yoked，主口径含越界轮）、Y2（token-yoked 对通用怀疑）；selected 之差为描述性。本页只有一个主检验，不做多重校正。

| 结果 | 结论 |
|---|---|
| Y1 不显著，Y2 显著 | "reach 的优势与多花计算相容"在第二个模型上复现 |
| Y1 显著（critique 仍到达更多） | 在 MiniMax 上 reach 的优势不只是 token；reach 是否来自计算因模型而异 |
| Y1 不显著，Y2 不显著 | 没有定论（多跑通用怀疑在这个模型上没有带来 reach，却也检不出与 critique 的差别） |

功效：critique 对通用怀疑的不一致对在 MiniMax 上是 37/13。差距全部保留时检出概率约 92%，保留一半时约 33%。

## 给执行 agent 的指令（原样转发）
```
任务 Y1-MM（规格：docs/TOKEN_YOKED_MINIMAX_ADDENDUM.md 与 docs/TOKEN_YOKED_CONTROL_SPEC.md v2.1）
MODEL=minimax-m2.5，--arm A2P --temperature 0 --max-rounds 100，
YOKE_BUDGET_FILE=experiments/hle400/t3/yoke_budget_minimax.json，
A_SOURCE_TRAJ=experiments/rep3_A_minimax-m2.5/minimax-m2.5/loop_trajectories.jsonl，
输出目录 experiments/yoke_A2PY_minimax-m2.5/。先跑 16 题健康度检查（只回报运行统计），确认后跑全量。
判分输出新文件 experiments/hle400/t3/is_correct_t3_sidecar_yoke_minimax.json（冻结口径，同
scripts/gen_t3_sidecar_rep3.py），不要写入已有的判分文件。不要计算 reach / selected。
```

---

# 另一个选择：在 deepseek-v4-flash 上（2026-11-16 20:30 补充，先于任何相关运行）

> 状态：**待作者决定**。判据与上文、与 `TOKEN_YOKED_CONTROL_SPEC.md` v2.1 完全相同。两个模型可以只做一个，也可以都做；做哪个不改变任何判据。

## 两个模型作为"第二个模型"的差别

| | MiniMax-M2.5 | deepseek-v4-flash |
|---|---|---|
| 预算（400 题合计） | 40.4M | 61.2M |
| critic token | 逐轮有实际记录 | 没有逐轮记录，每次调用按回放均值 9,826 计（与 qwen 的做法相同） |
| 截断 | 几乎没有 | 通用怀疑的轮次里约 8% 被截断（截断轮按规则判错，但 token 照常计入） |
| 通用怀疑在原实验里的作用 | reach 与 reassuring 无差别（128 对 125） | reach 高于 reassuring（171 对 153） |
| 作为检验的性质 | 对"reach 来自计算"最不利的检验 | 较容易通过的检验 |
| critique 对通用怀疑的不一致对 | 37/13 | 39/12 |

读法：deepseek 上 Y1 不显著，说明结论在第二个模型上复现，但 deepseek 与 qwen 一样是"通用怀疑本来就有用"的模型，推广的力度弱于 MiniMax。MiniMax 上无论哪种结果都更有信息量。

## deepseek 版本的设置
- 模型 `deepseek-v4-flash-payg`（与原 A2P、C2 运行相同的接入），原 400 题，首答沿用 `experiments/hle400_A/`。
- 预算文件 `experiments/hle400/t3/yoke_budget_deepseek.json`（已生成）。
- 输出目录 `experiments/yoke_A2PY_deepseek-v4-flash-payg/`；判分输出新文件 `experiments/hle400/t3/is_correct_t3_sidecar_yoke_deepseek.json`（口径同 `scripts/gen_t3_sidecar_v3.py`）。
- 功效：差距全部保留时约 98%，保留一半时约 45%。

## 给执行 agent 的指令（下达时原样转发；现在不要执行）
```
任务 Y1-DS（规格：docs/TOKEN_YOKED_MINIMAX_ADDENDUM.md 的 deepseek 部分与 docs/TOKEN_YOKED_CONTROL_SPEC.md v2.1）
MODEL=deepseek-v4-flash-payg，--arm A2P --temperature 0 --max-rounds 100，
YOKE_BUDGET_FILE=experiments/hle400/t3/yoke_budget_deepseek.json，
A_SOURCE_TRAJ 指向原 hle400_A 的 deepseek 轨迹，输出目录 experiments/yoke_A2PY_deepseek-v4-flash-payg/。
先跑 16 题健康度检查（只回报运行统计，含截断率），确认后跑全量。
判分输出新文件 experiments/hle400/t3/is_correct_t3_sidecar_yoke_deepseek.json（冻结口径），
不要写入已有的判分文件。不要计算 reach / selected。
```
