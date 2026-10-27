"""HLE scorer (scorer_LLM_rescue): T1 match + T2 LLM rescue + T3 human review.

scorer_LLM_rescue protocol (also used by the FAB benchmark): the judge never reads
the model's CoT and never overturns a correct T1 verdict. It re-reads only the
model's COMMITTED FINAL ANSWER on rows T1 already marked wrong, rescuing the
"answer present but the extractor failed" false-negative case (equivalence the
deterministic matcher missed):

    correct = T1_correct                  (deterministic, primary, token-free)
    correct = LLM_judge(final_answer)     (only when T1 said wrong; one-way FN rescue)
    correct = T3_human_review             (manual re-check of contested rows)

T1 dispatches on HLE's answer_type + shape:
  - multipleChoice        : exact option-letter match
  - exactMatch / int      : strict numeric equality (pure-number guard)
  - exactMatch / symbol   : normalized-string equality
  - exactMatch / word/text: strict normalized-string equality (no token overlap)
"""
from __future__ import annotations

import re
import threading
from decimal import Decimal, InvalidOperation

from src import config


# ======================================================================
# T1: deterministic final-answer extraction + exact match
# ======================================================================

_ANSWER_MARKER = re.compile(r"(?:^|\n)\s*(?:answer|ANSWER|Answer)\s*[:=]\s*(.+)")
_BOXED_RE = re.compile(r"\\boxed\s*\{([^{}]*)\}")
_LETTER_RE = re.compile(r"\b([A-F])\b")


def extract_final_answer(response: str) -> str:
    """Extract the model's FINAL answer from a full (CoT-containing) response.

    Preference: an explicit ``Answer:`` marker, then the last ``\\boxed{}``, then
    the last non-empty line. Deliberately shallow -- the T2 judge exists exactly
    because this extraction can miss answers buried in reasoning text.
    """
    if not response:
        return ""
    m = _ANSWER_MARKER.search(response)
    if m:
        return m.group(1).strip()
    boxes = _BOXED_RE.findall(response)
    if boxes:
        return boxes[-1].strip()
    lines = [ln.strip() for ln in response.strip().split("\n") if ln.strip()]
    return lines[-1] if lines else response.strip()


def _norm(s: str) -> str:
    """Light answer normalization: lowercase, strip cash/grouping symbols and commas,
    collapse whitespace, fold unicode minus."""
    if s is None:
        return ""
    s = s.lower().replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace(",", " ").replace("$", "").replace("%", "").replace("(", " ").replace(")", " ")
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _score_mc(gold: str, final: str) -> bool:
    m = _LETTER_RE.search(final)
    return bool(m) and m.group(1).upper() == str(gold).strip().upper()


_NUM_STR_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def _score_int(gold: str, final: str) -> bool:
    # strict numeric equality (exact-match): both sides must be pure numeric,
    # else T1 defers to the T2 judge. fix: old stripped every non-digit so
    # "$ aleph_0 $" matched an integer gold of "0" (hle_026).
    g = _norm(str(gold)).replace(" ", "")
    f = _norm(final).replace(" ", "")
    if not _NUM_STR_RE.match(g) or not _NUM_STR_RE.match(f):
        return False
    try:
        return Decimal(g) == Decimal(f)
    except InvalidOperation:
        return False


_LATEX_WRAP = re.compile(r"^\\\((.+)\\\)$")


def _score_symbol(gold: str, final: str) -> bool:
    """Symbol answers are heterogeneous (LaTeX, lambda calculus, chemistry names),
    so T1 uses exact normalized-equality only; equivalence variants go to T2."""
    g = str(gold).strip()
    f = final.strip()
    if not g or not f:
        return False
    m = _LATEX_WRAP.match(g)
    if m:
        g = m.group(1).strip()
    m = _LATEX_WRAP.match(f)
    if m:
        f = m.group(1).strip()
    return _norm(g) == _norm(f)


def _score_word_text(gold: str, final: str) -> bool:
    # strict normalized equality for word/text (exact-match). fix: old containment
    # (g in f) and token-overlap made prefixes (hle_013) and re-ordered comma
    # sequences (hle_031) false positives. equivalent variants -> T2 judge.
    g = _norm(gold)
    f = _norm(final)
    if not g or not f:
        return False
    return g == f


