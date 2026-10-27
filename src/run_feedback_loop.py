"""
run_feedback_loop.py
====================
Phase 1 (probe): the bounded feedback--self-correction loop.

This drives the L3/L4 observation experiment. For each (model, task) we run a
baseline solve (round 0, no feedback), then up to R feedback rounds. In every
feedback round the weak critic inspects the previous answer (gold-free: question
similarity + answer similarity vs. the wrong bank) and returns a Top-K error
direction + an estimated error probability; the agent then re-solves the SAME
question independently (fresh context, shared tool cache), but the previous
answer and the critic feedback are injected as an extra user message.

Design decisions (2026-10-06):
  - independent re-solve (not multi-turn continuation): matches the existing
    stateless ``HuggingFaceAgent.solve`` and does not alter the agent's natural
    single-question behaviour. Tool results are cached ACROSS rounds so a finance
    task does not re-fetch the same document every round.
  - temperature = 0 (deterministic), seed = None (temp=0 => seed is a no-op).
  - scoring is a ZERO-LLM deterministic pass (T1 rules only): enough to drive
    early stopping and the six end-states. It is NOT the same as the baseline's
    full T1+T2 score (finance T1+rubric only), so the round-0 accuracy here is a
    lower-bound proxy, not a re-statement of the baseline accuracy.
  - early stopping: stop once the final answer is unchanged for N consecutive
    rounds (N=3), to keep finance questions from over-oscillating.
  - six end-states (see RESEARCH_PLAN §5.10) classify each task's trajectory.

Reproducibility: fully deterministic given (model, task, critic); no randomness.
One command:
  python3 src/run_feedback_loop.py --models deepseek-v4-flash --num-tasks 5
"""
from __future__ import annotations

import concurrent.futures
import concurrent.futures.thread as _cf_thread
import json
import os
import re
import sys
import threading
import time
import weakref
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_dotenv() -> None:
    """Load TOKEN_PLAN_API_KEY etc. from the repo .env (never committed).

    Must run BEFORE `from src import config`: config reads the key at import time.
    """
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_gpqa_questions, load_hle_questions, load_new_discrimination_tasks, load_phase1_tasks
from src.hle_scorer import score_t1 as _score_hle_t1
from src.build_weak_critic import _task_family  # noqa: E402
from src.egte_critic import Level3Critic  # noqa: E402
from src.strong_critic import StrongCritic  # noqa: E402
from src.evaluator import (  # noqa: E402
    _extract_committed_integer, _extract_committed_number,
    _extract_committed_text, _extract_mcq_letter,
    _cot_tail, _math500_key, resolve_commit,
    _rubric_coverage_normalized, _score_aime, _score_bbh, _score_bfcl,
    _score_gpqa, _score_math500, _score_mmlu_pro,
    _score_t1_numeric, _score_t2_llm_semantic,
)

# ---- loop hyperparameters (reproducibility) ----
MAX_ROUNDS = 10        # feedback rounds (round 0 = baseline, rounds 1..R = feedback)
A3_SAMPLE_K = 10       # A3C3 round-0 self-consistency sample count (T>0), matches A3
EARLY_STOP_N = 3       # stop once answer unchanged for N consecutive rounds
TIER = "C"             # critic feedback tier (C = type + prob + cause + attention)

# Direction-memory HOLD gate (env toggle, off by default = baseline). When on, the
# C3/A3C3 critic suppresses re-issuing an archetype it already emitted this task
# (HOLD: feedback=None, no_signal=True), so a recurring same-direction perturbation
# cannot drive A->B->A oscillation. New (unseen) directions still perturb -> activation
# is preserved; only the cyclic repeat is cut.
CRITIC_HOLD_ON_REPEAT = os.environ.get("CRITIC_HOLD_ON_REPEAT", "0") == "1"

# ---- experimental arms (P2.1 control arms) ----
#   A  = no-treatment: bare re-solve (feedback=None), only seed/temperature variance.
#   A2 = form placebo: same scaffold, reviewer feedback ablated to a neutral sentence
#        with NO direction and NO keep/change nudge.
#   C  = treatment: weak-critic directional feedback (Phase-1, unchanged).
A2_PLACEBO_FEEDBACK = "No confident error direction was found for this answer."


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _is_correct(family: str | None, row: dict) -> bool:
    """Zero-LLM deterministic correctness (T1 rules only). family from task_id prefix."""
    if row.get("api_failure"):
        return False
    if not family:
        return False
    thresh = config.FINAL_PASS_THRESHOLD
    try:
        if family == "math":
            return _score_t1_numeric(row) >= thresh
        if family == "math500":
            return _score_math500(row) >= thresh
        if family == "mmlu_pro":
            return _score_mmlu_pro(row) >= thresh
        if family == "aime":
            return _score_aime(row) >= thresh
        if family == "gpqa":
            return _score_gpqa(row) >= thresh
        if family == "bbh":
            return _score_bbh(row) >= thresh
        if family == "bfcl":
            return _score_bfcl(row) >= thresh
        if family == "hle":
            # Deterministic T1 exact-match only (the evaluator stays offline). The
            # LLM judge cross-validation runs OUT of loop on the recorded trajectories.
            md = row.get("metadata") or {}
            return _score_hle_t1(
                row.get("gold_answer", ""),
                md.get("answer_type", ""),
                md.get("shape", ""),
                row.get("final_answer", ""),
            )
        if family == "finance":
            # quantitative (T1 numeric) or rubric-covered -> zero-LLM pass
            if _score_t1_numeric(row) >= thresh or _rubric_coverage_normalized(row):
                return True
            # qualitative answer T1 cannot settle -> T2 LLM judge rescue (registered
            # intervention). All answers are still recorded, so a bad judge call can be
            # re-scored offline afterwards.
            t2, dealbreaker = _score_t2_llm_semantic(row)
            return (not dealbreaker) and (t2 >= thresh)
    except Exception:
        return False
    return False


def _norm_ans(s) -> str:
    """Answer normalization for early-stop comparison.

    case/whitespace, plus strip leading/trailing punctuation so surface
    jitter (e.g. "3 bolts" vs "3 bolts.") is not treated as a revision.
    Hosted models at temp=0 still emit trailing-period jitter; without this
    the early stop never triggers and questions burn the full round budget.
    """
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")


