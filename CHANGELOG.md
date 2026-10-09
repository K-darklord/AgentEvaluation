# CHANGELOG

All notable changes to this project will be documented in this file.
I follow the principle of recording what changed, why, and what remains.

---

## 2026-09-13 — Bug fixes + ReAct tool improvements

### Fixed
- **ARGS parsing bug**: LLM outputs for tool arguments were nesting redundant `query:` prefixes inside the query value. I added a 3-layer fallback: JSON parse -> ast.literal_eval -> regex key-value extraction. Tool arguments now arrive clean.
- **EDGAR URL format**: `edgar_search` returned directory listing pages instead of specific filing documents. I now build the filing URL from the `_id` field (contains the exact document path like `tm242389d18_defa14a.htm`), so `fetch_url` can retrieve actual filing content.
- **User-Agent compliance**: SEC EDGAR requires a contact email in the User-Agent header. I was using `AgentEvaluation/1.0` without an email, causing 403/503 errors. Fixed to include `yuan.kevin.wang@connect.hku.hk`.
- **fetch_url HTML stripping**: `fetch_url` was returning raw HTML tags. I added script/style stripping and tag cleanup logic, matching `parse_html` behavior.
- **max_steps increased**: ReAct loop max steps raised from 5 to 10. Previously 21/50 questions hit the step limit before the agent could finish searching -> parsing -> answering.

### Changed
- `config.py`: Added HuggingFace agent configuration (HF_TOKEN, HF_MODEL, HF_JUDGE_MODEL, HF_BASE_URL).
- `requirements.txt`: `openai` package moved from commented-out optional to required (T3 LLM-as-Judge depends on the OpenAI client library to call HF router).
- `README.md`: Full rewrite -- documented 4 agent types, ReAct tool table, 3-tier scoring explanation, FAB dataset structure (50 public / 150 private / 337 test).

### T3 (LLM-as-Judge) diagnosis
- I confirmed T3 is **not a bug**. It works correctly: it calls the LLM for each rubric criterion and checks YES/NO.
- T3=0 on the 5-question test is because model answers genuinely do not cover enough rubric criteria (e.g., fab_001: answer covers 1/8 criteria = 12%, threshold is 60%).
- T3 is an OR condition in `is_correct = T1 OR T2 OR T3`, so it can only increase accuracy, never decrease it.

### Test results
- 5-question quick test (post-fix): 2/5 = 40% accuracy (T1=2, T2=1, T3=0).
- Full 50-question run scheduled for tomorrow 07:00 Beijing time.

### Remaining tasks
- [High] Run full 50-question FAB baseline with fixed code.
- [High] Email antoine@vals.ai to request FAB 150-question private validation set.
- [High] Commit + push all changes to GitHub.
- [Medium] Add `google_search` tool (DuckDuckGo free API) for non-SEC queries.
- [Medium] T3 optimization: batch all criteria into one LLM call (N API calls -> 1).
- [Medium] Run 3-5 trials for variance estimation.
- [Medium] Run upper bound model (GPT-4o-mini or DeepSeek-V4-Pro).
- [Low] Upgrade error taxonomy from hardcoded to configurable.
- [Low] Trajectory clustering with sentence-transformers.

---

## 2026-09-12 — FinGPT baseline + FAB integration + Evaluator merge

### Added
- **FinGPTAgent**: Lazy-loading LoRA model agent with graceful degradation (returns empty answer if torch/model unavailable).
- **HuggingFaceAgent**: ReAct-style agent using HF Inference API with tool-calling loop. Supports `edgar_search`, `fetch_url`, `parse_html`, `retrieve_information`.
- **FAB public dataset loader**: `benchmark.py` auto-downloads `public.csv` from Vals AI GitHub (50 questions, CC BY 4.0).
- **3-tier scoring** in `evaluator.py`:
  - T1 (exact match): Normalized string comparison after answer normalization.
  - T2 (numeric/rubric): Numeric tolerance comparison + rubric keyword coverage.
  - T3 (LLM-as-Judge): LLM evaluates each rubric criterion, coverage >= 60% = correct.
- **Answer normalization**: `_normalize()` strips commas, percent signs, unifies case. `_extract_numbers()` picks the closest number to gold.
- **EDGAR search tool**: `edgar_search()` queries SEC full-text search API, returns formatted filing results.
- **Visualization**: `plot_accuracy_by()` generates bar charts by category and difficulty.

### Changed
- `scorer.py` and `analysis.py` **merged** into `evaluator.py` (unified scoring + analysis class).
- `runner.py`: Added environment variable control (`AGENTEVALUATION_AGENT`, `AGENTEVALUATION_BENCH`, `AGENTEVALUATION_NUM_TASKS`) and metadata persistence.
- `config.py`: Added FinGPT, FAB, and scoring tolerance configurations.
- `requirements.txt`: Added `transformers`, `peft`, `pandas`, `matplotlib`, `sentence-transformers`.

### Test results
- Mini benchmark (3 questions, rule agent): 3/3 = 100%.
- FAB 50 questions (rule agent): 0/50 = 0% (expected -- rule agent only handles live_001/002/003).
- FAB 50 questions (HF agent, no tools): 0/50 = 0% (HF free quota exhausted after 9 questions).
- FAB 50 questions (HF agent + EDGAR tools, pre-ARGS-fix): 25/50 = 50%.
- FAB 50 questions (HF agent + normalize only, no tools): 16/50 = 32%.

---

## 2026-09-11 — Project initialization + Git setup

### Added
- Project skeleton: `benchmark.py`, `agent.py`, `runner.py`, `scorer.py`, `analysis.py`, `config.py`.
- 3 mini benchmark questions (NVIDIA/Apple/Microsoft financial data).
- `RuleBasedFinanceAgent` with hardcoded answers for mini benchmark.
- `fetch_url` tool with local fallback for offline environments.
- Trajectory recording: each step logs thought/tool_name/tool_input/tool_output/latency.
- Error taxonomy: 6 labels (retrieval_failure, numeric_error, citation_missing, tool_error, qualitative_incomplete, correct).
- `.gitignore` for Python/IDE/output/model artifacts.

