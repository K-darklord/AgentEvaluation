# Interference Causal Comparison Table

**Last Updated**: 2026-10-19 (INT-26 registered: deepseek-v4-flash hard-GPQA `thinking_budget=8192` exhaustion drops votes via `finish_reason=length`; a dropped vote that does NOT flip the majority is tolerated, a task whose majority can tie/flip is re-run)
**Prior**: 2026-10-18 (INT-24/INT-25 registered: Stage-B verdict returns UNSURE when every transition is cut (isolated states); twostage reason-call drops the original question + budget 512->1024 so glm no longer fragments its rationale to one char)
**Prior update**: 2026-10-18 (INT-23a/23b registered: _early_stop_key math/math500 numeric identity aligns run-side and transition-side commit views; a None commit resets the early-stop streak)
**Git Tag**: v3-interference-fix-60pct (5-task) → 50-task full run confirmed 48%

---

## 1. Bug vs Interference Classification

| ID | Issue | Classification | Rationale |
|---|---|---|---|
| INT-13-L1 | Schema missing REQUIRED markers | **BUG** | Code was wrong (schema didn't match function). Fixed by adding markers. |
| INT-13-L3 | Cache append in wrong function | **BUG** | Code was wrong (cache code in retrieve_information instead of parse_html). Fixed by moving code. |
| INT-13-L3b | retrieve_information references deleted `text` var | **BUG** | Code was wrong (stale variable reference). Fixed by removing reference. |
| INT-14 | Tool design requires LLM to pass 2000+ chars as JSON param | **INTERFERENCE** | Code is correct (function receives text, processes, returns). But design itself is incompatible with FC paradigm. LLM cannot reproduce large text in JSON. |
| INT-01 | ReAct vs Function Calling format | **INTERFERENCE** | Both implementations correct. But format choice systematically penalizes models less good at format-following. |
| INT-02 | Negative example priming | **INTERFERENCE** | Prompt code correct (does what it says). But including negative examples causes LLM to mimic them. |
| INT-03 | Fallback prompt "ONE LINE ONLY" | **INTERFERENCE** | Code correctly executes truncation. But parameter choice truncates key info. |
| INT-04 | max_tokens=256 | **INTERFERENCE** | Code correct. But parameter too restrictive for some answers. |
| INT-05 | max_steps=15 | **INTERFERENCE** | Code correct. But parameter may be insufficient for thorough models. |
| INT-06 | Context truncation 8000 chars | **INTERFERENCE** | Code correct. But SEC 10-K filings are 50K+ chars. |
| INT-07 | T2 judge = same model as agent | **INTERFERENCE** | Code correct. But mechanism introduces self-evaluation bias. |
| INT-12 | Forced synthesis step | **INTERFERENCE** | Code correct. But mechanism deprives search time. FAB doesn't force. |
| reasoning_content ignored | Final answer dropped for hidden-CoT models | **BUG** | `msg.content or ""` ignored `reasoning_content`; deepseek/qwen/glm put the answer there, so final_answer was empty (~20/22 deepseek logic errors). Fixed 2026-09-28 via `_extract_content()` fallback. **Incomplete**: that fix only covered EMPTY `content`; glm-5.3 (thinking locked on) emits a non-empty FRAGMENT whose answer is folded into the hidden CoT and whose visible `content` is truncated by the 8192 budget ('Looking' / '=N' / 'H'). Completed by INT-21 (2026-10-17). |
| INT-15 | Retrieve: whole-doc re-injection + no cache dedup → chunk + top-k keyword + dedup | **INTERFERENCE** | Old: every tool result (≤15000 chars) re-appended even on cache hit → O(N²) token growth. New: chunk docs, return top-5 chunks; cache-hit replies a short marker. Lossy (changes model-visible info). Frozen: chunk_size=1500, top_k=5, keyword scoring, stable order. |
| INT-16 | MMLU-Pro MCQ reuses generic finance prompt → model emits computed value, not option letter | **INTERFERENCE** | Code correct, but the "respond with ONLY the factual answer" finance prompt is wrong for a 10-option MCQ: reasoning models output a number instead of selecting A-J, so `\b[A-J]\b` finds no letter (69 wrong = 19 wrong-letter + 50 no-letter). Fix: benchmark-specific prompt demanding ONLY the option letter, frozen verbatim in src/agent.py. Lossless (does not change model-visible data, only instruction). |
| INT-17 | New-benchmark answer-format prompts (AIME integer-only; BBH short-answer). GPQA reuses the INT-16 MCQ letter-only prompt | **INTERFERENCE** | Prompt code correct (does what it says). Demanding a bare integer / short token instead of the generic finance narrative changes the model-visible instruction per family, so it must be declared separately from the evaluator (EVALUATION_STANDARD §6). Frozen verbatim in src/agent.py (aime L806-811, bbh L815-820). Lossless w.r.t. data; an intervention w.r.t. instruction. |
| INT-18 | Reasoning-benchmark generation budget 1024 → 8192 (`REASONING_BENCH_MAX_TOKENS`, aime/gpqa/mmlu_pro/bbh) | **INTERFERENCE** | Code correct; parameter too restrictive (same class as INT-04). Reasoning models spend the CoT in `reasoning_content`; at 1024 the CoT alone hits finish_reason=length, `content` returns empty and the row scores wrong even when solved. Frozen in src/config.py:98 (default 8192), applied at src/agent.py:796. Extended to mmlu_pro/bbh on 2026-10-08 (INT-20 removed the tool schema that had been silently shortening the CoT; 8192 restores mmlu_pro 82% → 92% and un-truncates bbh geometric-shapes items). |
| INT-19 | GPQA option shuffle (fixed per-question seed) removes the "correct is always A" position bias | **INTERFERENCE** | Code correct; design choice that reorders model-visible options. Removes a systematic position bias (net fairness-positive) but makes results non-comparable to the raw CSV order, so it must be declared. src/benchmark.py:645-679. |
| INT-20 | Closed-book L1 benchmarks exposed external retrieval tools (fetch_url / edgar_search / parse_html / retrieve_information) | **INTERFERENCE** | Tool schema was exposed unconditionally to every benchmark (`_build_fc_tools()`). GPQA-Diamond (a closed-book science MCQ) spontaneously called `fetch_url` against PubMed/Europe PMC, driving O(N²) token growth (~29M prompt tokens per run) and contaminating the L1 base measurement with L2 tool ability. Fix: `CLOSED_BOOK_BENCHMARKS` gate in src/config.py; closed-book families now take a single tool-free text generation (src/agent.py). |
| INT-21 | Hidden-CoT fragment drops the answer (glm-5.3, thinking locked on: 8192 budget exhausted by hidden CoT, visible `content` truncated to a 2-token fragment while the commit sits at the CoT tail) | **BUG** | `_extract_content()` returns non-empty `content` verbatim, so a truncated fragment ('Looking'/'=N'/'H') is never recovered from the hidden CoT where glm actually committed. Completes the 2026-09-28 `reasoning_content ignored` fix (row 25), which only handled empty `content`. Fixed 2026-10-17 via `resolve_commit()` in src/evaluator.py: commit from visible text first ('content'), else read the concluding CoT tail only ('cot'); pure rule, zero LLM, no full-chain scan. `commit_source` ('content'/'cot') tags the recovery so Stage B can tell an explicit commit from a CoT-recovered one. thinking is left ON for all three models. Follow-up (2026-10-18): the truncated single-letter-fragment branch (finish_reason==length → read the CoT tail ONLY, never commit the fragment) is rule-gated; a later LLM audit will confirm zero false positive / false negative from the CoT-tail recovery. |
| INT-22 | MATH-500 commit key emits a spurious imaginary candidate: a round whose `final_answer` is the single char `'I'` (leaked "I kept..." pronoun) is parsed by sympy as the imaginary unit and canonicalized to `'1.0*I'`, which can never match a real gold and pollutes the Stage-B candidate list (math500_010, 2026-10-18) | **BUG** | `_math500_key` now rejects any non-real sympy result: only `val.is_real` values produce a canonical key (the `return str(val)` tail became `return None`). Same principle as INT-21's commit-identity hardening -- pure rule, zero LLM. Alters candidate/settle identity口径 only if a task surfaces a non-real value (none did in the current slices). |
| INT-23a | `_early_stop_key` used the raw-prose fallback for math/math500 while the transition extractor (`_family_key`) used the numeric `_math500_key`; the two commit views disagreed, so run-side never settled (prose jittered every round) and transition-side extracted nothing (the numeric key never matched the prose) | **BUG** | Run-side commit and transition-side commit must be the SAME identity, else 'settled vs non-settled' and 'candidate extracted vs not' diverge for the same task. Fixed 2026-10-18: `_early_stop_key` gains a math/math500 branch returning `_math500_key` ("num") with source 'content'/'cot', mirroring `_family_key`; a round with no parseable arithmetic value returns `(None, None)` (no commit). |
| INT-23b | `streak = streak + 1 if committed_key == prev_key else 1` counted `None == None` as 'unchanged', so a task whose rounds never commit (gpqa/aime no-commit) early-stopped after 3 empty rounds | **BUG** | A None commit is 'no answer', not 'the same answer'; it must reset the streak. Fixed 2026-10-18: streak advances only when `committed_key is not None and committed_key == prev_key`. |
| INT-24 | Stage-B `_derive_verdict` silently trusted the latest isolated answer value when the model CUT every transition (chain disintegrates into singletons) | **BUG** | `_derive_verdict` sorts fragments by (len, end-r) and returns the longest fragment's terminal answer even when that 'longest' is a lone singleton. When EVERY edge is cut the model's own signal is 'no step is trustworthy', so returning an isolated answer contradicts the metacognition contract (never -> honest UNSURE). Fixed 2026-10-18: if `len(rounds)>=2` and every surviving fragment is a singleton, return UNSURE (None). |
| INT-25 | glm twostage reason-call fragments the rationale to one char ('I'/'The'/'My'): passing the original question re-triggers glm's locked-on hidden CoT (~1.5k reasoning tokens) which eats the 512 budget (finish_reason=length) | **BUG** | The reason side-channel must state a change/keep rationale from the prev/curr answer + feedback, not re-solve the task; the question is what makes glm re-derive (the 300-char stem fix alone did NOT stop it on short math500 items). Fixed 2026-10-18: reason call no longer receives the question, and `TWOSTAGE_RATIONALE_MAX_TOKENS` 512->1024. |
| INT-26 | deepseek-v4-flash hard-GPQA `thinking_budget=8192` exhaustion → model keeps writing hidden CoT into visible `content` until `finish_reason=length`, so `resolve_commit` extracts no letter (dropped vote). | **INTERFERENCE** | Budget-too-small for hard items (same class as INT-18); code is correct (`resolve_commit` returns None for a length round with no commit). **Accept/re-run rule**: dropped votes that do NOT flip the majority (`gap > lost`) are tolerated; a task whose majority can tie/flip (`gap <= lost`) is re-run. |

---

## 2. Causal Quantification (Interference Only)

| ID | Interference | Type | Before (Version) | Accuracy Before | After (Version) | Accuracy After | Delta (pp) | Evidence |
|---|---|---|---|---|---|---|---|---|
| INT-14 | Tool design vs FC paradigm | Tool Design | v1-native-fc (5 tasks) | 40% | v3-interference-fix (50 tasks) | 48% | **+8pp** | RI: 0→305/305 (100%), 50-task full validation |
| INT-01 | ReAct format tax | Format | v0-ReAct (V4-Pro) | 8.3% | v0-FC (FAB official) | 60.39% | **+52.09pp** | Same model, 7x gap |
| INT-02 | Negative example priming | Prompt | v0 (50 tasks) | 16% | v1 removed (50 tasks) | 34% | **+18pp** | Accuracy regressed 34%→16% when bad examples added |
| INT-03 | Fallback "ONE LINE ONLY" | Hyperparam | v0 (50 tasks) | 30% | v1 relaxed (50 tasks) | 34% | **+4pp** | Overly restrictive prompt truncated info |
| INT-04 | max_tokens=256 | Hyperparam | v0 (50 tasks) | 22% | v1 256 maintained (50 tasks) | 34% | **+12pp** | Increasing to 1024 had no effect; issue was elsewhere |
| INT-05 | max_steps=25→50 | Hyperparam | v3 baseline (50 tasks, max_steps=25) | 48% | INT-05 (50 tasks, max_steps=50) | 54% | **+6pp** | complete_failure 20→13 (-7), total errors 26→23 (-3). Confirmed interference. |
| INT-06 | T2 trajectory 4000→20000 chars | Hyperparam | INT-05 trajectories (T2=4000) | 54% | INT-06 (T2=20000, same trajectories) | 56% | **+2pp** | Hard 33.3→41.7%, Beat-or-Miss +1 task. Minimal interference; judge already had enough context. |
| INT-07 | Judge self-eval bias | Mechanism | PAUSED (cost) | TBD | TBD | TBD | TBD | V4-Pro judge too expensive; deferred. Use V4.1-Flash or R1 as cheaper alternative, or limit V4-Pro to boundary cases only. |
| INT-12 | Hidden max_steps + forced synthesis | Mechanism | PLANNED (Option D) | TBD | TBD | TBD | TBD | Dual-layer interference: max_steps is hidden constraint, fallback is compensation. Test: make budget transparent + remove fallback. See experiments/20260916_int12_transparent_budget/EXPERIMENT.md |
| INT-15 | Retrieve chunking + cache-dedup | Mechanism | PLANNED (pre-run) | TBD | TBD | TBD | TBD | Registered 2026-09-28; frozen hyperparams in src/config.py (RETRIEVE_CHUNK_SIZE=1500, RETRIEVE_TOP_K=5). Quantify vs prior run after re-running FAB. |
| INT-16 | MCQ answer-format prompt alignment | Prompt | v3-generic prompt (50 tasks) | 74% / 44% / 44% | INT-16 letter-only prompt (50 tasks) | 86% / 88% / 80% | **+12 / +44 / +36 pp** | deepseek-v4-flash / qwen3.8-flash / glm-5.3 (0 api_failure); ≈ official MMLU-Pro (86.4 / 88.6 / 86.77). Frozen prompt in src/agent.py. |
| INT-17 | Answer-format prompt for new benchmarks | Prompt | generic finance prompt (ablation pending) | TBD | aime integer-only / bbh short-answer prompt | TBD | TBD | Frozen in src/agent.py; clean before/after ablation pending (the AIME smoke applied prompt + budget together). |
| INT-18 | Reasoning budget 1024 → 8192 | Hyperparameter | 1024 (finish_reason=length, empty content) | TBD | 8192 (aime/gpqa/mmlu_pro/bbh) | TBD | TBD | Frozen in `REASONING_BENCH_MAX_TOKENS` (src/config.py:98); mmlu_pro/bbh added 2026-10-08 (mmlu_pro 82% → 92%). |
| INT-19 | GPQA option shuffle | Design | raw CSV order (correct always A) | TBD | fixed per-question-seed shuffle | TBD | TBD | Position bias removed; non-comparable to raw-order runs. src/benchmark.py:645-679. |
| INT-20 | Closed-book tool gating | Tool Design | tool schema exposed to all benchmarks | TBD | CLOSED_BOOK gate (tool-free single gen) | TBD | TBD | GPQA prompt tokens ~29M → ~0.2M per run; tool_calls 292 → 0. Accuracy delta quantified after clean re-run. |
| INT-21 | Fragment → CoT-tail answer recovery | Scoring/Commit (BUG fix) | content-only commit (glm truncation) | TBD | `resolve_commit` + `commit_source` (tail-only, no full scan) | TBD | TBD | glm GPQA full non-settle 33 (21 fragment + 12 oscillate) expected to shrink under cot recovery; settle / transition / no-commit counts shift under the new vs old scoring口径, quantified after clean re-run. Whole-text scan NOT used. |
| INT-22 | Non-real sympy value -> no candidate | Scoring/Commit (BUG fix) | any sympy result str'd (`'I'` -> `'1.0*I'`) | TBD | real-only keys (reject non-real) | TBD | TBD | Registered 2026-10-18; only materializes if a task yields a complex/imaginary sympy value (none in the current slices). |
| INT-26 | thinking_budget 8192 exhaustion → length dropped votes | Hyperparameter | 8192 | TBD | 16384/32768 (smoke in progress) | TBD | TBD | A3: length 43/410 (10.5%), extraction-loss 47/410 (11.5%); C: length 8/109 (7.3%). Most tasks majority gap ≥2 → no flip; re-run only `gap <= lost`. smoke (gpqa_056 × 4 budgets) quantifying the accept/re-run boundary. |

---

## 3. Interference by Category

### 3.1 Tool Design Interference (Highest Impact)
- **INT-14** (+8pp on 50 tasks, +20pp on 5 tasks): Tool design incompatible with calling paradigm
  - Root cause: retrieve_information required LLM to pass document text as JSON parameter
  - Fix: Made tool stateful (auto-search cached documents)
  - Key insight: "Code correct but design unusable" — hardest to detect

### 3.2 Format Interference
- **INT-01** (+52pp): ReAct text format vs native Function Calling
  - Root cause: ReAct requires text parsing; parse failure = tool call failure
  - Fix: Migrated to native FC
  - Key insight: Format choice is a confounding variable, not a technical detail

### 3.3 Prompt Design Interference
- **INT-02** (+18pp): Negative example priming
  - Root cause: LLM mimics example content regardless of positive/negative framing
  - Fix: Removed negative examples from fallback prompt
  - Key insight: Avoid specific examples in prompts; use abstract placeholders

- **INT-03** (+4pp): Fallback prompt truncation
  - Root cause: "ONE LINE ONLY" truncated critical information
  - Fix: Relaxed to allow multi-line answers
  - Key insight: Restrictive prompts don't improve precision; they lose information

### 3.4 Hyperparameter Interference
- **INT-04** (0pp direct): max_tokens
  - Finding: Increasing 256→1024 had no accuracy effect; root issue was API failures
  - Key insight: Hyperparameter changes can mask other issues; need isolation

- **INT-05/06** (TBD): max_steps, context length
  - Status: Suspected, needs controlled experiments

### 3.5 Mechanism Interference
- **INT-07** (TBD): LLM-as-Judge self-evaluation
  - Status: Suspected, needs multi-model judge experiment
  - Key insight: Using same model for agent and judge creates circular reasoning

- **INT-12** (TBD): Forced synthesis step
  - Status: Suspected, needs with/without comparison
  - Key insight: FAB doesn't force synthesis; we shouldn't either

---

### 3.6 New-benchmark (AIME / GPQA-Diamond / BBH) generation interventions

Scope: the hard-benchmark expansion. All three are generator-/config-side; none is a change to a
*correct* evaluator — they are declared so the new-family numbers are not silently incomparable to
the finance baseline, and so any future re-run reproduces the same model-visible conditions.

- **INT-17** (Prompt): per-family answer-format prompts — AIME integer-only, BBH short-answer;
  GPQA reuses the INT-16 MCQ letter-only prompt. Frozen verbatim in src/agent.py.
- **INT-18** (Hyperparameter): reasoning-benchmark generation budget 1024 → 8192
  (`REASONING_BENCH_MAX_TOKENS`), applied to aime/gpqa/mmlu_pro/bbh (mmlu_pro/bbh added
  2026-10-08 after INT-20 closed-book gating).
- **INT-19** (Design): GPQA option shuffle with a fixed per-question seed, removing the
  "correct is always A" position bias at the cost of comparability with the raw CSV order.
- **INT-20** (Tool Design): closed-book tool gating — L1 benchmarks (math / math500 /
  mmlu_pro / aime / gpqa / bbh) no longer expose external retrieval tools. Declared in
  `CLOSED_BOOK_BENCHMARKS` (src/config.py) and applied as a single tool-free text
  generation in src/agent.py. Triggered by GPQA-Diamond spontaneously retrieving against
  PubMed/Europe PMC (~29M prompt tokens/run), which also contaminated the L1 base
  measurement with L2 tool ability.

---

## 4. Summary Statistics

| Metric | Value |
|---|---|
| Total issues identified | 26 (INT-01 to INT-26, incl. sub-labels) |
| Pure bugs | 10 |
| True interferences | 16 |
| Confirmed (with causal data) | 5 |
| Suspected (needs experiment) | 8 |
| Non-interference | 1 (INT-11: cache hit rate) |
| Total accuracy recovered | 34% → 48% (+14pp on 50 tasks) |
| Of which: bug fixes | 34% → 40% (+6pp) |
| Of which: interference fixes | 40% → 48% (+8pp) |
| RI success rate | 0/105 (0%) → 305/305 (100%) |
