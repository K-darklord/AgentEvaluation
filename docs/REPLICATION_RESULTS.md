# Replication Results — Second Model (qwen3.8-flash)

> Numbers only. Scoring follows REPLICATION_SPEC.md §4 frozen protocol
> (finish_reason==length → wrong; T1 exact match → correct; astra K=1 → bool; K3 rules → adjudicated).
> Sidecar: `experiments/hle400/t3/is_correct_t3_sidecar_rep.json`.
> Main-experiment reference: frozen sidecar `is_correct_t3_sidecar_v3.json` (deepseek).

## 0. Data checks

| Item | Value |
|---|---|
| Arms | A, A2, A2P, A3, C2 (no C3) |
| Items per arm | 400 |
| Interface-failure rounds | 0 |
| Duplicate items | 0 |
| First answer consistent across arms | yes |

## 1. Pre-registered tests (R1–R4)

R1 primary statistic: per-item expected score under random ties (analytic), paired sign-flip
permutation test (10,000), 95% bootstrap interval over items. R2/R4: ceiling, exact McNemar.
R3: stay ratio C2 vs A2 (bootstrap interval over items).

| # | Test | Main experiment (pre-registered) | qwen replication | Holds |
|---|---|---|---|---|
| R1 | C2.mode vs A3.vote | 157.4 vs 137.2 (Δ 20.2 [8.5, 32.1], p=0.001) | 114.1 vs 91.0 (Δ +23.1 [9.5, 38.2], p=0.0019) | yes (same direction, CI excludes 0) |
| R2 | ceiling C2 vs A2 | 198 vs 154 (51/7) | 182 vs 123 (69/10), p=5.5e-12 | yes (same direction, p<0.05) |
| R3 | stay asymmetry C2 > A2 | 1.9 vs 1.25 | 1.595 vs 1.200 (C2 CI lower 1.370 > A2 1.200) | yes |
| R4 | ceiling A2P vs C2 | 198 vs 171 (39/12), p=0.0002 | 182 vs 149 (16/49), p=5.1e-05 | yes (same read-out: Δ=33 ≥ 15) |

**Read-out:** R1–R4 all hold → **two-model replication**.

## 2. Descriptives (two models side by side; §8)

No thresholds, not success criteria.

| Descriptor | deepseek | qwen |
|---|---|---|
| First-answer accuracy | 113/400 (28.3%) | 69/400 (17.2%) |
| Ceiling A2 / A2P / A3 / C2 | 153 / 171 / 190 / 198 | 123 / 149 / 171 / 182 |
| Mode/vote A2 / A2P / A3 / C2 | 145.0 / 146.1 / 136.7 / 157.4 | 90.8 / 95.6 / 91.0 / 114.1 |
| Distinct candidates A2 / A2P / A3 / C2 | 2.05 / 2.72 / 4.52 / 3.65 | 2.11 / 2.94 / 4.84 / 3.62 |
| Answer-change rate A2 / A2P / A3 / C2 | 0.372 / 0.497 / 0.631 / 0.661 | 0.404 / 0.561 / 0.707 / 0.672 |
| stay(correct) A2 / A2P / A3 / C2 | 0.771 / 0.692 / 0.502 / 0.535 | 0.676 / 0.511 / 0.359 / 0.455 |
| stay(wrong) A2 / A2P / A3 / C2 | 0.543 / 0.412 / 0.284 / 0.250 | 0.564 / 0.400 / 0.259 / 0.285 |
| stay ratio A2 / A2P / A3 / C2 | 1.42 / 1.68 / 1.77 / 2.14 | 1.20 / 1.28 / 1.38 / 1.60 |
| A3 inter-sample agreement | 0.369 | 0.293 |
| First-round repair/damage A2 | 17 / 7 (ratio 0.96) | 30 / 13 (ratio 0.48) |
| First-round repair/damage A2P | 22 / 13 (ratio 0.67) | 40 / 18 (ratio 0.46) |
| First-round repair/damage C2 | 45 / 20 (ratio 0.89) | 47 / 29 (ratio 0.34) |
| Break-even threshold a/(1−a) | 0.394 | 0.208 |

stay ratio bootstrap 95% intervals (items): deepseek A2 1.42 [1.27, 1.58], A2P 1.68 [1.50, 1.88],
A3 1.77 [1.45, 2.14], C2 2.14 [1.83, 2.50]; qwen A2 1.20 [1.07, 1.34], A2P 1.28 [1.12, 1.43],
A3 1.38 [1.10, 1.70], C2 1.60 [1.37, 1.83].

> Note on R3 reference: the pre-registered main-experiment stay asymmetry "1.9 vs 1.25" is the
> spec value. The frozen-sidecar (v3) recomputation gives deepseek C2/A2 stay ratio 2.14/1.42,
> matching manuscript Table 6 (2.1/1.4).
