# 300 秒墙钟超时对已有运行的影响（只读审计，2026-11-20）

**范围**：qwen3.8-flash 与 deepseek-v4-flash 在 HLE-800 上的 A、C2、A2、A2PY、A3、A3Y（USC 见 §6）；qwen3.8-flash 在 BBEH-800 上的 A、C2、A2、A2P、A2PY、A3、A3Y、GNM、GKI、GT7。
**约束**：全程只读；未读任何 `is_correct`、sidecar 或正确率；未改动任何轨迹、判分、配置或脚本。
**产物**：
- `scripts/wall_timeout_audit.py`（可重复运行）
- `experiments/hle400/t3/wall_timeout_flags.json`（每模型 × 条件 × 题的标记）

---

## 1. 背景与机制（直接看到）

`src/agent.py::_call_llm_text` 的流式调用：

- 每次尝试开始时设墙钟 `wall_deadline = now + LLM_STREAM_WALL_TIMEOUT`（`src/agent.py:749`），
  超时抛 `TimeoutError("stream wall-clock timed out after 300s")`（`:752`）；
- 外层 `for attempt in range(3)`（`:718`），每次重试**重置**墙钟；
- `latency_ms` 取自 `result.total_latency_ms`（`src/run_feedback_loop.py:760`），其 `t0` 在这些重试之外
  （`src/agent.py:881` 起），因此**"一次超时 + 一次成功"会被记成一条正常完成、但耗时包含浪费的记录**。
- 于是只有在"耗时 > 输出 token / 生成速度 + 30 s"时，才能断定至少发生过一次重试；这是下述 `imp` 的来源。

---

## 2. A：运行时实际生效的超时值

| 项 | 值 | 来源 |
|---|---|---|
| 流式墙钟上限 | **300 s**（每次尝试） | `src/config.py:31` 默认 |
| 流式读超时 | 60 s | `src/config.py:27` |
| 内部重试 | **3 次**，各重置 300 s | `src/agent.py:718, 749–752` |
| 外层单题 solve 预算 | 900 s | `src/run_feedback_loop.py:1530` 默认 |

- `scripts/*.sh`、根目录 `*.sh`、`~/.zsh_history`、`~/.bash_history` 中**均未发现**对
  `LLM_STREAM_WALL_TIMEOUT` / `LLM_STREAM_READ_TIMEOUT` / `AGENTEVALUATION_SOLVE_TIMEOUT` 的设置；
- 唯一有记录的覆盖：`docs/CAPABILITY_GRADIENT_SPEC.md` 中 `LLM_STREAM_WALL_TIMEOUT=900`、
  `AGENTEVALUATION_SOLVE_TIMEOUT=3000`——该覆盖属于后来的 capability-gradient 运行，**不属本审计范围**；
- 范围内运行没有落盘的 stdout 日志；TRAE 终端记录**查不到**。

**结论**：范围内运行按 300/60/900 默认执行的可能性最大，但**启动环境未被记录，无法证明**。

---

## 3. B：按条件、按角色的统计

`latency_ms` 每轮只有一个值，**覆盖解答调用**（含内部重试）；**critic 没有耗时字段**，故只报 critic 的调用数与 capped 数，不做耗时判断。

- `capped`：`reasoning_tokens >= 16384`
- `>300`：`latency_ms > 300000`
- `imp`：按规格判定——用同条件、`latency<=250 s`、`completion>2000` 的调用估速，取**最慢 5%** 的速度 `v`，
  `latency_s > completion/v + 30` 即判"不可能一次跑完"
- `imp_med`：同一判据改用**中位速度**的敏感性值（见 §7 口径提醒）

