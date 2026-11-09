# HLE-400 T3 — Second (independent) audit, 2026-11-02

Scope: `docs/HLE_SCORER.md` v1.2 + `docs/HLE400_T3_AUDIT_REPORT.md` v1.0. Rows read individually:
all 67 missed_rescue, 2 false_rescue, 7 none, all 137 FP candidates (87 judged + 50 low), the cluster
flip. Not audited: 74 confirmed, 932 true_neg (by agreement). Method: re-derived every
(arm, metric) correct set from the raw trajectories + `score_t1` + `t2_astra_audit.jsonl`
(`experiments/hle400/t3/_audit_correct_sets_by_metric.json`); reproduces `t3_final_scores.json`
exactly (112/143/135/142/133/141/117/144). All 67 missed-rescue rows, 2 false rescues, 1 FP and
7 `none` rows were read individually against gold + question.

## 1. Verdict on T3 as a whole

Arithmetic and pipeline: **correct**. Judge quality: **61 of 67 missed rescues are genuine** (format /
algebraic equivalence the T1 matcher cannot see — e.g. `hle_040` Dawson-function identity, `hle_035`
arctanh ≡ arcosh, `hle_290` arccos ≡ arcsin ≡ arctan, `hle_374` compressed path). False rescues
(`hle_129` sign, `hle_336` 2 of 4 eigenvalues) and the FP (`hle_182` C3) are correct calls.

## 2. Rows that must be reverted (astra rescued a truncated, uncommitted response)

| row | arm.metric | finish_reason | loop `committed_answer` | why bogus |
|---|---|---|---|---|
| `hle_032` | A2.final | length | CoT fragment | no `(r,t)` committed; astra inferred from reasoning |
| `hle_182` | A2.final, A2.mode | length | `A` (= Impossible, wrong) | text hedges "(1,6) or (2,4)"; loop itself extracted `A` |
| `hle_114` | C3.final | length | CoT fragment containing the formula | borderline; truncated |
| `hle_202` | C3.final | length | `2` (= gold) | defensible: loop committed `2`; raw text is CoT |

Rule to adopt (applied uniformly, all arms): **a winning round with `finish_reason == "length"` is a
no-commit and scores wrong**, regardless of judge verdict. Under this rule: A2.final 143→**141**,
A2.mode 142→**141**, C3.final 141→**139**, C3.mode 144 (hle_182 already FP-removed), others unchanged.

Rows checked and **kept** (not bogus): `hle_335` C3.settle (formula is literally option C),
`hle_030` (corrector factor present), `hle_156` (asked categories all match), `hle_153` (question asks
for the path-integral form; gold is the trace form — judge followed the question), `hle_280`
(Θ-equivalent), `hle_121` (equivalent under b→1−b).

## 3. Does T3 explain "A2 overtakes C3"? — No. The reversal is real and it is EIR.

Paired analysis vs the shared init-correct set (112 tasks), after §2 corrections:

| arm.metric | kept init-correct | **lost** | gained | total |
|---|---|---|---|---|
| A2.final | 106 | 6 | 35 | 141 |
| A2.mode | 107 | 5 | 34 | 141 |
| A3.vote | 98 | 14 | 35 | 133 |
| C3.final | 93 | **19** | 47 | 139–140 |
| C3.mode | 101 | 11 | 43 | 144 |

C3 gains the most (47 vs 35) **and loses the most** (19 vs 6). The critic fires on already-correct
answers and the solver abandons them (`hle_036` 1.03→0.424, `hle_052` 9/4→3, `hle_225`, `hle_156`
NCSX A,B,C→B,C …). This is the EIR term of `final = init + ECR − EIR`, measured, not a scoring artifact.

Paired McNemar (exact), after corrections: C3.final vs A2.final 26/27 (p≈1.0); C3.mode vs A2.mode
21/18 (p=0.75); C3.final vs A3.vote 28/21 (p=0.39); **C3.mode vs A3.vote 33/22 (p=0.18)**. Nothing
reaches significance; `mode` is C3's best lock and the only one ahead of both controls.

## 4. Two systemic issues outside the §2 rows

1. **In-loop `is_correct` is T1-only and has letter-extraction FPs** (`hle_182` rounds 2/4/8 flagged
   correct on CoT fragments) and T1 FNs on every format-equivalent answer (`hle_036`, `hle_052`, …
   flagged wrong at every round). Any EIR/ECR/`P_act` table computed from the trajectory flag is
   wrong. Recompute per-round correctness with the T3 rule (T1 ∪ astra, truncated = wrong) first.
2. **The audit is one-directional.** 932 `true_neg` rows were accepted on a single K=1 astra call.
   `hle_040` C3.final (`1.08316803058`) is numerically equal to the symbolic gold and was left wrong.
   Recommend: K=3 majority on the 69 revised rows (cheap), plus a 50-row spot check of `true_neg`
   `int`/`symbol` rows where the committed answer is a decimal.

## 4b. FP candidates (137) — all read

- `letter` 57 rows / `norm` 30 rows (K=3 judged): **1 true FP** (`hle_182` C3.final/C3.mode, T0/F3) —
  confirmed. `hle_068` (`2^{15/16}` == gold verbatim) got T2/F1: one noise vote, keep correct.
  `hle_111` text is hedged ("Let's maybe provide just B…") but commits B = gold — keep.
  Every other row: extracted letter / normalized string equals gold.
- `low` 50 rows: all strict equal to gold (incl. `\boxed{}` wrappers). Auto-pass is justified.

## 4c. Equivalences verified beyond inspection

`hle_162`: numerically checked (mpmath, g = 1, 2, 5) — gold `1−(2g/πk)[F(k)−E(k)]` and the committed
integral agree to 1e-10. Genuine rescue. `hle_194` / `hle_388` (chemical names) judged plausible on
structure, not formally verified.

## 5. Sign-off checklist delta vs AUDIT_REPORT §10

- [x] 7 `none` rows — **corrected**: `hle_121` (init ×4, A3.vote) are valid MILP encodings → correct; the other 5 stay wrong.
- [x] FP `hle_182` C3 — confirmed.
- [x] False rescues `hle_129`, `hle_336` — confirmed.
- [x] `hle_235` cluster — verdict unchanged.
- [x] Missed-rescue — **all 67 read**; 3 reverted (§2), 1 borderline kept.
- [x] FP candidates — **all 137 read**; 1 true FP, no further FP.
- [ ] Adopt the truncated-round rule and regenerate `t3_final_scores.json`.
- [ ] Recompute per-round correctness before any EIR/ECR table.

## 6. K=3 dispute adjudication (2026-11-02, afternoon)

22 disputed rows (`t3/k3_dispute_list.md`: 12 demote / 1 restore / 9 unstable) read individually against gold and
full question; verdicts applied per answer variant across all arms/rounds by
`scripts/t3_k3_adjudicate_and_recompute.py` → 25 overrides. Headline: the K=3 judge was coin-flipping on
identical formulas (`hle_280` 0/3 vs 2/3 on the same `max(√BL, L/log(2+L/B))`), got `hle_129` backwards on
both rows (derivation in `HLE_SCORER.md` §1.2), and would have kept two scansion fragments (`hle_170`) as
correct. Final numbers, paired tests, lost/gained and transition metrics: `HLE_SCORER.md` §1.2. Four tasks are
flagged for the user to overrule (`hle_021`, `hle_030`, `hle_153`, `hle_280`); the sensitivity of every
metric to each is listed there.
