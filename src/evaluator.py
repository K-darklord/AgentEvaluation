"""
evaluator.py
=============
Unified evaluation module: merges scorer.py + analysis.py.

I provide two scoring paths:
  1. Legacy classify_error() for the mini benchmark (rule-based, unchanged).
  2. Rubric-coverage scoring for FAB questions (uses structured rubric criteria).

Error taxonomy (6 labels, intentionally simple — upgrade is future work):
  - retrieval_failure      : did not retrieve / retrieved wrong source
  - numeric_error          : wrong number, unit, or rounding
  - citation_missing       : missing source citation
  - tool_error             : tool call itself errored
  - qualitative_incomplete : qualitative answer missing key points
  - correct                : passed
"""
from __future__ import annotations
import csv
import json
import re
import logging
import threading
import concurrent.futures
from pathlib import Path
from collections import Counter

from src.runner import OUTPUT_DIR
from src import config

logger = logging.getLogger(__name__)


# ======================================================================
# Scoring helpers (preserved verbatim from scorer.py)
# ======================================================================

def _extract_numbers(s: str) -> list[float]:
    """I extract all numbers from a string, handling thousand-separator commas."""
    cleaned = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(s))
    return [float(x) for x in re.findall(r"-?\d+\.?\d*", cleaned)]


def score_numeric(gold: str, pred: str, tol: float = 0.05) -> bool:
    """I parse numbers and allow relative tolerance. I pick the pred number closest to gold."""
    try:
        g_nums = _extract_numbers(gold)
        p_nums = _extract_numbers(pred)
        if not g_nums or not p_nums:
            return False
        g = g_nums[0]
        p = min(p_nums, key=lambda x: abs(x - g))
    except (IndexError, ValueError):
        return False
    if g == 0:
        return abs(p) < tol
    return abs(g - p) / abs(g) <= tol


def score_exact(gold: str, pred: str) -> bool:
    """I check if gold is a substring of pred (case-insensitive)."""
    return str(gold).strip().lower() in str(pred).strip().lower()


def classify_error(task: dict) -> str:
    """I classify an error based on trajectory + answer (legacy rule-based path).
    I keep the original 6-label taxonomy unchanged."""
    traj = task.get("trajectory", [])
    tool_steps = [s for s in traj if s.get("tool_name")]

    # 1) Tool itself errored
    if any("tool_error" in s.get("tool_output", "") for s in tool_steps):
        return "tool_error"

    # 2) No tool calls for retrieval/reasoning tasks
    if not tool_steps and task.get("category", "") in (
        "Quantitative Retrieval", "Qualitative Retrieval", "Numerical Reasoning"):
        return "retrieval_failure"

    # 3) Numerical reasoning -> numeric comparison
    if task.get("category") == "Numerical Reasoning":
        return "correct" if score_numeric(task.get("gold_answer", ""),
                                          task.get("final_answer", "")) else "numeric_error"

    # 4) Qualitative retrieval -> keyword coverage
    if task.get("category") == "Qualitative Retrieval":
        keywords = ["productivity", "intelligent cloud", "more personal computing"]
        hit = sum(1 for k in keywords if k.lower() in task.get("final_answer", "").lower())
        if hit >= 2:
            return "correct"
        return "qualitative_incomplete"

    # 5) Quantitative retrieval -> numeric with looser tolerance
    if task.get("category") == "Quantitative Retrieval":
        return "correct" if score_numeric(task.get("gold_answer", ""),
                                          task.get("final_answer", ""),
                                          tol=config.SCORING_QUANTITATIVE_TOL) else "numeric_error"
    return "correct"


# ======================================================================
# FAB rubric-based scoring (new path, same 6 labels)
# ======================================================================

def _rubric_coverage(row: dict, threshold: float = None) -> str:
    """I score FAB rows using their structured rubric.
    For each 'correctness' criterion I check (case-insensitive substring) if it
    appears in final_answer. I also penalize 'contradiction' criteria that match.
    I return one of the existing 6 labels, never a new one."""
    if threshold is None:
        threshold = config.SCORING_RUBRIC_COVERAGE

    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    structured = metadata.get("rubric_structured", [])
    if not structured:
        # Fall back to legacy classify_error path
        return classify_error(row)

    pred = str(row.get("final_answer", "")).lower().strip()
    if not pred:
        return "qualitative_incomplete"

    correctness = [c for c in structured if c.get("operator") == "correctness"]
    contradictions = [c for c in structured if c.get("operator") == "contradiction"]

    # If a forbidden contradiction string is present, the answer is wrong
    for c in contradictions:
        crit = c.get("criteria", "").strip().lower()
        if crit and crit in pred:
            return "numeric_error" if any(ch.isdigit() for ch in pred) else "qualitative_incomplete"

    # Check correctness criteria coverage
    if not correctness:
        return classify_error(row)

    hit = sum(1 for c in correctness
              if c.get("criteria", "").strip().lower() in pred)
    cov = hit / len(correctness)

    if cov >= threshold:
        return "correct"

    # Distinguish numeric vs qualitative errors
    gold = str(row.get("gold_answer", ""))
    if any(ch.isdigit() for ch in gold):
        return "numeric_error"
    return "qualitative_incomplete"



# ======================================================================
# Tier 3: LLM-as-Judge scoring (uses HF router API)
# ======================================================================


def _normalize_answer(s: str) -> str:
    """I normalize an answer string for robust comparison:
    - lowercase, strip whitespace
    - remove commas, dollar signs, percent signs, parentheses
    - remove common units (million, billion, etc.)
    - collapse multiple spaces
    """
    s = str(s).strip().lower()
    for ch in ["\$", "€", "£", "¥", ",", "(", ")", "%"]:
        s = s.replace(ch, " ")
    for unit in ["million", "billion", "trillion", "thousand", "mn", "bn", "mm"]:
        s = s.replace(unit, " ")
    s = " ".join(s.split())
    return s


def _extract_all_numbers(s: str) -> list:
    """I extract all numbers from a string, handling commas and units."""
    s = str(s).replace(",", "")
    matches = re.findall(r"-?\d+\.?\d*", s)
    nums = []
    for m in matches:
        try:
            nums.append(float(m))
        except ValueError:
            pass
    return nums


def _is_fab_row(row: dict) -> bool:
    """I check if a row is a FAB question (has rubric_structured or fab_ prefix)."""
    task_id = str(row.get("task_id", ""))
    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    return task_id.startswith("fab_") or bool(metadata.get("rubric_structured"))