| 范围 | 条件 | calls | capped | >300 s | imp | imp_med | api_fail | critic calls |
|---|---|---|---|---|---|---|---|---|
| HLE qwen | A | 800 | 143 | 62 (7.8%) | 1 | 46 | 0 | 0 |
| HLE qwen | C2 | 5,854 | 1,074 | 174 (3.0%) | 56 | 211 | 0 | 5,036 |
| HLE qwen | A2 | 3,883 | 644 | 97 (2.5%) | 32 | 170 | 0 | 0 |
| HLE qwen | A2PY | 12,967 | 1,457 | 882 (6.8%) | 9 | 402 | 0 | 0 |
| HLE qwen | A3 | 8,000 | 1,572 | 193 (2.4%) | 93 | 339 | 0 | 0 |
| HLE qwen | A3Y | 15,804 | 2,106 | 256 (1.6%) | 127 | 447 | 0 | 0 |
| HLE ds | A | 800 | 400 | 12 (1.5%) | 25 | 30 | 0 | 0 |
| HLE ds | C2 | 5,610 | 2,924 | 36 (0.6%) | 80 | 147 | 0 | 4,768 |
| HLE ds | A2 | 3,652 | 1,697 | 104 (2.8%) | 148 | 194 | 0 | 0 |
| HLE ds | A2PY | 10,952 | 4,397 | 479 (4.4%) | 379 | 736 | 0 | 0 |
| HLE ds | A3 | 8,000 | 3,887 | 455 (5.7%) | 360 | 669 | 0 | 0 |
| HLE ds | A3Y | 14,566 | 5,468 | 571 (3.9%) | 487 | 820 | 0 | 0 |
| BBEH qwen | A | 800 | 232 | 59 (7.4%) | 14 | 66 | 0 | 0 |
| BBEH qwen | C2 | 6,351 | 1,758 | 479 (7.5%) | 120 | 527 | 0 | 5,534 |
| BBEH qwen | A2 | 4,265 | 1,511 | **543 (12.7%)** | 136 | 583 | 0 | 0 |
| BBEH qwen | A2P | 4,866 | 1,840 | 537 (11.0%) | 255 | 656 | 0 | 0 |
| BBEH qwen | A2PY | 13,198 | 2,812 | 482 (3.7%) | 261 | 879 | 0 | 0 |
| BBEH qwen | A3 | 8,000 | 2,277 | 505 (6.3%) | 167 | 648 | 0 | 0 |
| BBEH qwen | A3Y | 17,728 | 3,229 | 556 (3.1%) | 213 | 761 | 0 | 0 |
| BBEH qwen | GNM | 14,085 | 2,676 | 714 (5.1%) | 290 | 950 | 0 | 0 |
| BBEH qwen | GKI | 6,550 | 1,636 | 522 (8.0%) | 242 | 675 | 0 | 0 |
| BBEH qwen | GT7 | 13,044 | 2,819 | 395 (3.0%) | 261 | 729 | 0 | 0 |

**读数**

- capped 比例：qwen HLE 11–20%，BBEH 18–38%；deepseek 37–52%（更爱用满思考预算）。
- 受影响程度**不均匀**：>300 s 占比从 0.6%（HLE ds C2）到 12.7%（BBEH qwen A2）。
- 论文主比较里，最值得注意的一处：**BBEH 的 reassuring（A2）是受影响最大的主臂**（12.7% >300 s，9.0% imp/capped），
  而 critique（C2）是 7.5% / 6.8%。这是"被审计的对象"，不是"结论"。

---

## 4. C：整题重跑

- `scripts/rerun_api_failures.py` 的规则：任一轮 `api_failure` → **整题重跑**（A3 只重采样失败样本轮），
  重跑前把原文件备份为 `<file>.bak_apifail_<ts>`。
- 全仓库共 **17 个** `.bak_apifail` 备份，**全部**位于 `experiments/_deprecated/backups_20261111/`，
  属于第一批 400 题时期（`rep200_*`、`hle400_*`）。
- **范围内 22 个条件，`api_failure` 轮次全部为 0**；没有范围内备份，也没有 merge 记录。

**结论：这些运行没有触发整题重跑。** 手工重跑没有记录，无法排除。

---

## 5. D：筛选是否与内容有关

只看 capped 调用，“有重试迹象（imp=True）”对“无迹象（imp=False）”：

