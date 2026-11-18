# Mechanism synthesis（2026-11-18，post-hoc；含 BBEH 读出）

**状态**：解释性综合，不是登记过的检验。登记过的预测见 `REACH_SELECTION_DATA.md` §8 与 `CONTROLS_RESULTS.md`（18:50）；
读出结果已冻结在 `experiments/hle400/t3/second_benchmark_readout.json`（sha256 `4be75883…`，commit `9162ca6`）。
**数据**：HLE 400 + 800 新题；BBEH-hard 800、BBEH-easy 240；冻结 sidecar（BBEH `31ab3cf8…`）。
**脚本**：`scripts/second_benchmark_readout.py`、`confidence_strata.py`、`confirm_common.py`、`mechanism_probe.py`。

---

## 0. 机制，四句话

1. **selection 是票数的最大值**：每个答案的票数 ≈ 进入次数 × 停留长度。
2. **loop 的记忆买“集中”**（同一答案被重复），**独立采样买“覆盖”**（k 次独立抽样），**critic 买“回到覆盖”**（打断三连击、延长探索）。
3. 三者各有失效模式：采样有 coverage 没集中；reassuring loop 有集中但早停、coverage 低；critique loop 两者都有，但要把正确锚推开。
4. **净收益 =（新到达 × 其转化率）−（被破坏的转化）**，所以符号取决于基线缺哪一项。

---

## 1. reach × conversion：每个 cell 的三种方法

| cell | 采样 reach / 转化 / selected | reassuring reach / 转化 / selected | critique reach / 转化 / selected |
|---|---|---|---|
| HLE qwen 800 | 329 / .54 / 178.1 | 245 / **.69** / 168.5 | **348** / .59 / **205.3** |
| HLE deepseek 800 | 361 / .62 / 224.7 | 291 / **.88** / 256.2 | **370** / .69 / 254.2 |
| BBEH-hard | 547 / .63 / 344.4 | 465 / **.82** / 379.9 | **591** / .66 / 390.5 |
| BBEH-easy | 232 / .97 / 225.5 | 231 / **.96** / 222.5 | 235 / .95 / 223.8 |

**规律**：reassuring 的转化率在每个 cell 都最高、reach 都最低；critique 反过来；采样居中偏 reach。
**净收益不取决于谁的 reach 高，而取决于“新到达的转化”能否付清“被压低的转化”。**

---

## 2. 四项拆解：BBEH 的 +10.6 花在哪

| 来源 | BBEH-hard | HLE qwen 800 |
|---|---|---|
| 两边都到达 | 178 题，.71 → .67，**−6.0** | 69 题，.57 → .76，**+13.1** |
| 只有 critique 到达 | 150 题，转化 **.27**，**+40.9** | 132 题，转化 .32，+41.9 |
| 只有 reassuring 到达 | 24 题，转化 .54，**−13.0** | 29 题，.31，−9.0 |
| 首答正确 | 263 题，**−11.3** | 149 题，−9.2 |
| **净** | **+10.6** | **+36.8** |

两处对比说明问题不在 critic，而在基线：**HLE qwen 上 critique 把“两边都到达”的转化从 .57 推到 .76；BBEH 上它把 .71 压到 .67。** 同样的扰动，符号相反。

---

## 3. 三个行为量：它们解释交易的两端

| cell | M1 监测（AUROC） | M2 控制（答对保持 − 答错保持） | M3 显式自评（怀疑数：被批评对 / 错） | reassuring 转化 | critique − reassuring |
|---|---|---|---|---|---|
| HLE qwen 800 | .54 | .14 | 2.96 / 2.96 | .69 | +36.8 |
| HLE deepseek 800 | .60 | .23 | 2.81 / 2.86 | .88 | −1.9 |
| BBEH-hard | **.745** | **.34** | 2.92 / 2.94 | .82 | +10.6 |
| BBEH-easy | .887 | — | 2.97 / 2.91 | .96 | +1.3 |

- **M3 → critic 的通道**：四个 cell、两个 benchmark，critic 对正确答案与错误答案的怀疑数相同（差 ≤ .05）。
  所以 critic **不携带对错信息**，只能扰动：reach ↑、转化 ↓。这是“净值永远是交换”的原因。
- **M1 → 票数本身的可信度**：一致性在 HLE 上几乎不预示对错（.54–.60），在 BBEH 上相当准（.745–.887）。
  这解释了为什么 BBEH 的 reassuring 转化能到 .82、HLE qwen 只有 .69。