def _rubric_coverage_normalized(row: dict) -> bool:
    """I check rubric criteria using normalized comparison. Fallback for T2 when no LLM token."""
    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    structured = metadata.get("rubric_structured", [])
    if not structured:
        return False

    pred = _normalize_answer(str(row.get("final_answer", "")))
    if not pred:
        return False

    correctness = [c for c in structured if c.get("operator") == "correctness"]
    if not correctness:
        return False

    hit = 0
    for c in correctness:
        crit = _normalize_answer(c.get("criteria", ""))
        if not crit:
            continue
        if crit in pred:
            hit += 1
            continue
        # Numeric fallback
        crit_nums = _extract_all_numbers(c.get("criteria", ""))
        pred_nums = _extract_all_numbers(str(row.get("final_answer", "")))
        sig_crit = [n for n in crit_nums if not (1900 < n < 2100)]
        if sig_crit and pred_nums:
            all_match = True
            for cn in sig_crit:
                found = False
                for pn in pred_nums:
                    if cn == 0:
                        if pn == 0:
                            found = True
                            break
                    elif abs(pn - cn) / max(abs(cn), 1e-10) < config.SCORING_NUMERIC_TOLERANCE:
                        found = True
                        break
                if not found:
                    all_match = False
                    break
            if all_match:
                hit += 1

    cov = hit / len(correctness) if correctness else 0
    return cov >= config.SCORING_RUBRIC_COVERAGE



_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "been", "have", "has", "had",
    "this", "that", "with", "from", "they", "them", "their", "there", "these",
    "those", "what", "which", "who", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "than", "too", "very", "can", "will", "just",
    "should", "now", "also", "not", "but", "however", "into", "its",
}

# ======================================================================
# Tier 1: Numeric Accuracy (rule-based, deterministic, continuous 0-1)
# ======================================================================

def _score_t1_numeric(row: dict) -> float:
    """I check whether the predicted answer contains the core numeric values
    from the gold answer, within a configurable tolerance.
    I return a continuous score in [0, 1].
    I do NOT care about reasoning text — I only look at numbers."""
    gold_raw = str(row.get("gold_answer", "")).strip()
    pred_raw = str(row.get("final_answer", "")).strip()
    if not gold_raw or not pred_raw:
        return 0.0

    # Extract numbers from gold, filter out years (1900-2100)
    gold_nums = _extract_all_numbers(gold_raw)
    sig_gold = [n for n in gold_nums if not (1900 < n < 2100)]

    if not sig_gold:
        # Text-only answer: fallback to keyword matching (continuous score)
        # I extract significant keywords from gold and count how many appear in pred
        gold_norm = _normalize_answer(gold_raw)
        pred_norm = _normalize_answer(pred_raw)

        # Exact substring match -> full score
        if gold_norm in pred_norm:
            return 1.0

        # Keyword coverage: extract significant tokens from gold (len >= 3, not stopwords)
        gold_tokens = [t for t in gold_norm.split() if len(t) >= 3 and t not in _STOPWORDS]
        if not gold_tokens:
            return 0.0

        pred_tokens_set = set(pred_norm.split())
        matched = sum(1 for t in gold_tokens if t in pred_tokens_set)
        return matched / len(gold_tokens)

    # Extract numbers from pred
    pred_nums = _extract_all_numbers(pred_raw)
    if not pred_nums:
        return 0.0

    # Count how many significant gold numbers appear in pred
    matched = 0
    for gn in sig_gold:
        for pn in pred_nums:
            if gn == 0:
                if pn == 0:
                    matched += 1
                    break
            elif abs(pn - gn) / max(abs(gn), 1e-10) < config.T1_NUMERIC_TOLERANCE:
                matched += 1
                break

    return matched / len(sig_gold)


# ======================================================================
# Tier 2: LLM Semantic Judgment (continuous 0-1, with dealbreaker)
# ======================================================================

_judge_client = None
_judge_client_lock = threading.Lock()

def _get_judge_client():
    """I lazily create an OpenAI client for the LLM judge.
    The client is a shared singleton; a lock guards init so concurrent scoring
    threads never double-create it.
    Judge channel moved off HF router (TCP timeout / HTTP 000, blocked) to
    Alibaba Token Plan (2026-09-28); reuses config.T2_JUDGE_*."""
    global _judge_client
    if _judge_client is None:
        with _judge_client_lock:
            if _judge_client is None:
                token = config.T2_JUDGE_API_KEY
                if not token:
                    return None
                from openai import OpenAI
                import httpx
                _judge_client = OpenAI(
                    base_url=config.T2_JUDGE_BASE_URL,
                    api_key=token,
                    timeout=httpx.Timeout(config.LLM_READ_TIMEOUT, connect=config.LLM_CONNECT_TIMEOUT),
                )
    return _judge_client


def _format_trajectory_summary(row: dict, max_chars: int = None) -> str:
    """I extract a compact summary of the agent trajectory for the LLM judge.
    I include tool names, inputs, and key observations, truncated to max_chars."""
    if max_chars is None:
        max_chars = config.T2_MAX_TRAJECTORY_CHARS

    traj = row.get("trajectory", [])
    if not traj:
        return "[no trajectory]"

    parts = []
    total_len = 0
    for step in traj:
        step_num = step.get("step", "?")
        tool = step.get("tool_name", "")
        tool_input = str(step.get("tool_input", ""))[:200]
        obs = str(step.get("observation", ""))[:300]
        thought = str(step.get("thought", ""))[:100]

        if tool:
            entry = f"Step {step_num}: Called {tool}({tool_input}) -> {obs}"
        else:
            entry = f"Step {step_num}: {thought}"
        parts.append(entry)
        total_len += len(entry)
        if total_len > max_chars:
            break

    result = "\n".join(parts)
    return result[:max_chars]


def _llm_judge_correctness_single(row: dict, criteria_list: list,
                                         question: str, pred: str,
                                         traj_summary: str) -> float:
    """I run ONE LLM judge call and return the score (0-1)."""
    client = _get_judge_client()
    if client is None:
        return 0.0

    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria_list))

    prompt = (
        f"You are an expert financial evaluator.\n"
        f"Judge whether the answer satisfies EACH criterion below.\n"
        f"IMPORTANT: The answer may contain reasoning text (e.g., 'The question asks...').\n"
        f"Ignore the reasoning prefix — focus on whether the factual content satisfies each criterion.\n"
        f"Consider the agent retrieved evidence in the trajectory.\n"
        f"Reply with ONLY a comma-separated list of YES/NO (one per criterion).\n"
        f"Example: YES,NO,YES,YES,NO\n\n"
        f"Question: {question}\n\n"
        f"Agent Trajectory (retrieved evidence):\n{traj_summary}\n\n"
        f"Answer: {pred[:2000]}\n\n"
        f"Criteria:\n{numbered}\n\n"
        f"Verdicts (comma-separated YES/NO):"
    )

    try:
        resp = client.chat.completions.create(
            model=config.T2_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.T2_JUDGE_MAX_TOKENS,
            temperature=config.T2_TEMPERATURE,
        )
        verdict_text = (resp.choices[0].message.content or "").strip().upper()
        verdicts = [v.strip() for v in verdict_text.split(",")]
        hit = sum(1 for v in verdicts[:len(criteria_list)] if v.startswith("YES"))
        return hit / len(criteria_list)
    except Exception as e:
        logger.warning(f"LLM judge correctness batch failed: {e}")
        return 0.0


