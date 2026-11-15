# Third-model (MiniMax-M2.5) replication — results & run health

Status: complete. Five arms × 400 questions, scored under the frozen protocol
(`trunc -> wrong -> exact match -> astra K=1 -> K3 rules`; sidecar
`experiments/hle400/t3/is_correct_t3_sidecar_rep3.json`).

This document records numbers and run health only. It makes no conclusions; the
statistical read-out (P1/S1–S5, permutation / McNemar / bootstrap) is performed
separately by the three-model version of `scripts/two_model_tables.py` per
`docs/THIRD_MODEL_SPEC.md` §6–§7.

## 1. Run protection (§4)

Model: `MiniMax-M2.5` (DashScope pay-as-you-go, North China 2 / Beijing).
Arm order: A (greedy round 0) -> A2 -> C2 -> A2P -> A3 (9 samples, T=0.7).
Constants: `max_rounds=10`, `early_stop=3`, `rationale off`, `T=0` (A3: 0.7),
A-seeding (every loop arm seeds round 0 from the A arm), `CRITIC_HOLD_ON_REPEAT=0`.

| arm | questions | rounds | interface failures | truncated rounds | truncation rate | mean reasoning tokens |
|---|---|---|---|---|---|---|
| A   | 400 | 400  | 0 | 0  | 0.00% | 10482 |
| A2  | 400 | 1926 | 0 | 0  | 0.00% | 10572 |
| C2  | 400 | 2651 | 0 | 1  | 0.04% | 10568 |
| A2P | 400 | 2083 | 0 | 14 | 0.67% | 10892 |
| A3  | 400 | 4000 | 0 | 34 | 0.85% | 10451 |

- Interface failures: 0 in every arm (no failed rounds; no consecutive-failure aborts).
- Truncation (`finish_reason = length`) counts per arm: A=0, A2=0, C2=1, A2P=14, A3=34.
- First-answer consistency: each loop arm's round-0 answer matches the A arm's
  round-0 answer on 400/400 questions (100%).
- Sidecar adjudication totals (frozen protocol): `astra_false=8674`, `t1=1356`,
  `astra_true=840`, `adjudicated=141`, `trunc=49`.

## 2. Descriptive numbers (§6)

All counts are out of 400 questions, read from the frozen sidecar
(`is_correct_t3_sidecar_rep3.json`) with the frozen per-round key identities.

| metric | A2 | A2P | C2 | A3 |
|---|---|---|---|---|
| final (last committed round) correct | 100 | 101 | 99 | 80 |
| selected (mode/vote, expected score) | 101.7 | 102.3 | 106.9 | 94.7 |
| ceiling (correct appeared in any round) | 125 | 128 | 152 | 173 |
| distinct candidates / question (mean) | 1.97 | 2.18 | 3.18 | 4.75 |
| rounds / question (mean) | 4.82 | 5.21 | 6.63 | 9.00 |

First-answer accuracy (greedy round 0, A arm): **81/400 (20.25%)**.

## 3. Token accounting (§9)

| arm | solver prompt | solver completion | reasoning | critic prompt | critic completion | critic reasoning |
|---|---|---|---|---|---|---|
| A   | 0.13M | 4.23M | 4.19M | — | — | — |
| A2  | 0.79M | 20.53M | 20.36M | — | — | — |
| C2  | 1.55M | 28.26M | 28.02M | 5.29M | 5.26M | 4.80M |
| A2P | 1.08M | 23.22M | 22.69M | — | — | — |
| A3  | 1.33M | 43.35M | 41.80M | — | — | — |

Totals: solver prompt+completion ≈ 124.5M; solver reasoning ≈ 117.1M; C2 critic
≈ 15.4M (prompt+completion+reasoning).
