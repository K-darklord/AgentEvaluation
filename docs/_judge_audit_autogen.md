# Same-model judge audit (freeze-key, sidecar v2)

mode: all 154 | dev 78 | test 76

## Judge-R

**dev (even)** — E1 edge accuracy (non-UNSURE decisive) = 26/52 = 0.500; decisive edges with verdict 52/167

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 12 | 12 | 81 | 0.90 | [0.42, 1.94] |
| KEEP | 14 | 14 | 59 | 0.90 | [0.44, 1.84] |
| UNSURE | 62 | 53 | 287 | 1.05 | [0.73, 1.51] |

**test (odd)** — E1 edge accuracy (non-UNSURE decisive) = 30/45 = 0.667; decisive edges with verdict 45/134

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 6 | 20 | 71 | 0.30 | [0.13, 0.70] |
| KEEP | 10 | 9 | 72 | 0.98 | [0.42, 2.31] |
| UNSURE | 55 | 34 | 330 | 1.43 | [0.94, 2.18] |

**all 400** — E1 edge accuracy (non-UNSURE decisive) = 56/97 = 0.577; decisive edges with verdict 97/301

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 18 | 32 | 152 | 0.52 | [0.29, 0.91] |
| KEEP | 24 | 23 | 131 | 0.93 | [0.53, 1.63] |
| UNSURE | 117 | 87 | 617 | 1.20 | [0.91, 1.58] |

**E3** dev-fit ±logLR -> test: 76 vs mode 76 (+2 −2, McNemar p=1)  
**E4** test-fit -> dev: 73 vs mode 78 (+5 −10); LR dev/test: CUT 0.90/0.30, KEEP 0.90/0.98, UNSURE 1.05/1.43

**Conditional on counts** (decisive edges with non-UNSURE verdict, n=97): judge 0.577 | counts-only 0.577 | agree 0.629 | **judge when disagreeing 18/36 = 0.500**

**Aggregation grid** (81 configs, in-sample all 400): max 154 (+0 −0) at ('node', 0, 0, 99); configs ≥155: 0; best-on-dev→test (76, 0, 0) (mode 76); best-on-test→dev (78, 0, 0) (mode 78)

## Judge-R+

**dev (even)** — E1 edge accuracy (non-UNSURE decisive) = 47/85 = 0.553; decisive edges with verdict 85/85

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 29 | 31 | 214 | 0.84 | [0.51, 1.38] |
| NO_CUT | 16 | 9 | 107 | 1.52 | [0.70, 3.33] |
| UNSURE | 0 | 0 | 0 | 0.90 | [0.06, 14.32] |

**test (odd)** — E1 edge accuracy (non-UNSURE decisive) = 50/80 = 0.625; decisive edges with verdict 80/80

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 22 | 30 | 254 | 0.68 | [0.39, 1.16] |
| NO_CUT | 20 | 8 | 107 | 2.13 | [0.97, 4.64] |
| UNSURE | 0 | 0 | 0 | 0.91 | [0.06, 14.57] |

**all 400** — E1 edge accuracy (non-UNSURE decisive) = 97/165 = 0.588; decisive edges with verdict 165/165

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| CUT | 51 | 61 | 468 | 0.75 | [0.52, 1.09] |
| NO_CUT | 36 | 17 | 214 | 1.85 | [1.05, 3.25] |
| UNSURE | 0 | 0 | 0 | 0.90 | [0.06, 14.39] |

**E3** dev-fit ±logLR -> test: 77 vs mode 76 (+3 −2, McNemar p=1)  
**E4** test-fit -> dev: 75 vs mode 78 (+4 −7); LR dev/test: CUT 0.84/0.68, NO_CUT 1.52/2.13, UNSURE 0.90/0.91

**Conditional on counts** (decisive edges with non-UNSURE verdict, n=165): judge 0.588 | counts-only 0.606 | agree 0.448 | **judge when disagreeing 44/91 = 0.484**

**Aggregation grid** (81 configs, in-sample all 400): max 156 (+4 −2) at ('node', 0.5, 0, 99); configs ≥155: 32; best-on-dev→test (75, 0, 1) (mode 76); best-on-test→dev (78, 2, 2) (mode 78)

## Judge-C

**dev (even)** — E1 edge accuracy (non-UNSURE decisive) = 62/97 = 0.639; decisive edges with verdict 97/167

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| OVER | 17 | 26 | 136 | 0.60 | [0.33, 1.09] |
| WARRANTED | 36 | 18 | 147 | 1.75 | [1.01, 3.05] |
| UNSURE | 35 | 35 | 144 | 0.90 | [0.57, 1.43] |

**test (odd)** — E1 edge accuracy (non-UNSURE decisive) = 58/84 = 0.690; decisive edges with verdict 84/134

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| OVER | 11 | 24 | 118 | 0.43 | [0.22, 0.85] |
| WARRANTED | 34 | 15 | 184 | 1.95 | [1.08, 3.52] |
| UNSURE | 26 | 24 | 171 | 0.96 | [0.56, 1.66] |

**all 400** — E1 edge accuracy (non-UNSURE decisive) = 120/181 = 0.663; decisive edges with verdict 181/301

| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |
|---|---|---|---|---|---|
| OVER | 28 | 50 | 254 | 0.51 | [0.32, 0.80] |
| WARRANTED | 70 | 33 | 331 | 1.87 | [1.24, 2.81] |
| UNSURE | 61 | 59 | 315 | 0.92 | [0.65, 1.32] |

**E3** dev-fit ±logLR -> test: 71 vs mode 76 (+3 −8, McNemar p=0.227)  
**E4** test-fit -> dev: 77 vs mode 78 (+8 −9); LR dev/test: OVER 0.60/0.43, WARRANTED 1.75/1.95, UNSURE 0.90/0.96

**Conditional on counts** (decisive edges with non-UNSURE verdict, n=181): judge 0.663 | counts-only 0.674 | agree 0.635 | **judge when disagreeing 32/66 = 0.485**

**Aggregation grid** (81 configs, in-sample all 400): max 155 (+1 −0) at ('node', 0, 0.5, 99); configs ≥155: 6; best-on-dev→test (76, 1, 1) (mode 76); best-on-test→dev (78, 0, 0) (mode 78)

