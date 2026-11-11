# C-Arm Opportunity Analysis — Stage A/B Optimization Paths

| | |
|---|---|
| Date | 2026-10-19 |
| Model / arm | `deepseek-v4-flash` C-arm (weak-critic directional feedback) |
| Scope | 542 unique tasks across 8 families |
| Settle definition | commit-based trailing 3-streak (`EARLY_STOP_N=3`, `transition_extract.py`) |
| Correctness | committed answer == canonical gold (`_family_key` + `_math500_key` identity) |

## 1. Headline — the opportunity is pruning, not model behaviour

Re-deriving commit/settle over the current C-arm data yields a **343 / 17 / 182** split
(settle-correct / settle-wrong / non-settle). The largest single lever is the answer-
pruning layer (`_family_key`), which currently **mis-classifies 82 tasks as non-settle**
even though the model's raw answer was correct and stable. Fixing the pruning collapses
those false non-settle into settle-correct, and it costs nothing at inference time.

| Metric | Baseline | S1 pruning repair | S2 frequency lock |
|---|---|---|---|
| settle-correct | 343 | **419** | 419 |
| settle-wrong | 17 | 23 | 23 |
| non-settle (abstain) | 182 | 100 | 100 |
| settle coverage | 360 / 542 (66%) | **442 / 542 (82%)** | 442 |
| settle accuracy | 95.3% | 94.8% | — |
| extra locked-correct (S2) | — | — | **+12** |

## 2. Settle-wrong list (17 tasks — Stage A accuracy leaks)

These tasks early-stopped onto a **wrong** committed answer. Only 2 are recoverable
by a round-0 anchor fallback; the rest settled wrong and the correct answer was never
strongly committed (see §5, Strategy 3).

| task_id | family | gold | settled(wrong) | rounds | no-commit | committed path |
|---|---|---|---|---|---|---|
| bbh_0003 | bbh | K | H | 4 | 0 | `D → H → H → H` |
| bbh_0018 | bbh | A | D | 3 | 0 | `D → D → D` |
| bbh_0020 | bbh | F | D | 4 | 0 | `D → D → D → D` |
| gpqa_018 | gpqa | C | D | 3 | 0 | `D → D → D` |
| gpqa_031 | gpqa | D | C | 6 | 0 | `D → C → D → C → C → C` |
| gpqa_095 | gpqa | B | A | 5 | 1 | `B → ∅ → A → A → A` |
| gpqa_103 | gpqa | B | D | 10 | 2 | `∅ → D → ∅ → D → D → B → A → D → D → D` |
| gpqa_107 | gpqa | A | C | 3 | 0 | `C → C → C` |
| gpqa_109 | gpqa | C | D | 8 | 3 | `∅ → ∅ → C → C → ∅ → D → D → D` |
| gpqa_130 | gpqa | A | B | 3 | 0 | `B → B → B` |
| gpqa_131 | gpqa | B | A | 4 | 0 | `C → A → A → A` |
| gpqa_161 | gpqa | B | D | 3 | 0 | `D → D → D` |
| gpqa_163 | gpqa | B | A | 9 | 2 | `A → ∅ → D → D → B → ∅ → A → A → A` |
| gpqa_168 | gpqa | D | A | 5 | 0 | `B → B → A → A → A` |
| gpqa_187 | gpqa | B | D | 3 | 0 | `D → D → D` |
| mmlu_pro_012 | mmlu_pro | G | C | 3 | 0 | `C → C → C` |
| mmlu_pro_014 | mmlu_pro | D | B | 6 | 0 | `B → B → H → B → B → B` |

**settle-wrong by family:** {'mmlu_pro': 2, 'gpqa': 12, 'bbh': 3}

## 3. Non-settle list (182 tasks — Stage A abstentions)

Grouped by family. `headroom` = correct answer was committed at least once (lockable);
`raw-correct` = raw answer scored correct at least once but was never pruned into a
discrete candidate (pure pruning gap).

| family | count | classification |
|---|---|---|
| math | 33 | 33 — all 33 `raw-correct` (natlang answers like "3 bolts" → `_math500_key` returns None) = S1 fixes |
| math500 | 20 | 20 — mixed numeric/LaTeX lock attempts |
| mmlu_pro | 1 | 1 |
| finance | 50 | 50 — non-voteable, long prose, weak-critic loop never converges |
| bfcl | 50 | 50 — non-voteable, JSON tool-call; `_family_key` lacks a bfcl branch = S1 fixes 45 |
| aime | 4 | 4 |
| gpqa | 24 | 24 |

**Voteable headroom (gold committed, lockable): 11** — `aime_018, aime_021, aime_035, aime_044, gpqa_009, gpqa_028, gpqa_048, gpqa_049, gpqa_167, math500_022, math500_027`

Non-voteable (finance 50 + bfcl 50) cannot settle by discrete commit; bfcl is fixed by
S1 (the missing `_bfcl_commit_key` branch), while finance remains a Stage-B-direct target.

### Non-settle task_ids by family

