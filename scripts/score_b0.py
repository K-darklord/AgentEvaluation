#!/usr/bin/env python3
"""B0 first-answer scoring (rule-based, reproducible, no model judge).

  - BBEH      : official evaluate_correctness(final_answer, gold_answer)
  - GSM8K     : last \\boxed{...} numeric comparison, tolerance 1e-6
  - OlymMATH  : official math_verify (extract_boxed + format_for_math_verify + parse/verify)

Writes experiments/b0_A_qwen3.8-flash-payg/b0_scores.json with per-question correctness
and per-task (BBEH) / per-split (OlymMATH EASY/HARD) first-answer accuracy.

Run: python3 scripts/score_b0.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.bbeh_eval import evaluate_correctness  # noqa: E402
from math_verify import parse, verify  # noqa: E402

MODEL = "qwen3.8-flash-payg"
B0_DIR = REPO / "experiments" / f"b0_A_{MODEL}"
OUT = B0_DIR / "b0_scores.json"


def extract_boxed(text: str) -> str:
    """Last \\boxed{...} content with nested-brace support (official OlymMATH local_tester)."""
    if not text:
        return ""
    stack = []
    contents = []
    i = 0
    start = -1
    n = len(text)
    while i < n:
        if text[i:i + 7] == "\\boxed{" and (i == 0 or text[i - 1] != "\\"):
            if not stack:
                start = i + 7
            stack.append("{")
            i += 7
        elif text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            stack.append("{")
            i += 1
        elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
            if stack:
                stack.pop()
                if not stack and start != -1:
                    contents.append(text[start:i])
                    start = -1
            i += 1
        else:
            i += 1
    if contents:
        return contents[-1]
    m = re.findall(r"\\boxed\{((?:[^{}]|{[^{}]*})*)\}", text)
    return m[-1] if m else ""


def _num(s: str):
    s = str(s).strip().replace(",", "").replace("$", "").replace("%", "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)", s)
    if m:
        den = float(m.group(2))
        if den == 0:
            return None
        return float(m.group(1)) / den
    try:
        return float(s)
    except ValueError:
        return None


def gsm8k_correct(final_answer: str, gold: str) -> bool:
    pred = _num(extract_boxed(final_answer))
    g = _num(gold)
    if pred is None or g is None:
        return False
    return abs(pred - g) <= 1e-6


def format_for_math_verify(answer: str) -> str:
    if not answer:
        return "$.$"
    answer = answer.strip()
    if answer.startswith("$"):
        answer = answer[1:]
    if answer.endswith("$"):
        answer = answer[:-1]
    answer = answer.strip()
    return f"${answer}$" if answer else "$.$"


def olymmath_correct(final_answer: str, gold: str) -> bool:
    b = extract_boxed(final_answer)
    try:
        gp = parse(format_for_math_verify(gold))
        ep = parse(format_for_math_verify(b))
        return bool(verify(gp, ep))
    except Exception:
        return False


def load_jsonl(path: Path):
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def summarize(correct: int, total: int) -> dict:
    return {"correct": correct, "total": total,
            "accuracy": round(correct / total, 6) if total else 0.0}


def main() -> None:
    out = {"model": MODEL, "benchmarks": {}}

    # BBEH
    rows = load_jsonl(B0_DIR / "bbeh.jsonl")
    per_task = {}
    details = {}
    for d in rows:
        c = bool(evaluate_correctness(d.get("final_answer", ""), d.get("gold_answer", "")))
        details[d["task_id"]] = c
        t = d.get("task", "?")
        per_task.setdefault(t, [0, 0])
        per_task[t][0] += 1
        per_task[t][1] += int(c)
    out["benchmarks"]["bbeh"] = {
        "total": len(rows),
        "summary": summarize(sum(int(v) for v in details.values()), len(rows)),
        "per_task": {t: summarize(c, n) for t, (n, c) in per_task.items()},
        "per_question": details,
    }

    # GSM8K
    rows = load_jsonl(B0_DIR / "gsm8k.jsonl")
    details = {d["task_id"]: gsm8k_correct(d.get("final_answer", ""), d.get("gold_answer", "")) for d in rows}
    out["benchmarks"]["gsm8k"] = {
        "total": len(rows),
        "summary": summarize(sum(int(v) for v in details.values()), len(rows)),
        "per_question": details,
    }

    # OlymMATH
    rows = load_jsonl(B0_DIR / "olymmath.jsonl")
    per_split = {}
    details = {}
    for d in rows:
        c = olymmath_correct(d.get("final_answer", ""), d.get("gold_answer", ""))
        details[d["task_id"]] = c
        s = d.get("split", "?")
        per_split.setdefault(s, [0, 0])
        per_split[s][0] += 1
        per_split[s][1] += int(c)
    out["benchmarks"]["olymmath"] = {
        "total": len(rows),
        "summary": summarize(sum(int(v) for v in details.values()), len(rows)),
        "per_split": {s: summarize(c, n) for s, (n, c) in per_split.items()},
        "per_question": details,
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"wrote {OUT}", flush=True)
    for b in ("gsm8k", "bbeh", "olymmath"):
        s = out["benchmarks"][b]["summary"]
        print(f"{b}: {s['correct']}/{s['total']} = {s['accuracy']:.4f}", flush=True)
    print("BBEH per task:", flush=True)
    for t, s in sorted(out["benchmarks"]["bbeh"]["per_task"].items()):
        print(f"  {t}: {s['correct']}/{s['total']} = {s['accuracy']:.4f}", flush=True)
    print("OlymMATH per split:", flush=True)
    for t, s in sorted(out["benchmarks"]["olymmath"]["per_split"].items()):
        print(f"  {t}: {s['correct']}/{s['total']} = {s['accuracy']:.4f}", flush=True)


if __name__ == "__main__":
    main()
