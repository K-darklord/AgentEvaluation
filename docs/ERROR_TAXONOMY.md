# Error Taxonomy & Capability-Matrix Mapping

**Version**: 1.1 (2026-10-08)
**Status**: authoritative (academic deliverable)
**Scope**: the operational error taxonomy used by the meta-cognitive proxy (critique module) and the shared cross-domain axis of the capability-matrix tensor. Candidate for paper appendix / §3.2–§5.4 supporting content.

---

## 1. Purpose and three-layer separation

The error taxonomy serves two distinct roles that must not be conflated:

| Layer | Granularity | Role | Fed back to the agent? |
|---|---|---|---|
| **leaf** | 20 fine-grained, domain-local error types | directional feedback signal (Top-N distribution, gold-free) | **yes** |
| **middle axis** | 6 shared cross-domain failure modes | tensor `E`-axis for PARAFAC / Tucker / PCA decomposition | no |
| **L1–L4** | latent capability axes (Base / Augmentation / Meta-cognitive / Correction) | post-hoc *naming* of the factorized axes; NOT a priori mapped | no |

- The **leaf** is the only signal returned to the model during self-correction loops. It is *directional* (an instance-similarity vote says "your error looks like X with probability p").
- The **middle axis** exists solely so the error-type dimension is shared across task families (breaking the block-diagonal structure that otherwise prevents factorization).
- **L1–L4** are hypotheses named after the fact, never preset (see §3.6.1 of RESEARCH_PLAN).

---

## 2. Master table (leaf → literature anchor → evaluation rule → middle axis)

All rules are deterministic (no LLM, no randomness) and operate on stored signals only: `final_answer` vs `gold_answer`, the tool trajectory, and the stored judge verdicts (tier-1 numeric / tier-2 semantic). The "literature anchor" follows the academic ontology in `build_error_taxonomy.py` (ONTOLOGY).

| leaf | literature anchor (group / source) | evaluation rule (deterministic) | middle axis |
|---|---|---|---|
| `sign_flip` | arithmetic_error / GSM-Ranges · NTT calculation | ratio `pred/gold ≤ −0.9` | computation |
| `magnitude_error` | arithmetic_error / GSM-Ranges · NTT calculation | `|ratio| < 0.1` or `|ratio| > 10` | computation |
| `factor_error` | arithmetic_error / GSM-Ranges · NTT calculation | ratio ≈ simple factor `k ∈ {2,3,4,5,6,½,…,5⁄2,2⁄5}` within 5% | computation |
| `near_miss` | arithmetic_error / GSM-Ranges · NTT calculation | `|ratio−1| ≤ 0.10` | computation |
| `numeric_error` | reasoning_error / PRISM Reasoning Error | finance: stored coarse label `numeric_error` (numeric wrong, partial credit) | computation |
| `wrong_symbolic` | symbolic_error / NTT symbolic manipulation | math/math500/aime/bbh(int): gold is symbolic/text, or no clean ratio comparison | reasoning |
| `wrong_option` | wrong_option / PRISM Reasoning Error | mmlu_pro/gpqa/bbh(letter): committed single letter but ≠ gold letter | reasoning |
| `wrong_word` | wrong_option / PRISM Reasoning Error · BIG-Bench closed-set inference | bbh(word): committed closed-set word (yes/no/true/false) ≠ gold word | reasoning |
| `complete_failure` | reasoning_error / n/a (reasoning not finalized — truncated / non-convergent) | finance: `T1==0 AND T2==0` with stored `complete_failure` | reasoning |
| `retrieval_failure` | knowledge_missing / PRISM Knowledge Missing | finance: zero tool calls | knowledge |
| `contradiction` | knowledge_error / PRISM Knowledge Error · fine-grained hallucination | finance: dealbreaker triggered or stored `factual_contradiction` | knowledge |
| `empty_or_unparseable` | invalid_output / n/a (not a reasoning class) | math/math500/aime: prediction has no extractable number; bbh(word): no valid committed word | instruction |
| `non_letter_output` | instruction_following_error / PRISM | mmlu_pro/gpqa/bbh(letter): no committed option letter in prediction | instruction |
| `multiple_letters` | instruction_following_error / PRISM | mmlu_pro: >1 distinct A–J token | instruction |
| `empty_pred` | invalid_output / n/a (not a reasoning class) | finance/bfcl: empty final answer | instruction |
| `json_parse_error` | malformed_output / BFCL | bfcl: prediction is not valid JSON | instruction |
| `tool_error` | tool_error / BFCL-adjacent (tool-use) | finance: a tool output contains `tool_error` | tool |
| `wrong_function_name` | wrong_function / BFCL task-level | bfcl: parsed JSON function name not in ground truth | tool |
| `wrong_argument` | wrong_argument / BFCL component-level | bfcl: name matches but a parameter value is not in the accepted set | tool |
| `coverage_incomplete` | reasoning_error / PRISM Reasoning Error | finance: stored `qualitative_incomplete` (answer complete but partial rubric coverage) | completeness |

