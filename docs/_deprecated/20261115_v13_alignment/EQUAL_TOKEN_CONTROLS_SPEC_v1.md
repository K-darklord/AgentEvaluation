# 规格：各种反馈在相同 token 下的比较，及 critique loop 的重复运行（qwen；v1，2026-11-16 20:50，先于任何相关运行）

> 状态：**作者已确认实施（2026-11-16 20:31）。下达后判据不再修改。**
> 名称对照见 `INDEX.md` 第 2 节。本规格沿用 `TOKEN_YOKED_CONTROL_SPEC.md` v2.1 的"token-yoked"定义与对齐判据，沿用 `CONTENT_CONTROLS_SPEC.md` v2.2 的两种反馈。

## 1. 为什么做，以及它在论文里是什么样子

不是再加一批新的安慰剂。反馈的种类不变，仍是五种：

| 反馈 | 自然停止（已有） | 相同 token（本规格补齐） |
|---|---|---|
| reassuring：没发现问题 | 123 题，15M | **新跑：A2Y** |
| 错配批评：别的题的批评 | 120 题，15M | **新跑：C2XY** |
| 通用怀疑 | 149 题，21M | 181 题，38M（已有） |
| 只读题目的批评 | 161 题，32M | **新跑：C2QY** |
| 完整批评（critique） | 182 题，36M | 即自身 |

右边一列现在只有通用怀疑一格。两位模拟审稿人都指出：只读题目的批评只花了 88% 的 token、错配批评只花了 15M，所以它们和 critique loop 的差别里混着 token。把右列补齐后，论文可以用一张表回答一个问题：**花同样多的 token 时，反馈的内容还重不重要？**

另跑一次 critique loop 的重复运行，用来估计运行之间的波动（现在所有比较共用同一次运行）。

## 2. 条件

三个新条件都在 `qwen3.8-flash-payg`、原 400 题、原首答上运行。各自与对应的已有条件只差停止规则：取消"连续三次相同即停"，每题跑到累计 token 达到 `experiments/hle400/t3/yoke_budget_qwen.json` 里该题的预算（critique loop 在该题上的总花费），上限 100 个反馈轮，越界的那一轮保留。

- **A2Y**（reassuring，相同 token）：反馈固定为 "No confident error direction was found for this answer."。累计只算 solver 的 prompt + completion token。
- **C2XY**（错配批评，相同 token）：反馈按 `mismatch_map_qwen.json` 取供体题的冻结批评，循环规则与 C2X 相同。不调用 critic。累计只算 solver token。
- **C2QY**（只读题目的批评，相同 token）：critic 的提示词、已提怀疑标签的回传、失败处理与 C2Q v2.2 完全相同。**累计计入 solver token 与每轮 critic 的 prompt + completion token**（实际记录值）。
- **C2R**（critique loop 重复运行）：与原 C2 完全相同的设置重跑一次，逐轮记录 critic token。

## 3. 运行规则与判分

与此前相同：各先过 16 题健康度检查（只回报运行统计）；含接口失败轮的轨迹整题重跑；不改提示词、不看中间对错。输出目录 `experiments/yoke_A2Y_qwen3.8-flash-payg/`、`experiments/yoke_C2XY_qwen3.8-flash-payg/`、`experiments/yoke_C2QY_qwen3.8-flash-payg/`、`experiments/rep_C2R_qwen3.8-flash-payg/`。判分为冻结口径，输出到**新文件** `experiments/hle400/t3/is_correct_t3_sidecar_ctrl2.json`，不得写入任何已有的判分文件，不新开争议复判。

## 4. 读出（判据在此写定）

读出脚本 `scripts/equal_token_readout.py` 在数据到齐后由分析方编写，只实现本节。原 critique loop 的运行（C2）仍是各检验的参照；C2R 只用于 4.4 节。

### 4.1 token 对齐
三个新条件各自检查：总 token 在 critique loop 总量（36.22M）的 95%–120% 之间，且触顶题不超过 20 道。不成立的条件，其检验标为"token 未对齐，不作判定"。

### 4.2 主检验（reached，精确 McNemar，双侧；三个一起做 Holm 校正，α = .05）
- **E1**：critique 对 C2QY。
- **E2**：critique 对 C2XY。
- **E3**：critique 对 A2Y。

### 4.3 配套检验与描述
- 每种反馈"相同 token"对"自然停止"：A2Y 对 A2、C2XY 对 C2X、C2QY 对 C2Q（多花 token 是否提高这种反馈的 reach）。
- 相同 token 的四种非 critique 反馈两两之间的 reached（描述）。
- selected：critique 减各"相同 token"条件之差（置换检验与 bootstrap 区间）。**描述性**；selection 的确认性检验是 `SELECTION_CONFIRMATION_SPEC.md`。同时报告只计精确匹配的数字和各条件精确匹配占选中题的比例。
- 检查量：每题轮数、候选数、改答比例、反馈长度、与题目的词汇重合、token、触顶题数、critic 回退轮次。

