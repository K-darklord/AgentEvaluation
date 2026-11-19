# 规格：拿掉 loop 的记忆（v3.1，两阶段；2026-11-18 写定，2026-11-19 修订一次，均先于这些条件的任何运行）

> **唯一执行依据。** 取代 `MEMORY_MANIPULATION_SPEC.md`（v1.4）、`_v2.md`（v2.1）、`_v3.md`（v3）；三份文件保留作记录，不执行。
> v3.1 = v2.1 的通用怀疑线（去掉 C2-NM）作第一阶段，v3 的 question-only 线作第二阶段，且第二阶段只在第一阶段成立时才跑。
> **2026-11-19 修订（运行之前）**：(1) 操纵检查改为双侧，方向另行报告，并据此增加一条措辞规则（5.4）；(2) 第二阶段增加一条事先写定的等 token 读出（6.3）；(3) 第 3 节给出可直接执行的命令；(4) 写明 400 题子集的规则、无键答案的处理、C2Q 的题目范围。读出脚本相应修改，哈希已更新。
> 写定时，G-NM、G-KI、QO-KI、QO-NM 四个条件都没有任何运行。

| 冻结记录（执行方在相应时刻填写并提交） | |
|---|---|
| 规格与第一阶段读出脚本冻结（commit / tag `pre-memory-runs-20261119`） | `b15bbb4` |
| `scripts/memory_manipulation_readout.py` sha256 | `631b44c7bb0d62926362253effcc0048b4e42df1c3a7a7a2fd887ffed366e4a3` |
| 第一阶段运行开始时间 | `2026-11-19 07:24:46`（全量 G-NM 800 / G-KI 400；健康检查 16 题/条件于 07:05 启动、07:22 终止后转全量）——事后补填 |
| `bbeh_sidecar_nm.json` sha256 | 待填 |
| 第一阶段读出时间与输出 sha256 | 待填 |
| 第二阶段读出脚本 `scripts/memory_qo_readout.py` commit 与 sha256（先于第二阶段任何运行） | 待填 |
| 第二阶段运行开始时间 / `is_correct_t3_sidecar_qo.json` sha256 / 读出时间与输出 sha256 | 待填 |

## 1. 目的与两阶段的理由

1. "loop 的记忆买集中"是 BBEH 读出之后的解释，没有直接证据。本实验直接操纵记忆：反馈不变，solver 看不到自己上一轮的答案。
2. **第一阶段放在 qwen × BBEH-hard 的通用怀疑线上**：这是 loop 对九次采样优势最大的格子（+46.1），反馈不含任何与答案有关的内容（无指代、无泄露），规则判分，且已有按 token 对齐的基线（A2PY）。
3. **第二阶段放在 qwen × HLE 新 800 题的 question-only critique 线上**：检验第一阶段的结论能否延伸到含 critique 的 loop。该格子里 loop 对采样的优势小，所以它是延伸检验，不是主检验：**它不成立，不撤回第一阶段的结论。**
4. 第一阶段不成立，则第二阶段不跑。

## 2. 提示词改动（两阶段共用）

只改 `src/run_feedback_loop.py::_feedback_message`，用两个环境变量控制，默认关闭（关闭时输出与现在逐字相同）：

- `DROP_KEEP_INSTRUCTION=1`：删去 `If you believe your previous answer was already correct, keep it as is.`；把要求"说明为何改动或保留上一轮答案"的输出格式改为只要求答案与理由。
- `HIDE_PREVIOUS_ANSWER=1`：删去 `Your previous answer was: …` 一段（含推理摘录）；把指向"你上面的答案"的措辞改为"此前一次作答（未显示）"。同时，solver 的对话历史里不得保留上一轮的回答（每轮 solver 输入 = 题目 + 本轮反馈）。

| 条件 | HIDE_PREVIOUS_ANSWER | DROP_KEEP_INSTRUCTION |
|---|---|---|
| 有记忆、有许可（A2PY、C2Q；已有） | 0 | 0 |
| 有记忆、无许可（G-KI、QO-KI） | 0 | 1 |
| 无记忆（G-NM、QO-NM） | 1 | 1 |

其余文字、温度（0）、token 上限、critic 侧一律不变。**运行前把三种设置下第 1 轮 solver 输入的完整文本各回报一份，得到确认后再跑。**

## 3. 第一阶段：运行与判分

模型 `qwen3.8-flash-payg`；首答沿用各题已有的 T=0 首答。

| 条件 | 题目 | 运行 | 输出目录 | 判分 arm 名 |
|---|---|---|---|---|
| G-NM | BBEH-hard 全部 800 | `--arm A2P`，两个开关都开 | `experiments/b1_GNM_hard_qwen3.8-flash-payg/` | `GNM` |
| G-KI | 每个任务题号 000–039，共 400 | `--arm A2P`，只开 `DROP_KEEP_INSTRUCTION` | `experiments/b1_GKI_hard_qwen3.8-flash-payg/` | `GKI` |

