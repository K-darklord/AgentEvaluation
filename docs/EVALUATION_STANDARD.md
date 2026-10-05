# AgentEvaluation Standard — Three-Tier Scoring

**Version**: 3.0 (2026-10-05)
**Author**: AgentEvaluation Project
**Alignment**: cross-domain (math / math500 / mmlu_pro / finance / bfcl); Finance Agent Benchmark (FAB) v2 for the finance family

> **Supersedes v2.3.** The previous 2-tier spec (`max(T1, T2)` + dealbreaker) is retained below as the
> finance-family scoring detail (§7); it is no longer the top-level architecture. Historical empirical
> findings and the interference registry from v2.3 now live in `docs/INTERFERENCE_CAUSAL_TABLE.md` and
> `docs/HISTORY.md`. The authoritative protocol is `docs/RESEARCH_PLAN.md` §5.9.

---

## 1. Design goals

1. **Dispatch by answer form.** A single scoring path cannot serve numeric, symbolic, multiple-choice,
   tool-call, and open-generation answers fairly; scoring is routed per task family.
2. **Three tiers (T1 / T2 / T3) with an explicit intervention boundary.** Only T1 is intervention-free;
   T2 and T3 change the scoring decision and are recorded as interventions (`eval_tier`).
3. **Zero-cost default.** T1 is fully deterministic (no LLM) and alone produces the baseline; T2/T3 are
   opt-in to contain cost.
4. **Trace-aware.** LLM-assisted tiers read the full response (and, for finance, the tool trajectory), not
   just a final answer.
5. **Reproducible.** T1 is deterministic; T2/T3 log the judge model, prompt, temperature, and token budget.

---

## 2. Tier dispatch

Correctness scoring is dispatched into three tiers by answer form and by how recoverable the answer is
from the model's full response. Every scored row records which tier produced its final score in an
`eval_tier` field, so hybrid scoring stays reproducible at per-question granularity.

| Family | Answer form | Primary tier | Fallback / rescue |
|---|---|---|---|
| math (GSM8K) | numeric | T1 (numeric + sympy) | — |
| math500 (MATH-500) | numeric / LaTeX / symbolic | T1 + T1b deterministic extraction | T2 (T1-missed only) |
| mmlu_pro (MMLU-Pro) | 10-option letter | T1 (exact letter) | — |
| finance (FAB) | agent + rubric | T1 + T2 (`max(T1, T2)` rubric coverage) | T3 multi-judge (deferred) |
| bfcl (BFCL) | function-call JSON | T1 (function name + argument match) | — |

---

## 3. T1 — deterministic match (no LLM)

T1 compares the predicted answer to the gold by rule or symbol equivalence. It never calls a model, so it
is zero-cost and fully reproducible.

- **Numeric** — relative-tolerance match (`abs(p − g) / max(abs(g), 1e-10) ≤ T1_NUMERIC_TOLERANCE`).
- **Symbolic / LaTeX** — `sympy` equivalence after Unicode normalisation (`_norm_unicode_math`), including
  coordinate tuples `(3, π/2)`, Unicode minus (`p − q`), and `\text{...}` wrapping.
- **Letter (MMLU-Pro)** — exact `A`–`J` option match (gold is a single letter).
- **JSON (BFCL)** — function name normalised (`math.factorial` ≡ `math_factorial`) and argument values
  matched against the accepted set.

### 3.1 T1b — deterministic extraction layer (MATH-500)

For MATH-500, the final answer is often buried inside a reasoning chain. T1b draws candidate answers from,
in order, `\boxed{...}`, the trailing `= …`, the last non-empty line, the last number (excluding year
tokens in 1900–2100), or the last option letter — and symbol-compares each candidate to the gold. T1b
targets false negatives caused by answer extraction, not by model error.

### 3.2 Finance T1 numeric algorithm

For the finance family, T1 checks whether the predicted answer contains the gold's **core numeric values**:

1. Extract all numbers from `gold_answer`, discard year-like values (1900–2100) → significant gold numbers.
2. Extract all numbers from `final_answer` → predicted numbers.
3. `T1_score = matched / len(significant_gold_numbers)`, each match within `T1_NUMERIC_TOLERANCE`.
4. No significant gold numbers (qualitative answer) → normalized substring match, then keyword coverage
   (`matched_tokens / total_tokens`).
5. No predicted numbers but gold has numbers → `T1_score = 0.0`.

---

## 4. T2 — LLM-assisted parse + judge rescue (registered intervention)

**Role.** When T1 marks a row wrong but the answer may be present-yet-unrecoverable by the extractor
(failure mode A: "the answer is in the response, the parser failed"), the full response is re-read by the
strongest judge model against a known gold and scored `CORRECT` / `INCORRECT`.

**Scope guard.** T2 runs *only* on rows T1 already judged wrong (tier-2 rescue) and is **disabled by
default** (`T2_RESCUE_ENABLED=0`) until an API key is supplied — this keeps zero-API rescoring deterministic.

