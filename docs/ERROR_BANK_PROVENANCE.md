# Error-bank provenance (deepseek-v4-flash) — what the paper must disclose

**Purpose**: the bank-source benchmarks are *not* evidence in the paper (the claim is tested on HLE-400);
they are disclosed only as the origin of the error bank. Nothing here needs re-running. This file is
the single source for the paper's Tab 2 ("bank provenance vs evaluation target"), Appendix A, and the
released artefacts. All counts verified against the files on 2026-11-03.

## 1. Pipeline and files

| stage | what | file | n (deepseek) |
|---|---|---|---|
| source runs | single-shot baseline runs whose wrong answers were collected | `experiments/d1_baseline_20260928_201128/` (math500, bfcl, finance), `experiments/mmlu_pro_int16_full/` (mmlu_pro), `experiments/new_set_20261008_full/` (aime, gpqa, bbh) — see `src/build_error_taxonomy.py` header | — |
| wrong bank | annotated wrong instances, all three models, incl. finance | `experiments/error_taxonomy_v2/wrong_bank.jsonl` | 209 rows total; deepseek non-finance **33** |
| L1 | one instance-level answer-free `mechanism` + `check_procedure` + `trigger` per wrong instance | `experiments/l0_distill_v1/relabeled_{family}.jsonl` (`src/build_behavior_leaves.py`) | 33 |
| L2 | per-benchmark classes by shared wrong verb (merge model `deepseek-v4-flash-0731`) | `experiments/l0_distill_v1/mechanism_levels_deepseek-v4-flash_{family}.json` (`src/build_mechanism_levels.py`) | 24 classes |
| L3 bank | frozen cross-benchmark bank consumed by the critic | `experiments/l0_distill_v1/level3_bank_deepseek-v4-flash.json` (`level3_bank_v2`, 24 entries, 7-archetype vocabulary) | 24 entries |

Frozen **2026-10-21** (file mtime; committed in `63d0991`, 2026-10-27). HLE-400 trajectories were
produced 2026-10-31 → 2026-11-01. The bank predates every HLE run.

## 2. Source instances (Tab 2 rows) — 33 wrong answers, six benchmarks

| benchmark | source run | wrong instances (task ids) | L2 classes |
|---|---|---|---|
| GPQA-Diamond | `new_set_20261008_full` | 9: gpqa_009, 013, 018, 022, 028, 031, 033, 043, 049 | 7 |
| MMLU-Pro | `mmlu_pro_int16_full` | 7: mmlu_pro_003, 004, 012, 017, 040, 044, 046 | 4 |
| MATH-500 | `d1_baseline_20260928_201128` | 5: math500_010, 012, 019, 044, 048 | 5 |
| BFCL | `d1_baseline_20260928_201128` | 5: bfcl_014, 015, 016, 017, 031 | 3 |
| BBH | `new_set_20261008_full` | 4: bbh_0003, 0018, 0019, 0020 | 2 |
| AIME | `new_set_20261008_full` | 3: aime_008, 033, 039 | 3 |
| **HLE** | — | **0 — no HLE item, answer or error enters any bank** | — |

Not in the bank: finance (FAB) rows (29 deepseek) — excluded by design; glm / qwen rows — per-model
banks are never pooled (the glm and qwen banks exist but are unused in this paper).

**Overlap note.** The 9 GPQA bank items all lie in gpqa_001–050; the gpqa_051–198 slice that was later
run as an in-family evaluation shares no item with the bank. This matters only for the in-family
numbers, which the paper no longer reports as results.

## 3. The bank itself (release as Appendix A / supplementary)

24 entries; archetype distribution: procedure_truncation 10, descriptor_conflation 6, constraint_blind 5,
format_nonconformance 2, retrieval_abort 1. Two archetypes of the 7-name vocabulary
(`memory_substitution`, `sign_normalization_slip`) are in the vocabulary but have **no entry** in the
deepseek bank — the paper must say "7-archetype vocabulary, 5 instantiated for this model".

**What the critic actually sees at test time.** The 24 bank entries do **not** all reach the critic:
`StrongCritic._vocab` (`src/strong_critic.py`) deduplicates the bank by `id`
(`seen.setdefault(e.get("id"), e)` — the first entry per id wins), so the C3 critic is prompted with
exactly **5** archetype entries. The five are the five instantiated archetypes, in first-appearance
order:

| id | name (verbatim) | `family` values across its entries |
|---|---|---|
| `constraint_blind` | constraint-blind decimation | gpqa, bbh, math500, mmlu_pro |
| `descriptor_conflation` | descriptor/label conflation | gpqa, aime, bbh, bfcl, mmlu_pro |
| `procedure_truncation` | procedure truncation / omission | gpqa, aime, bfcl, math500, mmlu_pro |
| `retrieval_abort` | retrieval-abort | gpqa |
| `format_nonconformance` | format / precision non-conformance | bfcl, mmlu_pro |

The `definition` text of the surviving entry for a multi-family id is that of the first occurrence in
the bank file (e.g. the `constraint_blind` entry the critic sees is its GPQA instance, not the
MMLU-Pro one). State this in Appendix A when releasing the bank.

Each entry = `id`, `name`, `definition` (past-participle wrong-execution clause), `trigger`
(question-type + committed-answer signature), `check_procedure` (gold-free), `examples` (one
de-identified sentence), `family`.

**Answer-freeness check (2026-11-03)**: no entry text contains the gold answer of any of its 33 source
instances (string search over definition / trigger / check / examples, excluding single letters); no
entry contains a task id. L2 entries are benchmark-level and fairly instance-shaped (e.g. "bracket
abundance notation" from a single GPQA astrophysics item); the cross-benchmark generalisation is carried
by the L3 archetype names, not by the entry texts. State this honestly.

## 4. What to write in the paper

- **Tab 2** = the table in §2 (benchmark · source run · n wrong · L2 classes · HLE = 0).
- **§3 / Appendix A**: "The bank was distilled from **33** wrong answers of the solver on six
  non-HLE benchmarks, frozen on 2026-10-21, before any HLE run. It contains 24 answer-free entries
  under a 7-archetype vocabulary (5 instantiated). No HLE item or error entered the bank."
- **Do not report** per-arm accuracies on the bank-source benchmarks as results: those runs predate the
  frozen standard (thinking fix 2026-10-18, truncation rule, scorer v2) and sit at ceiling for most
  benchmarks. If a motivation table is kept, label it "pre-freeze configuration" or drop it.
- **Release**: `level3_bank_deepseek-v4-flash.json`, `relabeled_*.jsonl` (deepseek rows), the three
  `build_*` scripts, and the 33-row deepseek subset of `wrong_bank.jsonl` (prompt + wrong answer + gold).

## 5. Limitation to state

The bank is small (33 instances → 24 entries) and single-model. The critic's activation effect
(C3 191 vs A2 154 reachable, p < 1e-4) is measured with this bank; whether a larger bank, or no bank
at all (generic critic), changes activation is the pending bank-free control.
