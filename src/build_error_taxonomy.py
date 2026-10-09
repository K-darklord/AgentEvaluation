"""
build_error_taxonomy.py
=======================
Phase 1 (probe) build-before-burn item 1b: build the critique reference library
(error question bank) by auto-labeling every WRONG question in d1_baseline with a
fine-grained, rule-based error type.

Why this exists
---------------
The `error_type` field in results.csv is a COARSE evaluator label (binary for 4/5
domains: correct vs one error label). Per RESEARCH_PLAN Sec 5.8, the critique error
taxonomy is a SEPARATE, inductively-built catalogue. This script derives it from
raw signals (final_answer vs gold_answer, tool trajectory, structured rubric) using
deterministic rules + hallucination signals -- no LLM, no manual labeling.

Taxonomy (20 types over 8 families)
-----------------------------------
  math500 (numeric/symbolic, signal = final vs gold):
    empty_or_unparseable, near_miss, factor_error, sign_flip,
    magnitude_error, wrong_symbolic
  mmlu_pro (letter MCQ, signal = A-J match):
    non_letter_output, wrong_option, multiple_letters
  gpqa (letter MCQ, signal = A-D match): same leaf space as mmlu_pro
  aime (integer-answer competition math): reuses math500 numeric rules
  bbh (letter / integer / closed-set word targets):
    letter -> mmlu leaves, integer -> math500 leaves,
    closed-set word -> wrong_word (new leaf)
  finance (tool loop + rubric, signal = trajectory + rubric_structured):
    empty_pred, tool_error, retrieval_failure, contradiction,
    complete_failure, numeric_error, coverage_incomplete
  bfcl (function call, signal = JSON  {name, arguments}  vs ground truth):
    json_parse_error, wrong_function_name, wrong_argument, empty_pred
  math (GSM8K): reuses math500 numeric rules; ceiling family (~0 wrong).

Reproducibility
---------------
- Fully deterministic (no randomness, no API, no model loading).
- All thresholds are named constants at module top and dumped to the output metadata.
- One command: `python3 src/build_error_taxonomy.py`

Data sources
------------
- math / math500 / finance / bfcl : experiments/d1_baseline_20260928_201128/
- mmlu_pro (INT-16 rerun)         : experiments/mmlu_pro_int16_full/
- aime / gpqa / bbh               : experiments/new_set_20261008_full/
Wrong-ness is read from results.csv `is_correct` (already includes the offline
gold-verdict, incl. T2 LLM-judge for finance). Trajectories.jsonl supplies the raw
signals (prompt, final_answer, metadata.rubric_structured, trajectory steps).
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "experiments" / "d1_baseline_20260928_201128"
INT16 = ROOT / "experiments" / "mmlu_pro_int16_full"
NEWSET = ROOT / "experiments" / "new_set_20261008_full"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]

# ----------------------------------------------------------------------
# Named thresholds (reproducibility: dumped to output metadata)
# ----------------------------------------------------------------------
TAXONOMY_VERSION = "v2.0"
RUBRIC_COVERAGE_THRESHOLD = 0.6          # same as config.SCORING_RUBRIC_COVERAGE
NUMERIC_TOL = 0.05                       # same as config.SCORING_NUMERIC_TOL
SIGN_FLIP_THRESHOLD = -0.9               # ratio <= -0.9 => sign flip
MAGNITUDE_LOW = 0.1                      # |ratio| < 0.1 => magnitude error
MAGNITUDE_HIGH = 10.0                    # |ratio| > 10  => magnitude error
NEAR_MISS_REL = 0.10                     # |ratio-1| <= 0.10 => near miss
FACTOR_TOLERANCE = 0.05                  # |ratio-k|/|k| <= 0.05 => factor error
SIMPLE_FACTORS = (2, 3, 4, 5, 6, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 6,
                  3 / 2, 2 / 3, 4 / 3, 3 / 4, 5 / 2, 2 / 5)

PREFIX2FAMILY = {
    "gsm8k": "math", "math500": "math500", "mmlu": "mmlu_pro",
    "fab": "finance", "bfcl": "bfcl",
    "aime": "aime", "gpqa": "gpqa", "bbh": "bbh",
}

# ----------------------------------------------------------------------
# Academic ontology mapping: each operationalized leaf label -> the published
# error category it detects. Sources: BFCL (official AST taxonomy),
# GSM-Ranges (logical vs arithmetic), NTT (reasoning-process error classes),
# PRISM (knowledge/reasoning/instruction-following), fine-grained hallucination
# taxonomies. Step-level classes we cannot detect from stored signals
# (final_answer + trajectory + stored judge) are listed in NOT_DETECTABLE.
# ----------------------------------------------------------------------
ONTOLOGY = {
    # math500 / math (GSM-Ranges arithmetic vs NTT symbolic/caclulation)
    "sign_flip":           {"group": "arithmetic_error", "source": "GSM-Ranges / NTT calculation"},
    "magnitude_error":     {"group": "arithmetic_error", "source": "GSM-Ranges / NTT calculation"},
    "factor_error":        {"group": "arithmetic_error", "source": "GSM-Ranges / NTT calculation"},
    "near_miss":           {"group": "arithmetic_error", "source": "GSM-Ranges / NTT calculation"},
    "wrong_symbolic":      {"group": "symbolic_error", "source": "NTT symbolic manipulation"},
    "empty_or_unparseable": {"group": "invalid_output", "source": "n/a (not a reasoning class)"},
    # mmlu_pro (PRISM instruction-following vs content)
    "non_letter_output":   {"group": "instruction_following_error", "source": "PRISM"},
    "multiple_letters":    {"group": "instruction_following_error", "source": "PRISM"},
    "wrong_option":        {"group": "wrong_option", "source": "PRISM Reasoning Error"},
    "wrong_word":          {"group": "wrong_option", "source": "PRISM Reasoning Error / BIG-Bench closed-set inference"},
    # finance (PRISM knowledge/reasoning + fine-grained hallucination)
    "empty_pred":          {"group": "invalid_output", "source": "n/a (not a reasoning class)"},
    "tool_error":          {"group": "tool_error", "source": "BFCL-adjacent (tool-use)"},
    "retrieval_failure":   {"group": "knowledge_missing", "source": "PRISM Knowledge Missing"},
    "contradiction":       {"group": "knowledge_error", "source": "PRISM Knowledge Error / fine-grained hallucination"},
    "complete_failure":    {"group": "reasoning_error", "source": "n/a (reasoning not finalized / truncated / non-convergent)"},
    "numeric_error":       {"group": "reasoning_error", "source": "PRISM Reasoning Error"},
    "coverage_incomplete": {"group": "reasoning_error", "source": "PRISM Reasoning Error"},
    # bfcl (BFCL official task-level vs component-level)
    "json_parse_error":    {"group": "malformed_output", "source": "BFCL"},
    "wrong_function_name": {"group": "wrong_function", "source": "BFCL task-level"},
    "wrong_argument":      {"group": "wrong_argument", "source": "BFCL component-level"},
}

# Published classes we CANNOT operationalize from stored signals (require
# per-reasoning-step annotation) — documented for future data collection.
NOT_DETECTABLE = {
    "GSM-Ranges": ["logical error", "number-copy error"],
    "NTT (21-class)": ["full step-level reasoning-process classes"],
    "PE/CE/IE": ["procedural / conceptual / impasse step classification"],
    "fine-grained hallucination": ["fabrication", "factual inconsistency",
                                   "context inconsistency", "logical inconsistency"],
}


# ----------------------------------------------------------------------
# Gold-free static diagnostics per leaf (added 2026-10-06).
# `cause`  = one-sentence diagnosis of the error direction (implicit, no gold).
# `attention` = one-sentence, directional "how to check", phrased so it never
#     points at the correct value (no gold leak). Both are fixed at taxonomy
#     build time; neither is ever computed from gold at inference. Used by the
#     weak critic as the B / C feedback-tiers (see build_weak_critic.py and
#     RESEARCH_PLAN §5.8).
# ----------------------------------------------------------------------
LEAF_CAUSE = {
    # math500 / math
    "sign_flip":           "a sign was flipped during the arithmetic",
    "magnitude_error":     "the magnitude is far off a reasonable scale",
    "factor_error":        "the result is off by a simple multiplicative factor",
    "near_miss":           "the result is close but not exact (small arithmetic slip)",
    "wrong_symbolic":      "the symbolic form is not the one the definitions imply",
    "empty_or_unparseable": "no numeric answer could be extracted from the response",
    # mmlu_pro
    "non_letter_output":   "the response contains no single option letter",
    "multiple_letters":    "the response mentions more than one option letter",
    "wrong_option":        "the selected option is not the intended one",
    "wrong_word":          "the committed closed-set word is not the intended one",
    # finance
    "empty_pred":          "no final answer was produced",
    "tool_error":          "a tool call returned an error",
    "retrieval_failure":   "no grounding evidence was retrieved",
    "contradiction":       "the answer contradicts retrieved evidence",
    "complete_failure":    "reasoning was truncated or did not converge",
    "numeric_error":       "a numeric computation is incorrect",
    "coverage_incomplete": "only part of the required answer was addressed",
    # bfcl
    "json_parse_error":    "the output is not valid JSON",
    "wrong_function_name": "the function name is not the expected one",
    "wrong_argument":      "an argument value is not the expected one",
}

LEAF_ATTENTION = {
    # math500 / math
    "sign_flip":           "re-examine the signs in every arithmetic step",
    "magnitude_error":     "re-check the order of magnitude and units",
    "factor_error":        "check whether a factor was dropped or doubled",
    "near_miss":           "re-run the final arithmetic step once more",
    "wrong_symbolic":      "re-derive the symbolic expression from the definitions",
    "empty_or_unparseable": "commit to one concrete value",
    # mmlu_pro
    "non_letter_output":   "state only the option letter",
    "multiple_letters":    "commit to exactly one option letter",
    "wrong_option":        "re-read the stem and re-check the selected option",
    "wrong_word":          "re-check the logical condition before committing a word",
    # finance
    "empty_pred":          "produce a final answer",
    "tool_error":          "retry the tool or fix its arguments",
    "retrieval_failure":   "retrieve source evidence before answering",
    "contradiction":       "reconcile the answer with the retrieved facts",
    "complete_failure":    "complete the derivation to a final answer",
    "numeric_error":       "re-check every arithmetic step",
    "coverage_incomplete": "address every part of the question",
    # bfcl
    "json_parse_error":    "emit valid JSON only",
    "wrong_function_name": "confirm the function name matches the task",
    "wrong_argument":      "confirm argument values match the schema",
}

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def family_of(task_id: str) -> str:
    for prefix, fam in PREFIX2FAMILY.items():
        if task_id.startswith(prefix + "_"):
            return fam
    return "other"


def _extract_numbers(s: str) -> list[float]:
    """Return all numbers in s (thousand-separator commas stripped)."""
    if s is None:
        return []
    cleaned = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(s))
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", cleaned)]
    # drop 4-digit years when they are plausibly years (1900-2100), like evaluator
    return [n for n in nums if not (1900 < n < 2100)]


def _looks_correct(v: str) -> bool:
    """is_correct may be stored as bool or string in various cases."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")