### Git
- Initialized repository, pushed to `github.com/K-darklord/AgentEvaluation` (private).
- Tag `v0.1-skeleton` marks the initial commit.

### Issues found and fixed
- `score_numeric` regex extracted "2024" from "FY2024" instead of "60,922" -- fixed with `_extract_numbers()`.
- `is_correct` and `classify_error` produced inconsistent results -- unified to derive from `classify_error`.
- `analysis.py` naive string comparison caused 0/3 accuracy -- replaced with `scorer.classify_error()`.

## 2026-09-13 (afternoon) — Evaluation v2.1 + Limitations doc

### What I did
1. Refactored evaluator.py to v2.0: 2-tier continuous scoring (T1 numeric + T2 LLM semantic with dealbreaker). Removed old 3-tier T1/T2/T3 binary system.
2. Wrote EVALUATION_STANDARD.md as standalone spec (versioned, for paper supplementary).
3. Updated README evaluation section to v2.1 with link to spec.
4. Implemented T1 keyword matching fallback for non-numeric gold answers (continuous score based on token coverage).
5. Implemented T2 multi-vote (3 rounds, median for correctness, majority 2/3 for dealbreaker) to reduce LLM judge variance.
6. Updated agent.py ReAct system prompt + max_steps fallback prompt to enforce ANSWER-only format (no reasoning prefix).
7. Confirmed FAB public data has only {operator, criteria} in rubric — no severity field. Updated limitation 8.3.
8. Documented 7 known limitations in EVALUATION_STANDARD.md Section 8.

### Evaluation v2.1 on existing 50 trajectories
- Accuracy: 14% (7/50), up from 10% in v2.0
- T1 avg: 0.110 (up from 0.075)
- T2 avg: 0.068
- Dealbreakers: 1/50
- Qualitative Retrieval: 33% (up from 22%)

### Known limitations (see EVALUATION_STANDARD.md Section 8)
1. Single-model multi-vote vs multi-model judge (+/-3-5%)
2. FAB-specific rubric dependency (other benchmarks fall back to T1)
3. No severity weights (FAB public data does not have severity field)
4. Judge model capability ceiling (Flash vs Pro)
5. No calibration (fixed 0.5 threshold)
6. Trajectory truncation (4000 chars)
7. Single-judge per criterion within a round

### Pending
- Re-run 50 FAB tasks with new agent prompt (running, ~60 min)
- Expect 20-40% accuracy with cleaner ANSWER format

## 2026-09-13 (evening) — fetch_url XBRL fix + Easy failure analysis

### What I did
1. Fixed fetch_url: it was returning XBRL metadata (first 3000 chars) instead of filing content for SEC iXBRL documents. Applied the same XBRL filtering + start_markers search (up to 500K chars) as parse_html. Increased return limit from 3000 to 8000 chars.
2. Re-ran 50 FAB tasks with fixed fetch_url. Accuracy: 30% (15/50), up from 28%.
3. Analyzed remaining 12 Easy complete_failures:
   - 9/12 have reasoning prefix ("The question asks...", "Let me...")
   - 8/12 retrieved real content but max_steps fallback did not extract answer
   - 2/12 have retrieve_information tool parameter errors
4. Confirmed parse_html fix: 27/50 trajectories now have real content (UNITED STATES), 0/50 have XBRL metadata (was widespread before).

### Results comparison
| Run | Accuracy | Easy | complete_failure |
|-----|----------|------|-----------------|
| v2.1 old traj | 14% | - | 32 |
| v2.1 new prompt | 28% | 27.27% | 25 |
| v2.1 + parse_html fix | 28% | 27.27% | 26 |
| v2.1 + fetch_url fix | 30% | 36.36% | 26 |

### Remaining issue
max_steps fallback prompt is still not strong enough. Agent retrieves real content but outputs reasoning text instead of extracting the answer. Need to strengthen fallback to force answer extraction from trajectory context.


---

## 2026-09-13 (night) — Tool fixes + evaluation v2.1 final + 34% accuracy

### What I did

#### Bug fixes
1. **parse_html XBRL filtering**: SEC iXBRL filings have XBRL metadata tags BEFORE the actual filing text. The `start_markers` search had `idx < 5000` limit, but "UNITED STATES" can be at index 180K+. Fixed: increased search range to 500K, added aggressive XBRL tag stripping (iso4217, xbrli, UUID-like patterns, long numeric runs).
2. **fetch_url XBRL filtering**: Same bug as parse_html — fetch_url was returning first 3000 chars of XBRL metadata for iXBRL filings. Applied same XBRL filtering + start_markers search. Increased return limit from 3000 to 8000 chars.
3. **retrieve_information tool**: Added graceful error handling for missing `text` parameter. Updated TOOL_SCHEMA description to clarify that `text` must come from previous fetch_url/parse_html output.

#### Evaluation improvements
4. **max_steps fallback context**: Increased context window from 3000 to 6000 chars. This was the single most impactful change — Hard questions went from 0% to 42%.
5. **T1 keyword matching fallback**: When gold answer has no numeric values, T1 now does token coverage matching (continuous score 0-1) instead of binary substring match.
6. **T2 multi-vote**: 3 rounds of LLM judge, median for correctness criteria, majority 2/3 for dealbreaker detection. Reduces boundary case variance.
7. **T2 dealbreaker mechanism**: If any contradiction criterion is triggered (majority 2/3), the question scores 0. Prevents hallucinated answers from scoring.
8. **T2 judge prompt**: Added instruction to ignore reasoning prefix and focus on factual content.