def _llm_judge_correctness(row: dict) -> float:
    """I use an LLM to judge correctness criteria with multi-vote (3 rounds).
    I run the judge 3 times and take the MEDIAN score to reduce variance.
    I batch ALL correctness criteria into ONE prompt per round (3 API calls total).
    I return a continuous score in [0, 1]."""
    client = _get_judge_client()
    if client is None:
        # No token: fall back to rubric coverage as approximation
        return 1.0 if _rubric_coverage_normalized(row) else 0.0

    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    structured = metadata.get("rubric_structured", [])
    if not structured:
        return 0.5  # No rubric: neutral, let T1 decide

    pred = str(row.get("final_answer", "")).strip()
    if not pred:
        return 0.0

    question = str(row.get("prompt", ""))
    correctness = [c for c in structured if c.get("operator") == "correctness"]

    if not correctness:
        return 0.5  # No correctness criteria: neutral

    criteria_list = [c.get("criteria", "").strip() for c in correctness
                     if c.get("criteria", "").strip()]
    if not criteria_list:
        return 0.0

    traj_summary = _format_trajectory_summary(row)

    # Multi-vote: run 3 times and take median
    n_votes = 3
    scores = []
    for _ in range(n_votes):
        s = _llm_judge_correctness_single(row, criteria_list, question, pred, traj_summary)
        scores.append(s)

    # Median: sort and pick middle
    scores.sort()
    median_score = scores[len(scores) // 2]
    return median_score


def _llm_judge_dealbreaker_single(row: dict, contra_list: list,
                                        pred: str) -> bool:
    """I run ONE dealbreaker check. Return True if any contradiction is YES."""
    client = _get_judge_client()
    if client is None:
        return False

    numbered_contra = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contra_list))

    prompt = (
        f"You are an expert financial fact-checker.\n"
        f"Does the answer CONTRADICT any statement below?\n"
        f"If the answer states something opposite to a statement, reply YES for that.\n"
        f"If the answer is silent or agrees, reply NO.\n"
        f"IMPORTANT: Ignore reasoning prefixes in the answer. Focus on factual claims.\n"
        f"Reply with ONLY a comma-separated list of YES/NO.\n\n"
        f"Answer: {pred[:2000]}\n\n"
        f"Statements (all must be true):\n{numbered_contra}\n\n"
        f"Contradiction verdicts (comma-separated YES/NO):"
    )

    try:
        resp = client.chat.completions.create(
            model=config.T2_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.T2_JUDGE_MAX_TOKENS,
            temperature=config.T2_TEMPERATURE,
        )
        contra_text = (resp.choices[0].message.content or "").strip().upper()
        contra_verdicts = [v.strip() for v in contra_text.split(",")]
        return any(v.startswith("YES") for v in contra_verdicts[:len(contra_list)])
    except Exception as e:
        logger.warning(f"LLM judge dealbreaker check failed: {e}")
        return False


def _llm_judge_dealbreaker(row: dict) -> bool:
    """I check if the answer contradicts any dealbreaker statement.
    I run 3 times and use majority vote (2/3) to reduce variance.
    If YES on any contradiction criterion (in majority of rounds), dealbreaker triggered.
    I return True if a dealbreaker is triggered (score should be 0)."""
    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    structured = metadata.get("rubric_structured", [])
    contradictions = [c for c in structured if c.get("operator") == "contradiction"]

    if not contradictions:
        return False

    pred = str(row.get("final_answer", "")).strip()
    if not pred:
        return False

    contra_list = [c.get("criteria", "").strip() for c in contradictions
                   if c.get("criteria", "").strip()]
    if not contra_list:
        return False

    # Multi-vote: run 3 times, majority (>=2) triggers dealbreaker
    n_votes = 3
    triggered_count = 0
    for _ in range(n_votes):
        if _llm_judge_dealbreaker_single(row, contra_list, pred):
            triggered_count += 1
    return triggered_count >= 2


def _score_t2_llm_semantic(row: dict) -> tuple:
    """I run the LLM semantic judge with dealbreaker check.
    I return (score: float, dealbreaker_triggered: bool).
    If dealbreaker triggers, score = 0.0."""
    # Step 1: Check dealbreakers (contradictions)
    dealbreaker = _llm_judge_dealbreaker(row)
    if dealbreaker:
        return (0.0, True)

    # Step 2: Score correctness criteria
    score = _llm_judge_correctness(row)
    return (score, False)


# ======================================================================
# Final score aggregation
# ======================================================================

def _score_logic_exact(row: dict) -> float:
    """I grade multiple-choice logic answers by exact option-letter match.
    I extract standalone A-E letters from the prediction and return 1.0 if the
    gold letter is present, else 0.0."""
    gold = str(row.get("gold_answer", "")).strip().upper()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0
    letters = re.findall(r"\b[A-E]\b", pred.upper())
    return 1.0 if gold in letters else 0.0


_UNICODE_MATH = {
    "\u03c0": "pi",     # π pi
    "\u2212": "-",       # -− minus sign
    "\u2013": "-",       # – en dash
    "\u2014": "-",       # — em dash
    "\u00d7": "*",       # × multiplication sign
    "\u22c5": "*",       # ⋅ dot operator
    "\u00b7": "*",       # · middle dot
    "\u221a": "\\sqrt",    # √ square root
}

_TEXT_ANSWER_RE = re.compile(r"\\text\s*\{([^}]*)\}")
_BOXED_RE = re.compile(r"\\boxed\s*\{([^{}]*)\}")
_MATH_NUM_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?")
_LETTER_TOKEN_RE = re.compile(r"\b[A-J]\b")


def _is_year_token(n: str) -> bool:
    """Treat 1900..2100 as years (likely incidental, not an answer) and skip them."""
    try:
        return 1900 < float(n) < 2100
    except ValueError:
        return False

def _norm_unicode_math(t: str) -> str:
    """I fold common Unicode math glyphs (pi, U+2212 minus, x, sqrt, ...) into their
    ASCII canonical forms so sympy parses them consistently with LaTeX gold answers."""
    for u, a in _UNICODE_MATH.items():
        t = t.replace(u, a)
    return t

_MATH_UNITS = [
    "inches", "inch", "degrees", "degree", "battalions", "battalion",
    "calories", "calorie", "dollars", "dollar", "cents", "feet", "foot",
    "units", "unit", "meters", "meter", "metres", "metre", "pounds", "pound",
    "minutes", "minute", "seconds", "second", "percent",
]


def _strip_math_noise(s: str) -> str:
    """Strip presentation noise (degree marks, units, currency, LaTeX padding) from a
    MATH-500 answer so equivalent numeric answers compare cleanly. Symmetric on gold
    and prediction; runs after the text-answer path has already been handled."""
    s = s.replace("^\\circ", " degrees ").replace("\\circ", " degrees ").replace("\u00b0", " degrees ")
    for u in _MATH_UNITS:
        s = re.sub(r"\b" + u + r"\b", " ", s, flags=re.IGNORECASE)
    s = s.replace("$", " ").replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\s*=\s*", "=", s)
    return " ".join(s.split())


def _extract_text_answer(t: str) -> str | None:
    """I return the inner text when `t` is a pure LaTeX \\text{...} answer (e.g.
    '\\text{Evelyn}'), else None. Pure-text answers are graded by string match."""
    m = _TEXT_ANSWER_RE.fullmatch(t.strip())
    return m.group(1).strip() if m else None