def _early_stop_key(family, gold: str, answer: str, reasoning: str = "", finish_reason: str = ""):
    """Robust answer identity for early-stop equality.

    The scorer grades the committed answer under 'commit, don't scan' (see
    evaluator._score_aime/_score_gpqa/_score_bbh), so early stop must compare the
    SAME committed value, not the raw normalized string. glm folds its answer into
    "Reason:" prose with no standalone commit line, so two rounds with the same
    committed value looked different under bare _norm_ans and early stop never fired
    (misled 32%, avg_rounds 7.06 on 2026-10-11). When the visible content is a truncated
    FRAGMENT (glm hidden CoT exhausts the budget), the value is recovered from the CoT tail
    and tagged with source='cot' (INTERFERENCE_CAUSAL_TABLE item 21).

    Returns ``(key, source)``: ``source`` is 'content' (explicit visible commit), 'cot'
    (recovered from the hidden CoT tail), or None (no commit). The source tag lets the
    Stage-B evaluator tell an explicit commit from a CoT-recovered one.
    """
    a = str(answer or "").strip()
    if not a:
        return None, None
    truncated = (finish_reason == "length")
    if family == "hle":
        g = str(gold or "").strip()
        # multipleChoice -> option letter; else dispatch on the gold's form so the
        # committed value stays canonical (prose jitter can't defeat early stop).
        if re.fullmatch(r"\(?([A-E])\)?", g):
            v, src = resolve_commit(a, reasoning, "letter", "ABCDE", truncated=truncated)
            return (("letter", v), src) if v is not None else (None, None)
        if re.fullmatch(r"-?\d+", g):
            v = _transition_committed_integer(a)
            if v is not None:
                return ("int", v), "content"
            v = _transition_committed_integer(_cot_tail(reasoning))
            return (("int", v), "cot") if v is not None else (None, None)
        # symbol / word / text: canonical normalized final-answer string
        return ("raw", _norm_ans(a)), "content"
    if family == "aime":
        # Keep the CLEAN-commit-only extractor for the transition mask (no 'last ='
        # scan), but still recover a boxed/bare final integer from the CoT tail.
        v = _transition_committed_integer(a)
        if v is not None:
            return ("int", v), "content"
        v = _transition_committed_integer(_cot_tail(reasoning))
        return (("int", v), "cot") if v is not None else (None, None)
    if family == "bfcl":
        return _bfcl_commit_key(a), "content"
    if family == "gpqa":
        v, src = resolve_commit(a, reasoning, "letter", "ABCD", truncated=truncated)
        return (("letter", v), src) if v is not None else (None, None)
    if family == "bbh":
        g = str(gold or "").strip()
        if re.fullmatch(r"\(?([A-Za-z])\)?", g):
            v, src = resolve_commit(a, reasoning, "letter", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", truncated=truncated)
            return (("letter", v), src) if v is not None else (None, None)
        if re.fullmatch(r"-?\d+(\.\d+)?", g):
            v, src = resolve_commit(a, reasoning, "number", truncated=truncated)
            return (("num", v), src) if v is not None else (None, None)
        v, src = resolve_commit(a, reasoning, "text", {"yes", "no", "true", "false"}, truncated=truncated)
        return (("word", v), src) if v is not None else (None, None)
    if family == "mmlu_pro":
        v, src = resolve_commit(a, reasoning, "letter", "ABCDEFGHIJ", truncated=truncated)
        return (("letter", v), src) if v is not None else (None, None)
    if family in ("math", "math500"):
        # Canonicalize to the SAME numeric identity as the transition extractor
        # (transition_extract._family_key). The old raw-string fallback committed each
        # round's prose verbatim, so the key jittered every round, the loop never
        # settled, and the transition view extracted nothing. Numeric identity makes
        # run-side commit == transition-side commit (INT-23a).
        k = _math500_key(a)
        if k is not None:
            return ("num", k), "content"
        k = _math500_key(_cot_tail(reasoning))
        return (("num", k), "cot") if k is not None else (None, None)
    return ("raw", _norm_ans(a)), "content"


def _transition_committed_integer(answer: str):
    """Clean-commit-only integer for the transition/early-stop view.

    The scorer's _extract_committed_integer also falls back to 'last =' / 'last line'
    over the whole answer so a reasoning model's leaked hidden CoT can still be graded.
    The transition mask must NOT do that: a multi-line CoT blob has no *committed*
    answer, so return None (no commit) rather than a mid-proof integer that would fire a
    spurious answer->answer switch and a CoT-polluted rationale (aime_035, 2026-10-17).
    Only a bare / emphasised / boxed / explicit-answer-cue integer counts as a commit.
    """
    p = str(answer or "").strip().replace("\u2212", "-")
    if not p:
        return None
    mw = re.fullmatch(r"([*_`]{1,3})\s*(-?\d+)\s*([*_`]{1,3})\s*[.,;:!?]*", p)
    if mw and mw.group(1) == mw.group(3):
        return int(mw.group(2))
    # \boxed{...} (mirrors evaluator._BOXED_RE, kept local to avoid an import)
    mb = re.search(r"\\boxed\s*\{([^{}]*)\}", p)
    if mb:
        mm = re.search(r"-?\d+", mb.group(1))
        if mm:
            return int(mm.group(0))
    bare = r"[\s\(\[\{]*\$?\s*(-?\d+)\s*\$?[\s\)\]\}\.,]*"
    mf = re.fullmatch(bare, p)
    if mf:
        return int(mf.group(1))
    mc = re.search(
        r"(?:answer|ans|result|value)\b(?:\s+(?:is|are|was|were))?\s*[:\-]?\s*\$?\(?(-?\d+)\)?(?!\d)(?!\.\d)",
        p, re.IGNORECASE)
    if mc:
        return int(mc.group(1))
    return None


def _bfcl_commit_key(answer: str):
    """Committed function-call identity for BFCL (structured, no CoT).

    The answer is a clean JSON {"name": X, "arguments": "{...}"} (see _score_bfcl).
    Canonicalize to name(arg=val,...) with sorted args so changing the function or any
    argument is a real answer->answer switch (and thus fires transition rationale), while
    formatting jitter does not. Returns None when the answer is not a single parseable call.
    """
    try:
        obj = json.loads(str(answer or "").strip())
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    name = str(obj.get("name", "")).strip().replace(".", "_")
    if not name:
        return None
    args_raw = obj.get("arguments", "{}")
    if isinstance(args_raw, str):
        try:
            args = json.loads(args_raw)
        except Exception:
            args = {}
    else:
        args = args_raw
    if not isinstance(args, dict):
        args = {}
    pairs = ",".join(f"{k}={args[k]!r}" for k in sorted(args))
    return ("bfcl", f"{name}({pairs})")


_SELF_CORRECT_RE = re.compile(
    r"(?:my|our|the)\s+previous\s+(?:answer|response|result|value)\b"
    r".{0,80}?\b(?:wrong|error|incorrect|mistake|dropped|off|miscount)",
    re.IGNORECASE)


def _commit_present(raw: str, key) -> bool:
    """Is a previously committed value re-stated in this round's raw answer?

    A feedback round that KEEPS its answer folds the value into re-derivation prose
    ("... t = 60, confirming the previous answer") instead of a standalone commit line
    (glm 2026-10-11). Treat the stable re-appearance of the committed value as a
    continuation of the SAME commitment -- commitment is the stable value across
    rounds, not a per-round prose scan. Preserves 'commit, don't scan' while stopping
    the bare-string extractor from grabbing a mid-proof integer/label.
    """
    if key is None:
        return False
    typ, val = key
    if val is None:
        return False
    if typ not in ("int", "num", "letter", "word"):
        return False
    if isinstance(val, float) and val.is_integer():
        s = str(int(val))
    else:
        s = str(val)
    if typ in ("int", "num"):
        return re.search(r"(?<![\d])" + re.escape(s) + r"(?![\d])", raw) is not None
    return re.search(r"\b" + re.escape(s) + r"\b", raw, re.IGNORECASE) is not None


def _carries_forward(raw: str, prev_key) -> bool:
    """Carry the previous committed value forward iff it is still present AND the model
    did not explicitly disown it (self-correction like 'my previous answer 28 was a
    magnitude error'). A disowning clause means the model REVISED; do not fold it."""
    if prev_key is None or raw is None or not str(raw).strip():
        return False
    if _SELF_CORRECT_RE.search(str(raw)):
        return False
    return _commit_present(str(raw), prev_key)


def _canonical_commit_str(key) -> str:
    """Reconstruct a canonical single-token answer string from a commitment key so a
    carried-forward value can be fed back through the normal scorer."""
    if key is None:
        return ""
    typ, val = key
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def _feedback_message(prev_answer: str, critic_text: str,
                      rationale_mode: str = "off") -> str:
    """Self-contained re-solve prompt: previous answer + critic feedback + revision
    instruction. The agent decides itself whether to revise (no forced output format).

    rationale_mode selects how the transition self-report is collected:

      - off        : no self-report (clean answer only).
      - reason_line: append a trailing "Reason:" line (native, single round-trip);
                     ``_split_rationale`` strips it before scoring.
      - json       : demand a strict {"answer": ..., "reason": ...} JSON object.
      - twostage   : handled at the agent layer (two-call decoupling), not here.
      - transition : no tail is appended here; the loop collects the change rationale
                     conditionally (two-stage side channel) ONLY when the committed
                     answer actually switches to a different value."""
    msg = (
        "A reviewer looked at your PREVIOUS answer to this question and gave feedback.\n"
        f"Your previous answer was:\n\"\"\"\n{prev_answer}\n\"\"\"\n\n"
        f"Reviewer feedback:\n{critic_text}\n\n"
        "Reconsider the question and provide your final answer again. "
        "If you believe your previous answer was already correct, keep it as is."
    )
    if rationale_mode == "reason_line":
        # Keep the answer on the SAME commit format as a rationale-free round (the
        # base family prompt already demands "ONLY the letter/integer/short answer").
        # Do NOT impose a rigid "two lines" scaffold -- it fights the base prompt and
        # is what pushed glm into folding the answer into "Reason:" prose (no-commit).
        # Only append a trailing "Reason:" line; _split_rationale strips just that tail.
        msg += (
            "\n\nRespond with your final answer in the SAME format requested above "
            "(answer only, no explanation). Then, on a new line, write \"Reason:\" "
            "followed by one short sentence explaining why you changed or kept your "
            "previous answer. Keep the answer and the Reason on separate lines."
        )
    elif rationale_mode == "json":
        msg += (
            "\n\nRespond in strict JSON with exactly two fields: \"answer\" and "
            "\"reason\". \"answer\" is your final answer in the SAME format requested "
            "above (letter / number / short answer only). \"reason\" is one short "
            "sentence explaining why you changed or kept your previous answer. Output "
            "ONLY the JSON object, nothing else."
            "\nExample: {\"answer\": \"B\", \"reason\": \"The reviewer's isotope "
            "note switched my choice.\"}"
        )
    return msg


def _split_json_rationale(text: str) -> tuple[str, str]:
    """Parse a strict-JSON self-report {"answer": ...} into (answer, reason)."""
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return text, ""
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return text, ""
    if not isinstance(obj, dict):
        return text, ""
    ans = obj.get("answer") or obj.get("final_answer") or ""
    reason = obj.get("reason") or obj.get("rationale") or ""
    return str(ans).strip(), str(reason).strip()


def _split_rationale(text: str, rationale_mode: str = "reason_line") -> tuple[str, str]:
    """Split a trailing self-report off the answer, returning (answer, reason).

    reason_line: a trailing "Reason:" line is the transition self-report; the answer
    part stays clean for scoring/normalization. json: a strict {"answer","reason"}
    object. Tolerates no-match and leading whitespace."""
    if rationale_mode == "json":
        return _split_json_rationale(text)
    m = re.search(r"(?:^|\n)\s*reason\s*:\s*", text, flags=re.IGNORECASE)
    if not m:
        return text, ""
    answer = text[:m.start()].strip()
    reason = text[m.end():].strip()
    # Fix: when the model folds the answer INTO the "Reason:" line (no standalone
    # answer before it), do NOT fall back to the raw text -- that pollutes scoring
    # and breaks early-stop equality (the whole "Reason:" body is what killed glm).
    # Keep the Reason body (prefix stripped) as the answer so the round still has
    # concrete content, and preserve the self-report for transition analysis.
    if answer:
        return answer, reason
    return reason, reason


# Three-part transition self-report for rationale_mode="transition". The core
# semantic is NOT "why is the current answer right" but "why did you CHANGE":
# ERROR (where the previous answer was wrong) / REASON (why the model switched) /
# FIX (the specific reason the new answer is correct). Runs under its OWN system
# prompt (not the base "answer only" prompt) so reasoning models do not fold the
# answer into a fragment.
_TRANSITION_RATIONALE_SYSTEM = (
    "You are explaining a change you made to your own answer. Answer in exactly "
    "three short sentences: (1) ERROR: where your previous answer was wrong; "
    "(2) REASON: why you decided to change; (3) FIX: the specific reason your new "
    "answer is correct. Do not restate the question and do not output any answer "
    "letter or choice."
)

# None-state self-report: at least one adjacent round produced NO explicit committed
# answer (still reasoning / CoT truncated / unsure). The Stage-B evaluator must tell
# such rounds apart by their change-of-state rationale, not by the answer string (item
# 17/18), so we still collect a three-part report here; "<no explicit answer>" is a
# deliberate placeholder so the model states what it WAS doing instead of a label.
_TRANSITION_RATIONALE_SYSTEM_NONE = (
    "You are explaining how your own reasoning changed between two consecutive "
    "rounds on the same question, where at least one round produced no clear final "
    "answer. Answer in exactly three short sentences: "
    "(1) BEFORE: what answer or state you held in the previous round (if there was "
    "no clear answer, say whether you were still reasoning, was truncated, or unsure); "
    "(2) WHY: why your answer or state changed (or stayed the same); "
    "(3) NOW: what answer or state you now hold and why. "
    "Do not restate the question and do not output any answer choice."
)

# The transition rationale is a self-report of the STATE CHANGE (prev/curr answer),
# not a re-solve of the task. Passing the full hard question makes reasoning models
# (glm-5.3) re-derive the whole problem in hidden CoT, which grows unbounded --
# 8190 / 32766 reasoning tokens at 8192 / 32768 caps -- and truncates the visible
# rationale to "**" (item 16; raising the budget alone does NOT fix glm, and its
# endpoint rejects enable_thinking=False). A short question stem keeps enough topical
# context without triggering the runaway CoT (verified on gpqa_102: stem ~300 chars
# -> ~1.2k reasoning tokens, clean 3-part report).
_RATIONALE_QUESTION_MAX_CHARS = 300


def _collect_transition_rationale(agent, task, feedback: str,
                                  prev_label: str, new_label: str) -> str:
    """Side-channel collection of the change rationale for a real answer->answer
    switch OR for any round touching an empty commit (None state), in
    rationale_mode="transition". The question is truncated to a short stem (see
    ``_RATIONALE_QUESTION_MAX_CHARS``) so reasoning models do not re-solve the full
    problem in hidden CoT and fold the visible rationale into a fragment (item 16).
    Returns "" on any API failure (rationale is a side channel, never fatal)."""
    prev_none = (prev_label == "")
    new_none = (new_label == "")
    none_touched = prev_none or new_none
    q = str(task.prompt or "")
    if len(q) > _RATIONALE_QUESTION_MAX_CHARS:
        q = q[:_RATIONALE_QUESTION_MAX_CHARS] + "…"
    msgs = [
        {"role": "system",
         "content": _TRANSITION_RATIONALE_SYSTEM_NONE if none_touched
                    else _TRANSITION_RATIONALE_SYSTEM},
        {"role": "user", "content": q},
    ]
    if feedback:
        msgs.append({"role": "user", "content": feedback})
    if none_touched:
        prev_disp = prev_label or "<no explicit answer>"
        new_disp = new_label or "<no explicit answer>"
        tail = (
            f"Previous round: \"{prev_disp}\". Current round: \"{new_disp}\". "
            "Explain, in three short sentences, what changed (or did not change) "
            "between the two rounds."
        )
    else:
        tail = (
            f"Your previous answer was \"{prev_label}\"; your new answer is "
            f"\"{new_label}\". Explain the change in three short sentences: "
            "(1) where the previous answer was wrong, (2) why you changed, "
            "(3) why the new answer is correct."
        )
    msgs.append({"role": "user", "content": tail})
    try:
        content, _reasoning, _usage = agent._call_llm_text(
            msgs, max_tokens=config.TRANSITION_RATIONALE_MAX_TOKENS)
        u = getattr(_usage, "usage", None)
        toks = (
            getattr(u, "prompt_tokens", 0) or 0,
            getattr(u, "completion_tokens", 0) or 0,
            getattr(u, "reasoning_tokens", 0) or 0,
        )
        return (content or "").strip(), toks
    except Exception:
        return "", (0, 0, 0)


def _round_record(r: int, result, correct: bool, evidence, error, no_signal,
                  top3, arm: str, rationale: str = "", rat_toks=(0, 0, 0),
                  committed_answer=None, carried: bool = False,
                  commit_source: str = None, critic_direction=None) -> dict:
    return {
        "round": r,
        "arm": arm,
        "final_answer": result.final_answer,
        "committed_answer": committed_answer if committed_answer is not None else result.final_answer,
        "carried": carried,
        "commit_source": commit_source or None,
        "reasoning_content": result.reasoning_content or "",
        "finish_reason": result.finish_reason or "",
        "is_correct": correct,
        "rationale": rationale or None,
        "evidence": round(evidence, 4) if evidence is not None else None,
        "error_score": round(error, 4) if error is not None else None,
        "no_signal": no_signal,
        "top3": [{"leaf": l, "prob": round(p, 4)} for l, p in (top3 or [])],
        "critic_direction": critic_direction or None,
        "tool_calls": result.tool_calls,
        "latency_ms": result.total_latency_ms,
        "api_failure": result.api_failure,
        "prompt_tokens": result.total_prompt_tokens,
        "completion_tokens": result.total_completion_tokens,
        "reasoning_tokens": result.reasoning_tokens,
        "rationale_prompt_tokens": rat_toks[0],
        "rationale_completion_tokens": rat_toks[1],
        "rationale_reasoning_tokens": rat_toks[2],
    }


def _end_state(corrects: list[bool]) -> int:
    """Six end-states (RESEARCH_PLAN §5.10) from the per-round correctness vector."""
    start, final = corrects[0], corrects[-1]
    if start and final:
        return 1 if all(corrects) else 3   # 1: L4 full; 3: L4 weak but recoverable
    if start and not final:
        return 2                            # 2: L4 deficit (misled into an error)
    if not start and final:
        return 4                            # 4: L3 + L4 full (activated then locked)
    return 5 if any(corrects[1:]) else 6    # 5: L3 present / L4 deficit; 6: L3 absent


class _DaemonThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):
    """ThreadPoolExecutor with daemon workers.

    The stdlib pool starts *non*-daemon workers (Python 3.14), so a worker
    blocked on a hung socket read (which httpx read_timeout cannot always
    interrupt on reasoning endpoints) would otherwise block interpreter exit.
    Daemon workers let the process exit cleanly even with a hung request."""
    def _adjust_thread_count(self) -> None:
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            t = threading.Thread(
                name=thread_name,
                target=_cf_thread._worker,
                args=(
                    weakref.ref(self, weakref_cb),
                    self._create_worker_context(),
                    self._work_queue,
                ),
            )
            t.daemon = True
            t.start()
            self._threads.add(t)
            _cf_thread._threads_queues[t] = self._work_queue


