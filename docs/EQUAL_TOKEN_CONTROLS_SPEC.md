# 规格：各种反馈在相同 token 下的比较——在已有运行上续跑（qwen；v4，2026-11-16 21:25，先于任何相关运行）

> 状态：**作者已确认实施。下达后判据不再修改。** v1（同日 20:50，存 `docs/_deprecated/20261115_v13_alignment/`）要求从头重跑；作者决定只做续跑、不重跑，v2 据此改写：三个条件都在已有轨迹后面接着跑；critique loop 的重复运行取消（新题实验 `SELECTION_CONFIRMATION_SPEC.md` 会给出一次独立的 critique 运行）。v1 没有任何运行。v3（同日 21:10）：只读题目的批评改为按**总量**对齐（见第 3 节），其余不变；v2 也没有任何运行。v4（同日 21:25，外部审阅后）：三个条件统一为**按题对齐**——不足预算的题续跑到预算，已超出预算的题在读出时只计到预算为止的轮次（见第 3 节）；v3 的按比例补法取消，它使每题的 token 多少取决于已有轨迹的长度。v3 也没有任何运行。
> 名称对照见 `INDEX.md` 第 2 节。

## 1. 为什么做，以及它在论文里是什么样子

反馈的种类不变，仍是五种；本规格只把右边一列补齐：

| 反馈 | 自然停止（已有） | 相同 token |
|---|---|---|
| reassuring：没发现问题 | 123 题，15.2M | **续跑：A2Y** |
| 错配批评：别的题的批评 | 120 题，15.3M | **续跑：C2XY** |
| 通用怀疑 | 149 题，21.0M | 181 题，38.0M（已有，从头跑的） |
| 只读题目的批评 | 161 题，32.0M | **续跑：C2QY** |
| 完整批评（critique） | 182 题，36.2M | 即自身 |

要回答的问题：**花同样多的 token 时，反馈的内容还重不重要？** 两位模拟审稿人都指出，只读题目的批评和错配批评与 critique loop 的差别里混着 token。

## 2. 续跑的定义

三个条件都在 `qwen3.8-flash-payg`、原 400 题上，从各自已有的轨迹接着跑：
- A2Y 接 `experiments/rep200_A2_qwen3.8-flash-payg/`；
- C2XY 接 `experiments/ctrl_C2X_qwen3.8-flash-payg/`；
- C2QY 接 `experiments/ctrl_C2Q_qwen3.8-flash-payg/`。

对每道题：
1. 已有的各轮原样保留，一字不改，作为新轨迹的前半段。
2. 计算已花的 token：solver 各轮的 prompt + completion；C2QY 另加各轮 critic 的 prompt + completion（实际记录值）。
3. 预算取 `experiments/hle400/t3/yoke_budget_qwen.json` 里该题的值（critique loop 在该题上的总花费）。已花不少于预算的题不再跑，原样保留。
4. 其余的题从已有的最后一轮接着往下跑，**不再使用"连续三次相同即停"**，每轮结束后累计 token，达到预算即停，越界的那一轮保留；反馈轮总数（含已有的）上限 100。
5. 续跑各轮的反馈规则与原条件完全相同：A2Y 是固定的那一句；C2XY 按 `mismatch_map_qwen.json` 的供体与循环规则，轮次编号接着已有的往下数；C2QY 的 critic 只看题目，收到此前**所有**轮次（含已有轮次）的怀疑标签，失败处理同 C2Q v2.2。solver 设置与提示词不变。

续跑与"从头按预算跑"的差别只在前半段：前半段就是已有的那次运行。这使"多花 token 之后多到达了哪些题"可以在同一批轨迹上直接读出。

## 3. 按题对齐的定义与对齐判据（写于运行前）

**定义（三个条件相同，也与已有的 token-yoked 通用怀疑相同）。** 每道题的"相同 token"轨迹 = 该条件的轨迹从首答起、到累计 token 第一次达到或超过该题预算的那一轮为止（含这一轮）。预算是 critique loop 在该题上的花费（`yoke_budget_qwen.json`）。
- 已有运行不足预算的题：续跑，直到达到预算。
- 已有运行已经超出预算的题（A2 43 题，C2X 45 题，C2Q 135 题）：不再跑；读出时只计到预算为止的轮次，之后的轮次不计。这正是一个从头按预算跑的运行会停下的位置，所以它不是另一种分析，而是同一条停止规则用在已有轨迹上。
- 这样每道题上对照花的 token 都与 critique loop 相当（只多出越界的那一轮），token 的多少不取决于已有轨迹跑了多长。