- 停止规则与 A2PY 相同：不因重复而停；跑到累计 solver token ≥ 该题预算；上限 100 轮。预算文件 `experiments/hle400/t3/yoke_budget_bbeh_hard.json`（critique loop 在该题上的 solver 加 critic token，与 A2PY 用的是同一个文件）。
- **命令写死**（在 `scripts/run_b1.sh` 里加两个分支，照抄 A2PY 分支，只多环境变量；其余参数由该脚本的 `run()` 给出，不得改动）：

```bash
  GNM)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export HIDE_PREVIOUS_ANSWER=1 DROP_KEEP_INSTRUCTION=1
    run A2P "b1_GNM_hard_${M}" --temperature 0 --max-rounds 100
    ;;
  GKI)   # 只跑每个任务题号 000-039 的 400 题：--tasks 传入这 400 个 task_id
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export DROP_KEEP_INSTRUCTION=1
    run A2P "b1_GKI_hard_${M}" --temperature 0 --max-rounds 100 --tasks "$TASKS400"
    ;;
```

  `YOKE_BUDGET_FILE` 不设则按自然停止跑，整组对比作废。健康检查与全量运行后都要核对：每条轨迹带 `yoke_budget` 字段，且累计 solver token 达到预算或触顶。两个分支只对 `hard` 有效。
- 400 题子集对所有条件用同一条规则：task_id 末尾题号 < 40（读出脚本对 A2PY、G-NM、九次采样也按这条规则取同样的 400 题）。
- 健康检查：每个条件 16 题，只回报运行统计（完成数、轮数、token 占预算比、触顶数、空答案数、第 1 轮答案与首答相同的题数），并各抽 2 题贴出第 2 轮 solver 输入全文。不判分、不看对错。
- 判分：官方规则函数（与生成 `bbeh_sidecar.json` 的同一份脚本、同样的键规则），写入**新文件** `experiments/hle400/t3/bbeh_sidecar_nm.json`，格式 `{"arms": {"GNM": {task_id: [{"c": bool, "k": key|None}, ...]}, "GKI": {...}}}`。每条轨迹每一轮都须有判定，否则停下回报。

## 4. 第一阶段：成本

G-NM 约 100M token，G-KI 约 50M，合计约 150M（qwen）。不得删减题数；配额不足则停下回报。

## 5. 第一阶段：读出（`scripts/memory_manipulation_readout.py`，只执行一次）

**5.1 操纵检查（决定 NM-2 是否可判）。** 量：第 1 轮答案与首答相同的题目比例，G-NM 对 A2PY，800 题。判据（**双侧**）：精确 McNemar p < .05 **且**两者相差至少 5 个百分点，方向不限；方向如实报告。理由：无记忆时 solver 在 T=0 下只看到题目和通用怀疑，可能直接回到首答，重复率反而更高，这同样说明操纵改变了行为。首答或第 1 轮答案没有键（空输出或被截断）的题目不计入。不通过 → NM-2 记为"操纵未生效，不作判定"，不得读成"记忆无用"。

**5.2 确认性检验（唯一一条）NM-2。** `selected(A2PY) − selected(G-NM) > 0`，800 题；selected 沿用主实验定义；题目级符号翻转置换（10,000 次）双侧，方向为正，p < .05；bootstrap 95% 区间。前置条件：G-NM 的 solver token 总量在预算总量的 95%–120% 之间，触顶题数 ≤ 40；不满足则不作判定。

**5.3 描述性（400 题子集）。** 可见性 = `selected(G-KI) − selected(G-NM)`；许可 = `selected(A2PY) − selected(G-KI)`；各附 95% 区间。另报各条件的 reached、候选数、token、轮数、对九次采样的 selected 之差。

**5.4 措辞与论文处理（事先写定）。**

| 结果 | 论文处理 | 第二阶段 |
|---|---|---|
| NM-2 成立，但"集中"条件不满足（见下） | 只能写"没有上一轮答案，loop 的 selection 更低"，并写明原因是重复更多或 reach 更低；**不得**写"记忆买集中" | 跑 |
| NM-2 成立，且可见性区间下限 > 0 | 可写"呈现上一轮答案提高 selection"（限定：qwen、BBEH-hard、不含内容的反馈） | 跑 |
| NM-2 成立，可见性区间含零 | 只能写"上一轮答案及其保留许可，作为一个整体，提高 selection"，两部分估计都报告 | 跑 |
| NM-2 不成立（操纵检查通过） | "记忆买集中"从论文撤下；loop 优于采样的原因写为未知 | 不跑 |
| NM-2 不作判定 | 如实报告，不下结论 | 不跑 |

**"集中"措辞的条件（三条同时满足，脚本打印 `concentration wording allowed`）**：NM-2 成立；G-NM 的第 1 轮重复率低于 A2PY（即去掉记忆使答案更分散）；G-NM 的 reached 不显著低于 A2PY（精确 McNemar）。若 G-NM 反而更重复，或它的损失来自 reach，则 selection 之差不是"分散"造成的，"记忆买集中"这句话没有得到支持，即使 NM-2 成立。

