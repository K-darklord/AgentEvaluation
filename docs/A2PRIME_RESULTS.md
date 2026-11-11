# A2′ (Perturbing Placebo) — Results

**Status.** Frozen scoring on HLE-400 (`is_correct_t3_sidecar_v2.json`, K=3 adjudication), arm `A2P`.
All numbers are taken from the frozen files; nothing is re-estimated post hoc. Ceiling and
persistence (stay) numbers are recomputed on the frozen freeze-key / sidecar-v2 identity with the
exact rule stated below.

---

## Pre-registered endpoints (§5)

### Primary — reachable ceiling (pass@trajectory)

Ceiling = a task is reachable if there exists an answer identity (freeze-key) whose last-occurrence
round is graded correct (the most optimistic selector bound).

| arm | ceiling | A2′ vs arm (paired McNemar) |
|---|---|---|
| A2′ | 170 | — |
| C2 | 198 | p = 0.0001 (A2′-only 12 / C2-only 40 / both 158) |
| A2 | 154 | p = 0.0113 (A2′-only 26 / A2-only 10 / both 144) |

### Secondary 1 — selection (mode / final / settle)

| arm | mode | final | settle |
|---|---|---|---|
| A2′ | 143 (0.3575) | 135 (0.3375) | 127 (0.3175) |
| C2 | 159 (0.3975) | 148 (0.3700) | 121 (0.3025) |
| A2 | 145 (0.3625) | 142 (0.3550) | 136 (0.3400) |
| A3 | 136 (0.3400, vote) | — | — |

mode, paired comparison — recency (latest-tie) and symmetric (both sides randomized, 300 paired draws):

| comparison | recency (A2′ vs other) | recency p (A2′-only / other / both) | symmetric (A2′ vs other) | symmetric p (median [IQR]) |
|---|---|---|---|---|
| A2′ vs C2 | 143 vs 159 | 0.0259 (15 / 31 / 128) | 142.1 vs 157.4 | 0.032 [0.019, 0.054] (74% p < 0.05) |
| A2′ vs A2 | 143 vs 145 | 0.8714 (18 / 20 / 125) | 142.2 vs 146.0 | 0.63 |
| A2′ vs A3 | 143 vs 136 | 0.3604 (25 / 18 / 118) | 142.1 vs 137.1 | 0.54 |

### Secondary 2 — stay asymmetry (persistence)

P(stay) = P(next committed round keeps the same freeze-key | current round correct / wrong).
Adjacent committed rounds only; `None`-key and `finish_reason == "length"` rounds excluded.
Brackets are 95% bootstrap CIs (3,000 draws over tasks, pooled).

| arm | P(stay\|correct) | P(stay\|wrong) | ratio | run-3 (stay² ratio) |
|---|---|---|---|---|
| A2′ | 0.710 [0.656, 0.768] | 0.501 [0.462, 0.542] | 1.42 [1.27, 1.59] | 2.01 |
| C2 | 0.570 [0.507, 0.636] | 0.298 [0.267, 0.333] | 1.91 [1.63, 2.21] | 3.66 |
| A2 | 0.793 [0.734, 0.855] | 0.628 [0.585, 0.672] | 1.26 [1.15, 1.39] | 1.59 |
| C3 | 0.555 [0.494, 0.622] | 0.359 [0.323, 0.395] | 1.55 [1.34, 1.79] | 2.39 |
| A3 | 0.535 [0.468, 0.604] | 0.345 [0.294, 0.395] | 1.55 [1.29, 1.89] | 2.42 |

### Secondary 3 — per-item dynamics

| arm | mean rounds | tasks w/ switch | wrong→correct | correct→wrong | candidates (mean) |
|---|---|---|---|---|---|
| A2′ | 5.80 | 248 | 98 | 76 | 2.69 |
| C2 | 6.89 | 276 | 187 | 154 | 3.66 |
| A2 | 4.87 | 186 | 65 | 37 | 2.06 |
| C3 | 6.72 | 274 | 190 | 162 | 3.50 |
| A3 | 10.00 | 339 | 271 | 267 | 4.88 |

Candidates = mean number of distinct freeze-key identities committed per task.

### Secondary 4 — solver cost (no critic cost)

| arm | solver tokens (total) | solver rounds | LLM critic calls |
|---|---|---|---|
| A2′ | 30.22M | 2320 | 0 |
| C2 | 38.13M | 2758 | 2358 |
| A2 | 24.66M | 1948 | 0 |
| C3 | 37.05M | 2688 | 2288 |
| A3 | 51.32M | 4000 | 0 |

---

## Pre-registered interpretation (§5)

A2′ ceiling (170) ≤ C2 ceiling − 15 (198 − 15 = 183), and the A2′ vs C2 mode difference is
significant (p = 0.0259 < 0.05). Both criteria of the pre-registered "content-has-effect" branch are
met → **content has an effect** (内容有作用): the specific, grounded critique is the active
ingredient; a structured, non-specific perturbation does not reproduce the C2 ceiling (170 vs 198).

A2′ vs A2 (reported regardless): the perturbation raises the ceiling over the soothing placebo
(170 vs 154, p = 0.0113) but does not improve the selected answer (mode 143 vs 145, p = 0.8714) —
it reaches more correct answers than soothing yet loses them to a weaker persistence lock
(asymmetry 1.42 vs 1.26).
