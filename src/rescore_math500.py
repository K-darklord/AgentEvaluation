"""
rescore_math500.py
==================
Re-score MATH-500 rows in d1_baseline with the fixed _score_math500 grader and
write back the canonical artifacts: per-model results.csv, per-model
error_report.json, and the merged summary.json. Zero API cost: reads stored
answers only, never re-runs any model or the T2 judge.

Run:  python3 src/rescore_math500.py
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from src.evaluator import _score_math500

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "experiments" / "d1_baseline_20260928_201128"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
PASS = 0.5  # config.FINAL_PASS_THRESHOLD


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def rescore_model(model_dir: Path) -> dict:
    """Re-score math500 rows in results.csv; rewrite results.csv + error_report.json.
    Return {"flips": int, "regressions": int}."""
    csv_path = model_dir / "results.csv"
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    flips = regressions = 0
    for r in rows:
        if not r["task_id"].startswith("math500_"):
            continue
        s = _score_math500({"final_answer": r["final_answer"], "gold_answer": r["gold_answer"]})
        is_c = s >= PASS
        was_c = _truthy(r["is_correct"])
        if is_c and not was_c:
            flips += 1
        elif was_c and not is_c:
            regressions += 1
        r["is_correct"] = "True" if is_c else "False"
        r["error_type"] = "correct" if is_c else "numeric_error"
        r["tier1_numeric"] = str(round(s, 4))
        r["final_score"] = str(round(s, 4))

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # Rebuild error_report.json from the updated rows (same schema as Evaluator.score).
    n = len(rows)
    n_api = sum(1 for r in rows if r.get("error_type") == "api_failure")
    n_valid = n - n_api
    correct = sum(1 for r in rows if _truthy(r.get("is_correct")))
    errors = Counter(r.get("error_type", "unknown") for r in rows)
    lats = [_f(r["total_latency_ms"]) for r in rows if r.get("total_latency_ms") not in ("", None)]
    avg_latency = sum(lats) / n if n else 0.0

    valid = [r for r in rows if r.get("error_type") != "api_failure"]
    vn = len(valid) if valid else 1
    t1_avg = sum(_f(r["tier1_numeric"]) for r in valid) / vn
    t2_avg = sum(_f(r["tier2_llm_semantic"]) for r in valid) / vn
    final_avg = sum(_f(r["final_score"]) for r in valid) / vn
    dealbreakers = sum(1 for r in valid if _truthy(r.get("dealbreaker_triggered")))

    report = {
        "n_tasks": n,
        "n_valid_tasks": n_valid,
        "n_api_failures": n_api,
        "accuracy": correct / n if n else 0,
        "accuracy_excl_api_failures": correct / n_valid if n_valid else 0,
        "error_distribution": dict(errors),
        "avg_latency_ms": round(avg_latency, 1),
        "total_cost_usd": 0.0,
        "tier_breakdown": {
            "t1_numeric_avg": round(t1_avg, 4),
            "t2_llm_semantic_avg": round(t2_avg, 4),
            "final_score_avg": round(final_avg, 4),
            "dealbreakers_triggered": dealbreakers,
        },
    }
    (model_dir / "error_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"flips": flips, "regressions": regressions}


def update_summary(flips_by_model: dict) -> None:
    """Surgically bump math500 counts + accuracy + error_distribution in summary.json.
    Preserve mmlu_pro_int16 + merged notes (not mechanically derivable from results.csv)."""
    sp = D1 / "summary.json"
    summary = json.loads(sp.read_text(encoding="utf-8"))
    for model, flips in flips_by_model.items():
        if flips == 0:
            continue
        m = summary["models"][model]
        m["per_domain"]["math500"]["correct"] += flips
        m["error_distribution"]["correct"] = m["error_distribution"].get("correct", 0) + flips
        m["error_distribution"]["numeric_error"] = m["error_distribution"].get("numeric_error", 0) - flips
        n = m["n_valid_tasks"] + m["n_api_failures"]
        correct_total = m["error_distribution"]["correct"]
        m["accuracy"] = correct_total / n if n else 0
        m["accuracy_excl_api_failures"] = correct_total / m["n_valid_tasks"] if m["n_valid_tasks"] else 0
    sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    flips_by_model = {}
    for model in MODELS:
        res = rescore_model(D1 / model)
        flips_by_model[model] = res["flips"]
        reg = res["regressions"]
        print(f"{model:20} fn->tp flips: {res['flips']:3d}   regressions: {reg}")
    update_summary(flips_by_model)
    print(f"TOTAL flips: {sum(flips_by_model.values())}")
    print("Wrote: per-model results.csv + error_report.json, and summary.json")
