# Task-Family Taxonomy & L1/L2 Tool Policy

**Version**: 1.0 (2026-10-08)
**Status**: authoritative (academic deliverable)
**Scope**: the canonical classification of evaluation task families, the closed-book vs tool-native assumption that separates L1 Base from L2 Augmentation, and the code-level tool/budget policy that operationalises it. Candidate for paper §3.1 / §5.2 supporting content.

---

## 1. Core hypothesis

> **Capability layer = tool policy.** L1 (Base) is measured **closed-book** — the model answers from its own weights with no external tool schema; L2 (Augmentation) is measured **tool-native** — the tool (function-calling / retrieval / browser) is part of the task itself. The boundary follows each benchmark's **official evaluation protocol**, not a project-level preference.

Two consequences:

1. **L1 must never expose tools.** Exposing a tool schema to a closed-book benchmark is an unregistered intervention that (a) violates the official protocol and (b) contaminates the L1 base measurement with L2 tool ability. This was observed directly: GPQA-Diamond (a closed-book science MCQ) drifted into spontaneous `fetch_url` calls against PubMed/Europe PMC, growing ~29M prompt tokens per run — see **INT-20**.

2. **L2 tools are the point.** BFCL is *function calling* (the schema IS the task); finance/FAB is an *open-book agent* (it must retrieve filings). Removing tools here would destroy the benchmark.

This is the same L1/L2 split already used for capability-matrix inversion in `docs/RESEARCH_PLAN.md` §5.2/§5.4 — here it is stated as an explicit, code-enforced policy rather than an implicit assumption.

---

## 2. The two-layer classification

| Layer | Tool policy | What it measures | Families |
|---|---|---|---|
| **L1 Base** | closed-book (no tool schema) | model's own knowledge / reasoning / computation | math, logic, science, commonsense, factual-QA, translation |
| **L2 Augmentation** | tool-native (tool schema exposed) | model-plus-system: function calling, retrieval, orchestration | finance, tool-use, code, multi-hop, web |

**L1:L2 probe ratio = 3:2** (three L1 sets, two L2 sets), so the capability tensor is not block-diagonal on the tool axis alone.

---

## 3. Master task-family table

| Family | Benchmarks (easy → hard) | Layer | Answer form | Evaluator (zero-LLM unless noted) | Tool | Qs/set | Budget | Stage |
|---|---|---|---|---|---|---|---|---|
| math | GSM8K → MATH-500 → AIME | L1 | numeric / LaTeX / integer | `_score_t1_numeric` / `_score_math500` / `_score_aime` | no | 50 | 8192 (aime) · 1024 (gsm8k/math500) | P1–P3 |
| logic | BBH → MMLU-Pro | L1 | letter (10-opt) / letter+int+word | `_score_mmlu_pro` / `_score_bbh` | no | 50 | 8192 | P1–P3 |
| science | GPQA-Diamond | L1 | letter (4-opt, hard) | `_score_gpqa` | no | 50 | 8192 | P1 (advanced) · P2–P3 |
| commonsense | HellaSwag / CSQA | L1 | letter | exact letter | no | 50 | ~1.5K | P2–P3 |
| factual-QA | TriviaQA / NQ / SimpleQA | L1 | short answer | LLM-judge / EM | no | 50 | ~1.5K | P2–P3 |
| translation | WMT zh–en / FLORES | L1 | generation | BLEU / COMET / judge | no | 50 | ~2K | P2–P3 |
| finance | FAB | L2 heavy-FC | agent + domain tools | max(T1, T2) + rubric | yes | 50 | 1024/step (50–80K total) | P1–P3 |
| tool-use | BFCL (simple) | L2 light-FC | `{name, arguments}` | `_score_bfcl` (AST match) | yes | 50 | 2–5K | P1–P3 |
| code | HumanEval → SWE-bench | L2 light→heavy | code | pass@k (executor) | partial* | 50 | 2–150K | P2–P3 |
| multi-hop | HotpotQA / MuSiQue | L2 light-FC | retrieval QA | EM / F1 | yes | 50 | 10–20K | P2–P3 |
| web | WebArena / GAIA | L2 heavy-FC | agent + browser | judge + completion | yes | 50 | 30–100K | P3 |