def _strip_outer_delims(s: str) -> str:
    """Strip one wrapping pair of parentheses (LaTeX left/right delimiters or plain)."""
    s = s.strip()
    for lo, hi in (("\\left(", "\\right)"), ("\\left[", "\\right]"), ("(", ")"), ("[", "]")):
        if s.startswith(lo) and s.endswith(hi):
            return s[len(lo):len(s) - len(hi)].strip()
    return s


def _split_top_level_commas(s: str) -> list[str]:
    """Split s on commas not nested inside ( ) / { } / [ ]; used to decompose
    coordinate-tuple answers like "(3, pi/2)" that sympy cannot parse."""
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in s:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur).strip())
    return parts


def _math_answer_candidates(pred: str) -> list[str]:
    """Extract deterministic final-answer candidates from a MATH-500 prediction.
    The ground-truth answer is conventionally emitted last — inside a \\boxed{...}, after
    a trailing '=', on the final line, or as the final numeric/letter token — with
    reasoning text preceding it. I return these candidates (deduplicated, order-preserved)
    so the answer can be rescued when the full-string sympy parse of the whole response
    fails. This is the deterministic T1b extraction layer (zero LLM)."""
    out: list[str] = []
    for m in _BOXED_RE.finditer(pred):
        out.append(m.group(1).strip())
    if "=" in pred:
        out.append(pred.rsplit("=", 1)[1].strip())
    lines = [l.strip() for l in pred.splitlines() if l.strip()]
    if lines:
        out.append(lines[-1])
    nums = [n for n in _MATH_NUM_TOKEN_RE.findall(pred) if not _is_year_token(n)]
    if nums:
        out.append(nums[-1])
    lets = _LETTER_TOKEN_RE.findall(pred)
    if lets:
        out.append(lets[-1].upper())
    seen: set[str] = set()
    res: list[str] = []
    for c in out:
        if c and c not in seen and len(c) <= 200:
            seen.add(c)
            res.append(c)
    return res


def _score_math500(row: dict) -> float:
    """I grade MATH-500 by symbolic equivalence. I parse the gold (LaTeX) answer and the
    prediction with sympy (parse_latex for LaTeX, sympify for plain expressions), then
    check simplify(gold - pred) == 0. I fall back to normalized string equality when
    either side does not parse. I return 1.0 if equivalent, else 0.0."""
    gold = str(row.get("gold_answer", "")).strip()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0

    gold = _norm_unicode_math(gold)
    pred = _norm_unicode_math(pred)

    try:
        import sympy
    except ImportError:
        return 1.0 if _normalize_answer(gold) == _normalize_answer(pred) else 0.0

    from sympy.parsing.latex import parse_latex

    g_text = _extract_text_answer(gold)
    if g_text is not None:
        p_text = _extract_text_answer(pred) or pred
        return 1.0 if _normalize_answer(g_text) == _normalize_answer(p_text) else 0.0

    gold = _strip_math_noise(gold)
    pred = _strip_math_noise(pred)
    if not gold or not pred:
        return 0.0

    def _parse(t: str):
        t = t.strip()
        while True:
            m = re.search(r"\\boxed\{([^{}]*)\}", t)
            if not m:
                break
            t = m.group(1)
        # Normalize unbraced radicals (e.g. \\sqrt2 -> \\sqrt{2}) for sympy parse_latex.
        t = re.sub(r"\\sqrt([0-9]+)", r"\\sqrt{\1}", t)
        if re.search(r"\\[a-zA-Z]+", t):
            try:
                return parse_latex(t)
            except Exception:
                return None
        # Plain expression: allow implicit multiplication (e.g. 5i -> 5*i) for complex answers.
        t = re.sub(r"(\d)i\b", lambda m: m.group(1) + "*i", t)
        try:
            return sympy.sympify(t)
        except Exception:
            return None

    consts = {sympy.Symbol("pi"): sympy.pi, sympy.Symbol("e"): sympy.E, sympy.Symbol("i"): sympy.I}

    def _sym_equiv(a: str, b: str) -> bool:
        ga = _parse(a)
        pb = _parse(b)
        if ga is None or pb is None:
            return _normalize_answer(a) == _normalize_answer(b)
        try:
            return sympy.simplify(ga.subs(consts) - pb.subs(consts)) == 0
        except Exception:
            return _normalize_answer(a) == _normalize_answer(b)

    if _sym_equiv(gold, pred):
        return 1.0

    if "," in gold:
        g_parts = _split_top_level_commas(_strip_outer_delims(gold))
        p_parts = _split_top_level_commas(_strip_outer_delims(pred))
        if len(g_parts) == len(p_parts) > 1 and all(_sym_equiv(a, b) for a, b in zip(g_parts, p_parts)):
            return 1.0

        # Order-insensitive numeric multiset: '-2, 1' vs '1,-2', or prose roots
        # 'The roots are $x = 3, 5, 7$.' vs '3, 5, 7'. Guarded to multi-value gold.
        g_nums = sorted(_extract_numbers(gold))
        p_nums = sorted(_extract_numbers(pred))
        if len(g_nums) > 1 and len(g_nums) == len(p_nums) and all(
                abs(a - b) <= config.SCORING_NUMERIC_TOL * max(abs(a), abs(b), 1e-12)
                for a, b in zip(g_nums, p_nums)):
            return 1.0

    # T1b: deterministic final-answer candidate extraction. Some predictions emit the
    # final answer buried after reasoning text (not boxed, not parseable as one
    # expression); grade each extracted candidate against gold to rescue extraction
    # false negatives (answers that are present but were missed by full-string parse).
    for cand in _math_answer_candidates(pred):
        cand = _strip_math_noise(_norm_unicode_math(cand))
        if not cand or cand == pred:
            continue
        if _sym_equiv(gold, cand):
            return 1.0

    return 0.0