| Parameter | Default | Description |
|---|---|---|
| `T2_JUDGE_MODEL` | `deepseek-v4-pro` | Strongest available judge (was `deepseek-ai/DeepSeek-V4-Flash` pre-v3.0). |
| `T2_JUDGE_BASE_URL` | Aliyun Token Plan endpoint | HF router abandoned (TCP timeout / HTTP 000). |
| `T2_JUDGE_MAX_TOKENS` | `500` | Reserve output tokens — `deepseek-v4-pro` has a hidden CoT that can otherwise consume the whole budget and leave empty `content`. |
| `T2_RESCUE_ENABLED` | `0` | Master switch for tier-2 rescue. |
| `T2_RESCUE_MAX_TOKENS` | `1000` | Rescue-response token budget. |
| `T2_PASS_THRESHOLD` | `0.5` | Minimum score to pass T2. |
| `T2_TEMPERATURE` | `0` | Reproducibility. |

**Intervention.** T2 changes the scoring decision, so any row it touches is flagged `eval_tier=T2` — a
registered intervention, distinct from T1.

---

## 5. T3 — multi-LLM voting (registered intervention)

**Role.** Open / qualitative answers whose gold is not exhaustively expressible by a rule are judged by
multiple LLMs with majority vote. This tier is reserved for domains where neither T1 nor a single-judge
T2 suffices.

**Current status.** The finance family uses `max(T1, T2)` rubric coverage as an **interim** stand-in for a
multi-judge setup; a true multi-judge T3 is deferred. T3 is a registered intervention wherever applied.

---

## 6. False-negative convention and intervention registration

- **False-negative convention.** `correct` is the positive class, so "scored wrong but actually right" is a
  **false negative (FN)** and "scored right but actually wrong" is a false positive. T1b extraction and the
  T2 rescue both target FN specifically. FNs are quantified per model by re-scoring stored answers (zero
  API) against a strict rule re-label.
- **Intervention registration.** Only T1 is intervention-free. T2 (LLM re-judge) and T3 (multi-judge) must
  be declared as interventions in every result they touch. The "answer-format-doesn't-matter" stance is
  *not* a universal default — it is declared per task family (e.g. a direct-letter prompt for MMLU-Pro),
  and a format-enforcing prompt applied to the *generator* is itself an intervention, separate from the
  evaluator.

---

## 7. Finance-family scoring detail (retained from v2 — dealbreaker)

The finance (FAB) path retains the dealbreaker from the v2 spec: a **contradiction** of a gold fact zeroes
the score, because stating something opposite to the gold fact is worse than missing it.

- T2 correctness is scored by rubric coverage (`matched / total`), batched into a single judge call.
- A contradiction criterion (rubric `operator == contradiction`) triggers a multi-vote check; majority
  (2/3) sets `final_score = 0.0`, overriding even a matching numeric value.
- `final_score = max(T1_score, T2_score)`, `final_pass = final_score ≥ FINAL_PASS_THRESHOLD (0.5)`.

This is the only place the v2 `max(T1, T2)` + dealbreaker survives; it is scoped to the finance family.

---

## 8. Error taxonomy

The operational error taxonomy is a separate authoritative document, `docs/ERROR_TAXONOMY.md`:

- **19 fine-grained leaf types** (per-family, each anchored to an academic ontology), fed back to the agent
  as directional signal.
- **6 shared middle axes** (knowledge / reasoning / computation / instruction / tool / completeness) forming
  the tensor `E`-axis for capability decomposition.
- **L1–L4** latent capability layers (Base / Augmentation / Meta-cognitive / Correction), named post-hoc,
  never a priori mapped.

The legacy 6-label finance error set (`retrieval_failure`, `numeric_error`, `citation_missing`,
`tool_error`, `qualitative_incomplete`, `correct`) is superseded by the 19-leaf taxonomy.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-12 | Initial 3-tier (T1 exact, T2 numeric, T3 LLM-judge; binary). |
| 2.0 | 2026-09-13 | Merged to 2-tier (T1 numeric, T2 LLM semantic + dealbreaker); removed T3. |
| 2.1 | 2026-09-13 | T1 keyword fallback; T2 multi-vote; dealbreaker mechanism; ANSWER-only prompt. |
| 2.2 | 2026-09-15 | Fair-evaluation principles (§9); API retry + `api_failure` flag. |
| 2.3 | 2026-09-15 | Empirical V4-Flash vs V4-Pro comparison; failure-mode taxonomy; cost analysis. |
| 3.0 | 2026-10-05 | Re-architected to a three-tier scoring framework (T1 deterministic / T2 LLM rescue / T3 multi-judge); T2 judge moved to `deepseek-v4-pro` with `T2_JUDGE_MAX_TOKENS`; cross-domain scope (5 families); taxonomy delegated to `docs/ERROR_TAXONOMY.md`; finance-path detail (dealbreaker) retained in §7. |
