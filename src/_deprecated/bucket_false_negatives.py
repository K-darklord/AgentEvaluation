"""bucket_false_negatives.py
Quantify the false-negative (extraction-artifact) rate in the v2 wrong bank.
Re-grades every wrong record with a lenient final-answer extractor (boxed /
last-'='/last-line/last-token) to separate: (b) extraction false negatives,
(c) format violations, (a) genuine errors. Finance is reported as unresolved
(needs LLM-judge re-run). Deterministic, no API.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluator import _score_math500, _score_mmlu_pro, _score_bfcl, score_numeric

WB = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
rows = [json.loads(l) for l in WB.read_text().splitlines() if l.strip()]

_BOXED = re.compile(r"\\boxed\s*\{([^{}]*)\}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_LETTER = re.compile(r"\b[A-J]\b")


def is_year(n):
    try:
        return 1900 < float(n) < 2100
    except ValueError:
        return False


def candidates(pred):
    out = []
    for m in _BOXED.findall(pred):
        out.append(m.strip())
    if "=" in pred:
        out.append(pred.rsplit("=", 1)[1].strip())
    lines = [l.strip() for l in pred.splitlines() if l.strip()]
    if lines:
        out.append(lines[-1])
    nums = [n for n in _NUM.findall(pred) if not is_year(n)]
    if nums:
        out.append(nums[-1])
    lets = _LETTER.findall(pred)
    if lets:
        out.append(lets[-1].upper())
    seen, res = set(), []
    for c in out:
        if c and c not in seen and len(c) <= 60:
            seen.add(c)
            res.append(c)
    return res


def grade(fam, gold, pred):
    row = {"gold_answer": gold, "final_answer": pred}
    try:
        if fam == "math500":
            return _score_math500(row) >= 0.999
        if fam == "math":
            return bool(score_numeric(gold, pred))
        if fam == "mmlu_pro":
            return _score_mmlu_pro(row) >= 0.999
        if fam == "bfcl":
            return _score_bfcl(row) >= 0.999
    except Exception:
        return False
    return False


def gold_key(fam, gold):
    if fam in ("math500", "math"):
        for n in _NUM.findall(gold):
            if not is_year(n):
                return n
    if fam == "mmlu_pro":
        m = _LETTER.search(gold)
        return m.group(0).upper() if m else None
    return None


def loose_present(fam, gold, pred):
    k = gold_key(fam, gold)
    if k is None:
        return False
    if fam == "mmlu_pro":
        return k in [x.upper() for x in _LETTER.findall(pred)]
    return k in _NUM.findall(pred)


def has_clean(fam, pred):
    if fam in ("math500", "math"):
        return bool(_NUM.search(pred))
    if fam == "mmlu_pro":
        return bool(_LETTER.search(pred))
    if fam == "bfcl":
        return bool(re.search(r"\{.*\}", pred, re.S))
    return True


stats = defaultdict(lambda: Counter())
bucket_rows = []
for r in rows:
    fam, pred, gold = r["family"], str(r["final_answer"]), str(r["gold_answer"])
    if fam == "finance":
        b = "finance_unresolved"
    elif any(grade(fam, gold, c) for c in candidates(pred)):
        b = "b_false_negative"
    elif not has_clean(fam, pred):
        b = "c_format_violation"
    else:
        b = "a_genuine"
    loose = fam != "finance" and loose_present(fam, gold, pred)
    bucket_rows.append({**r, "bucket": b, "loose_present": loose})
    stats[fam][b] += 1
    stats["ALL"][b] += 1

print("=== strict bucketing (position-based extractor) by family ===")
print(f"{'family':10s} {'total':>6s} {'b_fn':>5s} {'c_fmt':>5s} {'a_gen':>5s} {'fin_unres':>9s}")
for fam in ["math", "math500", "mmlu_pro", "bfcl", "finance"]:
    c = stats[fam]
    print(f"{fam:10s} {sum(c.values()):6d} {c['b_false_negative']:5d} "
          f"{c['c_format_violation']:5d} {c['a_genuine']:5d} {c['finance_unresolved']:9d}")

det = [r for r in bucket_rows if r["family"] != "finance"]
b_strict = sum(1 for r in det if r["bucket"] == "b_false_negative")
b_loose = sum(1 for r in det if r["loose_present"])
c_fmt = sum(1 for r in det if r["bucket"] == "c_format_violation")
tot_det = len(det)
tot_all = len(rows)
print()
print(f"deterministic domains (non-finance): {tot_det} wrong")
print(f"  b_false_negative STRICT (answer produced, grader missed): {b_strict} ({b_strict/tot_det:.1%})")
print(f"  b_false_negative LOOSE  (gold key token anywhere in pred): {b_loose} ({b_loose/tot_det:.1%})")
print(f"  c_format_violation (no clean answer emitted):               {c_fmt} ({c_fmt/tot_det:.1%})")
print(f"  a_genuine (really wrong, strict):                           {tot_det-b_strict-c_fmt}")
print(f"TOTAL wrong bank: {tot_all};  strict FN {b_strict}/{tot_all} = {b_strict/tot_all:.1%};  finance unresolved {stats['finance']['finance_unresolved']}")

print()
print("=== b_false_negative (strict) per model ===")
mc = Counter(r["model"] for r in det if r["bucket"] == "b_false_negative")
print(dict(mc))

out = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank_bucketed.jsonl"
with open(out, "w") as f:
    for r in bucket_rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("\nannotated ->", out.relative_to(ROOT))