def _extract_mcq_letter(pred: str, choices: str = "ABCD") -> str | None:
    """I extract the single option letter a prediction actually committed to, for MCQ
    benchmarks. I accept (1) a bare answer ('A', 'A.', '(A)', 'a'), (2) the letter right
    after an explicit answer cue ('answer is A', 'ANSWER: B'), and (3) a final line that is
    just an option letter. I deliberately do NOT upper-case the whole prediction before
    matching: doing so turned the English article 'a' into 'A' and let prose-only answers
    match gold='A' by luck (gpqa_009/gpqa_016, smoke-20 2026-10-08). I return None when no
    option letter is committed to, so such answers score wrong instead of matching a stray
    letter. `choices` restricts the accepted letters (e.g. 'ABCD' for GPQA, A-Z for BBH). I also
accept a committed letter that carries a short label ('(B) heptagon', 'B. heptagon'),
requiring a bracket/punctuation separator so the bare article 'a'/'A' cannot match."""
    p = pred.strip()
    # Markdown emphasis/backticks wrapping a lone committed letter ('**B**', '*b*',
    # '`C`') hide it from the patterns below and produced GPQA false negatives
    # (gpqa_001 '**B**' labelled complete_failure on 2026-10-08). Unwrap an emphasised
    # single letter, then drop stray asterisks/backticks; identifiers such as '__init__'
    # or 'snake_case' are left intact because they are not a lone letter.
    p = re.sub(r"(?<![A-Za-z0-9])_{1,2}([A-Za-z])_{1,2}(?![A-Za-z0-9])", r"\1", p)
    p = re.sub(r"[*`]", "", p)
    bare = r"[\s\(\[]*([A-Za-z])[\s\)\]]*[\.\:]?"
    m = re.fullmatch(bare, p)
    if m and m.group(1).upper() in choices:
        return m.group(1).upper()
    m = re.search(r"(?:answer|choice|option|ans)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*\(?([A-Za-z])\)?(?![A-Za-z])",
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


def _score_mmlu_pro(row: dict) -> float:
    """I grade MMLU-Pro 10-option MCQ by exact option-letter (A-J) match."""
    gold = str(row.get("gold_answer", "")).strip().upper()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0
    letters = re.findall(r"\b[A-J]\b", pred.upper())
    return 1.0 if gold in letters else 0.0


def _score_gpqa(row: dict) -> float:
    """I grade GPQA-Diamond 4-option MCQ by exact option-letter (A-D) match. I require the
    prediction to actually commit to an option letter (see _extract_mcq_letter) instead of
    scanning the whole text, so prose answers that merely contain an 'a'/'A' no longer score
    by luck (gpqa_009/gpqa_016, smoke-20 2026-10-08)."""
    gold = str(row.get("gold_answer", "")).strip().upper()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0
    return 1.0 if _extract_mcq_letter(pred, choices="ABCD") == gold else 0.0


def _extract_committed_integer(pred: str) -> int | None:
    """I extract the single integer a prediction commits to as its AIME answer,
    mirroring _extract_mcq_letter's 'commit, don't scan' rule for integer answers.
    Order: \boxed{...} -> whole string is a bare integer -> integer right after an
    answer cue -> last line is a bare integer -> integer after the last '='. I return
    None when no integer is committed to, so a CoT blob that
    merely mentions the gold integer mid-derivation scores wrong instead of matching by
    luck (same false-positive class as the GPQA whole-text scan, fixed 2026-10-08)."""
    p = pred.strip()
    if not p:
        return None

    def _first_int(s: str) -> int | None:
        m = re.search(r"-?\d+", s)
        return int(m.group(0)) if m else None

    def _last_int(s: str) -> int | None:
        t = re.findall(r"-?\d+", s)
        return int(t[-1]) if t else None

    bare = r"[\s\(\[\{]*\$?\s*(-?\d+)\s*\$?[\s\)\]\}\.,]*"

    m = _BOXED_RE.search(p)
    if m:
        v = _first_int(m.group(1))
        if v is not None:
            return v

    m = re.fullmatch(bare, p)
    if m:
        return int(m.group(1))

    m = re.search(
        r"(?:answer|ans|result|value)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*\$?\(?(-?\d+)\)?(?!\d)(?!\.\d)",
        p, re.IGNORECASE)
    if m:
        return int(m.group(1))

    lines = [l.strip() for l in p.splitlines() if l.strip()]
    if lines:
        m = re.fullmatch(bare, lines[-1])
        if m:
            return int(m.group(1))
        if "=" in lines[-1]:
            v = _last_int(lines[-1].rsplit("=", 1)[1])
            if v is not None:
                return v

    if "=" in p:
        v = _last_int(p.rsplit("=", 1)[1])
        if v is not None:
            return v

    return None


def _extract_committed_number(pred: str) -> float | None:
    """I extract the single number a prediction commits to as its final answer, the
    real-valued sibling of _extract_committed_integer under the same 'commit, don't scan'
    rule. Order: \boxed{...} -> whole string is a bare number -> number right after an
    answer cue -> last line is a bare number -> number after the last '='. I return None
    when no number is committed to, so a reasoning chain that merely passes through the
    gold value mid-derivation (or whose *first* number is a sub-result) no longer scores
    by luck. Used by BBH numeric targets (object_counting / multistep_arithmetic_two)."""
    p = pred.strip()
    if not p:
        return None

    num = r"-?\d+(?:\.\d+)?"

    def _first_num(s: str) -> float | None:
        m = re.search(num, s)
        return float(m.group(0)) if m else None

    def _last_num(s: str) -> float | None:
        t = re.findall(num, s)
        return float(t[-1]) if t else None

    bare = r"[\s\(\[\{]*\$?\s*(-?\d+(?:\.\d+)?)\s*\$?[\s\)\]\}\.,]*"

    m = _BOXED_RE.search(p)
    if m:
        v = _first_num(m.group(1))
        if v is not None:
            return v

    m = re.fullmatch(bare, p)
    if m:
        return float(m.group(1))

    m = re.search(
        r"(?:answer|ans|result|value)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*\$?\(?(-?\d+(?:\.\d+)?)\)?(?!\d)(?!\.\d)",
        p, re.IGNORECASE)
    if m:
        return float(m.group(1))

    lines = [l.strip() for l in p.splitlines() if l.strip()]
    if lines:
        m = re.fullmatch(bare, lines[-1])
        if m:
            return float(m.group(1))
        if "=" in lines[-1]:
            v = _last_num(lines[-1].rsplit("=", 1)[1])
            if v is not None:
                return v

    if "=" in p:
        v = _last_num(p.rsplit("=", 1)[1])
        if v is not None:
            return v

    return None


def _extract_committed_text(pred: str, choices) -> str | None:
    """I extract the single closed-set word a prediction commits to (e.g. Yes/No/True/
    False), the text sibling of _extract_committed_integer under 'commit, don't scan'. I
    accept (1) a bare word, (2) the word right after an explicit answer cue, (3) a final
    line that is just the word. I deliberately do NOT substring-match inside prose: that
    turned gold='No' into a hit on "I don't know" (which contains "no") and gold='Yes'
    into a hit on "Yesterday" (which contains "yes"). I return None when no allowed word
    is committed to, so such prose answers score wrong instead of matching by luck. Used
    by BBH word targets (boolean_expressions / navigate / web_of_lies)."""
    p = pred.strip()
    if not p:
        return None
    low = {str(c).lower() for c in choices}

    def _norm_token(t: str) -> str | None:
        t = t.strip().strip(" \t\r\n\"'`*_().[]").rstrip(".!?,;:").strip().lower()
        return t if t in low else None

    tok = _norm_token(p)
    if tok:
        return tok

    m = re.search(
        r"(?:answer|choice|option|ans|result)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*([A-Za-z]+)",
        p, re.IGNORECASE)
    if m:
        tok = _norm_token(m.group(1))
        if tok:
            return tok

    lines = [l.strip() for l in p.splitlines() if l.strip()]
    if lines:
        tok = _norm_token(lines[-1])
        if tok:
            return tok

    return None


def _score_aime(row: dict) -> float:
    """I grade AIME integer-answer (0-999) by exact match on the integer the model
    actually committed to (see _extract_committed_integer), NOT by scanning the whole
    text for the gold integer: a reasoning blob that merely passes through the gold
    value scores wrong, closing the false-positive channel fixed for GPQA 2026-10-08."""
    gold_raw = str(row.get("gold_answer", "")).strip()
    pred_raw = str(row.get("final_answer", "")).strip()
    if not gold_raw or not pred_raw:
        return 0.0
    g_nums = _extract_all_numbers(gold_raw)
    if not g_nums:
        return 0.0
    gold = int(round(g_nums[0]))
    pred_int = _extract_committed_integer(pred_raw)
    return 1.0 if pred_int is not None and pred_int == gold else 0.0


def _score_bbh(row: dict) -> float:
    """I grade BIG-Bench Hard answers. In the sampled tasks the target is always one of
    three forms: an '(X)' option letter, an integer, or a closed-set word
    (Yes/No/True/False). I grade each with the matching 'commit, don't scan' extractor
    (_extract_mcq_letter / _extract_committed_number / _extract_committed_text) instead of
    scanning the whole text, so an answer that merely contains the gold value as a
    substring (e.g. gold='No' inside "I don't know") or passes through it mid-derivation
    no longer scores by luck (fixed 2026-10-08, same channel as the GPQA/AIME fixes)."""
    gold = str(row.get("gold_answer", "")).strip()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0

    letter = re.fullmatch(r"\(?([A-Za-z])\)?", gold)
    if letter:
        want = letter.group(1).upper()
        got = _extract_mcq_letter(pred, choices="ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return 1.0 if got == want else 0.0

    if re.fullmatch(r"-?\d+(\.\d+)?", gold):
        g_nums = _extract_all_numbers(gold)
        if not g_nums:
            return 0.0
        pred_num = _extract_committed_number(pred)
        return 1.0 if pred_num is not None and abs(g_nums[0] - pred_num) < 1e-6 else 0.0

    got = _extract_committed_text(pred, choices={"yes", "no", "true", "false"})
    return 1.0 if got is not None and got == gold.strip().lower() else 0.0


def _norm_math_expr(s: str) -> str:
    """I normalise a maths-expression string so notationally-equivalent forms compare
    equal: caret power ``x^3`` -> ``x**3``, implicit multiplication ``3x**2`` -> ``3*x**2``,
    and remove all whitespace. Used by BFCL function-string arguments, which the model and
    the ground truth may spell differently (``x^3`` vs ``x**3``, ``2x**2`` vs ``2*x**2``)."""
    s = str(s)
    s = s.replace("^", "**")
    s = re.sub(r"(\d)([a-zA-Z(])", r"\1*\2", s)
    s = re.sub(r"\s+", "", s)
    return s


def _bfcl_val_equal(a, b) -> bool:
    """I compare one BFCL accepted value `a` against a predicted value `b`, tolerant to
    (i) list-typed values compared element-wise (so ``[1, 3]`` == ``[1.0, 3.0]``),
    (ii) numeric values compared with a tight relative tolerance (so ``0`` == ``0.0``), and
    (iii) maths-expression strings compared after ``_norm_math_expr``. An empty-string
    accepted value remains the wildcard for an absent optional argument."""
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_bfcl_val_equal(x, y) for x, y in zip(a, b))
    if (isinstance(a, (int, float)) and isinstance(b, (int, float))
            and not isinstance(a, bool) and not isinstance(b, bool)):
        return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1.0)
    sa, sb = str(a).strip(), str(b).strip()
    if _norm_math_expr(sa) == _norm_math_expr(sb):
        return True
    try:
        fa, fb = float(sa), float(sb)
        return abs(fa - fb) <= 1e-9 * max(abs(fa), abs(fb), 1.0)
    except (ValueError, TypeError):
        return False