def _json_or_none(s):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _float_or_zero(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

# ----------------------------------------------------------------------
# Per-family rule classifiers. Each returns (primary_label, signals_dict).
# ----------------------------------------------------------------------

def label_math500(final, gold):
    """Numeric-ratio sub-typing. Symbolic/sparse answers fall to wrong_symbolic."""
    pred = str(final).strip()
    gold_s = str(gold).strip()
    sig = {"ratio": None, "gold_num": None, "pred_num": None}
    if not pred:
        return "empty_or_unparseable", sig
    g_nums = _extract_numbers(gold_s)
    p_nums = _extract_numbers(pred)
    if not p_nums:
        # pred has text but no extractable number -> unparseable for numeric typing
        return "empty_or_unparseable", sig
    if not g_nums:
        # gold is symbolic/text; pred numeric -> not a clean ratio comparison
        return "wrong_symbolic", sig

    g, p = g_nums[0], p_nums[0]
    sig["gold_num"], sig["pred_num"] = g, p
    if g == 0:
        sig["ratio"] = float("inf") if p != 0 else 1.0
        return "wrong_symbolic", sig

    r = p / g
    sig["ratio"] = round(r, 6)

    if r <= SIGN_FLIP_THRESHOLD:
        return "sign_flip", sig
    ar = abs(r)
    if ar < MAGNITUDE_LOW or ar > MAGNITUDE_HIGH:
        return "magnitude_error", sig
    if abs(r - 1.0) <= NEAR_MISS_REL:
        return "near_miss", sig
    for k in SIMPLE_FACTORS:
        if abs(r - k) / abs(k) <= FACTOR_TOLERANCE:
            return "factor_error", sig
    return "wrong_symbolic", sig


def label_mmlu(final, gold):
    """Letter MCQ: A-J token extraction vs gold option letter."""
    pred = str(final)
    gold_s = str(gold).strip().upper()
    letters = re.findall(r"\b[A-J]\b", pred.upper())
    sig = {"letters": letters, "gold": gold_s}
    if not letters:
        return "non_letter_output", sig
    distinct = set(letters)
    if len(distinct) > 1:
        return "multiple_letters", sig
    if gold_s in distinct:
        return "correct", sig            # defensive; should not appear in wrong set
    return "wrong_option", sig


def label_gpqa(final, gold):
    """GPQA-Diamond 4-option (A-D) letter MCQ — same leaf space as mmlu_pro, but scored
    with the 'commit, don't scan' rule (mirrors evaluator._score_gpqa / _extract_mcq_letter),
    so a prose answer that merely contains a stray option letter is NOT called correct."""
    pred = str(final)
    gold_s = str(gold).strip().upper()
    got = _extract_committed_letter(pred, choices="ABCD")
    sig = {"committed": got, "gold": gold_s}
    if got is None:
        return "non_letter_output", sig
    if got == gold_s:
        return "correct", sig            # defensive; should not appear in wrong set
    return "wrong_option", sig


def _extract_committed_word(final: str, choices=("yes", "no", "true", "false")) -> str | None:
    """Closed-set word commit extraction (mirrors evaluator._extract_committed_text).
    Only a BARE committed word (whole string / after an answer cue / last line) counts;
    prose that merely contains the word as a substring does NOT (gold='No' inside
    "I don't know" must not match)."""
    p = str(final).strip()
    if not p:
        return None
    low = {str(c).lower() for c in choices}

    def _norm(t: str) -> str | None:
        t = t.strip().strip(" \t\r\n\"'`*_().[]").rstrip(".!?,;:").strip().lower()
        return t if t in low else None

    tok = _norm(p)
    if tok:
        return tok
    m = re.search(
        r"(?:answer|choice|option|ans|result)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*([A-Za-z]+)",
        p, re.IGNORECASE)
    if m:
        tok = _norm(m.group(1))
        if tok:
            return tok
    lines = [l.strip() for l in p.splitlines() if l.strip()]
    if lines:
        tok = _norm(lines[-1])
        if tok:
            return tok
    return None


def _extract_committed_letter(final: str, choices: str = "ABCD") -> str | None:
    """Commit, don't scan: extract the single option letter a prediction committed to
    (mirrors evaluator._extract_mcq_letter). Accepts a bare answer -> explicit answer cue
    -> final line -> labeled '(X) value'. Returns None when no single letter is committed,
    so a prose answer that merely contains a stray option letter does NOT match."""
    p = str(final).strip()
    if not p:
        return None
    p = re.sub(r"(?<![A-Za-z0-9])_{1,2}([A-Za-z])_{1,2}(?![A-Za-z0-9])", r"\1", p)
    p = re.sub(r"[*`]", "", p)
    bare = r"[\s\(\[]*([A-Za-z])[\s\)\]]*[\.\:]?"
    m = re.fullmatch(bare, p)
    if m and m.group(1).upper() in choices:
        return m.group(1).upper()
    m = re.search(
        r"(?:answer|choice|option|ans)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*\(?([A-Za-z])\)?(?![A-Za-z])",
        p, re.IGNORECASE)
    if m and m.group(1).upper() in choices:
        return m.group(1).upper()
    lines = [l.strip() for l in p.splitlines() if l.strip()]
    if lines:
        m = re.fullmatch(bare, lines[-1])
        if m and m.group(1).upper() in choices:
            return m.group(1).upper()
    labeled = re.compile(r"\s*[\(\[]?([A-Za-z])(?:[\)\]]|[\.\:\-\u2013\u2014])(?!\w)")
    for cand in ([lines[-1]] if lines else []) + [p]:
        m = labeled.match(cand)
        if m and m.group(1).upper() in choices:
            return m.group(1).upper()
    return None


def label_bbh(final, gold):
    """BIG-Bench Hard: three target forms (letter / integer / closed-set word).
    Letter -> mmlu-style (A-Z range); integer -> math500 numeric-ratio typing;
    closed-set word -> new `wrong_word` leaf (with invalid -> empty_or_unparseable)."""
    pred = str(final).strip()
    gold_s = str(gold).strip()
    sig = {}

    # (1) letter MCQ target: '(X)' or bare 'X'
    letter = re.fullmatch(r"\(?([A-Za-z])\)?", gold_s)
    if letter:
        want = letter.group(1).upper()
        got = _extract_committed_letter(pred, choices="ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        sig["committed"] = got
        if got is None:
            return "non_letter_output", sig
        if got == want:
            return "correct", sig
        return "wrong_option", sig

    # (2) integer / number target
    if re.fullmatch(r"-?\d+(\.\d+)?", gold_s):
        return label_math500(final, gold)

    # (3) closed-set word target (Yes/No/True/False)
    want = gold_s.strip().lower()
    got = _extract_committed_word(pred)
    sig["committed_word"] = got
    if got is None:
        return "empty_or_unparseable", sig
    if got == want:
        return "correct", sig
    return "wrong_word", sig


def label_finance(row, rubric_threshold=RUBRIC_COVERAGE_THRESHOLD):
    """Tool-loop rule signals + stored LLM-judge hallucination signals.

    Signal sources (all deterministic, offline — no new API):
      - rule:          empty answer, tool_error, zero tool calls (retrieval_failure)
      - stored:        dealbreaker_triggered (judge factual contradiction = hallucination),
                       tier1==tier2==0 (complete_failure), coarse stored error_type
      - rubric:        correctness-coverage structural check (defensive numeric/qualitative)
    """
    final = str(row.get("final_answer", "")).strip()
    gold = str(row.get("gold_answer", "")).strip()
    traj = row.get("trajectory", [])
    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        metadata = _json_or_none(metadata) or {}

    stored_type = str(row.get("_stored_etype", "")).strip()
    dealbreaker = row.get("_dealbreaker")
    if isinstance(dealbreaker, str):
        dealbreaker = dealbreaker.strip().lower() in ("true", "1", "yes")
    t1 = _float_or_zero(row.get("_t1"))
    t2 = _float_or_zero(row.get("_t2"))

    tool_steps = [s for s in traj if s.get("tool_name")]
    n_tool = len(tool_steps)
    sig = {"n_tool_calls": n_tool, "rubric_coverage": None,
           "dealbreaker": bool(dealbreaker), "t1": t1, "t2": t2}

    # 1) empty answer
    if not final:
        return "empty_pred", sig

    # 2) tool errored (rule, from trajectory)
    if any("tool_error" in str(s.get("tool_output", "")) for s in tool_steps):
        return "tool_error", sig

    # 3) zero tool calls (rule) -> retrieval failure
    if not tool_steps:
        return "retrieval_failure", sig

    # 4) hallucination / factual contradiction (stored judge signal)
    if dealbreaker or stored_type == "factual_contradiction":
        return "contradiction", sig

    # 5) total failure: both tiers zero (stored signal)
    if t1 == 0 and t2 == 0 and stored_type == "complete_failure":
        return "complete_failure", sig

    # 6) rule-based rubric coverage (defensive correct guard)
    structured = metadata.get("rubric_structured", [])
    correctness = [c for c in structured if c.get("operator") == "correctness"]
    if correctness:
        pred_l = final.lower()
        hit = sum(1 for c in correctness
                  if c.get("criteria", "").strip().lower() in pred_l)
        cov = hit / len(correctness)
        sig["rubric_coverage"] = round(cov, 4)
        if cov >= rubric_threshold:
            return "correct", sig

    # 7) numeric vs qualitative from stored coarse label, else gold digit presence
    if stored_type == "numeric_error":
        return "numeric_error", sig
    if stored_type == "qualitative_incomplete":
        return "coverage_incomplete", sig
    if stored_type == "complete_failure":
        return "complete_failure", sig
    return "numeric_error" if any(ch.isdigit() for ch in gold) else "coverage_incomplete", sig


def label_bfcl(final, gold):
    """Function-call JSON vs ground-truth {name, arguments} — mirror evaluator._score_bfcl."""
    pred_raw = str(final).strip()
    sig = {}
    if not pred_raw:
        return "empty_pred", sig

    gt = gold if isinstance(gold, list) else _json_or_none(str(gold))
    if not gt:
        return "empty_pred", sig

    pred = _json_or_none(pred_raw)
    if pred is None:
        return "json_parse_error", sig

    name = str(pred.get("name", "")).replace(".", "_")
    args_raw = pred.get("arguments", "{}")
    args = args_raw
    if isinstance(args_raw, str):
        args = _json_or_none(args_raw)
    if not isinstance(args, dict):
        args = {}

    entry = None
    for e in gt:
        if not isinstance(e, dict):
            continue
        for k, v in e.items():
            if str(k).replace(".", "_") == name:
                entry = v
                break
        if entry is not None:
            break

    if entry is None:
        return "wrong_function_name", sig

    for param, accepted in entry.items():
        accepted_list = accepted if isinstance(accepted, list) else [accepted]
        pred_val = args.get(param, "")
        if not any(str(pred_val) == str(a) for a in accepted_list):
            return "wrong_argument", sig
    return "correct", sig            # defensive


FAMILY_LABELER = {
    "math": label_math500,       # math reuses math500 numeric rules
    "math500": label_math500,
    "mmlu_pro": label_mmlu,
    "finance": label_finance,
    "bfcl": label_bfcl,
    "aime": label_math500,       # AIME reuses math500 numeric-ratio typing
    "gpqa": label_gpqa,          # 4-option letter MCQ (A-D)
    "bbh": label_bbh,            # three target forms: letter / integer / word
}

# ----------------------------------------------------------------------
# Data loading (join results.csv `is_correct` onto trajectories.jsonl signals)
# ----------------------------------------------------------------------

def _load_trajectories(path: Path) -> dict[str, dict]:
    with open(path) as f:
        return {json.loads(line)["task_id"]: json.loads(line) for line in f}


def _load_verdicts(path: Path) -> dict[str, dict]:
    """Return full results.csv rows keyed by task_id (carries judge/score signals)."""
    with open(path) as f:
        return {r["task_id"]: r for r in __import__("csv").DictReader(f)}


def load_records() -> list[dict]:
    """Return merged records across all models and both runs."""
    records = []
    # math / math500 / finance / bfcl from d1_baseline
    for model in MODELS:
        dir_ = D1 / model
        traj = _load_trajectories(dir_ / "trajectories.jsonl")
        verdict = _load_verdicts(dir_ / "results.csv")
        for tid, row in traj.items():
            fam = family_of(tid)
            if fam == "mmlu_pro":
                continue                    # use INT-16 authoritative run instead
            rec = dict(row)
            rec["_model"] = model
            v = verdict.get(tid, {})
            rec["_correct"] = _looks_correct(v.get("is_correct", "True"))
            rec["_stored_etype"] = v.get("error_type", "")
            rec["_dealbreaker"] = v.get("dealbreaker_triggered", "False")
            rec["_t1"] = v.get("tier1_numeric", "0")
            rec["_t2"] = v.get("tier2_llm_semantic", "0")
            records.append(rec)
    # mmlu_pro from INT-16 rerun
    for model in MODELS:
        dir_ = INT16 / model
        traj = _load_trajectories(dir_ / "trajectories.jsonl")
        verdict = _load_verdicts(dir_ / "results.csv")
        for tid, row in traj.items():
            rec = dict(row)
            rec["_model"] = model
            v = verdict.get(tid, {})
            rec["_correct"] = _looks_correct(v.get("is_correct", "True"))
            rec["_stored_etype"] = v.get("error_type", "")
            rec["_dealbreaker"] = v.get("dealbreaker_triggered", "False")
            rec["_t1"] = v.get("tier1_numeric", "0")
            rec["_t2"] = v.get("tier2_llm_semantic", "0")
            records.append(rec)
    # aime / gpqa / bbh from the new discrimination set
    for model in MODELS:
        dir_ = NEWSET / model
        traj = _load_trajectories(dir_ / "trajectories.jsonl")
        verdict = _load_verdicts(dir_ / "results.csv")
        for tid, row in traj.items():
            rec = dict(row)
            rec["_model"] = model
            v = verdict.get(tid, {})
            rec["_correct"] = _looks_correct(v.get("is_correct", "True"))
            rec["_stored_etype"] = v.get("error_type", "")
            rec["_dealbreaker"] = v.get("dealbreaker_triggered", "False")
            rec["_t1"] = v.get("tier1_numeric", "0")
            rec["_t2"] = v.get("tier2_llm_semantic", "0")
            records.append(rec)
    return records


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> None:
    records = load_records()

    wrong_bank = []                                 # annotated wrong instances

    for rec in records:
        fam = family_of(rec["task_id"])
        if fam not in FAMILY_LABELER or fam == "other":
            continue
        if rec["_correct"]:
            continue                                # only label wrong instances
        if rec.get("api_failure") is True or str(rec.get("api_failure", "")).strip().lower() == "true":
            continue                                # api failures carry no signal -> skip
        labeler = FAMILY_LABELER[fam]
        if fam == "finance":
            label, sig = labeler(rec)
        else:
            label, sig = labeler(rec.get("final_answer", ""), rec.get("gold_answer", ""))

        ontology = ONTOLOGY.get(label, {})
        wrong_bank.append({
            "task_id": rec["task_id"],
            "family": fam,
            "model": rec["_model"],
            "error_type": label,
            "group": ontology.get("group", "other"),
            "ontology": ontology,
            "final_answer": rec.get("final_answer", ""),
            "gold_answer": rec.get("gold_answer", ""),
            "prompt": rec.get("prompt", ""),
            "signals": sig,
            "cause": LEAF_CAUSE.get(label, ""),
            "attention": LEAF_ATTENTION.get(label, ""),
        })

    # Build a clean distribution aggregate
    dist = defaultdict(lambda: defaultdict(Counter))
    gdist = defaultdict(lambda: defaultdict(Counter))
    for item in wrong_bank:
        dist[item["family"]][item["model"]][item["error_type"]] += 1
        gdist[item["family"]][item["model"]][item["group"]] += 1

    # ---- console report ----
    print("=" * 80)
    print("Error-taxonomy distribution (wrong instances only, per family x model)")
    print("=" * 80)
    for fam in ["math", "math500", "mmlu_pro", "finance", "bfcl",
                "aime", "gpqa", "bbh"]:
        print(f"\n[{fam}]")
        total = 0
        for model in MODELS:
            c = dist[fam][model]
            if not c:
                continue
            total += sum(c.values())
            errs = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
            print(f"  {model:<18} n_wrong={sum(c.values()):>3}  {{{errs}}}")
        print(f"  -> family wrong_total = {total}")

    # ---- write artifacts ----
    out_dir = ROOT / "experiments" / "error_taxonomy_v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "taxonomy_version": TAXONOMY_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": "src/build_error_taxonomy.py",
        "data_sources": {
            "math_math500_finance_bfcl": str(D1.relative_to(ROOT)),
            "mmlu_pro": str(INT16.relative_to(ROOT)),
            "aime_gpqa_bbh": str(NEWSET.relative_to(ROOT)),
        },
        "thresholds": {
            "RUBRIC_COVERAGE_THRESHOLD": RUBRIC_COVERAGE_THRESHOLD,
            "NUMERIC_TOL": NUMERIC_TOL,
            "SIGN_FLIP_THRESHOLD": SIGN_FLIP_THRESHOLD,
            "MAGNITUDE_LOW": MAGNITUDE_LOW,
            "MAGNITUDE_HIGH": MAGNITUDE_HIGH,
            "NEAR_MISS_REL": NEAR_MISS_REL,
            "FACTOR_TOLERANCE": FACTOR_TOLERANCE,
            "SIMPLE_FACTORS": list(SIMPLE_FACTORS),
        },
        "labelers": {
            "math": "label_math500 (reused)",
            "math500": "label_math500",
            "mmlu_pro": "label_mmlu",
            "finance": "label_finance",
            "bfcl": "label_bfcl",
            "aime": "label_math500 (reused, numeric-ratio)",
            "gpqa": "label_gpqa (A-D letter)",
            "bbh": "label_bbh (letter/integer/word)",
        },
        "ontology": ONTOLOGY,
        "leaf_cause": LEAF_CAUSE,
        "leaf_attention": LEAF_ATTENTION,
        "not_detectable_classes": NOT_DETECTABLE,
    }

    # wrong bank (NDJSON) + distribution (JSON)
    bank_path = out_dir / "wrong_bank.jsonl"
    with open(bank_path, "w") as f:
        for item in wrong_bank:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    dist_serializable = {fam: {m: dict(c) for m, c in models.items()}
                         for fam, models in dist.items()}
    gdist_serializable = {fam: {m: dict(c) for m, c in models.items()}
                          for fam, models in gdist.items()}
    dist_path = out_dir / "taxonomy_distribution.json"
    with open(dist_path, "w") as f:
        json.dump({"metadata": metadata,
                   "distribution": dist_serializable,
                   "group_distribution": gdist_serializable}, f, indent=2, ensure_ascii=False)

    print(f"\n[written] {bank_path}  ({len(wrong_bank)} wrong instances)")
    print(f"[written] {dist_path}")


if __name__ == "__main__":
    main()
