"""transition_extract.py
========================
Stage B step 1: extract transition data from C-arm trajectories.

Rebuilds, per task, the *transition view* the Stage-B evaluator consumes: the
candidate answers seen along the trajectory, the per-round committed-answer
sequence (with the transition self-report ``rationale``), and the explicit
answer-switch events. We do **not** emit the original question text -- the
Stage-B evaluator must judge state plausibility from candidates + transitions
only. The gold answer / correctness flags are kept purely for offline analysis.

Commitment identity is reproduced faithfully from the C-arm runtime (see
run_feedback_loop): each round's committed key is ``_early_stop_key`` on the raw
``final_answer``, folded to the previous committed key when ``_carries_forward``
and the raw text still re-states it (no self-correction clause). This matters in
``reason_line`` data where ``final_answer`` is prose-polluted and a naive
per-round extraction mistags carried rounds.

Usage:
  python3 src/transition_extract.py --traj <path/to/loop_trajectories.jsonl> \
      --out <path/to/transitions.jsonl>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src.evaluator import (  # noqa: E402
    _cot_tail,
    _math500_key,
    _norm_unicode_math,
    _strip_math_noise,
    resolve_commit,
)
from src.run_feedback_loop import _transition_committed_integer, _norm_ans  # noqa: E402
from src.build_weak_critic import LEAF_PHRASE  # noqa: E402

EARLY_STOP_N = 3  # same trigger as run_feedback_loop

_SELF_CORRECT_RE = re.compile(
    r"(?:my|our|the)\s+previous\s+(?:answer|response|result|value)\b"
    r".{0,80}?\b(?:wrong|error|incorrect|mistake|dropped|off|miscount)",
    re.IGNORECASE)


def _family_key(family, gold, answer, reasoning="", finish_reason=""):
    """Committed answer identity per family (mirrors run_feedback_loop._early_stop_key).

    Letter branches return ``("letter", val)`` even when ``val is None`` (extraction
    failure) to stay consistent with the runtime commitment loop, where a key of
    ``("letter", None)`` is distinct from ``None`` and competes in the carry-forward
    comparison. math/math500 are numeric (the stock key raw-strings them and never
    settles, so we resolve to a number). finance/bfcl -> None (no discrete candidate to select).

    Returns ``(key, source)``: source is 'content' (explicit visible commit), 'cot'
    (recovered from the hidden CoT tail), or None (no commit) -- INTERFERENCE_CAUSAL_TABLE
    item 21. Numeric/integer branches keep the plain ``None`` no-commit convention, while
    letter branches keep the ``("letter", None)`` sentinel.
    """
    a = str(answer or "").strip()
    if not a:
        return None, None
    truncated = (finish_reason == "length")
    if family in ("math", "math500"):
        # _math500_key canonicalizes LaTeX fractions/radicals/pi, base-subscript
        # notation ('52_8'/'52₈'), and unit/degree forms so gold and a committed
        # answer resolve to the SAME decimal identity (2026-10-18: fixes gold=None).
        k = _math500_key(a)
        if k is not None:
            return ("num", k), "content"
        k = _math500_key(_cot_tail(reasoning))
        return (("num", k), "cot") if k is not None else (None, None)
    if family == "aime":
        # Clean-commit-only integer, mirroring run_feedback_loop._early_stop_key
        # exactly. The broad scorer _extract_committed_integer has 'last ='/'last line'
        # fallbacks that read a mid-proof integer out of prose-polluted final_answer
        # (deepseek/qwen flash dumps its reasoning into the answer field), mistagging a
        # bogus candidate the runtime never committed (aime_035/aime_043, 2026-10-18).
        i = _transition_committed_integer(a)
        if i is not None:
            return ("int", i), "content"
        i = _transition_committed_integer(_cot_tail(reasoning))
        return (("int", i), "cot") if i is not None else (None, None)
    if family == "gpqa":
        v, src = resolve_commit(a, reasoning, "letter", "ABCD", truncated=truncated)
        return ("letter", v), src
    if family == "bbh":
        g = str(gold or "").strip()
        if re.fullmatch(r"\(?([A-Za-z])\)?", g):
            v, src = resolve_commit(a, reasoning, "letter", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", truncated=truncated)
            return ("letter", v), src
        if re.fullmatch(r"-?\d+(\.\d+)?", g):
            n, src = resolve_commit(a, reasoning, "number", truncated=truncated)
            return (("num", n), src) if n is not None else (None, None)
        v, src = resolve_commit(a, reasoning, "text", {"yes", "no", "true", "false"}, truncated=truncated)
        return ("word", v), src
    if family == "mmlu_pro":
        v, src = resolve_commit(a, reasoning, "letter", "ABCDEFGHIJ", truncated=truncated)
        return ("letter", v), src
    if family == "hle":
        # Mirror run_feedback_loop._early_stop_key hle branch EXACTLY so the transition
        # view reproduces the runtime committed keys. multipleChoice -> option letter;
        # integer gold -> clean integer commit; symbol/word/text -> normalized raw string.
        g = str(gold or "").strip()
        if re.fullmatch(r"\(?([A-E])\)?", g):
            v, src = resolve_commit(a, reasoning, "letter", "ABCDE", truncated=truncated)
            return (("letter", v), src) if v is not None else (None, None)
        if re.fullmatch(r"-?\d+", g):
            i = _transition_committed_integer(a)
            if i is not None:
                return ("int", i), "content"
            i = _transition_committed_integer(_cot_tail(reasoning))
            return (("int", i), "cot") if i is not None else (None, None)
        return ("raw", _norm_ans(a)), "content"
    return None, None


def _key_str(key):
    if key is None:
        return None
    typ, val = key
    if val is None:
        return None
    if typ == "num" and isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def _commit_present(raw, key):
    """Is a previously committed value re-stated in this round's raw answer?

    Mirrors run_feedback_loop._commit_present: a keep-round folds the value into
    re-derivation prose instead of a standalone commit line.
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
        return re.search(r"(?<![\d])" + re.escape(s) + r"(?![\d])", raw or "") is not None
    return re.search(r"\b" + re.escape(s) + r"\b", raw or "", re.IGNORECASE) is not None


