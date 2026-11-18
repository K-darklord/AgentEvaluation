"""Official BBEH evaluator bridge.

Loads data/raw/bbeh/bbeh/evaluate.py (BIG-Bench Extra Hard official scorer) via
importlib and re-exports its functions VERBATIM (the spec requires using the
official evaluate_correctness / preprocess_sample as-is). The official file runs
print() example calls at module bottom; they are suppressed on import.

answer_key() implements the B1 candidate-identity rule (docs/SECOND_BENCHMARK_SPEC.md
sec 2): key = preprocess_sample output; numeric when parseable; None when the answer
is empty or truncated (finish_reason == "length").
"""
from __future__ import annotations
import importlib.util, io, sys
from pathlib import Path

_BBEH_EVAL_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "bbeh" / "bbeh" / "evaluate.py"


def _load():
    spec = importlib.util.spec_from_file_location("bbeh_evaluate", str(_BBEH_EVAL_PATH))
    mod = importlib.util.module_from_spec(spec)
    _stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.stdout = _stdout
    return mod


_mod = _load()
evaluate_correctness = _mod.evaluate_correctness
preprocess_sample = _mod.preprocess_sample


def answer_key(answer, finish_reason: str = ""):
    """Candidate-identity key for one round's committed answer (or None).

    key = official preprocess_sample output; numeric when parseable; None when the
    answer is empty or the round was truncated (finish_reason == "length").
    """
    a = (answer or "").strip()
    if not a or finish_reason == "length":
        return None
    k = preprocess_sample(a)
    if k == "":
        return None
    try:
        v = float(k)
        if v.is_integer():
            return int(v)
        return v
    except ValueError:
        return k