差显著为负时，如实写为"记忆的净效应在该题集上为负"，按"不成立"处理。脚本末行打印 `stage 2 ... to be run: True/False`，以此为准。

## 6. 第二阶段（仅当第一阶段读出打印 True）

**6.1 设计。** question-only critique（critic 只读题目，不读答案与推理，因此不可能指代或泄露答案）。三个条件的 critic 提示词与停止规则相同（连续三次相同答案即停，最多 10 轮反馈）：

| 条件 | 题目 | 输出目录 | 判分 arm 名 |
|---|---|---|---|
| C2Q（已有，`is_correct_t3_sidecar_confirm2.json`，自然停止的那一组，不是续跑到预算的 C2QY） | HLE 新 800 题（`hle_401`–`hle_1200`，全部 800 题，不是任何 400 题子集） | 已有 | `C2Q` |
| QO-KI（只开 `DROP_KEEP_INSTRUCTION`） | 同一 800 题 | `experiments/conf_QOKI_qwen3.8-flash-payg/` | `QOKI` |
| QO-NM（两个开关都开） | 同一 800 题 | `experiments/conf_QONM_qwen3.8-flash-payg/` | `QONM` |

成本约 116M token。健康检查同 §3（16 题，只看运行统计）。

**6.2 判分。** 与主实验相同的冻结口径，写入新文件 `experiments/hle400/t3/is_correct_t3_sidecar_qo.json`。接口错误不得写成判定；判分后必须跑 `scripts/audit_grader_errors.py`，有未判定条目则补判后再读出。

**6.3 读出（`scripts/memory_qo_readout.py`，由分析方在第二阶段任何运行之前写好并提交、记哈希；只执行一次）。**

- 操纵检查：第 1 轮答案与首答相同的比例，QO-NM 对 QO-KI，判据同 5.1。
- 确认性检验（唯一一条）**NM-A**：`selected(QO-KI) − selected(QO-NM) > 0`，800 题，检验方法同 5.2。
- token：三个条件的总 token 如实报告；不据此取消判定。
- **等 token 读出（次要，事先写定）**：逐题把 QO-KI 与 QO-NM 中 token 较多的一条截到另一条的累计 token（保留累计 token 不超过该值的各轮，至少保留首答），在截断后的轨迹上重算 NM-A 的差与区间。它不改变 NM-A 的判定，只决定措辞（6.4）。
- 次要（描述）：许可 = `selected(C2Q) − selected(QO-KI)`；reached、候选数、轮数、对九次采样之差。
- **不做 200 题试读**；不在跑完之前看任何对错。

**6.4 论文处理。**

| 结果 | 论文处理 |
|---|---|
| NM-A 成立 | 可写"在不读答案的 critique loop 里，呈现上一轮答案同样提高 selection"；**不得**写成"critique loop 的 selection 由记忆驱动"（critique 是否读答案，T-Q 未能确认：+11.8 [−7.4, 29.4]） |
| NM-A 成立，但等 token 读出的区间含零 | 写"在自然停止下成立，在等 token 下未保持"，两个数都报告 |
| NM-A 不成立或不作判定 | 第一阶段的结论保留，限定在"qwen、BBEH-hard、不含内容的反馈"；如实报告延伸未成立 |

## 7. 已知限制（写进论文）

1. 单一模型（qwen）；每个阶段单一题集。
2. 第一阶段的反馈不含 critique；它检验的是"loop 的记忆"，不是"critique 的作用"。
3. 无记忆条件与九次采样的比较受温度影响（loop 为 0，采样为 0.7），只作描述。
4. 可见性与许可的拆分只有 400 题，功效有限。
5. 读答案的 critique loop（C2）不做无记忆条件：critic 的批评会指代 solver 看不到的对象，无法干净解释。

## 8. 给执行方的顺序（一步不省）

1. 提交本规格与 `scripts/memory_manipulation_readout.py`；核对其 sha256 与上表一致；打 tag `pre-memory-runs-20261119` 并 push；填冻结表第一行。
2. 实现 §2 的两个开关；回报三种设置下第 1 轮 solver 输入全文；等确认。
3. G-NM、G-KI 各 16 题健康检查，按 §3 回报；等确认。
4. 填"运行开始时间"；跑满 G-NM 800、G-KI 400（并发可用 120–240）。
5. 判分到 `bbeh_sidecar_nm.json`，记 sha256 并提交。
6. 再次核对读出脚本 sha256；执行一次 `python3 scripts/memory_manipulation_readout.py`；提交输出并记 sha256。**不解读结果**，原样回报。
7. 仅当末行为 True：等分析方提交 `scripts/memory_qo_readout.py` 后，按 §6 重复第 3–6 步（判分后加跑 `audit_grader_errors.py`）。