**对齐判据。** 按上述口径计入的总 token 在 critique loop 总量（36.22M）的 95%–120% 之间，且跑满 100 轮仍不足预算的题不超过 20 道。预计三个条件都在 103%–108%。

**同时报告的另外两种口径。**
- 自然停止：原条件（已有）。
- 全部轮次：把已超出预算的题多跑的轮次也计入。此时对照花的 token 不少于 critique loop（C2QY 约为 120%），"critique 仍到达更多"在这个口径下是保守的结论。
三种口径一致，结论稳健；不一致时如实报告，不下单一的因果结论。

## 4. 运行规则与判分

- 先各跑 16 题健康度检查（同一组 16 题），只回报运行统计，并核对：新轨迹的前半段与已有轨迹逐字相同。
- 含接口失败轮的轨迹：只重跑续跑的部分（从已有的最后一轮重新接起），已有的前半段不动；报错文本不算答案。
- 输出目录 `experiments/yoke_A2Y_qwen3.8-flash-payg/`、`experiments/yoke_C2XY_qwen3.8-flash-payg/`、`experiments/yoke_C2QY_qwen3.8-flash-payg/`（各含完整轨迹：前半段 + 续跑轮次；每条轨迹记录 `resumed_from_rounds`、预算、累计 token、是否触顶）。
- 判分：冻结口径；已有轮次的判分从已有判分文件原样抄入，只对续跑的新轮次判分；输出到**新文件** `experiments/hle400/t3/is_correct_t3_sidecar_ctrl2.json`，不得写入任何已有的判分文件，不新开争议复判。

## 5. 读出（判据在此写定）

读出脚本 `scripts/equal_token_readout.py` 在数据到齐后由分析方编写，只实现本节。critique loop 的原运行（C2）是各检验的参照。

### 5.1 主检验（reached，按题对齐的口径；精确 McNemar，双侧；三个一起做 Holm 校正，α = .05）
- **E1**：critique 对 C2QY。
- **E2**：critique 对 C2XY。
- **E3**：critique 对 A2Y。

### 5.2 配套检验与描述
- 每种反馈续跑后对续跑前：A2Y 对 A2、C2XY 对 C2X、C2QY 对 C2Q。因为前半段相同，续跑后到达的题只会增加；报告增加了多少题，以及相对通用怀疑的增加量（149 → 181）。
- 相同 token 的四种非 critique 反馈两两之间的 reached（描述）。
- 另外两种口径（自然停止、全部轮次）下的 E1–E3。
- C2QY 的分层：分别在已超出预算的 135 题和续跑过的 265 题上报告 critique 与 C2QY 的 reached，以及两层的 token 分布。
- selected：critique 减各续跑条件之差（置换检验与 bootstrap 区间）。**描述性**；selection 的确认性检验是 `SELECTION_CONFIRMATION_SPEC.md`。同时报告只计精确匹配的数字，以及各条件精确匹配占选中题的比例。
- 检查量：每题轮数、候选数、改答比例、反馈长度、与题目的词汇重合、token、触顶题数、critic 回退轮次。

### 5.3 解释表（限 qwen；成对比较）

| 结果 | 可以说 | 不能说 |
|---|---|---|
| E3 不显著，且 A2Y 比 A2 多到达的题数与通用怀疑的增量相当 | 连"没发现问题"这样的反馈，只要一直问到花够 token，也到达同样多：reach 取决于花掉的 token，与反馈内容无关 | 不能推到其他模型 |
| E3 显著 | 只是反复询问、不加怀疑，花同样的 token 到达不了同样多：token 要配上让 solver 改答的反馈才换得到 reach | — |
| E2 不显著 | 文不对题的批评花够 token 也到达同样多 | — |
| E2 显著 | 文不对题的批评即使花够 token 也不行 | 若 C2XY 低于 A2Y，读作错配有害而非无效 |
| E1 不显著 | 每题花同样多的 token 时，只读题目的批评追上了：到达更多并不需要读答案 | 不能说读答案对 selection 也不需要 |
| E1 显著 | 每题花同样多的 token 时，读了答案的批评仍到达更多 | — |

功效与此前同量级：某个条件与 critique 的差距保留四分之三时检出概率约 88%，保留一半时约 45%。不显著不等于没有差别，届时同时报告不一致对。

