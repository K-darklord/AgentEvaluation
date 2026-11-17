# 规格：在新题上确认"reach 来自计算、critique 的贡献在 selection"（qwen；v1.1，2026-11-16 21:15，先于任何新题运行）

> 状态：**作者已确认实施（2026-11-16 20:03）。下达后判据不再修改。** 新题已于 2026-11-16 21:08 由执行 agent 抽出（各 400 题，与已用的 400 题无重叠，两批之间无重叠）。v1.1 只在 4.4 节增列一项描述性的分层报告，不改任何判据；增列时尚无任何新题上的运行。
> 本规格取代 `MODEL_DEPENDENCE_SPEC.md` 草案中 qwen 的部分；该草案里 MiniMax 的新题部分（P2）不实施，改由 `TOKEN_YOKED_CONTROL_SPEC.md` 的 MiniMax 附页处理。
> 名称对照见 `INDEX.md` 第 2 节（A 首答，A2 reassuring，A2P generic-doubt，A2PY token-yoked generic-doubt，C2 critique）。

## 1. 来由与要检验的假设

qwen 上原 400 题的对照（`CONTROLS_RESULTS.md`）显示：
- 通用怀疑花掉与 critique loop 同样多的 token 后，到达的题数相同（181 对 182，不一致对 32/31）。这是事先登记的主检验。
- 但 critique loop 的 selected 高于每一个对照（对 token-yoked +22.1 [9.0, 35.8]；对 reassuring +23.3 [8.8, 39.2]）。这些是**描述性**的，且共用同一次 critique loop 运行。

由此提出、并在本实验中用全新的题正式检验的假设：
- **H-sel**：critique loop 选对的题多于 token 对齐的通用怀疑，也多于 reassuring loop。
- **H-reach**：token 对齐后，critique loop 到达的题与通用怀疑相当。

## 2. 设计

- 模型：`qwen3.8-flash-payg`。
- 题目：800 道新题。从 HLE 纯文本题中去掉已用的 400 题，按原规则（按学科比例分层、固定种子）抽两批各 400 题，脚本 `scripts/build_hle_confirm_sets.py`，由执行 agent 运行一次；抽出后不得更换、不得剔除。两批合并为一个 800 题的样本，**只在全部跑完并判分后读出一次**，没有期中查看。
- 条件：A、A2、A2P、C2，然后 A2PY。设置、提示词、停止规则与原运行完全相同。
- A2PY 按 `TOKEN_YOKED_CONTROL_SPEC.md` v2.1 的定义：取消"三次相同即停"，每题跑到累计 solver token 达到该题的预算，上限 100 个反馈轮。预算由**本次新题上的 C2 运行**生成：`python3 scripts/make_yoke_budget.py --c2 <新 C2 目录> --out experiments/hle400/t3/yoke_budget_qwen_confirm.json`；critic token 逐轮有记录时用记录值，否则按回放均值 4,816 计。因此 C2 必须先跑完。
- 运行规则与判分：与此前相同（含接口失败轮的轨迹整题重跑；报错文本不算答案；冻结判分口径，不新开争议复判）。判分输出**新文件** `experiments/hle400/t3/is_correct_t3_sidecar_confirm.json`，不得写入任何已有的判分文件。运行期间不查看任何对错。

## 3. 成本

每 400 题约：A 3M、A2 15M、A2P 21M、C2 36M、A2PY 38M，合计约 113M；800 题约 226M token，另加判分调用。

## 4. 读出（判据在此写定）

读出脚本 `scripts/selection_confirmation_readout.py` 在数据到齐后由分析方编写，只实现本节。量的定义与论文相同。原 400 题的数据不进入任何检验。

### 4.1 token 对齐（先于对错读出）
A2PY 的总 token 在 C2 总量的 95%–120% 之间，且触顶题不超过 40 道（5%）。不成立时 S1 与 R1 都标为"token 未对齐，不作判定"。

### 4.2 确认性检验（两个，Holm 校正，总 α = .05）
- **S1**：selected(C2) − selected(A2PY) > 0。
- **S2**：selected(C2) − selected(A2) > 0。
- 题目级符号翻转置换检验（10,000 次），双侧，方向须与假设一致；区间为题目级 bootstrap 95%。A2PY 用全部轮次（含越界轮）。

### 4.3 reach 的等价性检验（一个，α = .05，不占 4.2 的份额）
- **R1**：reached(C2) − reached(A2PY) 的 90% bootstrap 区间完全落在 ±33 题之内（800 题上的 ±4.1 个百分点）。界限的来由：原 400 题上 critique loop 对未对齐的通用怀疑多到达 33 题，800 题上相当于 66 题；界限取其一半。区间落在界内 → "token 对齐后 reach 相当"；区间完全在界外 → "仍有差别"；其余 → 没有定论。同时报告不一致对与 McNemar p 值。