- **M2 → 无 critic 的 loop 为什么也能选对**：无人质疑时模型更愿意保留正确答案（差 .14–.34），这是记忆偏向正确的那一半。
- **合成**：M3 决定 critic 只能扰动；M1、M2 决定被扰动的系统自己有多稳。系统越稳，扰动越只留下代价。
  表上唯一的近似单调关系：**reassuring 转化越高，critique 净增益越小**（.69→+36.8，.82→+10.6，.88→−1.9，.96→+1.3）。

**两个必须标注的限制**：
1. 这不是已检验的预测（P1/P2 失败），只能作为解释，不能作为规律；
2. **M1 是任务属性，不是模型属性**。HLE 的 .54 只能写成“在开放式答案上无法靠一致性判断对错”，不能写成模型的普遍能力。

---

## 4. BBEH 读出（登记结果的原文判定）

**确认性（18:50 的两条假说）**

| 检验 | 估计 | 区间 | 判定 |
|---|---|---|---|
| B-S2 critique − reassuring（selected, hard） | **+10.6** | [−11.3, 33.5] | 不显著 |
| B-S1 critique − token-yoked | +18.6 | [−3.3, 41.4]，Holm p = .21 | 不显著 |
| （附带）critique − 九样本 | **+46.1** | [25.8, 67.1]，p = .0001 | **显著** |

按登记判据（区间含 0 且估计 < HLE 的一半 18.4）→ **支持 H-状态，不支持 H-能力**。
BBEH-hard 首答 263/800 = 32.9%，增益约为 HLE 的 29%（每 400 题 +5.3 对 +18.2）。
**reach 的 token 解释复现**：critique 591 对 reassuring 465（150/24，p≈0），对 token-yoked 576（61/46，p = .18）。

**五条预测**

| # | 预测 | 实测 | 判定 |
|---|---|---|---|
| P1 | 高把握层“仍选首答”≥ .85，且首答对/错差 ≤ .10 | 单调 ✓、.924 ✓、但 .972 对 .864 = **.108** | **不成立** |
| P2 | ≥ 2/3 增益来自“把握低且首答错” | 5.7 / 10.6 = **53%** | **不成立** |
| P3 | easy 上 \|Δ\| ≤ 12 | 1.3 | 成立 |
| P4 | easy 的高把握首答正确率明显高于 hard | 95.9% vs 55.3% | 成立 |
| P5 | HLE 分层外推落在 95% 区间 | hard 20.9 对 10.6，区间内 ✓；easy −6.1 对 1.3，区间外 | hard 成立 / easy 不成立 |

P2 失败的具体原因（六格）：最大单格贡献是“把握中且答错”（+10.3），不是“把握低且答错”（+5.6）。
即“增益集中在低把握层”在 BBEH 上不成立——增益向中间移动了一层。

---

## 5. 结论：哪些成立、哪些必须改

**成立（可写进论文）**
1. loop 的记忆让 selection 优于独立采样：BBEH-hard **+46.1**（p = .0001）；HLE 两个模型显著。
2. reach 靠 token，不靠 critique：两个 benchmark 的 token-yoked 对照都成立。
3. critic 不携带对错信息（M3 跨 benchmark 复现）：critique 是扰动，不是纠错。
4. 扰动是否划算，取决于基线：reassuring 转化从 .69 到 .96，净增益从 +36.8 到 +1.3。

**必须改（否则被 BBEH 反驳）**
1. 摘要/贡献里“the critique raises what is selected”**站不住**（BBEH +10.6，n.s.）。
   应改为：**a loop's memory raises what is selected relative to sampling; the critic's further contribution is conditional and did not replicate on a second benchmark.**
2. “模型不知道自己对不对”必须限定为“在开放式答案上”；BBEH 的 M1 = .745。
3. 把握分层只能作为 exploratory 报告，并如实写 P1/P2 失败。

**不许做**
- 不改 P1–P5 的阈值、不重新分层、不因为读出结果重跑分析；
- 不用四项拆解声称“解释”了原因——它是恒等式，只说明钱花在哪。

---

## 6. 出处

| 文件 | 值 |
|---|---|
| `experiments/hle400/t3/second_benchmark_readout.json` | sha256 `4be75883f4d246ef80ea0dc6ad91a2592b3e0d1e6c6d8f73b2d63d25b85e47e4`，commit `9162ca6` |
| `experiments/hle400/t3/bbeh_sidecar.json` | sha256 `31ab3cf8…`，commit `d3a2afe` |
| 读出脚本 | `50affe7a…`（readout）、`2e5da7db…`（confidence_strata）、`d3d88368…`（confirm_common） |
| 登记 | commit `6f63ba5`，tag `pre-bbeh-readout-20261118` |