_write_lock = threading.Lock()


def _load_completed(traj_path) -> set:
    # Task ids already checkpointed on disk (token-outage / restart recovery).
    done = set()
    if traj_path.exists():
        with traj_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)["task_id"])
                except Exception:
                    continue  # ignore torn/partial trailing line
    return done


def _append_record(traj_path, record: dict) -> None:
    # Thread-safe append of one completed task (per-task resume checkpoint).
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _write_lock:
        with traj_path.open("a", encoding="utf-8") as f:
            f.write(line)


def _run_task_loop(agent, critic, task, tier, max_rounds, early_stop_n,
                   arm: str, rationale_mode: str = "off",
                   feedback_agent=None) -> dict:
    family = _task_family(task.task_id)
    tool_cache: dict = {}
    records: list[dict] = []

    def score(result, answer=None) -> bool:
        row = {
            "task_id": task.task_id, "category": task.category,
            "gold_answer": task.gold_answer,
            "final_answer": result.final_answer if answer is None else answer,
            "reasoning_content": result.reasoning_content or "",
            "finish_reason": result.finish_reason or "",
            "metadata": task.metadata, "api_failure": result.api_failure,
            "prompt": task.prompt, "trajectory": result.trajectory,
        }
        return _is_correct(family, row)

    # round 0: baseline (no feedback). A3C3 replaces the single baseline solve with
    # K independent temperature samples (T>0) majority-voted on the committed key; the
    # voted answer becomes round 0's committed answer and the C3 feedback loop (rounds
    # 1..R) then runs at T=0 (feedback_agent) to isolate the round-0 gain.
    round0_sample_corrects = None
    if arm == "A3C3":
        samples = []  # (result, committed_key, commit_source, correct)
        for _ in range(A3_SAMPLE_K):
            sres = agent.solve(task, feedback=None, tool_cache=tool_cache)
            skey, ssrc = _early_stop_key(family, task.gold_answer, sres.final_answer,
                                         sres.reasoning_content, sres.finish_reason)
            samples.append((sres, skey, ssrc, score(sres)))
        # Majority vote over committed keys (ties -> first-encountered, consistent with
        # Counter.most_common insertion order). None (no-commit) samples are excluded.
        key_counts = Counter(k for _, k, _, _ in samples if k is not None)
        voted_key = key_counts.most_common(1)[0][0] if key_counts else None
        winner = next((s for s in samples if s[1] == voted_key),
                      samples[0] if samples else None)
        voted_result, _, voted_source, voted_correct = winner
        prev_answer = voted_result.final_answer
        prev_key = voted_key
        prev_source = voted_source
        prev_reasoning = voted_result.reasoning_content or ""
        records.append(_round_record(0, voted_result, voted_correct, None, None, None,
                                     None, arm, commit_source=voted_source))
        round0_sample_corrects = [s[3] for s in samples]
    else:
        result = agent.solve(task, feedback=None, tool_cache=tool_cache)
        prev_answer = result.final_answer
        prev_key, prev_source = _early_stop_key(family, task.gold_answer, prev_answer,
                                                 result.reasoning_content,
                                                 result.finish_reason)
        prev_reasoning = result.reasoning_content or ""
        records.append(_round_record(0, result, score(result), None, None, None, None,
                                     arm, commit_source=prev_source))

    if arm == "A3":
        # Self-consistency control: fixed K independent samples at T>0, no feedback,
        # no early stop. Each round is one i.i.d. sample; vote = freq (majority).
        # Coverage over the K samples = pass@k; C's analog is correct_appeared.
        for r in range(1, max_rounds):
            result = agent.solve(task, feedback=None, tool_cache=tool_cache)
            records.append(_round_record(r, result, score(result),
                                         None, None, None, None, arm))
        corrects = [rec["is_correct"] for rec in records]
        return {
            "task_id": task.task_id, "arm": arm, "family": family,
            "gold_answer": task.gold_answer, "prompt": task.prompt,
            "rounds": records, "n_rounds": len(records),
            "start_correct": corrects[0], "final_correct": corrects[-1],
            "correct_appeared": any(corrects), "end_state": _end_state(corrects),
        }

    critic_direction = None
    streak = 1
    issued_archetypes = set()   # direction memory for CRITIC_HOLD_ON_REPEAT
    # A3C3 feedback rounds run on the deterministic (T=0) agent to match C3; only the
    # round-0 self-consistency sampling used the T>0 `agent` above.
    solver = feedback_agent if (arm == "A3C3" and feedback_agent is not None) else agent
    for r in range(1, max_rounds + 1):
        if arm == "A":
            # no-treatment: bare re-solve, no reviewer message at all.
            feedback = None
            pred = evidence = error = no_signal = None
        elif arm == "A2":
            # form placebo: scaffold + fixed neutral feedback (no direction, no keep).
            if family is None:
                break
            feedback = _feedback_message(prev_answer, A2_PLACEBO_FEEDBACK, rationale_mode)
            pred = evidence = error = no_signal = None
        else:  # C (single) / C2 (top-3) / C3 (strong LLM critic)
            if family is None:
                break
            evidence = None
            if arm == "C2":
                pairs = critic.topk(task.prompt, prev_answer, family, k=3)
                fb_text, critic_direction = critic.render_topk(pairs)
            else:  # "C" / "C3" / "A3C3": strong LLM critic feeds the solver CoT
                if arm in ("C3", "A3C3"):
                    # lever-1: both C3 and A3C3 ground the critic's check in the
                    # solver's hidden CoT. A3C3 was previously missing reasoning here
                    # (arm == "C3" guard), so its critic silently degraded to the old
                    # no-CoT behaviour while C3-v2 fed CoT -- fixed 2026-10-24.
                    fb_text, critic_direction, evidence = critic.feedback(
                        task.prompt, prev_answer, family, reasoning=prev_reasoning)
                else:
                    fb_text, critic_direction, evidence = critic.feedback(
                        task.prompt, prev_answer, family)
            error = None
            pred = None
            feedback = _feedback_message(prev_answer, fb_text, rationale_mode)
            no_signal = False
            if CRITIC_HOLD_ON_REPEAT and arm in ("C3", "A3C3"):
                # Direction-memory HOLD gate: if the critic re-proposes an archetype it
                # already emitted this task, suppress the perturbation (feedback=None) so
                # a recurring same-direction push cannot drive A->B->A oscillation.
                cur_names = set()
                for _d in (critic_direction or []):
                    if isinstance(_d, dict):
                        _nm = _d.get("archetype_name") or _d.get("id") or _d.get("archetype_id")
                        if _nm:
                            cur_names.add(str(_nm).strip())
                if cur_names and (cur_names & issued_archetypes):
                    feedback = None
                    no_signal = True
                else:
                    issued_archetypes |= cur_names
        result = solver.solve(task, feedback=feedback, tool_cache=tool_cache,
                             rationale_mode=rationale_mode)
        rationale = ""
        rat_toks = (0, 0, 0)
        if feedback and rationale_mode in ("reason_line", "json"):
            result.final_answer, rationale = _split_rationale(result.final_answer, rationale_mode)
        elif feedback and rationale_mode == "twostage":
            rationale = result.rationale
        new_answer = result.final_answer
        raw_key, raw_source = _early_stop_key(family, task.gold_answer, new_answer,
                                               result.reasoning_content,
                                               result.finish_reason)
        # glm folds its committed answer into re-derivation prose on feedback rounds
        # instead of a clean commit line; carry the stable committed value forward so
        # scoring and early stop stay on the SAME value rather than a mid-proof
        # intermediate (the bare-string misread surfaced as a fake 32% "misled" rate,
        # 2026-10-11).
        if prev_key is not None and raw_key != prev_key and _carries_forward(new_answer, prev_key):
            committed_key = prev_key
            carried = True
        else:
            committed_key = raw_key
            carried = False
        # A carried value is re-stated in the visible prose (content), not recovered
        # from CoT; a fresh commit records where it was extracted from (item 21).
        commit_source = "content" if carried else raw_source
        # Conditional transition rationale (rationale_mode="transition"): collect the
        # "why did the state change" self-report when EITHER
        #   (a) the committed answer switches to a different non-empty value
        #       (a real answer -> answer transition), or
        #   (b) either adjacent round is an empty commit (None state: still reasoning /
        #       CoT truncated / unsure). The Stage-B evaluator needs rationale to tell an
        #       empty round apart from its neighbour (item 17/18), so None -> X,
        #       X -> None, and None -> None must also collect a report.
        # Only round 0 (no feedback yet) is exempt.
        if feedback and rationale_mode == "transition":
            prev_label = _canonical_commit_str(prev_key)
            new_label = _canonical_commit_str(committed_key)
            prev_none = (prev_label == "")
            new_none = (new_label == "")
            is_switch = (not prev_none and not new_none and new_label != prev_label)
            if is_switch or prev_none or new_none:
                rationale, rat_toks = _collect_transition_rationale(
                    solver, task, feedback, prev_label, new_label)
        score_answer = new_answer if committed_key == raw_key else _canonical_commit_str(committed_key)
        correct = score(result, answer=score_answer)
        # A round with NO commit (committed_key is None) must reset the streak,
        # not count as "unchanged": None == None used to early-stop a
        # never-committing task after 3 empty rounds (INT-23b).
        streak = streak + 1 if (committed_key is not None and committed_key == prev_key) else 1
        prev_key = committed_key
        prev_answer = new_answer
        prev_reasoning = result.reasoning_content or ""
        records.append(_round_record(r, result, correct, evidence, error, no_signal,
                                     pred, arm, rationale, rat_toks,
                                     committed_answer=(score_answer if carried else None),
                                     carried=carried, commit_source=commit_source,
                                     critic_direction=critic_direction))
        if streak >= early_stop_n:
            break

    corrects = [rec["is_correct"] for rec in records]
    # A3C3 activation spans BOTH the round-0 self-consistency samples (pass@k) and
    # the feedback rounds, not just the voted round-0 answer.
    if arm == "A3C3" and round0_sample_corrects is not None:
        appeared = any(round0_sample_corrects) or any(corrects[1:])
    else:
        appeared = any(corrects)
    return {
        "task_id": task.task_id,
        "arm": arm,
        "rationale_mode": rationale_mode,
        "family": family,
        "gold_answer": task.gold_answer,
        "prompt": task.prompt,
        "rounds": records,
        "n_rounds": len(records),
        "start_correct": corrects[0],
        "final_correct": corrects[-1],
        "correct_appeared": appeared,
        "end_state": _end_state(corrects),
        "round0_sample_corrects": round0_sample_corrects,
    }