\* HumanEval is generation-only (no FC) unless run under an executor harness; SWE-bench uses file-edit / bash tools.

**Probe subset (Phase 1, live).** Each family fixed at 50 questions for uniform statistical power:

| Family | Probe set | Layer | Status |
|---|---|---|---|
| math | GSM8K 50 / MATH-500 50 / AIME 50 | L1 | ran (gsm8k/math500 d1; aime new-set) |
| logic | MMLU-Pro 50 / BBH 44 | L1 | ran (mmlu int16→int20; bbh new-set) |
| science | GPQA-Diamond 50 | L1 | ran (new-set, int20 re-run) |
| finance | FAB 50 (heavy-FC anchor) | L2 | ran (d1) |
| tool-use | BFCL 50 (light-FC anchor) | L2 | ran (d1 + auto rerun) |

---

## 4. Code-level policy (INT-20 / INT-18)

The classification is enforced in two code locations, both registered interventions.

### 4.1 Tool gating — INT-20

`src/config.py` declares the sets; `src/agent.py` routes closed-book families to a single tool-free text generation (no `tools` argument, no tool loop):

```python
CLOSED_BOOK_BENCHMARKS = frozenset({
    "math", "math500", "mmlu_pro", "aime", "gpqa", "bbh",
})
TOOL_NATIVE_BENCHMARKS = frozenset({
    "bfcl", "finance",
})
```

`HuggingFaceAgent.solve` computes `closed_book = benchmark in CLOSED_BOOK_BENCHMARKS`; when true it sets `fc_tools = []` and returns a single `_call_llm_text` result, skipping the tool loop entirely.

### 4.2 Generation budget — INT-18

Reasoning models (deepseek/qwen/glm) spend their hidden chain-of-thought in `reasoning_content`. At the 1024-token default the CoT alone exhausts the cap (`finish_reason=length`), `content` comes back empty and the answer truncates. The CoT-heavy **closed-book** families get the frozen reasoning budget:

```python
_mt = config.REASONING_BENCH_MAX_TOKENS if benchmark in ("aime", "gpqa", "mmlu_pro", "bbh") else self.max_tokens
```

- **8192** (`REASONING_BENCH_MAX_TOKENS`): aime, gpqa, mmlu_pro, bbh.
- **1024** (default `max_tokens`): math (gsm8k), math500, finance, bfcl.

**Note on the INT-18/INT-20 interaction (2026-10-08).** Before INT-20, mmlu_pro/bbh ran *with* a tool schema, which had been silently shortening the model's CoT so 1024 sufficed (mmlu_pro 86%). After INT-20 removed the schema, the CoT grew past 1024 and truncated the answer (mmlu_pro 82%). Extending INT-18 to mmlu_pro/bbh restored/improved it (mmlu_pro 92%, and un-truncated bbh geometric-shapes items). This is recorded in `docs/INTERFERENCE_CAUSAL_TABLE.md` (INT-18 row, INT-20 row).

---

## 5. Phase coverage

| Stage | Scope | Families added | Models |
|---|---|---|---|
| **P1 (probe)** | feasibility + L3/L4 mechanism | math, logic, science, finance, tool-use | 3 mid-tier (deepseek-v4-flash / qwen3.8-flash / glm-5.3) |
| **P2 (feasibility)** | broader L1/L2 coverage | commonsense, factual-QA, translation, code, multi-hop | + weak tier (qwen3.6-flash / glm-4.7-flash) |
| **P3 (full)** | 12–15 families, L2/L3 ≥ 40% | web | + strong tier (Claude Opus 5.5 / GPT-6) |

---

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-08 | Initial task-family taxonomy. Formalised the closed-book (L1) vs tool-native (L2) assumption, the master table, and the INT-20 / INT-18 code policy that enforces it. |