def _score_bfcl(row: dict) -> float:
    """I grade BFCL by AST comparison: the predicted {name, arguments} must match the
    function name in ground truth, and every ground-truth parameter must take a value
    present in that parameter accepted-value list. Extra predicted parameters are
    ignored; values are compared with tolerance for maths-notation and numeric formatting
    (absent == "" wildcard). 1.0 on full match else 0.0."""
    pred_raw = str(row.get("final_answer", "")).strip()
    if not pred_raw:
        return 0.0

    gold_raw = row.get("gold_answer", "")
    if isinstance(gold_raw, str):
        try:
            gt = json.loads(gold_raw)
        except (json.JSONDecodeError, TypeError):
            gt = []
    else:
        gt = gold_raw
    if not gt:
        return 0.0

    try:
        pred = json.loads(pred_raw)
    except (json.JSONDecodeError, TypeError):
        return 0.0
    if not isinstance(pred, dict):
        return 0.0

    name = str(pred.get("name", "")).replace(".", "_")
    args_raw = pred.get("arguments", "{}")
    if isinstance(args_raw, str):
        try:
            args = json.loads(args_raw)
        except (json.JSONDecodeError, TypeError):
            args = {}
    else:
        args = args_raw
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
        return 0.0
    if not isinstance(entry, dict) or not entry:
        return 1.0

    for param, accepted in entry.items():
        accepted_list = accepted if isinstance(accepted, list) else [accepted]
        pred_val = args.get(param, "")
        if not any(_bfcl_val_equal(pred_val, a) for a in accepted_list):
            return 0.0
    return 1.0