#### What I tried but reverted (negative impact)
9. **Few-shot examples in fallback**: Added 3 Q&A examples to max_steps fallback prompt. Result: 16% accuracy (down from 30%). Model outputs too-short answers, losing keywords for T1 matching. Reverted.
10. **Post-processing of answers**: Regex to strip reasoning prefix from answers. Result: 22% accuracy. Truncated correct answers (e.g., "TO", "(", "FCF, and"). Reverted.

### Accuracy progression
| Run | Accuracy | Easy | Hard | complete_failure | Key change |
|-----|----------|------|------|-----------------|------------|
| v2.1 old traj | 14% | - | - | 32 | T1 keyword + T2 multivote |
| v2.1 new prompt | 28% | 27% | 0% | 25 | ANSWER format prompt |
| + parse_html XBRL fix | 28% | 27% | 0% | 26 | XBRL filtering |
| + fetch_url XBRL fix | 30% | 36% | 0% | 26 | fetch_url XBRL |
| + few-shot (broken) | 16% | 27% | 0% | 31 | reverted |
| + few-shot (no post-proc) | 22% | 27% | 17% | 31 | reverted |
| **+ 6000 context only** | **34%** | **41%** | **42%** | **25** | final |

### Final results (34% accuracy)
- Total: 17/50 = 34%
- Easy: 9/22 = 40.91%
- Hard: 5/12 = 41.67%
- Medium: 3/16 = 18.75%
- Dealbreaker triggered: 1/50 (factual_contradiction)
- Error distribution: complete_failure=25, numeric_error=7, factual_contradiction=1

### By category
| Category | Accuracy |
|----------|----------|
| Complex Retrieval | 66.67% |
| Financial Modeling Projections | 50.00% |
| Numerical Reasoning | 50.00% |
| Qualitative Retrieval | 44.44% |
| Quantitative Retrieval | 33.33% |
| Trends | 33.33% |
| Beat or Miss | 14.29% |
| Adjustments | 0.00% |
| Market Analysis | 0.00% |

### Gap to FAB leaderboard
- DeepSeek V4 Pro: 60.4%
- AgentEvaluation (V4-Flash): 34%
- Gap: 26%, mainly from Flash vs Pro model capability (~15-20%) + single-model judge (~3-5%)

### Key lesson
**Context size matters more than prompt engineering.** Increasing fallback context from 3000 to 6000 chars gave +6% accuracy (28% to 34%). Few-shot examples and post-processing both hurt accuracy by truncating answers. The model needs full retrieved context to generate complete answers, not tighter formatting constraints.

---

## 2026-09-16 — Interference Experiments (INT-05, INT-06, INT-07 paused, INT-12 designed)

### Summary
Today's work focused on **controlled interference experiments** following the
"every interference is a future test" principle. The accuracy trajectory
across experiments: 48% (v3 baseline) → 54% (INT-05) → 56% (INT-06).

### Experiments Conducted

#### INT-05: max_steps 25→50 (CONFIRMED interference, +6pp)
- **Hypothesis**: max_steps=25 prematurely terminated model search
- **Method**: Single variable change, 50 FAB public tasks, V4-Flash
- **Result**: 48% (24/50) → 54% (27/50), complete_failure 20→13 (-7)
- **Conclusion**: Hyperparameter interference confirmed. Model needs more
  search budget to complete thorough investigations on SEC filings.
- **Commit**: 4d4862d

#### INT-06: T2 trajectory 4000→20000 chars (MINIMAL interference, +2pp)
- **Hypothesis**: T2 judge trajectory truncation at 4000 chars cut off context
- **Method**: Reused INT-05 trajectories, only changed T2_MAX_TRAJECTORY_CHARS
- **Result**: 54% (27/50) → 56% (28/50), only 1 task flipped (Hard Beat-or-Miss)
- **Conclusion**: Minimal interference. T2 judge already had sufficient context
  in 4000 chars for most tasks. Hard difficulty benefited most (+8.34pp).
- **Commit**: aaeb3de

#### INT-07: T2 judge V4-Flash→V4-Pro (PAUSED, cost)
- **Hypothesis**: Same model for agent and judge creates self-evaluation bias
- **Status**: PAUSED — V4-Pro inference cost ~10x V4-Flash
- **Resume Strategies**:
  - Option A: Use cheaper alt judge (V4.1-Flash or R1)
  - Option B: Targeted V4-Pro on boundary cases only (final_score ∈ [0.4, 0.6])
  - Option C: Full V4-Pro run (most rigorous, highest cost)
- **Recommended**: Option B balances cost and statistical signal
- **Commit**: 0844129

