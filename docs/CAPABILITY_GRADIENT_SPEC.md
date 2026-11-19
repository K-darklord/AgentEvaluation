# 规格：能力梯度——Qwen4-Max 在 HLE 新 800 题上（v1，2026-11-20，先于 qwen4-max 的任何运行）

| 冻结记录（执行方在相应时刻填写并提交） | |
|---|---|
| 规格与读出脚本冻结（commit / tag `pre-gradient-20261120`） | 待填 |
| `scripts/capability_gradient_readout.py` sha256 | `582fee21c6fc2f7e4185e817323c4a51dddff95f6e76b9449f81766e1cac2f67` |
| 试跑（16 题）实测 token 与全量费用估计；作者批准全量的时间 | 待填 |
| 运行开始时间 | 待填 |
| 两个判分文件的 sha256 | 待填 |
| 读出时间与输出 sha256 | 待填 |

## 1. 目的

论文目前只有 flash 一档的模型。本实验在同一家族的旗舰模型上重复同一批题、同一套检验，回答两个问题：
1. "同样的 token，critique loop 比独立采样选中更多"在更强的模型上是否仍成立；
2. critique 相对安慰剂 loop 的优势（qwen3.8-flash 上确认，deepseek 上没有）在更强的模型上落在哪一边。

无论结果如何都写进论文。

## 2. 设计

- 模型：`qwen4-max`（2026-11-16 发布）。在 `src/config.py` 新增 `qwen4-max-payg`，除模型名外与 `qwen3.8-flash-payg` 完全相同（thinking 保持模型默认开启，`thinking_budget` 16384，可见输出上限 8192）。solver、critic、USC 都用它。
- 题目：HLE 新 800 题（`hle_401`–`hle_1200`），与 qwen3.8-flash、deepseek 的确认实验完全同一批。
- 提示词、loop 设置、停止规则、通用怀疑的五句话：与 qwen3.8-flash 的确认实验逐字相同，不得调整。
- 条件与顺序（输出目录 `experiments/conf_{arm}_qwen4-max-payg/`）：

| 步 | 条件 | 说明 |
|---|---|---|
| 1 | A | 首答，T=0 |
| 2 | C2 | critique loop |
| 3 | 预算文件 | `experiments/hle400/t3/yoke_budget_q4max_confirm.json`：C2 在每题上的 solver 加 critic token，生成方式同 `yoke_budget_qwen_confirm.json` |
| 4 | A2 | reassuring loop（自然停止） |
| 5 | A2PY | token-yoked 通用怀疑（`YOKE_BUDGET_FILE`，`--max-rounds 100`） |
| 6 | A3 → A3Y | 九次采样（T=0.7），再续采到预算（`scripts/run_a3y_confirm.sh` 的同一路径） |
| 7 | USC | `scripts/s2_usc.py`，输入 A3Y 的全部采样，输出 `usc_confirm_q4max.jsonl` |

不跑 A2P（普通通用怀疑）、C2Q、C2X。

## 3. 预算闸门（必须先过）

1. 先只跑 A 与 C2 的 16 题（`hle_401`–`hle_416`），只看运行统计：每题 solver 与 critic 的 prompt / completion token、轮数、截断数、空答案数、接口失败数、单次调用耗时。不判分，不看对错。
2. 由此估算全量 token 与费用（按当日控制台标价，分别给出不开缓存与开显式缓存两种），**回报给作者，得到明确批准后才跑全量**。参考：qwen3.8-flash 在这 800 题上，A、C2、A2、A2PY、A3Y 合计约 2.5 亿 token。
3. 若 16 题中截断率超过 10% 或接口失败无法通过重试消除，停下回报，不调整任何设置。

## 4. 运行与判分

- 每个条件全量前各跑同一组 16 题健康检查（A、C2 的试跑即可沿用），只回报运行统计；A2PY、A3Y 另回报 token 占预算比、触顶数、每条轨迹是否带 `yoke_budget`；A3Y 回报前九次与 A3 逐字相同。
- 含接口失败的轨迹整题重跑；报错文本不得写成答案。
- 判分：冻结口径（截断 > 精确匹配 > 裁判 > K3 规则不触发），裁判与缓存文件不变（`astra_verdicts_confirm.jsonl`）。写入两个新文件：
  - `is_correct_t3_sidecar_q4max.json`：arms `A`、`A2`、`C2`、`A2PY`、`A3`；
  - `is_correct_t3_sidecar_q4max_e2.json`：arms `A3Y`（前十项从上一文件原样抄入）与 `USC`（格式同 `is_correct_t3_sidecar_confirm3.json`）。
- 裁判接口报错时重试，仍失败则不写缓存、不生成判分文件。读出脚本自带检查：任何由裁判判定的轮次在缓存里没有真实判定，脚本即报错退出。
- 判分期间不计算任何 reached / selected。

## 5. 读出（`scripts/capability_gradient_readout.py`，只执行一次）

定义、统计方法与此前相同（符号翻转置换 10,000 次，bootstrap 95% / 90%，Holm）。

**前置条件**：A2PY 与 A3Y 的 token 总量各在预算总量的 95%–120% 之间，触顶不超过 40 题；不满足则用到它的检验不作判定。

| 族 | 检验 | 量 |
|---|---|---|
| 1（Holm 三项） | G-SC | selected(critique) − selected(等 token 采样) > 0 |
| | G-USC | selected(critique) − USC 选中 > 0 |
| | G-C | 两者都 reached 的题上，同 G-SC |
| 2（Holm 两项） | G-S1 | selected(critique) − selected(token-yoked) > 0 |
| | G-S2 | selected(critique) − selected(reassuring) > 0 |
| 等价（90% 区间在 ±33 内） | G-R1 | reached(critique) − reached(token-yoked) |
| | G-R | reached(critique) − reached(等 token 采样) |

**描述性**：reassuring、token-yoked 各自对等 token 采样；只计精确匹配；最后答案；预算内的采样；合并正确候选；找到 / 转化拆分；保留率；按题型；以及与 qwen3.8-flash 在同一批题上各差值之差（题目级 bootstrap）。

## 6. 论文处理（事先写定）

| 结果 | 写法 |
|---|---|
| G-SC 成立 | "critique loop 在等 token 下选中多于采样"扩展到同家族的旗舰模型（第四个确认） |
| G-SC 不成立 | 如实写为该结论在更强的模型上未确认，并报告首答正确率与两档模型的差 |
| G-S1、G-S2 成立 | 旗舰模型与 qwen3.8-flash 同侧：批评的内容对 selection 有用 |
| G-S1、G-S2 不成立 | 与 deepseek 同侧："再问一次"即可；论文据此写"是否需要批评因模型而异，且不随能力单调" |
| 首答正确率 ≥ 50% | 照常读出；在论文中注明该模型已超出"首答多数错误"的范围 |

梯度只有两档（flash 与 max），"随能力如何变化"只作描述，不作趋势结论。

## 7. 限制

单一家族的两档；每个条件只跑一次；qwen4-max 发布仅数日，接口与默认设置可能变动——运行期间记录模型返回的版本标识，若中途变化则停下回报。