def _label_row_tiered(row: dict) -> dict:
    """I run T1 (numeric) and T2 (LLM semantic) and aggregate the final score.
    For pure-reasoning domains (metadata.benchmark = math / logic) I use a single
    rule-based grader instead of the financial T2 judge, since those tasks carry no
    financial rubric. Finance keeps final_score = max(T1, T2); dealbreaker forces 0."""
    # API failure override (uniform across domains): exclude from accuracy denominator
    if row.get("api_failure", False):
        return {
            "tier1_numeric": 0.0,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": 0.0,
            "is_correct": False,
            "error_type": "api_failure",
        }

    metadata = row.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    benchmark = metadata.get("benchmark", "")

    if benchmark == "math":
        t1 = _score_t1_numeric(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "numeric_error",
        }
    if benchmark == "logic":
        t1 = _score_logic_exact(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "complete_failure",
        }

    if benchmark == "math500":
        t1 = _score_math500(row)
        tier = "T1"
        t2 = 0.0
        if t1 < config.FINAL_PASS_THRESHOLD and config.T2_RESCUE_ENABLED:
            t2 = _score_t2_extract_judge(row)
            if t2 >= config.FINAL_PASS_THRESHOLD:
                tier = "T2"
        final = max(t1, t2)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": t2,
            "dealbreaker_triggered": False,
            "final_score": final,
            "is_correct": final >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if final >= config.FINAL_PASS_THRESHOLD else "numeric_error",
            "eval_tier": tier,
        }
    if benchmark == "mmlu_pro":
        t1 = _score_mmlu_pro(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "complete_failure",
        }
    if benchmark == "bfcl":
        t1 = _score_bfcl(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "complete_failure",
        }
    if benchmark == "aime":
        t1 = _score_aime(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "numeric_error",
        }
    if benchmark == "gpqa":
        t1 = _score_gpqa(row)
        correct = t1 >= config.FINAL_PASS_THRESHOLD
        if correct:
            err = "correct"
        else:
            # Distinguish a committed-but-wrong option letter from "no commit at all",
            # so the error distribution does not lump wrong picks into complete_failure.
            committed = _extract_mcq_letter(str(row.get("final_answer", "")), choices="ABCD")
            err = "wrong_option" if committed is not None else "complete_failure"
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": correct,
            "error_type": err,
        }
    if benchmark == "bbh":
        t1 = _score_bbh(row)
        return {
            "tier1_numeric": t1,
            "tier2_llm_semantic": 0.0,
            "dealbreaker_triggered": False,
            "final_score": t1,
            "is_correct": t1 >= config.FINAL_PASS_THRESHOLD,
            "error_type": "correct" if t1 >= config.FINAL_PASS_THRESHOLD else "complete_failure",
        }

    t1_score = _score_t1_numeric(row)
    t2_score, dealbreaker = _score_t2_llm_semantic(row)

    # Dealbreaker override: if T2 detected a contradiction, force 0
    if dealbreaker:
        final_score = 0.0
        error_type = "factual_contradiction"
    else:
        final_score = max(t1_score, t2_score)
        if final_score >= config.FINAL_PASS_THRESHOLD:
            error_type = "correct"
        elif t1_score == 0 and t2_score == 0:
            error_type = "complete_failure"
        elif t1_score > 0 and t1_score < config.FINAL_PASS_THRESHOLD:
            error_type = "numeric_error"
        else:
            error_type = "qualitative_incomplete"

    return {
        "tier1_numeric": t1_score,
        "tier2_llm_semantic": t2_score,
        "dealbreaker_triggered": dealbreaker,
        "final_score": final_score,
        "is_correct": final_score >= config.FINAL_PASS_THRESHOLD,
        "error_type": error_type,
        "eval_tier": "T3" if (dealbreaker or t2_score > t1_score) else "T1",
    }


def _score_one_row(r: dict) -> dict:
    """I label a single row (T1 + T2 + final aggregation) and attach scores in place.
    I never raise: on any failure I log and fall back to 'qualitative_incomplete' so
    one bad row never aborts the whole scoring pass."""
    try:
        tiered = _label_row_tiered(r)
        r["tier1_numeric"] = round(tiered["tier1_numeric"], 4)
        r["tier2_llm_semantic"] = round(tiered["tier2_llm_semantic"], 4)
        r["dealbreaker_triggered"] = tiered["dealbreaker_triggered"]
        r["eval_tier"] = tiered.get("eval_tier", "T1")
        r["final_score"] = round(tiered["final_score"], 4)
        r["is_correct"] = tiered["is_correct"]
        r["error_type"] = tiered["error_type"]
    except Exception as e:
        logger.warning(f"Scoring failed for {r.get('task_id', '?')}: {e}")
        r["error_type"] = "qualitative_incomplete"
        r["is_correct"] = False
        r["tier1_numeric"] = 0.0
        r["tier2_llm_semantic"] = 0.0
        r["dealbreaker_triggered"] = False
        r["final_score"] = 0.0
    return r


# ======================================================================
# Evaluator class (merged Analysis + evaluate)
# ======================================================================