### 4.4 运行间波动（C2R 对 C2）
- 两次运行各自的 reached、selected；只有一次到达的题数（两个方向）；selected 之差及区间。
- 用 C2R 代替 C2 重算 `CONTROLS_RESULTS.md` 里 critique 对各对照的 reached 不一致对与 selected 之差，作为敏感性分析并列报告。
- 纯描述，不设判据。若两次运行的 selected 相差超过 10 题，论文里所有以 critique loop 为一方的 selected 比较都注明这一波动。

### 4.5 解释表（限 qwen；成对比较）

| 结果 | 可以说 | 不能说 |
|---|---|---|
| E3 不显著，且 A2Y 显著多于 A2 | 连"没发现问题"这样的反馈，只要一直问到花够 token，也到达同样多：reach 取决于花掉的 token，与反馈内容无关 | 不能推到其他模型 |
| E3 显著 | 只是重复询问、不加怀疑，花同样的 token 到达不了同样多：token 要配上让 solver 改答的反馈才换得到 reach | — |
| E2 不显著 | 文不对题的批评花够 token 也到达同样多 | — |
| E2 显著 | 文不对题的批评即使花够 token 也不行 | 若 C2XY 低于 A2Y，判为错配有害而非无效 |
| E1 不显著，且 C2QY 显著多于 C2Q | 只读题目的批评花够 token 后追上了：到达更多并不需要读答案 | 不能说读答案对 selection 也不需要 |
| E1 显著 | 相同 token 下，读了答案的批评仍到达更多 | — |
| 任一主检验不显著而对应的配套检验也不显著 | 没有定论 | — |

功效与 Y1 同量级：某个条件与 critique 的差距保留四分之三时检出概率约 88%，保留一半时约 45%。不显著不等于没有差别，届时同时报告不一致对。

无论结果如何，五种反馈在两种停止规则下的 reached 与 selected 全部列入论文的一张表。

## 5. 成本
A2Y、C2XY 各约 36M–38M（只有 solver）；C2QY 约 36M–38M（含 critic）；C2R 约 36M。合计约 150M token，另加判分调用。

## 6. 给执行 agent 的指令（原样转发）

```
任务 E（规格：docs/EQUAL_TOKEN_CONTROLS_SPEC.md，判据已冻结，只执行、不改判读）。可与任务 S1 并行；并发可以开高（单个条件 60）。

1. 代码：把"预算停止"模式从 A2P 推广到 A2、C2X、C2Q。
   - YOKE_BUDGET_FILE 设置时，对这三个 arm 同样：不使用"连续三次相同即停"；每轮结束后累计 token，
     累计 >= budget[task_id] 即停；--max-rounds 100；记录 yoke_budget、yoke_cum_tokens、yoke_hit_cap。
   - 累计口径：A2、C2X 只算 solver 的 prompt_tokens + completion_tokens（含第 0 轮）；
     C2Q 另加每轮 critic 的 critic_prompt_tokens + critic_completion_tokens。
   - 未设置 YOKE_BUDGET_FILE 时，三个 arm 的行为必须与现在逐字相同。其余逻辑（反馈内容、提示词、
     A 首答 seeding、solver 参数、C2Q 的失败处理与标签回传、C2X 的供体与循环规则）不变。
2. 四个运行，MODEL=qwen3.8-flash-payg，原 400 题，--temperature 0，
   A_SOURCE_TRAJ=experiments/rep200_A_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl：
   - A2Y ：--arm A2  ，YOKE_BUDGET_FILE=experiments/hle400/t3/yoke_budget_qwen.json，输出 experiments/yoke_A2Y_qwen3.8-flash-payg/
   - C2XY：--arm C2X ，同一预算文件，输出 experiments/yoke_C2XY_qwen3.8-flash-payg/
   - C2QY：--arm C2Q ，同一预算文件，输出 experiments/yoke_C2QY_qwen3.8-flash-payg/
   - C2R ：--arm C2  ，不设 YOKE_BUDGET_FILE，--max-rounds 10 --early-stop 3，CRITIC_HOLD_ON_REPEAT=0，
           与原 C2 完全相同，逐轮记录 critic token，输出 experiments/rep_C2R_qwen3.8-flash-payg/
3. 每个运行先跑 16 题健康度检查（同一组 16 题），只回报运行统计（完成/超时、截断率、每题轮数、
   累计 token / 预算、触顶题数、C2QY 的 critic 回退轮次）。不要计算或查看对错。回报后等待确认。
4. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。单题最长可能 100 轮，请放宽单题超时。
5. 判分：冻结口径，输出到新文件 experiments/hle400/t3/is_correct_t3_sidecar_ctrl2.json（四个 arm 各一节：
   A2Y、C2XY、C2QY、C2R）。不要写入 is_correct_t3_sidecar_rep.json 或任何已有的判分文件。不新开 K3 争议。
6. 完成后回报运行统计与文件路径。不要计算任何 reach / selected。
7. 不提交 audit/ 下的文件；提交信息沿用 [P2.x] 编号。
```