Count: 20 leaves over 8 families (math / math500 / mmlu_pro / finance / bfcl / aime / gpqa / bbh).

The three new discrimination-set families **reuse** the existing leaf space rather than add domain-specific types (except `wrong_word`, added for BBH's closed-set word targets):

| new family | target form | leaf space reused |
|---|---|---|
| `aime` | integer (0–999) | math500 numeric/symbolic leaves (6) |
| `gpqa` | 4-option letter (A–D) | mmlu_pro letter leaves (3) |
| `bbh` | letter / integer / closed-set word | math500 (6) + mmlu_pro (3) + `wrong_word` (1) |

`aime` maps to `label_math500` (numeric-ratio typing); `gpqa` to `label_gpqa` (4-option letter, "commit, don't scan"); `bbh` to `label_bbh` (three-way dispatch by gold form). See `build_error_taxonomy.py` `FAMILY_LABELER`.

---

## 3. Middle-axis definition (6 cross-domain failure modes)

The 6 shared axes above are the observable failure modes, not an a priori L1–L4 mapping:

| middle axis | leaf members | shared across families |
|---|---|---|
| **computation** | sign_flip, magnitude_error, factor_error, near_miss, numeric_error | math, math500, finance, aime, bbh |
| **reasoning** | wrong_symbolic, wrong_option, wrong_word, complete_failure | math, math500, mmlu_pro, finance, aime, gpqa, bbh |
| **knowledge** | retrieval_failure, contradiction | finance |
| **instruction** | empty_or_unparseable, non_letter_output, multiple_letters, json_parse_error, empty_pred | math, math500, mmlu_pro, finance, bfcl, aime, gpqa, bbh |
| **tool** | tool_error, wrong_function_name, wrong_argument | finance, bfcl |
| **completeness** | coverage_incomplete | finance |

Block-diagonality is broken where a single axis spans ≥2 families; `knowledge` and `completeness` remain single-family (finance only) and are expected to under-anchor the factorization until Phase 2 adds ≥2 tool families with error signal (see §5.4 of RESEARCH_PLAN).

---

## 4. `complete_failure` re-characterization (trajectory evidence)

`complete_failure` was originally grouped as `no_reasoning` ("no valid reasoning produced"). Trajectory inspection (wrong instances, all three models) shows this is inaccurate: the model **does** reason (11–17 tool calls; data is retrieved), but the final answer **does not converge** to a committed conclusion.

| instance | final answer | observed failure |
|---|---|---|
| deepseek-`fab_002` | `"Actually wait — … Let"` | reasoning truncated mid-sentence |
| glm-`fab_010` | `"Revenue"` | single header token, stopped |
| qwen-`fab_002` | `*Source: Netflix 10-K …*` (citation only) | source emitted, answer value never produced |
| deepseek-`fab_008` | stream-of-consciousness "Let me check … Or maybe April?" | answer never locked (also hit one HTTP 500) |

**Conclusion**: `complete_failure` = *reasoning not finalized* (truncated / non-convergent), therefore mapped to the **reasoning** middle axis, distinct from `coverage_incomplete` (answer complete but covers only part of the rubric). The legacy name is retained operationally; a semantic rename (`unconverged_answer` / `truncated_answer`) is tracked as an open decision.

---

## 5. Step-level classes (not detectable from stored signals)

The following published classes require per-reasoning-step annotation and are stored as `NOT_DETECTABLE` in the taxonomy metadata, deferred to Phase-2 data collection:

- GSM-Ranges: logical error, number-copy error
- NTT (21-class): full step-level reasoning-process classes
- PE / CE / IE: procedural / conceptual / impasse step classification
- fine-grained hallucination: fabrication, factual inconsistency, context inconsistency, logical inconsistency

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-29 | Initial master table (leaf → literature anchor → evaluation rule → middle axis). Re-classified `complete_failure` from `no_reasoning` to `reasoning` (non-convergence) with trajectory evidence. |
| 1.1 | 2026-10-08 | Added `wrong_word` leaf (BBH closed-set word targets); extended the taxonomy from 19→20 leaves over 5→8 families (aime / gpqa / bbh). New families reuse the existing leaf space — aime→math500 numeric, gpqa→mmlu_pro letter, bbh→three-way dispatch — per `build_error_taxonomy.py` `FAMILY_LABELER`. |