- **math** (33): gsm8k_002, gsm8k_003, gsm8k_005, gsm8k_007, gsm8k_009, gsm8k_011, gsm8k_013, gsm8k_014, gsm8k_015, gsm8k_017, gsm8k_018, gsm8k_019, gsm8k_020, gsm8k_021, gsm8k_022, gsm8k_023, gsm8k_024, gsm8k_026, gsm8k_029, gsm8k_031, gsm8k_032, gsm8k_033, gsm8k_034, gsm8k_035, gsm8k_036, gsm8k_038, gsm8k_039, gsm8k_040, gsm8k_041, gsm8k_043, gsm8k_044, gsm8k_046, gsm8k_049
- **math500** (20): math500_001, math500_002, math500_005, math500_010, math500_012, math500_014, math500_016, math500_018, math500_019, math500_021, math500_022, math500_024, math500_026, math500_027, math500_029, math500_030, math500_037, math500_041, math500_044, math500_045
- **mmlu_pro** (1): mmlu_pro_044
- **aime** (4): aime_018, aime_021, aime_035, aime_044
- **gpqa** (24): gpqa_009, gpqa_013, gpqa_028, gpqa_033, gpqa_048, gpqa_049, gpqa_065, gpqa_070, gpqa_072, gpqa_077, gpqa_082, gpqa_089, gpqa_090, gpqa_091, gpqa_094, gpqa_116, gpqa_121, gpqa_122, gpqa_127, gpqa_128, gpqa_146, gpqa_148, gpqa_167, gpqa_186
- **finance** (50): fab_001, fab_002, fab_003, fab_004, fab_005, fab_006, fab_007, fab_008, fab_009, fab_010, fab_011, fab_012, fab_013, fab_014, fab_015, fab_016, fab_017, fab_018, fab_019, fab_020, fab_021, fab_022, fab_023, fab_024, fab_025, fab_026, fab_027, fab_028, fab_029, fab_030, fab_031, fab_032, fab_033, fab_034, fab_035, fab_036, fab_037, fab_038, fab_039, fab_040, fab_041, fab_042, fab_043, fab_044, fab_045, fab_046, fab_047, fab_048, fab_049, fab_050
- **bfcl** (50): bfcl_001, bfcl_002, bfcl_003, bfcl_004, bfcl_005, bfcl_006, bfcl_007, bfcl_008, bfcl_009, bfcl_010, bfcl_011, bfcl_012, bfcl_013, bfcl_014, bfcl_015, bfcl_016, bfcl_017, bfcl_018, bfcl_019, bfcl_020, bfcl_021, bfcl_022, bfcl_023, bfcl_024, bfcl_025, bfcl_026, bfcl_027, bfcl_028, bfcl_029, bfcl_030, bfcl_031, bfcl_032, bfcl_033, bfcl_034, bfcl_035, bfcl_036, bfcl_037, bfcl_038, bfcl_039, bfcl_040, bfcl_041, bfcl_042, bfcl_043, bfcl_044, bfcl_045, bfcl_046, bfcl_047, bfcl_048, bfcl_049, bfcl_050

## 4. Transition / pruning / path extraction

The commit identity is `_family_key` (transition_extract) ↔ `_early_stop_key` (runtime),
which prunes a raw `final_answer` into a discrete committed candidate with a `source` tag
(`content` = explicit commit, `cot` = recovered from the hidden CoT tail). Three pruning
gaps drive the false non-settle:

1. **math (GSM8K) — natural-language numeric.** Gold `3`, committed `None`, raw `"3 bolts"`
   every round. `_math500_key("3 bolts")` → `None` because `sympify` treats `bolts` as a
   free symbol, so the loop never sees a number and never settles 32/33 correct answers.
2. **bfcl — missing branch.** `_family_key` has no bfcl case (runtime `_early_stop_key`
   reaches `_bfcl_commit_key` but the transition extractor falls through to `None`), so
   50/50 structured JSON calls read as no-commit.
3. **finance — raw-string jitter.** Long qualitative prose re-states the same answer with
   different wording each round, so neither a numeric nor a robust textual key exists;
   this family is a genuine non-settle target (→ Stage B direct), not a pruning bug.

Sample transition paths (committed chain, `∅` = no-commit round):

```
math   gsm8k_002  raw="3 bolts"×3   commit chain: ∅ → ∅ → ∅   (pruning gap → S1)
bfcl   bfcl_001   raw={"name":"calculate_triangle_area",...}×3  commit chain: ∅ → ∅ → ∅   (missing branch → S1)
gpqa   (settle-wrong)  commit chain e.g. B → C → C → C   (feedback oscillation then settle wrong = misled)
```

## 5. Three optimization strategies (offline-projected)

### Strategy 1 (Stage A) — answer-pruning repair
Add a natural-language numeric fallback for `math` (`"3 bolts"→3`, `"$70,000"→70000`) and
a `bfcl` branch (reuse `_bfcl_commit_key`) to `_family_key`. **+76 locked-correct, settle
coverage 360→442 (+22pts), zero inference cost.** This is the highest-value change and is
a pure code fix (no re-run of the loop).

### Strategy 2 (Stage A) — non-settle frequency lock
For the residual non-settle tasks that still produced discrete candidates, lock the
frequency-majority committed candidate (gold-free) instead of abstaining. **+12 correct**
over the 100 residual (12 correct / 4 wrong / 84 still no candidate).

### Strategy 3 (Stage B) — activation-aware abstain + round-0 anchor
- **Meta (Stage B):** with corrected candidates (§S1), the activation signal
  (`activated` = gold-in-candidates vs `never`) is trustworthy. Stage-B should abstain
  (`UNSURE`) on the **never** slab (62 voteable + finance) and lock the **activated** slab
  (11). This is the metacognition gain A3 sampling cannot replicate.
- **Anti-misled (Stage A):** round-0 anchor recovers only **2/17** settle-wrong; the mode
  fallback recovers 0. Tightening the streak to ≥4 collapses settle almost entirely (the
  data early-stops at 3), so a stronger streak is not viable. The settle-wrong residual is
  the honest ceiling of the weak-critic loop, not a tuning target.

## 6. Next steps

The Stage-A wins (Strategy 1 + 2) are deterministic and need no LLM calls. The only
API-dependent step is the Stage-B evaluator re-run over the corrected non-settle slice
(Strategy 3) to lock the 11 activated tasks and scan `_T_KEEP`/`_T_ANSWER` for maximum
metacognition. Awaiting alignment before spending API budget.
