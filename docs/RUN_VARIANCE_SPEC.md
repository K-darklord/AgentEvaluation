# 规格：同一条件重复运行的波动（qwen；v1，2026-11-17 23:10，先于重复运行）

**目的。** 每个条件只跑过一次，区间只反映换题的波动。本项估计同一批题、同一条件再跑一次的波动，用来解读两批新题上 S1 的不均匀（+4.8 与 +19.0）。**纯描述性，不改变任何已读出的检验。**

**设计。** 模型 qwen3.8-flash-payg；题目为第一批新题 hle_401–hle_800（400 题）。重复两个条件，输入与原运行完全相同：
- C2r：critique loop，首答沿用 conf_A，设置同 conf_C2。
- A2PYr：token-yoked generic doubt，预算文件仍为 `yoke_budget_qwen_confirm.json`（与原 A2PY 相同的预算），设置同 conf_A2PY。
判分：冻结口径，新文件 `is_correct_t3_sidecar_confirm_rerun.json`。

**报告（写定）。** 两次运行各自的 reached、selected；逐题 selected 得分的差的总和与标准差；两次运行的多数答案相同的题目比例；selected(C2) − selected(A2PY) 在四种组合（原/重复 × 原/重复）下的取值。不做检验。结果无论如何写入附录。