| 条件 | 有迹象：completion / 答案字符 | 无迹象：completion / 答案字符 |
|---|---|---|
| HLE qwen C2 | 16,754 / **42** | 16,769 / 38 |
| HLE qwen A2 | 16,767 / **22** | 16,738 / 43 |
| HLE qwen A3 | 16,774 / **32** | 16,897 / 48 |
| HLE ds C2 | 17,696 / **206** | 17,375 / 183 |
| HLE ds A2 | 17,080 / **84** | 17,463 / 201 |
| HLE ds A2PY | 16,962 / **81** | 17,262 / 162 |
| BBEH qwen A2PY | 16,636 / **268** | 16,693 / 50 |
| BBEH qwen GNM | 16,610 / **40** | 16,755 / 108 |

- **思考长度无差异**（两组都 capped，16.5–17.9k token）；
- **可见答案长度有系统性差异**，但方向随条件而变：deepseek 上重试迹象组更短（81 vs 162、84 vs 201），
  BBEH qwen A2PY 上明显更长（268 vs 50），其余差异较小；
- `finish_reason`：deepseek 无迹象组出现 `length` 的比例更高（42/375 vs 4/25），
  说明重试迹象组较少以 length 结束。

**结论：保留的那次尝试并非与内容无关——可见答案长度存在系统性差异；思考长度无差异。**

---

## 6. USC

`experiments/hle400/t3/usc_result.jsonl`：2,400 行（A3 的 800 题 × 3 次选择），
字段含 `prompt_tokens`、`completion_tokens`、`reasoning_tokens`，**没有 `latency`**。
其中 reasoning 顶到 16,384 的有 313 行。

**结论：USC 的调用没有耗时字段，无法做超时影响分析；只能报告 capped 比例。**
USC 不是独立运行的臂——它是在 A3 的样本上做选择，故其超时影响与 A3 的调用重叠。

---

## 7. 方法学提醒：速度分位数的选择决定结果

规格的"最慢 5% 速度"非常保守。以 HLE qwen A 为例：最慢 5% 速度 26.6 tok/s，
16.4k token 需要约 646 s，而"300 s 超时 + 重试成功"的总耗时通常低于它，于是 62 个 >300 s 的调用里只有 **1** 个被判"不可能"。
改用中位速度（69.5 tok/s）则判出 **46** 个。

因此 `wall_timeout_flags.json` 同时提供：

- `impossible`：规格口径（5 百分位，保守下界）；
- `impossible_med`：中位速度口径（敏感性）。

敏感性分析请明确选一个，并在论文里写明用的是哪一个；两个口径给出的是**下界**与**中位估计**，不是同一件事。

---

## 8. 事实 / 推断 / 查不到

**直接看到**
- §3 全部数字；config 默认 300/60；重试结构 3 次、每次重置墙钟；latency 的起点在重试之外；
- 范围内 `api_failure = 0`；17 个 `.bak_apifail` 全在 `_deprecated`；
- capped 调用的答案长度差异。

**推断**
- 范围内运行使用 300 s 默认值（无覆盖记录，但启动环境未落盘）；
- `imp` 标记代表"至少一次重试"（由 token/时间下界反推，不是直接日志）。

**查不到**
- TRAE 终端记录；
- 范围内运行的 stdout 日志；
- 任何手工整题重跑记录；
- 具体某次调用是否真的重试过（只能由时间/token 反推）。

---

## 9. 复现

```bash
python3 scripts/wall_timeout_audit.py --repo ~/PycharmProjects/AgentEvaluation            # 写 flags，打印汇总
python3 scripts/wall_timeout_audit.py --repo ~/PycharmProjects/AgentEvaluation --no-write # 只打印
```

标记文件结构：`{"<scope>|<model>|<condition>": {"<task_id>": {"impossible": bool, "impossible_med": bool, "rounds": [int], "api_fail": bool}}, "_definitions": {...}}`

---

## 10. 敏感性分析（另一份脚本；使用判分数据，不属于本审计的只读范围）

- `scripts/wall_timeout_sensitivity.py` → `experiments/hle400/t3/wall_timeout_sensitivity.json`
- 对 8 个对比（qwen/deepseek HLE、qwen BBEH × 三个对照），在每个对比内分两个子集重算 selected 之差：
  “两条件都未被标记”与“任一被标记”；`spec` 与 `median` 两种口径各一份，附区间与每百题差。
- 该脚本读取 `confirm_common` 与判分 sidecar，**不属于本次只读审计**；本审计只用它产出的标记文件。