def score_t1(gold: str, answer_type: str, shape: str, response: str) -> bool:
    """Deterministic correctness. Returns True only on a confident exact match."""
    final = extract_final_answer(response)
    if answer_type == "multipleChoice":
        return _score_mc(gold, final)
    if shape == "int":
        return _score_int(gold, final)
    if shape == "symbol":
        return _score_symbol(gold, final)
    return _score_word_text(gold, final)


# ======================================================================
# T2: LLM judge — one-way FN rescue (no CoT; never overturns a correct T1)
# ======================================================================

_judge_client = None
_judge_client_lock = threading.Lock()


def _get_judge_client():
    global _judge_client
    if _judge_client is not None:
        return _judge_client
    with _judge_client_lock:
        if _judge_client is None:
            token = config.T2_JUDGE_API_KEY
            if not token:
                return None
            from openai import OpenAI
            _judge_client = OpenAI(
                base_url=config.T2_JUDGE_BASE_URL,
                api_key=token,
            )
        return _judge_client


JUDGE_PROMPT = (
    "You are an expert evaluator.\n"
    "You are given a model's FINAL answer to a question, and a REFERENCE answer.\n"
    "Judge whether the model's final answer is CORRECT, i.e. equivalent to the\n"
    "reference answer (allow equivalent formatting, units, simplification, and a\n"
    "small margin of error for numerical answers). Do NOT consider any reasoning;\n"
    "only the final answer matters.\n"
    "Reply with ONLY one word: CORRECT or INCORRECT.\n\n"
    "Question: {question}\n\n"
    "Model final answer: {response}\n\n"
    "Reference answer: {gold}\n\n"
    "Verdict (CORRECT / INCORRECT):"
)


_judge_cache: dict = {}
_judge_cache_lock = threading.Lock()


def llm_judge(question: str, gold: str, response: str) -> bool | None:
    """Judge whether the model's FINAL answer (not its CoT) is equivalent to gold.
    Returns True/False, or None when no judge is available (no token, or the call
    failed). None means the rescue is unavailable, so the caller keeps T1's verdict.
    Thread-safe: one shared client + a memo cache keyed on (question, gold, response)."""
    client = _get_judge_client()
    if client is None:
        return None
    if not response or not gold:
        return None
    key = (question, gold, response[:4000])
    with _judge_cache_lock:
        if key in _judge_cache:
            return _judge_cache[key]
    prompt = JUDGE_PROMPT.format(
        question=question, response=response[:4000], gold=gold
    )
    try:
        resp = client.chat.completions.create(
            model=config.T2_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.T2_RESCUE_MAX_TOKENS,
            temperature=config.T2_TEMPERATURE,
        )
        text = (resp.choices[0].message.content or "").strip().upper()
        result = text.startswith("CORRECT")
    except Exception:
        result = None
    with _judge_cache_lock:
        _judge_cache[key] = result
    return result


def score_hle(question: str, gold: str, answer_type: str, shape: str,
              response: str) -> dict:
    """Score one HLE response: T1 exact-match, T2 LLM judge as one-way FN rescue.

    scorer_LLM_rescue (max(T1, T2); judge reads only the committed final answer, no
    CoT; contested rows go to T3 human review):
      - If T1 says correct, the verdict is correct and the judge is NOT called
        (the judge never overturns a correct T1).
      - If T1 says wrong, the judge re-reads the extracted final answer and may
        rescue the row (equivalence the deterministic matcher missed).

    Fields:
      correct       : final verdict (T1, then judge rescue on T1-missed only)
      t1_correct    : deterministic exact-match (the primary, token-free metric)
      judge_correct : LLM verdict (None when judge not called or unavailable)
      agreement     : True when T1 and judge agree; None when judge not called
      disagreement  : "FN" when T1 missed but the judge rescued; else None
    """
    t1 = score_t1(gold, answer_type, shape, response)
    if t1:
        return {
            "correct": True,
            "t1_correct": True,
            "judge_correct": None,
            "agreement": None,
            "disagreement": None,
        }
    # T1 missed -> T2 rescue. Feed only the extracted final answer (no CoT).
    final = extract_final_answer(response)
    judge = llm_judge(question, gold, final)
    if judge is None:
        return {
            "correct": False,
            "t1_correct": False,
            "judge_correct": None,
            "agreement": None,
            "disagreement": None,
        }
    return {
        "correct": judge,
        "t1_correct": False,
        "judge_correct": judge,
        "agreement": False,
        "disagreement": "FN" if judge else None,
    }