class Evaluator:
    """I unify scoring and analysis into one class.
    I read trajectories.jsonl, label each row, write results.csv + error_report.json,
    then provide stats and visualization."""

    def __init__(self, output_dir=OUTPUT_DIR,
                 numeric_tol=None,
                 rubric_threshold=None):
        self.output_dir = Path(output_dir)
        self.numeric_tol = numeric_tol or config.SCORING_NUMERIC_TOL
        self.rubric_threshold = rubric_threshold or config.SCORING_RUBRIC_COVERAGE
        self.results = None   # list[dict] of scored rows

    # ---- Scoring ----
    def score(self, traj_path=None) -> dict:
        """I read trajectories.jsonl, label each row, and write results.csv + error_report.json.
        Every row is wrapped in try/except: on any failure I log a warning and label
        the row 'qualitative_incomplete' so a single bad row never aborts the whole run."""
        if traj_path is None:
            traj_path = self.output_dir / "trajectories.jsonl"
        traj_path = Path(traj_path)

        rows = []
        with traj_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))

        concurrency = max(1, config.RUNNER_CONCURRENCY)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
            scored = list(ex.map(_score_one_row, rows))

        self.results = scored

        # Write results.csv
        out_csv = self.output_dir / "results.csv"
        fields = ["run_id", "task_id", "category", "difficulty", "gold_answer",
                  "final_answer", "is_correct", "error_type",
                  "tier1_numeric", "tier2_llm_semantic", "dealbreaker_triggered",
                  "eval_tier", "final_score",
                  "tool_calls", "total_latency_ms", "model_name"]
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(scored)

        # Build report
        n = len(scored)
        # Separate API failures from valid tasks
        n_api_failures = sum(1 for r in scored if r.get("error_type") == "api_failure")
        n_valid = n - n_api_failures
        correct = sum(1 for r in scored if r.get("is_correct"))
        errors = Counter(r.get("error_type", "unknown") for r in scored)
        avg_latency = (sum(r.get("total_latency_ms", 0) for r in scored) / n) if n else 0
        total_cost = sum(r.get("total_cost_usd", 0) for r in scored)

        # Tier breakdown (diagnostic: continuous scores) — exclude api_failures
        valid_scored = [r for r in scored if r.get("error_type") != "api_failure"]
        vn = len(valid_scored) if valid_scored else 1
        t1_avg = sum(r.get("tier1_numeric", 0) for r in valid_scored) / vn
        t2_avg = sum(r.get("tier2_llm_semantic", 0) for r in valid_scored) / vn
        final_avg = sum(r.get("final_score", 0) for r in valid_scored) / vn
        dealbreakers = sum(1 for r in valid_scored if r.get("dealbreaker_triggered"))

        report = {
            "n_tasks": n,
            "n_valid_tasks": n_valid,
            "n_api_failures": n_api_failures,
            "accuracy": correct / n if n else 0,
            "accuracy_excl_api_failures": correct / n_valid if n_valid else 0,
            "error_distribution": dict(errors),
            "avg_latency_ms": round(avg_latency, 1),
            "total_cost_usd": round(total_cost, 4),
            "tier_breakdown": {
                "t1_numeric_avg": round(t1_avg, 4),
                "t2_llm_semantic_avg": round(t2_avg, 4),
                "final_score_avg": round(final_avg, 4),
                "dealbreakers_triggered": dealbreakers,
            },
        }

        print("\n=== Evaluation Report (v2.0 — continuous scoring) ===")
        print(f"Accuracy: {correct}/{n} = {report['accuracy']:.2%} (threshold={config.FINAL_PASS_THRESHOLD})")
        if n_api_failures > 0:
            print(f"Accuracy (excl. {n_api_failures} API failures): {correct}/{n_valid} = {report['accuracy_excl_api_failures']:.2%}")
        print(f"Avg scores: T1(numeric)={t1_avg:.3f}  T2(LLM-semantic)={t2_avg:.3f}  Final={final_avg:.3f}")
        print(f"Dealbreakers triggered: {dealbreakers}/{n}")
        print("Error distribution:", dict(errors))
        print(f"Avg latency: {report['avg_latency_ms']} ms  |  Total cost: ${report['total_cost_usd']}")
        print(f"Detailed results: {out_csv}")

        report_path = self.output_dir / "error_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report

    # ---- Analysis (formerly Analysis class) ----
    def analyze(self) -> dict:
        """I load results.csv (the scored file — single source of truth),
        then run basic_stats + error_distribution + plot_accuracy_by.
        matplotlib is lazily imported so basic_stats works without it."""
        if self.results is None:
            self._load_results()

        stats = self.basic_stats()
        err_dist = self.error_distribution()
        return {"basic_stats": stats, "error_distribution": err_dist}

    def _load_results(self):
        """I load results.csv into self.results (list of dicts)."""
        results_csv = self.output_dir / "results.csv"
        if not results_csv.exists():
            print("[warn] No results.csv found. Run score() first.")
            self.results = []
            return

        with results_csv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.results = list(reader)


    def _is_correct(self, row) -> bool:
        """I normalize is_correct from bool, string, or int to a proper bool."""
        val = row.get("is_correct", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        return str(val).strip().lower() in ("true", "1", "yes")

    def basic_stats(self) -> dict:
        """I compute accuracy by category and difficulty."""
        if self.results is None:
            self._load_results()

        n = len(self.results)
        n_api = sum(1 for r in self.results if r.get("error_type") == "api_failure")
        n_valid = n - n_api
        correct = sum(1 for r in self.results if self._is_correct(r))
        accuracy = correct / n if n else 0.0
        accuracy_valid = correct / n_valid if n_valid else 0.0

        print("\n=== Basic Stats ===")
        print(f"Total tasks : {n} (excl. {n_api} API failures: {n_valid} valid)")
        print(f"Correct     : {correct}")
        print(f"Accuracy    : {accuracy:.2%} (all tasks)")
        if n_api > 0:
            print(f"Accuracy    : {accuracy_valid:.2%} (excl. API failures)")

        # By category
        cats = {}
        for r in self.results:
            cat = r.get("category", "Unknown")
            cats.setdefault(cat, {"total": 0, "correct": 0})
            cats[cat]["total"] += 1
            if self._is_correct(r):
                cats[cat]["correct"] += 1

        if cats:
            print("\n--- By Category ---")
            for cat, vals in sorted(cats.items()):
                acc = vals["correct"] / vals["total"] if vals["total"] else 0
                print(f"  {cat:<30} {vals['correct']}/{vals['total']} = {acc:.2%}")

        # By difficulty
        diffs = {}
        for r in self.results:
            d = r.get("difficulty", "Unknown")
            diffs.setdefault(d, {"total": 0, "correct": 0})
            diffs[d]["total"] += 1
            if self._is_correct(r):
                diffs[d]["correct"] += 1

        if diffs:
            print("\n--- By Difficulty ---")
            for d, vals in sorted(diffs.items()):
                acc = vals["correct"] / vals["total"] if vals["total"] else 0
                print(f"  {d:<10} {vals['correct']}/{vals['total']} = {acc:.2%}")

        return {"accuracy": accuracy, "n": n, "correct": correct,
                "by_category": cats, "by_difficulty": diffs}

    def error_distribution(self) -> dict:
        """I compute error type distribution."""
        if self.results is None:
            self._load_results()

        errors = Counter(r.get("error_type", "unknown") for r in self.results
                         if not self._is_correct(r))

        print("\n=== Error Distribution ===")
        total_wrong = sum(errors.values())
        total = len(self.results)
        print(f"Total errors: {total_wrong} / {total}")
        for etype, count in errors.most_common():
            print(f"  {etype:<25} {count}")
        return dict(errors)

    def plot_accuracy_by(self, column, save=True, show=False):
        """I plot accuracy grouped by a column. matplotlib is lazily imported."""
        if self.results is None:
            self._load_results()

        groups = {}
        for r in self.results:
            val = r.get(column, "Unknown")
            groups.setdefault(val, {"total": 0, "correct": 0})
            groups[val]["total"] += 1
            if self._is_correct(r):
                groups[val]["correct"] += 1

        if not groups:
            print(f"[skip] No data for column {column}")
            return

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = sorted(groups.keys())
        accs = [groups[l]["correct"] / groups[l]["total"] if groups[l]["total"] else 0
                for l in labels]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(range(len(labels)), accs)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(f"Accuracy by {column}")
        ax.set_ylabel("Accuracy")
        ax.set_ylim(0, 1.05)
        plt.tight_layout()

        if save:
            path = self.output_dir / f"accuracy_by_{column}.png"
            fig.savefig(path)
            print(f"saved: {path}")
        if show:
            plt.show()
        else:
            plt.close(fig)


# ======================================================================
# Backward-compatible module-level entry point
# ======================================================================

def evaluate(traj_path=None) -> dict:
    """I keep the old scorer.evaluate() CLI contract. I create an Evaluator and run score()."""
    if traj_path is None:
        traj_path = OUTPUT_DIR / "trajectories.jsonl"
    return Evaluator().score(traj_path)


if __name__ == "__main__":
    ev = Evaluator()
    ev.score()
    ev.analyze()


def _score_t2_extract_judge(row: dict) -> float:
    # T2 (registered intervention): LLM-assisted parse + judge. For answers buried in
    # reasoning text that deterministic extraction (T1) cannot recover, ask the judge to
    # read the full response, extract the FINAL answer, and compare it against the KNOWN
    # gold for mathematical equivalence. Returns 1.0 (correct) or 0.0 (incorrect).
    # Only invoked for rows T1 already judged wrong (rescue) and only when enabled.
    client = _get_judge_client()
    if client is None:
        return 0.0
    question = str(row.get("prompt", "")).strip()
    gold = str(row.get("gold_answer", "")).strip()
    pred = str(row.get("final_answer", "")).strip()
    if not gold or not pred:
        return 0.0
    prompt = (
        "You are an expert math evaluator.\n"
        "Read the model's full response below (it may contain reasoning text).\n"
        "Extract the model's FINAL answer to the question, then judge whether that final\n"
        "answer is mathematically equivalent to the REFERENCE answer.\n"
        "Ignore any intermediate working - only the final answer matters.\n"
        "Reply with ONLY one word: CORRECT or INCORRECT.\n\n"
        f"Question: {question}\n\n"
        f"Model response:\n{pred[:4000]}\n\n"
        f"Reference answer: {gold}\n\n"
        "Verdict (CORRECT / INCORRECT):"
    )
    try:
        resp = client.chat.completions.create(
            model=config.T2_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.T2_RESCUE_MAX_TOKENS,
            temperature=config.T2_TEMPERATURE,
        )
        text = (resp.choices[0].message.content or "").strip().upper()
        return 1.0 if text.startswith("CORRECT") else 0.0
    except Exception as e:
        logger.warning(f"T2 extract-judge failed: {e}")
        return 0.0

