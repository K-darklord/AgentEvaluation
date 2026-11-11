"""
build_unified_taxonomy.py
=========================
PARALLEL scheme (does NOT replace build_error_taxonomy.py): a cross-domain
UNIFIED leaf taxonomy, detector-first. Each leaf is ONE family-agnostic rule
applied wherever its required signal exists, so the SAME leaf can genuinely
fire across families (unlike the per-family 19-leaf taxonomy where an error
type is defined within a single family).

Motivation (user directive 2026-09-29): the static matrix is a projection of
whichever grouping we impose; L1/L2 splitting is tautological. A detector-first
unified leaf set is the only static way to let the same operation co-occur
cross-domain, so we can measure block-diagonality honestly and prepare for
Phase-2 (more families / weak models) where the same rules extend unchanged.

8 unified leaves (all rules operate on final_answer vs gold_answer + stored
judge/tool signals; fine distinctions retained as signals["subtype"]):
  empty             blank final answer                                  [all]
  missing_candidate non-blank but no token of the expected type        [all]
  format_violation  token present but wrong form contract              [mmlu,bfcl,edge]
  numeric_error     both sides numeric, values mismatch                [math,math500,finance]
  wrong_target      right form, wrong content (non-numeric)            [mmlu,bfcl,finance]
  retrieval_failure zero tool calls (tool family)                      [finance]
  contradiction     judge dealbreaker (factual contradiction)          [finance]
  non_converged     ran a tool loop but tier1==tier2==0               [finance]
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRONG_BANK = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
OUT_DIR = ROOT / "experiments" / "unified_taxonomy_v1"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
FAMILIES = ["math", "math500", "mmlu_pro", "finance", "bfcl"]
VERSION = "v1.0-unified"

SIMPLE_FACTORS = (2, 3, 4, 5, 6, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 6,
                  3 / 2, 2 / 3, 4 / 3, 3 / 4, 5 / 2, 2 / 5)


def _extract_numbers(s):
    if s is None:
        return []
    cleaned = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(s))
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", cleaned)]
    return [n for n in nums if not (1900 < n < 2100)]


def _ratio_class(r):
    if r <= -0.9:
        return "sign_flip"
    ar = abs(r)
    if ar < 0.1 or ar > 10.0:
        return "magnitude"
    if abs(r - 1.0) <= 0.10:
        return "near_miss"
    for k in SIMPLE_FACTORS:
        if abs(r - k) / abs(k) <= 0.05:
            return "factor"
    return "plain"


def classify(final, gold, family, sig):
    """Return (unified_leaf, subtype, extra_signals). Unified rule, family only
    selects the 'expected answer type', not a different error vocabulary."""
    fs = str(final).strip() if final is not None else ""
    gs = str(gold).strip() if gold is not None else ""

    if not fs:
        return "empty", None, {}

    if family in ("math", "math500"):
        pnum, gnum = _extract_numbers(fs), _extract_numbers(gs)
        if not pnum:
            return "missing_candidate", None, {}
        if not gnum:
            return "format_violation", "gold_not_numeric", {}
        r = float("inf") if gnum[0] == 0 else pnum[0] / gnum[0]
        return "numeric_error", _ratio_class(r), {"ratio": round(r, 6),
                                                  "gold_num": gnum[0], "pred_num": pnum[0]}

    if family == "mmlu_pro":
        letters = re.findall(r"\b[A-J]\b", fs.upper())
        if not letters:
            return "missing_candidate", None, {}
        if len(set(letters)) > 1:
            return "format_violation", "multiple_letters", {"letters": letters}
        if gs.upper() in set(letters):
            return "correct", None, {}
        return "wrong_target", "wrong_option", {"pred": letters[0], "gold": gs.upper()}

    if family == "bfcl":
        pred = None
        try:
            pred = json.loads(fs)
        except (json.JSONDecodeError, TypeError):
            pred = None
        if pred is None:
            return "format_violation", "non_json", {}
        gt = gold if isinstance(gold, list) else None
        if gt is None:
            try:
                gt = json.loads(gs)
            except (json.JSONDecodeError, TypeError):
                gt = None
        if not gt:
            return "missing_candidate", "no_gold", {}
        name = str(pred.get("name", "")).replace(".", "_")
        entry = None
        for e in gt:
            if isinstance(e, dict):
                for k, v in e.items():
                    if str(k).replace(".", "_") == name:
                        entry = v
                        break
            if entry is not None:
                break
        if entry is None:
            return "wrong_target", "wrong_function", {"name": name}
        args = pred.get("arguments", "{}")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                args = {}
        if not isinstance(args, dict):
            args = {}
        for param, accepted in entry.items():
            alist = accepted if isinstance(accepted, list) else [accepted]
            if not any(str(args.get(param, "")) == str(a) for a in alist):
                return "wrong_target", "wrong_argument", {"param": param}
        return "correct", None, {}

    if family == "finance":
        n_tool = sig.get("n_tool_calls", 0) or 0
        dealbreaker = bool(sig.get("dealbreaker", False))
        t1 = sig.get("t1"); t2 = sig.get("t2")
        if n_tool == 0:
            return "retrieval_failure", None, {}
        if dealbreaker:
            return "contradiction", None, {}
        if t1 is not None and t2 is not None and float(t1) == 0 and float(t2) == 0:
            return "non_converged", None, {}
        pnum, gnum = _extract_numbers(fs), _extract_numbers(gs)
        if pnum and gnum:
            r = float("inf") if gnum[0] == 0 else pnum[0] / gnum[0]
            return "numeric_error", _ratio_class(r), {"ratio": round(r, 6)}
        return "wrong_target", "qualitative_wrong", {}

    return "missing_candidate", None, {}


def main():
    rows = [json.loads(l) for l in open(WRONG_BANK)]
    out_rows = []
    dist = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        leaf, sub, extra = classify(r["final_answer"], r["gold_answer"],
                                    r["family"], r.get("signals", {}))
        if leaf == "correct":
            continue  # defensive; should not appear in wrong bank
        out_rows.append({"task_id": r["task_id"], "family": r["family"],
                         "model": r["model"], "unified_leaf": leaf,
                         "subtype": sub, "sub_signals": extra})
        dist[r["family"]][r["model"]][leaf] += 1

    leaf_fam = defaultdict(set)
    for r in out_rows:
        leaf_fam[r["unified_leaf"]].add(r["family"])

    print("=" * 74)
    print("Unified-leaf block-diagonality (detector-first, 8 leaves)")
    print("=" * 74)
    all_leaves = ["empty", "missing_candidate", "format_violation", "numeric_error",
                  "wrong_target", "retrieval_failure", "contradiction", "non_converged"]
    for l in all_leaves:
        fams = sorted(leaf_fam.get(l, set()))
        status = "CROSS-DOMAIN" if len(fams) > 1 else ("single-family" if len(fams) == 1 else "never-fires")
        print(f"  {l:<20} {str(fams):<40} {status}")

    print("\n" + "=" * 74)
    print("Unified-leaf distribution (family x model)")
    print("=" * 74)
    for fam in FAMILIES:
        print(f"\n[{fam}]")
        for m in MODELS:
            c = dist[fam][m]
            if not c:
                continue
            s = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
            print(f"  {m:<18} n={sum(c.values()):>3}  {{{s}}}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "wrong_bank_unified.jsonl", "w") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    payload = {
        "version": VERSION,
        "note": "detector-first unified leaf; parallel to per-family 19-leaf taxonomy",
        "leaf_family_coverage": {l: sorted(leaf_fam.get(l, set())) for l in all_leaves},
        "distribution": {fam: {m: dict(c) for m, c in models.items()}
                         for fam, models in dist.items()},
    }
    with open(OUT_DIR / "unified_distribution.json", "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {OUT_DIR / 'wrong_bank_unified.jsonl'}")
    print(f"[written] {OUT_DIR / 'unified_distribution.json'}")


if __name__ == "__main__":
    main()