### 4.4 次要与描述
- reach：C2 对 A2、C2 对 A2P、A2PY 对 A2P（预期复现）。
- selected：C2 − A2P；A2PY − A2P；conversion；"只计精确匹配"下的 S1、S2、R1。
- A2PY 只计预算内轮次时的 S1、R1（辅口径）。
- 每题轮数、候选数、改答比例、token。
- 新旧两批题合并（1,200 题）的估计：仅作探索性结果。
- **按学科与题型的分层（v1.1 增列，描述性）**：新题按与原 400 题相同的规则抽取，学科分布与原题集一致（每批：数学 182、生物医学 41、计算机 41、物理 37、人文社科 36、其他 33、化学 18–19、工程 11–12；原题集为 175、41、44、40、36、31、20、13）。读出时按八个学科、按选择题与开放题分别报告：critique 对 reassuring、对通用怀疑、对 token-yoked 的 reached 不一致对与 selected 之差，新 800 题单独一份，新旧 1,200 题合并一份。不做逐层检验；报告方向一致的学科数，方向相反的学科点名写出。这一项用来回应"单一 benchmark"的质疑：它不能替代第二个 benchmark，但能说明结果是否由某一类题支撑。

### 4.5 功效（按原 400 题的标准误估计，800 题）

| 检验 | 真实效应（每 400 题） | 检出概率 |
|---|---|---|
| S1 | 22 题（与现在相同） | 约 99% |
| S1 | 15 题 | 约 81% |
| S1 | 11 题（减半） | 约 51% |
| S2 | 23 题 | 约 97% |
| S2 | 15 题 | 约 68% |

原 400 题上的估计可能偏高（qwen 是 selected 增益最大的模型，且各比较共用一次运行），"15 题"与"减半"两行更值得参考。不显著不等于没有效应，届时报告估计值与区间。

### 4.6 判定与论文处理

| 结果 | 结论（限 qwen） | 论文处理 |
|---|---|---|
| S1、S2 成立，R1 等价 | 多花 token 带来 reach，带不来 selection；读了答案的批评提高 selection | 作为主结论之一：摘要第二条改为"在一个模型上、用新题确认"；reach 的表述改为"token 对齐后相当" |
| S1 成立，S2 不成立（或反之） | 部分确认 | 两者都如实报告；只把成立的那一个写成确认的结果 |
| S1、S2 都不成立 | critique 对 selection 的增益未得到确认 | 摘要第二条保持"未确立"并写明新题上的检验未通过；Discussion 里相应的假设删去；论文的主结论为"自我批评的 reach 增益可由多花的计算解释" |
| R1 不等价（critique 仍到达更多） | 原 400 题上"token 对齐后 reach 相当"未复现 | 两批结果并列报告，不下结论 |
| R1 没有定论 | — | 报告区间，不下结论 |

无论结果如何，全部写入论文。结论限于 qwen。

## 5. 给执行 agent 的指令（原样转发）

```
任务 S1（规格：docs/SELECTION_CONFIRMATION_SPEC.md，判据已冻结，只执行、不改判读）。并发可以开高（单个条件 60）。

1. 抽题：运行 python3 scripts/build_hle_confirm_sets.py 一次（需要 pyarrow、pandas），生成
   data/raw/hle/hle_confirm_s1.jsonl、hle_confirm_s2.jsonl、hle_confirm_selection.json。
   不得重抽、不得剔除题目。把两批共 800 题接入 --task-set，task id 延续现有编号：
   s1 为 hle_401–hle_800，s2 为 hle_801–hle_1200，顺序同文件。
2. MODEL=qwen3.8-flash-payg，在这 800 题上跑 A、A2、A2P、C2（不跑 A3），流程与
   scripts/run_replication.sh 相同，CRITIC_HOLD_ON_REPEAT=0，所有参数与提示词不变。
   输出目录 experiments/conf_{A,A2,A2P,C2}_qwen3.8-flash-payg/。C2 逐轮记录 critic token。
3. C2 跑完后生成预算：
   python3 scripts/make_yoke_budget.py --c2 experiments/conf_C2_qwen3.8-flash-payg/qwen3.8-flash-payg \
       --out experiments/hle400/t3/yoke_budget_qwen_confirm.json
   然后跑 A2PY：--arm A2P，YOKE_BUDGET_FILE 指向上述文件，--max-rounds 100，
   输出目录 experiments/conf_A2PY_qwen3.8-flash-payg/。
4. 开跑前在前 16 题上做一次流程冒烟，只回报运行健康度，不看对错。
5. 含 api_failure 轮的轨迹整题重跑；报错文本不得写成答案。
6. 判分：冻结口径，输出到新文件 experiments/hle400/t3/is_correct_t3_sidecar_confirm.json。
   不要写入 is_correct_t3_sidecar_rep.json 或任何已有的判分文件（上次把新条件写进了冻结文件，
   已由分析方拆出并恢复；这次请直接写新文件，判分缓存可以另存为 astra_verdicts_confirm.jsonl）。
   不新开 K3 争议。
7. 完成后回报运行统计与文件路径。不要计算任何 reach / selected。
8. 不提交 audit/ 下的文件；提交信息沿用 [P2.x] 编号。
```