def run_feedback_loop(models=None, num_tasks=0, max_rounds=MAX_ROUNDS,
                      early_stop_n=EARLY_STOP_N, tier=TIER, concurrency=None,
                      arm="C", family=None, out_dir=None,
                      task_set="phase1", max_tokens=None,
                      temperature=0.0, skip_finance=False,
                      task_offset=0, rationale_mode: str = "off",
                      task_ids=None, enable_thinking: bool | None = None) -> dict:
    _force_no_proxy()
    if task_set == "gpqa":
        # Full GPQA-Diamond (all 198 rows) in deterministic CSV order. The
        # per-question option shuffle uses seed = row index, so gpqa_001..198
        # are byte-identical to any smaller limit prefix (auditable fixed list).
        tasks = load_gpqa_questions(limit=None)
        if max_tokens is None:
            max_tokens = config.REASONING_BENCH_MAX_TOKENS
    elif task_set == "new":
        tasks = load_new_discrimination_tasks()
        # AIME / GPQA-Diamond are reasoning models whose hidden CoT truncates the
        # visible answer at the default 1024 cap (see config.REASONING_BENCH_MAX_TOKENS);
        # use the frozen reasoning budget for the whole discrimination set.
        if max_tokens is None:
            max_tokens = config.REASONING_BENCH_MAX_TOKENS
    elif task_set == "hle":
        tasks = load_hle_questions()
        # HLE hard symbolic questions can outgrow 8192 (same CoT-truncation risk as
        # AIME/GPQA); use the frozen reasoning budget.
        if max_tokens is None:
            max_tokens = config.REASONING_BENCH_MAX_TOKENS
    else:
        tasks = load_phase1_tasks()
        if max_tokens is None:
            max_tokens = 1024
    if family:
        tasks = [t for t in tasks if _task_family(t.task_id) == family]
    if task_ids:
        _wanted = set(task_ids)
        tasks = [t for t in tasks if t.task_id in _wanted]
    if skip_finance:
        tasks = [t for t in tasks if _task_family(t.task_id) != "finance"]
    if task_offset:
        tasks = tasks[task_offset:]
    if num_tasks:
        tasks = tasks[:num_tasks]
    if concurrency is None:
        concurrency = config.RUNNER_CONCURRENCY

    if out_dir:
        run_id = out_dir
        out_root = REPO_ROOT / "experiments" / out_dir
    else:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_root = REPO_ROOT / "experiments" / f"feedback_loop_{arm}_{run_id}"
    out_root.mkdir(parents=True, exist_ok=True)

    names = models or [m for m in config.PHASE1_MODELS if config.PHASE1_MODELS[m].get("api_key")]
    summary = {
        "run_id": run_id, "arm": arm, "family_filter": family,
        "task_set": task_set, "max_tokens": max_tokens,
        "max_rounds": max_rounds,
        "early_stop_n": early_stop_n, "tier": tier, "temperature": temperature,
        "skip_finance": skip_finance,
        "rationale_mode": rationale_mode,
        "seed": None, "n_tasks": len(tasks), "concurrency": concurrency,
        "models": {},
    }

    for name in names:
        entry = config.PHASE1_MODELS[name]
        agent = HuggingFaceAgent(
            model=entry["model"], token=entry.get("api_key"),
            base_url=entry["base_url"], max_tokens=max_tokens, temperature=temperature,
            seed=None, enable_thinking=(enable_thinking
                                        if enable_thinking is not None
                                        else entry.get("enable_thinking")),
            thinking_budget=entry.get("thinking_budget"))
        # A3C3: round-0 self-consistency samples run at T>0 (this `agent`); the C3
        # feedback rounds run on a second deterministic (T=0) agent for a fair C3 match.
        feedback_agent = None
        if arm == "A3C3":
            feedback_agent = HuggingFaceAgent(
                model=entry["model"], token=entry.get("api_key"),
                base_url=entry["base_url"], max_tokens=max_tokens, temperature=0.0,
                seed=None, enable_thinking=(enable_thinking
                                            if enable_thinking is not None
                                            else entry.get("enable_thinking")),
                thinking_budget=entry.get("thinking_budget"))
        critic = None
        if arm in ("C", "C2"):
            critic = Level3Critic.load(name)
        elif arm in ("C3", "A3C3"):
            critic = StrongCritic.load(name)
        model_dir = out_root / name
        model_dir.mkdir(parents=True, exist_ok=True)
        traj_path = model_dir / "loop_trajectories.jsonl"

        # resume support: reopen the checkpoint and skip already-finished tasks
        # (token-outage recovery -> no re-billing of completed tasks).
        done_ids = _load_completed(traj_path)
        pending_tasks = [t for t in tasks if t.task_id not in done_ids]
        print(f"\n=== feedback loop [{name}] model={entry['model']} "
              f"tasks={len(tasks)} done={len(done_ids)} pending={len(pending_tasks)} "
              f"R={max_rounds} N={early_stop_n} tier={tier} arm={arm} ===")

        if pending_tasks:
            # Per-SOLVE budget: AGENTEVALUATION_SOLVE_TIMEOUT bounds ONE agent.solve
            # call (mirrors httpx read timeout, which does not fire on reasoning
            # endpoints). The task-loop runs up to max_rounds+1 solves, so its deadline
            # must scale accordingly -- a fixed 180s total wrongly abandoned slow-but-
            # normal aime tasks (30% timeouts in the 2026-10-12 glm smoke).
            solve_timeout = float(os.getenv("AGENTEVALUATION_SOLVE_TIMEOUT", "180"))
            ex = _DaemonThreadPoolExecutor(max_workers=concurrency)
            task_iter = iter(pending_tasks)
            in_flight = {}   # future -> task
            deadline = {}    # future -> monotonic per-task deadline (rounds-scaled)

            def _submit_one():
                try:
                    task = next(task_iter)
                except StopIteration:
                    return
                fut = ex.submit(_run_task_loop, agent, critic, task, tier,
                                max_rounds, early_stop_n, arm, rationale_mode,
                                feedback_agent)
                in_flight[fut] = task
                deadline[fut] = time.monotonic() + solve_timeout * (max_rounds + 1)

            for _ in range(concurrency):
                _submit_one()

            done = 0
            try:
                while in_flight:
                    now = time.monotonic()
                    for fut in [f for f, d in deadline.items() if d <= now]:
                        t = in_flight.pop(fut)
                        deadline.pop(fut, None)
                        fut.cancel()
                        print(f"  [{name}] TIMEOUT {t.task_id} (> {solve_timeout}s "
                              f"hung request); skipped for re-run", flush=True)
                        _submit_one()
                    if not in_flight:
                        break
                    wait_for = max(min(deadline.values()) - now, 0.0)
                    finished, _ = concurrent.futures.wait(
                        in_flight, timeout=wait_for,
                        return_when=concurrent.futures.FIRST_COMPLETED)
                    for fut in finished:
                        if fut not in in_flight:
                            continue
                        deadline.pop(fut, None)
                        in_flight.pop(fut)
                        _append_record(traj_path, fut.result())
                        done += 1
                        print(f"  [{name}] {done}/{len(pending_tasks)} tasks done",
                              flush=True)
                        _submit_one()
            finally:
                ex.shutdown(wait=False, cancel_futures=True)
        else:
            print(f"  [{name}] all {len(done_ids)} tasks already completed; "
                  f"re-aggregating from checkpoint.", flush=True)

        # aggregate from disk (covers checkpointed + newly completed tasks)
        per_task = []
        with traj_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    per_task.append(json.loads(line))
        n = len(per_task)
        init_correct = sum(1 for t in per_task if t["start_correct"])
        final_correct = sum(1 for t in per_task if t["final_correct"])
        states = Counter(t["end_state"] for t in per_task)
        wrong_start = [t for t in per_task if not t["start_correct"] and t["family"]]
        right_start = [t for t in per_task if t["start_correct"]]
        # L3 activation = fraction of ALL tasks where the correct answer appeared
        # in >=1 round (incl. round 0). Absolute activation capability, decoupled
        # from whether the model locks it in (that is L4's job).
        appeared = sum(1 for t in per_task if t["correct_appeared"])
        activation = appeared / n if n else 0.0
        # L3 reversibility = among first-wrong tasks, fraction that later produced
        # the correct answer (feedback-driven recovery potential).
        reversibility = (sum(1 for t in wrong_start
                             if any(r["is_correct"] for r in t["rounds"][1:]))
                         / len(wrong_start)) if wrong_start else 0.0
        locked = (sum(1 for t in right_start if t["end_state"] == 1)
                  / len(right_start)) if right_start else 0.0
        misled = (sum(1 for t in right_start if t["end_state"] == 2)
                  / len(right_start)) if right_start else 0.0
        avg_rounds = sum(t["n_rounds"] for t in per_task) / n if n else 0.0

        m = {
            "model_id": entry["model"],
            "init_accuracy": round(init_correct / n, 4) if n else 0.0,
            "final_accuracy": round(final_correct / n, 4) if n else 0.0,
            "end_state_distribution": {str(k): v for k, v in sorted(states.items())},
            "l3_activation_rate": round(activation, 4),
            "l3_reversibility_rate": round(reversibility, 4),
            "l4_lock_rate": round(locked, 4),
            "l4_misled_rate": round(misled, 4),
            "avg_rounds": round(avg_rounds, 2),
            "total_prompt_tokens": sum(r["prompt_tokens"] for t in per_task for r in t["rounds"]),
            "total_completion_tokens": sum(r["completion_tokens"] for t in per_task for r in t["rounds"]),
            "total_reasoning_tokens": sum(r.get("reasoning_tokens", 0) for t in per_task for r in t["rounds"]),
            "total_rationale_prompt_tokens": sum(r.get("rationale_prompt_tokens", 0) for t in per_task for r in t["rounds"]),
            "total_rationale_completion_tokens": sum(r.get("rationale_completion_tokens", 0) for t in per_task for r in t["rounds"]),
            "total_rationale_reasoning_tokens": sum(r.get("rationale_reasoning_tokens", 0) for t in per_task for r in t["rounds"]),
        }
        summary["models"][name] = m
        (out_root / "loop_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [{name}] init={m['init_accuracy']:.2%} final={m['final_accuracy']:.2%} "
              f"states={m['end_state_distribution']} L3_act={m['l3_activation_rate']:.2%} "
              f"L3_rev={m['l3_reversibility_rate']:.2%} "
              f"L4_lock={m['l4_lock_rate']:.2%} L4_misled={m['l4_misled_rate']:.2%} "
              f"avg_rounds={m['avg_rounds']} "
              f"tok={m['total_prompt_tokens']}+{m['total_completion_tokens']} "
              f"reason={m['total_reasoning_tokens']} "
              f"rat={m['total_rationale_prompt_tokens']}+{m['total_rationale_completion_tokens']} "
              f"rat_reason={m['total_rationale_reasoning_tokens']}")

    (out_root / "loop_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== feedback loop summary -> {out_root / 'loop_summary.json'} ===")
    return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Phase-1 feedback loop (L3/L4 probe)")
    ap.add_argument("--models", default="",
                    help="comma-separated model names (default: all with api_key)")
    ap.add_argument("--num-tasks", type=int, default=0, help="limit tasks (0 = all 250)")
    ap.add_argument("--task-offset", type=int, default=0,
                    help="skip the first N loaded tasks (e.g. 50 to run gpqa_051..198)")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--early-stop", type=int, default=EARLY_STOP_N)
    ap.add_argument("--tier", default=TIER, choices=["A", "B", "C"])
    ap.add_argument("--arm", default="C", choices=["A", "A2", "A3", "A3C3", "C", "C2", "C3"],
                    help="experimental arm: A=no-treatment, A2=form placebo, "
                         "A3=i.i.d. temperature sampling (self-consistency), "
                         "A3C3=self-consistency round0 + C3 strong-critic loop, "
                         "C=critic(single), C2=critic(top-3), C3=strong LLM critic")
    ap.add_argument("--family", default=None,
                    help="restrict to one family: math/math500/mmlu_pro/bfcl/finance/"
                         "aime/gpqa/bbh/hle")
    ap.add_argument("--task-set", default="phase1", choices=["phase1", "new", "gpqa", "hle"],
                    help="phase1 = the 5 baseline families; new = AIME+GPQA+BBH "
                         "discrimination set; gpqa = full 198 GPQA-Diamond; "
                         "hle = 50-question HLE stratified pilot")
    ap.add_argument("--tasks", default=None,
                    help="comma-separated task ids to run (exact filter, overrides "
                         "num/offset)")
    ap.add_argument("--concurrency", type=int, default=0, help="0 = config default")
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="sampling temperature (A3 uses T>0; 0 = greedy)")
    ap.add_argument("--skip-finance", action="store_true",
                    help="exclude the finance (FAB) family (high tool cost)")
    ap.add_argument("--rationale-mode", default="off",
                    choices=["off", "reason_line", "json", "twostage", "transition"],
                    help="how the agent self-reports each transition reason: "
                         "off=none, reason_line=trailing 'Reason:' line, "
                         "json=strict {answer,reason} object, twostage=two-call "
                         "decoupling (answer then reason side channel), "
                         "transition=conditional two-stage 'why did you change' "
                         "rationale collected only on a real answer->answer switch")
    ap.add_argument("--enable-thinking", type=int, default=None, choices=[0, 1],
                    help="override model enable_thinking (0=off, 1=on) for no-commit "
                         "resample; default None = model config")
    ap.add_argument("--out-dir", default=None,
                    help="reuse an existing experiments dir (resume from checkpoint)")
    a = ap.parse_args()

    run_feedback_loop(
        models=[m for m in a.models.split(",") if m] or None,
        num_tasks=a.num_tasks,
        max_rounds=a.max_rounds,
        early_stop_n=a.early_stop,
        tier=a.tier,
        concurrency=(a.concurrency or None),
        arm=a.arm,
        family=a.family,
        out_dir=a.out_dir,
        task_set=a.task_set,
        temperature=a.temperature,
        skip_finance=a.skip_finance,
        task_offset=a.task_offset,
        rationale_mode=a.rationale_mode,
        task_ids=([x.strip() for x in a.tasks.split(",") if x.strip()]
                  if a.tasks else None),
        enable_thinking=(bool(a.enable_thinking)
                         if a.enable_thinking is not None else None),
    )