def _carries_forward(raw, prev_key):
    """Carry the previous commitment forward iff still present AND not disowned."""
    if prev_key is None or raw is None or not str(raw).strip():
        return False
    if _SELF_CORRECT_RE.search(str(raw)):
        return False
    return _commit_present(str(raw), prev_key)


def _committed_seq(rec):
    """Reproduce the runtime commitment loop -> per-round committed answer strings."""
    family = rec.get("family")
    gold = rec.get("gold_answer", "")
    ans_seq, carried_seq, source_seq = [], [], []
    prev_key = None
    for r in rec.get("rounds", []):
        raw = r.get("final_answer")
        raw_key, raw_source = _family_key(family, gold, raw, r.get("reasoning_content", ""), r.get("finish_reason", ""))
        if prev_key is not None and raw_key != prev_key and _carries_forward(raw, prev_key):
            committed_key, carried = prev_key, True
            source = "content"
        else:
            committed_key, carried = raw_key, False
            source = raw_source
        ans_seq.append(committed_key)
        carried_seq.append(carried)
        source_seq.append(source)
        if committed_key is not None and _key_str(committed_key) is not None:
            prev_key = committed_key
    return ans_seq, carried_seq, source_seq


def extract_task(rec):
    family = rec.get("family")
    gold = rec.get("gold_answer", "")
    # Normalize LaTeX/unit gold ("90^\\circ", "90 degrees") to plain numeric/letter
    # form so _family_key resolves it; frac/radical/text gold still needs sympy (Phase 3).
    gold = _strip_math_noise(_norm_unicode_math(str(gold or "")))
    gold_key = _key_str(_family_key(family, gold, gold)[0]) if gold else None

    rounds = rec.get("rounds", [])
    ans_key_seq, carried_seq, source_seq = _committed_seq(rec)
    ans_seq = [_key_str(k) for k in ans_key_seq]

    candidates = []
    for a in ans_seq:
        if a is not None and a not in candidates:
            candidates.append(a)
    freq = Counter(a for a in ans_seq if a is not None)

    # Complete state space (2026-10-16): every NON-self-loop step is a transition
    # event -- X->Y, X->None, None->X and None->None all matter. Only the X->X "hold"
    # (same committed letter carried forward) is not a transition event; those holds
    # stay visible in ``rounds`` but carry no switch decision.
    transitions = []
    for i in range(1, len(ans_seq)):
        fr, to = ans_seq[i - 1], ans_seq[i]
        if fr is not None and fr == to:
            continue
        # weak critic error directions for the OLD (from) answer. The feedback loop
        # runs the critic on ``prev_answer`` BEFORE round i generates, so round[i]
        # stores the critic's flag on round[i-1]'s answer -- exactly the OLD side of
        # this switch. ``weak_top3`` is rendered leaf -> natural-language phrase so the
        # rubric judgement (stage_b) can print a ready signpost without re-importing
        # the taxonomy mapping.
        wt3 = rounds[i].get("top3") or []
        weak_top3 = [{"leaf": d.get("leaf"),
                      "phrase": LEAF_PHRASE.get(d.get("leaf"), d.get("leaf")),
                      "prob": d.get("prob")} for d in wt3]
        transitions.append({
            "from_r": i - 1,
            "to_r": i,
            "from": fr,
            "to": to,
            "rationale": rounds[i].get("rationale"),
            "cot_tail": _cot_tail(rounds[i].get("reasoning_content", "")),
            # full hidden CoT of the "to" round, for the rubric_cut judge to inspect
            # the actual derivation (not just the 400-char concluding tail).
            "reasoning": rounds[i].get("reasoning_content", ""),
            "weak_top3": weak_top3,
            "weak_error_score": rounds[i].get("error_score"),
            # strong critic's error directions for the OLD (from) answer -- carries the
            # concrete gold-free ``check`` the critic generated, so stage_b can backlink
            # its CUT veredict to the SAME error archetype the critic flagged (the critic/
            # evaluator shared anchor, 2026-10-24).
            "critic_direction": rounds[i].get("critic_direction"),
        })

    # settle: trailing run of >= EARLY_STOP_N identical committed answers
    settled = None
    run = 1
    for i in range(len(ans_seq) - 1, 0, -1):
        if ans_seq[i] is not None and ans_seq[i] == ans_seq[i - 1]:
            run += 1
        else:
            break
    if ans_seq and ans_seq[-1] is not None and run >= EARLY_STOP_N:
        settled = ans_seq[-1]

    return {
        "task_id": rec.get("task_id"),
        "family": family,
        "question": rec.get("prompt"),
        "gold": gold_key,
        "candidates": candidates,
        "frequency": {k: freq[k] for k in candidates},
        "rounds": [
            {
                "r": r.get("round"),
                "ans": ans_seq[i],
                "correct": r.get("is_correct"),
                "carried": carried_seq[i],
                "commit_source": source_seq[i],
                "rationale": r.get("rationale"),
                "cot_tail": _cot_tail(r.get("reasoning_content", "")),
                "reasoning": r.get("reasoning_content", ""),
                "top3": r.get("top3") or [],
                "error_score": r.get("error_score"),
                "critic_direction": r.get("critic_direction"),
            }
            for i, r in enumerate(rounds)
        ],
        "transitions": transitions,
        "n_rounds": len(rounds),
        "n_no_commit": sum(1 for a in ans_seq if a is None),
        "settled_ans": settled,
        "final_ans": ans_seq[-1] if ans_seq else None,
        "start_correct": rec.get("start_correct"),
        "final_correct": rec.get("final_correct"),
        "correct_appeared": rec.get("correct_appeared"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--family", default=None, help="optional single-family filter")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(args.traj, encoding="utf-8") as fin, open(args.out, "w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            if args.family and rec.get("family") != args.family:
                continue
            fout.write(json.dumps(extract_task(rec), ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} transition records -> {args.out}")


if __name__ == "__main__":
    main()