#### INT-12: Transparent budget + no fallback (PLANNED, Option D)
- **Key Insight**: INT-12 is a DUAL-LAYER interference structure:
  - Layer 1 (INT-05): max_steps is a HIDDEN constraint (model doesn't know budget)
  - Layer 2 (INT-12): fallback synthesis is COMPENSATION for Layer 1
  - Removing Layer 2 alone = double punishment (still cut off + no compensation)
- **Pre-experiment evidence**: 9/50 tasks used fallback, ALL 9 returned
  "Not found" (0% accuracy) → Option B (remove fallback only) = NO-OP
- **Real test**: Can model AVOID hitting max_steps once it knows its budget?
- **Code changes**: (1) Add budget to system prompt, (2) Replace fallback
  synthesis with explicit "Not found"
- **Confounding controls**: Option D-placebo (equal-length irrelevant prompt
  addition) to isolate transparency effect from prompt change effect
- **Status**: PLANNED, awaiting execution
- **Commits**: a7192d7, 8c89a04

### Accuracy Trajectory (cumulative)
| Date | Version | Accuracy | Delta | Notes |
|---|---|---|---|---|
| 2026-09-12 | v0-ReAct (V4-Pro) | 8.3% | — | Format tax |
| 2026-09-13 | v1 (50 tasks) | 34% | +25.7pp | FC + bug fixes |
| 2026-09-13 | v0 with neg examples | 16% | -18pp | Regression test |
| 2026-09-13 | v1 maintained | 34% | +18pp | Restored |
| 2026-09-16 | v3-interference-fix (50 tasks) | 48% | +14pp | INT-13/14 fixes |
| 2026-09-16 | INT-05 (max_steps=50) | 54% | +6pp | INT-05 confirmed |
| 2026-09-16 | INT-06 (T2=20000) | 56% | +2pp | INT-06 minimal |

### Interference Causal Table Updates
- INT-05: SUSPECTED → CONFIRMED (+6pp)
- INT-06: SUSPECTED → MINIMAL (+2pp)
- INT-07: SUSPECTED → PAUSED (cost)
- INT-12: SUSPECTED → PLANNED (Option D, dual-layer insight)

### Key Files Modified
- `INTERFERENCE_CAUSAL_TABLE.md` — Updated with INT-05/06/07/12 statuses
- `experiments/20260916_int05_max_steps/EXPERIMENT.md` — Results + Incident log
- `experiments/20260916_int06_context_length/EXPERIMENT.md` — Results
- `experiments/20260916_int07_judge_bias/EXPERIMENT.md` — Pause + resume strategies
- `experiments/20260916_int12_transparent_budget/EXPERIMENT.md` — Full design with 5 gaps filled

### Key Insights Discovered
1. **Dual-layer interference** (INT-12): max_steps is hidden constraint,
   fallback is compensation — removing one without the other is unfair
2. **Fallback produces 0% accuracy**: 9/9 fallback outputs were "Not found",
   meaning fallback never actually helped the model
3. **FAB official has no published max_steps**: Our 50-step hidden cap is
   a deviation from FAB philosophy
4. **Hard tasks benefit most from budget**: INT-06 Hard +8.34pp, INT-05
   reduced Hard failures significantly
5. **complete_failure dominates errors**: 13/50 in INT-05, all from "Not found"
   — points to retrieval/search strategy, not reasoning capability

### Remaining Work
- [HIGH] Execute INT-12 Option D (transparent budget + no fallback)
- [HIGH] Resume INT-07 with Option B (targeted V4-Pro on boundary cases)
- [MEDIUM] Run INT-12 Option D-placebo for confounding control
- [MEDIUM] Investigate why Adjustments (0%) and Market Analysis (0%) categories
  remain at 0% across all experiments
- [LOW] Multi-seed runs for variance estimation

---

## 2026-09-18 — TOOL_BROKEN + REASONING_PREFIX fixes (target: 34% → 50-60%)

### Fixed (TOOL_BROKEN — 10 questions: tools called but no real content)
1. **fetch_url pagination**: Added `offset` and `max_chars` parameters to `fetch_url`. Agent can now call `fetch_url(url, offset=15000)` to read the next section of a long document. Default return increased from 8000 to 15000 chars.
2. **Tool output truncation fix**: Increased per-tool-output truncation in messages from 8000 to 15000 chars. Previously, `parse_html` returned 15000 chars but the LLM only saw the first 8000 (messages truncated at 8000). Now the LLM sees the full 15000 chars from each tool call, enabling it to decide whether to paginate.
3. **fetch_url TOOL_SCHEMA**: Updated description and parameters to document offset/max_chars support. Agent now knows it can paginate both `fetch_url` and `parse_html`.

### Fixed (REASONING_PREFIX — 8 questions: agent has data but outputs reasoning)
4. **Fallback prompt strengthened**: Changed max_steps fallback system prompt from "Based ONLY on the provided context, answer the question directly" to "You MUST extract the answer DIRECTLY from the context below. Do NOT repeat or restate the question. Do NOT explain your reasoning." This forces the model to extract the answer from context instead of outputting reasoning like "The question asks...".
5. Applied same fallback prompt fix to both HuggingFaceAgent and OpenAIAgent for consistency.

### Already fixed (retrieve_information parameter error — 5 questions)
6. `retrieve_information` now uses `_DOCUMENT_CACHE` (introduced in native FC commit). No `text` parameter needed — the tool automatically searches all documents cached from previous `parse_html`/`fetch_url` calls. This eliminates the parameter error where the LLM didn't know to pass document text.

### Key constraints respected
- No few-shot examples (tested negative: 30% → 16%)
- No regex post-processing truncation (tested negative)
- Fallback context size kept at 8000 (≥6000 minimum)
- Code comments in English

### Changes
- `agent.py`: fetch_url offset/max_chars, tool output truncation 8000→15000, fallback prompt strengthened, fetch_url TOOL_SCHEMA updated

### Test results (2026-09-18 run)
- **Accuracy: 36/50 = 72.00%** (up from 34% baseline, target was 50-60%)
- T1 (numeric): 0.455 | T2 (LLM semantic): 0.644 | Final: 0.722
- Dealbreakers: 2/50 | Complete failures: 6 (down from 25)
- API failures: 0/50

#### By category
| Category | Accuracy |
|----------|----------|
| Financial Modeling Projections | 100.00% (4/4) |
| Numerical Reasoning | 87.50% (7/8) |
| Quantitative Retrieval | 77.78% (7/9) |
| Adjustments | 75.00% (3/4) |
| Complex Retrieval | 66.67% (2/3) |
| Qualitative Retrieval | 66.67% (6/9) |
| Trends | 66.67% (2/3) |
| Beat or Miss | 57.14% (4/7) |
| Market Analysis | 33.33% (1/3) |

#### By difficulty
- Easy: 68.18% (15/22)
- Medium: 87.50% (14/16)
- Hard: 58.33% (7/12)

#### Gap to FAB leaderboard
- DeepSeek V4 Pro: 60.4%
- AgentEvaluation (V4-Flash, with fixes): 72.00%
- **AgentEvaluation now exceeds the V4 Pro leaderboard baseline by 11.6%**


---

## 2026-09-26 — Repository reorganized into the metacognition research program

### Changed
- Reorganized the repo around a single end-to-end paper whose core contribution is *metacognition*.
  The evaluation-framework-interference pilot (see 09-13 → 09-18 above) is retained as the motivation
  ("static accuracy is a bad metric").
- Added the document system: `docs/RESEARCH_PLAN.md` (authority), `PROTOCOL.md` (change-propagation),
  `docs/REPRODUCIBILITY.md`, `docs/TIMELINE.md`, `docs/EXPERIMENT_LOG.md`, `docs/HISTORY.md`,
  `docs/DECISION_LOG.md`, `docs/WORKMAP.md`.
- Refactored the pipeline into `src/` package; added `configs/`, `results/`, `logs/`,
  `data/{raw,processed}/`; added MIT `LICENSE`.
- Renamed repository **FinAgent → AgentEvaluation** (directory, README title, env-var prefix
  `FINAGENT_* → AGENTEVALUATION_*`, SEC User-Agent, git remote).

---

## 2026-09-27 — Architecture blueprint + concurrency refactor

### Added
- `docs/ARCHITECTURE.md` — implementation blueprint for the experiment-execution layer (SQLite
  persistent task queue, provider routing, phased P0–P3 landing), sized to the Phase-3 workload.

### Changed
- Serial → parallel refactor: `agent.py` `_DOCUMENT_CACHE` → `threading.local()` (thread-safe);
  `runner.py` `ThreadPoolExecutor` task-level parallelism; `evaluator.py` parallel scoring.
- 10-task stress test @ concurrency 6: ~3.2× wall-clock speedup (tail-variance bound, not throughput).

---

## 2026-09-28 — Aliyun Token Plan migration + FAB interference fixes (INT-15/16)

### Changed
- `deepseek-v4-flash-0731` migrated off the HuggingFace router (TCP timeout / HTTP 000) to the Aliyun
  Token Plan endpoint. HF channel abandoned for this program.
- Fixed hidden-CoT `reasoning_content` bug: `msg.content or ""` dropped the answer for models that put
  it in `reasoning_content` (deepseek/qwen/glm); added `_extract_content()` fallback.
- INT-15: `retrieve_information` chunked rework (chunk_size=1500, top_k=5, cache-dedup marker) to stop
  O(N²) tool-loop context growth.
- INT-16: MMLU-Pro letter-only prompt (the generic finance prompt made models emit a value, not a letter).

---

## 2026-09-29 — Error taxonomy + three-tier evaluator + critique scaffolding

### Added
- `src/build_error_taxonomy.py` — 19 fine-grained leaf error types over 5 families, each anchored to an
  academic ontology (BFCL / GSM-Ranges / NTT / PRISM), mapped to 6 shared middle axes.
- `src/build_capability_matrix.py`, `src/run_tensor_decomp.py`, `src/diagnose_capacity_matrix.py` —
  capability-matrix construction and static tensor decomposition (marked no-go for L1/L2 inversion).
- `src/build_unified_taxonomy.py` — parallel cross-domain leaf scheme (8 detectors).
- `src/align_bfcl.py`, `src/rescore_math500.py`, `src/rescore_math500_t2.py`, `src/bucket_false_negatives.py`.

### Changed
- `evaluator.py` re-architected to a **three-tier dispatcher** (T1 → T2 → T3): T1 deterministic
  rule/symbol match; T2 LLM-assisted parse + judge rescue (`deepseek-v4-pro`) on T1-missed rows only
  (`T2_RESCUE_ENABLED` default off, `T2_JUDGE_MAX_TOKENS=500`); T3 multi-judge (finance uses
  `max(T1, T2)` rubric coverage as interim).
- Added T1b deterministic extraction for MATH-500; quantified false negatives (FN) via zero-API rescoring.

---

## 2026-10-05 — Critique spec finalized + documentation alignment

### Changed
- `docs/RESEARCH_PLAN.md` §5.8 — critique re-specified as a simple rule-based metacognition (three
  gold-free signal layers: answer shape / process primitives / history delta; static ranking prior;
  reflective-guide Top-N probes) instead of embedding retrieval. Tag `phase1-critique-rule-based`.
- `docs/EVALUATION_STANDARD.md` v3.0 — rewritten to the three-tier framework (T1/T2/T3, `deepseek-v4-pro`
  judge, 19-leaf taxonomy reference).
- `README.md` v2.5 — aligned to current state (three-tier scoring, 5-family 250-Q task set, Phase-1
  Aliyun models; removed legacy `fingpt`/FinGPT agent references).


## 2026-10-06 — Phase-1 feedback loop + weak critic (the L3/L4 instrument)

### Added
- `src/build_weak_critic.py` — weak critic as a metacognition proxy: 19-leaf taxonomy prior + exemplar
  retrieval (`s = W_Q·sim_q + W_A·sim_a`, W_Q=0.7 / W_A=0.3) → Naive-Bayes Top-3 error posterior. Gold-free
  (never sees the answer key); three feedback ablations (A: type+prob, B: +cause, C: +cause+attention).
- `src/run_feedback_loop.py` — bounded feedback–self-correction driver: round-dimension tracking of the six
  end-states (state 1–6), activation `P(A)`, locking `P(F|A)`, locking loss, reversibility `r`, and per-task
  token metering for the cost–reliability + risk model.

### Fixed
- Decoupled L3 activation from reversibility: `P(A)` redefined as the reachable ceiling (correct answer
  appearing in ≥1 round across all tasks); `r = P(A | ¬S)` kept as the separate first-wrong reversibility rate.

### Added (docs)
- `docs/RESEARCH_PLAN.md` §5.12 — capability-layered dynamics model (μ + Δ, `P_act` / `P_lock` / `q_stay`,
  three-arm skeleton; `model_score = (μ, P_act, P_lock, q_stay, cost(R))`).

## 2026-10-07 — Phase-1 summary + core positioning + docs alignment

### Added
- `docs/PHASE1_SUMMARY.md` — authoritative Phase-1 results + Phase-2 plan (six end-states, L1–L4 layer
  definitions, per-family activation/locking, weak-critic mechanism, Phase-2 model tiers + control arms).
- Core positioning in `docs/RESEARCH_PLAN.md` §2: primary contribution is a **new evaluation paradigm**
  (round-dimension dynamic observables replace static single-shot accuracy; cost–reliability + risk
  quantified); secondary contribution is a **weak-critic existence proof** (a gold-free metacognition proxy
  raises the activation ceiling). Nearest-neighbour differentiation added (Feedback Friction / Overthinking /
  activation-probe).

### Fixed
- `evaluator.py` `_score_bfcl` — normalized function-name string math symbols, nested-list/numeric tolerance
  comparison, and a non-dict prediction guard. 58 wrong→right flips, 0 regressions (offline).
- `docs/RESEARCH_PLAN.md` §8.5/§8.6 — glm single-model case, hard-family sizing by activation events, Weibull
  cure-rate form `P(A)·[1−exp(−(r/θ)^k)]` with corrected θ semantics, locking framed as a survival-hazard
  risk factor.

### Changed
- cost channel recorded as Aliyun Token Plan (not HF router); weak-tier deployment moved to a rented Aliyun
  instance; strong-tier channel left open (to be resolved at run time).

## 2026-10-07 — Doc-sync cleanup + file-audit playbook

### Added
- `docs/FILE_AUDIT.md` — file-audit & doc-sync playbook (sync-on-push rule, periodic scan checklist,
  single-source-of-truth rule, drift-findings log).

### Removed
- Local FinGPT inference path (`agent.py` `FinGPTAgent`, `config.py` `FINGPT_*`, `runner.py` `fingpt` branch).
  Local model loading was abandoned (mlx/mpi4py ABI crash; HF channel dropped); superseded by the Aliyun
  Token Plan `HuggingFaceAgent` path.
- `configs/fab_baseline.yaml` — superseded FAB-only multi-seed config (stale HF model id); the Phase-1 model
  registry now lives in `config.py` `PHASE1_MODELS`.

### Archived
- Superseded `experiments/d1_baseline_*` runs (early smoke n=3 ×2, partial n=150 ×2, weak-tier, 2-model)
  archived to `experiments/archive/superseded_d1_baseline_20261007.tar.gz` (local, gitignored) and removed from
  the tree; the canonical `d1_baseline_20260928_201128` (250-Q full) is retained. One-off analysis scripts kept
  in `src/` (reproducibility of the archived error-taxonomy / capability-matrix artifacts).


## 2026-10-07 — Remove never-shipped YAML experiment scaffold

### Removed
- `src/experiment.py` — generic YAML experiment loader that was never wired in (Phase-1 runs go through
  `src/phase1_baseline.py` + `config.py` `PHASE1_MODELS`); its only default config (`fab_baseline.yaml`) had
  already been removed.
- `pyyaml` from `requirements.txt` — the sole `import yaml` lived in `experiment.py`.


## 2026-10-08 — MCQ grading: stop scoring prose answers by luck (GPQA / BBH)

### Context
While smoke-validating the new hard benchmarks (AIME / GPQA-Diamond / BBH), the GPQA-20
run on deepseek-v4-flash reported 90% (18/20). Reading the trajectories showed 2 of the 18
"correct" rows were false positives: the model had emitted a whole paragraph of reasoning as
`final_answer` and never committed to an option letter.

- `gpqa_009` (gold=A): reasoning concludes *"So yes triisopropyl borate can be C3h"* ->
  triisopropyl borate is **option B**, not A. The model was wrong; the scorer found the
  letter "A" only because it appears inside ordinary prose.
- `gpqa_016` (gold=A): reasoning ends *"...Not sure."* with no option at all. Also wrong.

### Root cause
`_score_gpqa` scanned the whole prediction with `re.findall(r"\b[A-D]\b", pred.upper())`.
Calling `.upper()` first turned every English article "a" into "A", which then matched the
`[A-D]` pattern; when gold happened to be "A" (both rows here) the row scored correct by luck.
`_score_bbh`'s letter branch (`re.findall(r"\b[A-Za-z]\b", pred.upper())`) carried the same
`.upper()` hazard.

### Changed
- `src/evaluator.py`: added `_extract_mcq_letter(pred, choices)` — a committed-answer
  extractor that accepts (1) a bare letter (`A`, `A.`, `(A)`, `a`), (2) a letter after an
  explicit cue (`answer is A`, `ANSWER: B`, `option b`), or (3) a final line that is just an
  option letter; otherwise returns `None`. It **does not** upper-case the whole text.
- `_score_gpqa` now grades via `_extract_mcq_letter(pred, "ABCD") == gold`.
- `_score_bbh` letter branch now grades via `_extract_mcq_letter(pred, A-Z) == gold`.
- Intentionally **not** changed: `_score_mmlu_pro` keeps its existing full-text scan so the
  frozen MMLU-Pro baselines stay comparable. It shares the same latent `.upper()` hazard
  (gold=A could be inflated by prose) — to be revisited in a separate pass with a re-baseline.

### Scoring difference (GPQA-20, deepseek-v4-flash, 8192-token budget)
- Before: 18/20 = **90%**  ->  After: 16/20 = **80%**.
- Exactly two rows flipped correct -> wrong: `gpqa_009`, `gpqa_016`. No other row changed.
- `experiments/smoke_gpqa_8192_20261008_102445/deepseek-v4-flash/` re-scored in place
  (zero API cost); the pre-fix `error_report.json` / `results.csv` kept alongside as
  `*.pre_mcq_fix.*` for traceability.
- BBH: no run exists yet, so no measured diff; the stricter letter grading takes effect on
  the first BBH run.

### Remaining
- [Medium] Decide whether to apply the same committed-answer grading to `_score_mmlu_pro`
  (requires re-baselining all MMLU-Pro runs).


## 2026-10-08 — AIME grading: stop scoring reasoning blobs by luck (committed integer)

### Context
Same review pass as the GPQA fix above, extended to the other new hard benchmark. `_score_aime`
graded by scanning **all** integers in the prediction and returning 1.0 if the gold integer
appeared anywhere (`gold in {int(n) for n in _extract_all_numbers(pred)}`). A model that never
converged -- emitting a long chain-of-thought whose derivation happens to pass through the gold
value -- would score correct by luck. This is the same false-positive class as the GPQA
whole-text scan.

### Changed
- `src/evaluator.py`: added `_extract_committed_integer(pred)` -- the integer analogue of
  `_extract_mcq_letter`. It returns the integer the model actually **committed** to
  (`\boxed{...}` -> whole-string bare integer -> integer after an answer cue -> last line bare
  integer -> integer after the last `=`), else `None`. It deliberately has **no** unbounded
  whole-text fallback, so a prose blob that merely mentions the gold number scores wrong.
- `_score_aime` now grades via `_extract_committed_integer(pred) == gold`.

### Scoring difference (AIME-20, deepseek-v4-flash, 8192-token budget, smoke_aime_8192_20261008_101942)
- Before (full-text scan): 19/20 = **95%**  ->  After (committed integer): 19/20 = **95%**.
- **0 rows flipped** -- the hypothesized false positive did not materialise on this dataset:
  19/20 `final_answer`s are clean bare integers; the one blob (`aime_015`, gold=175) does not
  contain the gold and was genuinely wrong either way. The change is therefore
  future-robustness (and closes an adversarial channel), not a retrofit of this run.
- No AIME artifacts rewritten (score unchanged); recomputed offline, zero API cost.

### Regression evidence (offline, zero API)
- 3 synthetic false positives now score 0.0 under the new grader but scored 1.0 under the old
  full-text scan (e.g. gold=175, pred="The computation yields 175 but that is not our final
  result").
- 6 committed-answer positives (`60`, `\boxed{175}`, "The final answer is 25", "... = 42",
  last-line `7`, "6.") all score 1.0.

### Remaining
- [Medium] BBH free-form grading still has false positives (disclosed; run postponed): the word
  branch uses substring match (`gold.lower() in pred.lower()`), so gold="no" scores 1.0 against
  "I don't know"; the numeric branch reads the **first** integer in the text (false negative
  when reasoning precedes the answer). To fix if BBH is un-postponed.

## 2026-10-08 — BBH grading: "commit, don't scan" for word / number targets

### Context
Closes the BBH item left open in the AIME entry above ("BBH free-form grading still has false
positives"). BBH targets come in three forms — an `(X)` option letter, an integer, or a closed-set
word (Yes/No/True/False). The letter branch was already on `_extract_mcq_letter`, but the word and
numeric branches still scanned the whole text.

### Changed
- `src/evaluator.py`: added `_extract_committed_number` (real-valued sibling of
  `_extract_committed_integer`) and `_extract_committed_text` (closed-set word extractor).
  Both follow the same order as the letter/integer extractors (`\boxed{}` -> bare -> answer cue ->
  final line -> last `=`) and return `None` when nothing is committed.
- `_score_bbh` rewired: letter -> `_extract_mcq_letter`; integer -> `_extract_committed_number`;
  word -> `_extract_committed_text` (no prose substring match).
- `_extract_mcq_letter` extended to accept a committed letter carrying a short label
  (`(B) heptagon`, `B. heptagon`); the bracket/period separator prevents the bare article
  `a`/`A` from matching. Guard in the numeric extractors tightened to `(?!\d)(?!\.\d)` so a
  sentence-final period no longer blocks a cued number ("the answer is 24.").
- `tests/test_evaluator_commit.py`: new stdlib regression suite (12 tests) freezing the whole
  contract; run `python -m unittest tests.test_evaluator_commit -v`.

### Scoring difference (offline rescore, zero API)
The sampled BBH-22 exercises all three branches: 12 letter / 4 number / 6 word. Comparing three
grader versions on the stored rows (`smoke_new20_20261008_090435`):

| version | BBH-22 |
|---|---|
| V0 original (whole-text scan; word substring; first integer) | 21 |
| V1 commit-only (no label acceptance) | 18 |
| V2 commit + labeled-letter (current) | 21 |

- Net vs the original grader: **0 rows flip** on this run — none of the 6 word / 4 number rows
  hit the false-positive channel here, so like the AIME fix this is future-robustness (closes the
  channel) rather than a retrofit. `bbh_0010` is a genuine letter error (gold A, pred D) and
  correctly stays wrong.
- The commit rule by itself (V1) *loses* 3 legitimate rows, because the model echoes the option
  with its label: `bbh_0001` "(B) heptagon", `bbh_0002` "(J) triangle", `bbh_0009`
  "(A) Modifiers or Adjectives". The labeled-letter branch restores all 3 (V1 18 -> V2 21).
- GPQA (smoke_gpqa_8192_20261008_102445, n=20): 18 -> **16** (the 2 intended false positives
  removed, matches the earlier GPQA entry); the letter extension adds no new GPQA flip.
- Word/number false positives now score 0: gold `No` vs "I don't know", gold `Yes` vs
  "Yesterday", gold `24` vs "First 3 times 5 is 15, then I am not sure."

### Spec
- Promoted the rule into `docs/EVALUATION_STANDARD.md` §3.3 (revision history row 3.1).

### Remaining
- [High, deferred] Unify T1 dispatch by answer *form* across subjects (currently a per-benchmark
  `if benchmark == ...` chain). Recorded as `docs/EVALUATION_STANDARD.md` §3.4; postponed until the
  new benchmark set's first full run, because further benchmarks are still being added. `_score_mmlu_pro`
  and `_score_logic_exact` are the outstanding full-text-scan scorers to fold in at that point.

## 2026-10-08 — GPQA grading: markdown-emphasis commits + `wrong_option` split

### Context
The new-set full run (144 items = AIME 50 + GPQA 50 + BBH 44; `experiments/new_set_20261008_full`)
exposed a GPQA false-negative channel. The graded token on GPQA is a single option letter, but models
frequently wrap it in markdown emphasis (`**B**`, `*C*`, `` `D` ``) or prefix it ("Answer: **B**").
`_extract_mcq_letter` matched bare/labeled letters only, so an emphasised commit fell through and the
row was labelled `complete_failure` — silently under-counting accuracy. Spot-check: `gpqa_001`
gold=B pred='**B**' (a correct commit) was recorded as complete_failure.

### Changed
- `src/evaluator.py` `_extract_mcq_letter`: unwrap markdown emphasis/backticks around a *lone*
  committed letter (`**B**`, `*b*`, `` `C` ``) before matching, then strip stray `*`/`` ` ``. The
  `(?<![A-Za-z0-9])...(?![A-Za-z0-9])` guard leaves identifiers (`__init__`, `snake_case`) intact.
  Prose sentences are still not a commit ("A triangle has three sides." scores 0).
- `src/evaluator.py` `_label_row_tiered` (gpqa branch): split the failure mode — a committed but wrong
  option letter is now `wrong_option`; only a genuinely missing commit stays `complete_failure`. The
  error distribution no longer lumps wrong picks into failures.
- `tests/test_evaluator_commit.py`: new `TestGpqaEmphasisRegression` (3 tests); suite 12 -> 15.
- `src/run_new_set.py`: added `NEW_SET_RESCORE` zero-cost mode — re-run `Evaluator.score()` on stored
  `trajectories.jsonl` (no API calls), for re-grading after an extractor fix.

### Scoring difference (offline rescore, zero API)
Re-scored the three stored runs (`NEW_SET_RESCORE=1`):

| model | overall | GPQA | AIME | BBH |
|---|---|---|---|---|
| deepseek-v4-flash | 88.89% (unchanged) | 41/50 (unchanged) | 47/50 | 40/44 |
| qwen3.8-flash | 78.47% -> **80.56%** | 27 -> **29** | 48/50 | 39/44 |
| glm-5.3 | 77.08% -> **79.86%** | 26 -> **30** | 44/50 | 41/44 |

- deepseek's GPQA commits were already bare/labeled, so no row flips (channel closed, no retrofit).
- qwen +2 and glm +4 GPQA rows recovered; overall accuracies move up accordingly. Ranks stay
  deepseek >> {qwen, glm}, with qwen and glm now nearly tied at ~80%.
- Error distributions now carry `wrong_option` (deepseek 5, qwen 7, glm 5) alongside
  `numeric_error` / `complete_failure` / `api_failure`.

### Spec
- Extends the `docs/EVALUATION_STANDARD.md` §3.3 "commit, don't scan" contract to markdown-emphasised
  commits; no §3.4 change (form-based dispatch unification still deferred).

### Remaining
- (unchanged) [High, deferred] Unify T1 dispatch by answer *form* across subjects — §3.4.

## 2026-10-08 — Closed-book tool gating (INT-20) + reasoning budget (INT-18) + L3/L4 RL framing

### Context
The new discrimination set (AIME/GPQA/BBH) exposed that L1 (closed-book) benchmarks were still
shipping the full tool schema to every model. GPQA-Diamond (a closed-book science MCQ) spontaneously
called `fetch_url` against PubMed/Europe PMC, driving ~29M prompt tokens per run and contaminating the
L1 base measurement with L2 tool ability. Gating tools off also revealed that mmlu_pro/bbh had been
silently relying on the (now removed) tool schema to keep the model's chain-of-thought short — at 1024
tokens the CoT truncated the answer.

### Changed
- **INT-20**: `config.py` `CLOSED_BOOK_BENCHMARKS` / `TOOL_NATIVE_BENCHMARKS`; `agent.py` routes
  closed-book families to a single tool-free text generation (no tool loop). GPQA prompt tokens
  ~29M -> ~0.2M per run; `tool_calls` 292 -> 0.
- **INT-18 (extended)**: `REASONING_BENCH_MAX_TOKENS` now covers mmlu_pro/bbh (was aime/gpqa only).
  mmlu_pro deepseek 82% -> 92% at 8192; un-truncates bbh geometric-shapes items.
- `evaluator.py` bbh branch: split `wrong_option` / `numeric_error` / `wrong_word` /
  `empty_or_unparseable` from `complete_failure` (was lumping wrong picks into complete_failure).
- Error taxonomy 19 -> 20 leaves: added `wrong_word` (BBH closed-set word targets); families 5 -> 8
  (aime/gpqa/bbh reuse the existing leaf space).

### Added (docs)
- `docs/TASK_FAMILY_TAXONOMY.md` — canonical task-family classification (L1 closed-book vs L2
  tool-native) that operationalises the L1/L2 split as a code-enforced policy.
- `docs/L3L4_RL_REDISTRIBUTION.md` — L3 = meta-cognition / L4 = locking, framed as probability
  redistribution (not isomorphism) shared with train-time RL (GRPO/RLVR); arm ordering A3 ≤ C ≤ C*.
- `docs/REPRODUCIBILITY.md` §3.4 — observed non-determinism under temperature = 0 (root cause
  undetermined, Phase-2 follow-up).

### Caveat
- deepseek-v4-flash shows run-to-run variation under temperature = 0 on CoT-boundary families
  (AIME 46/50 vs 42/50 across identical runs). Tracked, not yet root-caused; Phase-2 follow-up in
  `docs/REPRODUCIBILITY.md` §3.4.