无论结果如何，五种反馈在两种停止规则下的 reached 与 selected 全部列入论文的一张表。

## 6. 成本
续跑部分：A2Y 约 22M–24M，C2XY 约 22M–24M，C2QY 约 11M–13M，合计约 55M–60M token，另加新轮次的判分调用。

## 7. 给执行 agent 的指令（原样转发）

```
任务 E（规格：docs/EQUAL_TOKEN_CONTROLS_SPEC.md v4，判据已冻结，只执行、不改判读）。可与任务 S1 并行；并发可以开高（单个条件 60）。
这是续跑，不是重跑：三个条件都从已有轨迹的最后一轮接着往下跑。

1. 代码：给 A2、C2X、C2Q 增加"续跑到预算"模式（建议用环境变量 RESUME_TRAJ 指向已有轨迹，
   与 YOKE_BUDGET_FILE 一起设置时启用）。启用时，对每道题：
   - 读入该题已有的全部轮次，原样作为新轨迹的前半段，不得改动任何字段；记录 resumed_from_rounds。
   - 已花 token = 各轮 prompt_tokens + completion_tokens；C2Q 另加各轮 critic_prompt_tokens + critic_completion_tokens。
   - 已花 >= budget[task_id]：不再跑，直接写出。
   - 否则从已有的最后一轮接着跑：不使用"连续三次相同即停"；每轮结束后累计 token（口径同上），
     累计 >= 预算即停，越界的那一轮保留；反馈轮总数（含已有的）上限 100。
   - 续跑各轮的反馈规则与原 arm 完全相同：A2 用 A2_PLACEBO_FEEDBACK；C2X 的供体与循环规则不变，
     轮次编号接着已有的往下数；C2Q 的 prior_names 用已有全部轮次的 archetype_name 初始化后继续累积，
     critic 提示词与失败处理不变。solver 的输入取已有最后一轮的答案与推理，参数与提示词不变。
   - 每条轨迹记录 yoke_budget、yoke_cum_tokens、yoke_hit_cap。
   - 未设置这两个环境变量时，三个 arm 的行为必须与现在逐字相同。
2. 三个运行，MODEL=qwen3.8-flash-payg，--temperature 0，--max-rounds 100，
   三个都用同一个预算文件 YOKE_BUDGET_FILE=experiments/hle400/t3/yoke_budget_qwen.json
   （v3 里给 C2QY 单独准备的 yoke_budget_qwen_c2qy.json 已取消，不要使用）。
   已有轨迹里已经超出预算的题不再跑、原样写出，不要截断或删改它们的任何轮次；读出时怎么计由分析方处理。
   - A2Y ：--arm A2 ，RESUME_TRAJ=experiments/rep200_A2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl，输出 experiments/yoke_A2Y_qwen3.8-flash-payg/
   - C2XY：--arm C2X，RESUME_TRAJ=experiments/ctrl_C2X_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl，输出 experiments/yoke_C2XY_qwen3.8-flash-payg/
   - C2QY：--arm C2Q，RESUME_TRAJ=experiments/ctrl_C2Q_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl，输出 experiments/yoke_C2QY_qwen3.8-flash-payg/
   不得改动、覆盖或追加写入上述三个已有目录。
3. 每个运行先跑 16 题健康度检查（同一组 16 题），只回报：完成/超时、截断率、每题总轮数与续跑轮数、
   累计 token / 预算、触顶题数、C2QY 的 critic 回退轮次，以及"前半段与已有轨迹逐字相同"的核对结果。
   不要计算或查看对错。回报后等待确认。
4. 续跑中出现 api_failure：只重跑该题续跑的部分（从已有的最后一轮重新接起）；报错文本不得写成答案。
   单题最长可能 100 轮，请放宽单题超时。
5. 判分：冻结口径；已有轮次的判分从 is_correct_t3_sidecar_rep.json（A2）与 is_correct_t3_sidecar_ctrl.json
   （C2X、C2Q）原样抄入，只对续跑的新轮次判分；输出到新文件
   experiments/hle400/t3/is_correct_t3_sidecar_ctrl2.json（三个 arm 各一节：A2Y、C2XY、C2QY）。
   不要写入任何已有的判分文件。不新开 K3 争议。
6. 完成后回报运行统计与文件路径。不要计算任何 reach / selected。
7. 不提交 audit/ 下的文件；提交信息沿用 [P2.x] 编号。
```
