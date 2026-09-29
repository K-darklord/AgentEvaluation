"""align_bfcl.py
Merge the BFCL re-run truth (tool_choice=auto, experiments/bfcl_rerun_auto) back into the
canonical d1_baseline artifacts: per-model results.csv (replace the 50 bfcl_* rows), the
per-model error_report.json, and the merged summary.json. Surgical: only bfcl fields move;
math500 (T1b) and mmlu_pro (INT-16) in summary.json are left untouched.

Run:  python3 -m src.align_bfcl
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "experiments" / "d1_baseline_20260928_201128"
RERUN = ROOT / "experiments" / "bfcl_rerun_auto"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
N_TASKS = 250


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def merge_bfcl_rows(model: str) -> None:
    """Replace bfcl_* rows in d1 results.csv with the re-run rows (same task_id + schema)."""
    csv_path = D1 / model / "results.csv"
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    rerun_rows = list(csv.DictReader((RERUN / model / "results.csv").open(encoding="utf-8")))
    rerun_by_id = {r["task_id"]: r for r in rerun_rows}
    for r in rows:
        if r["task_id"].startswith("bfcl") and r["task_id"] in rerun_by_id:
            src = rerun_by_id[r["task_id"]]
            for k in fieldnames:
                if k in src:
                    r[k] = src[k]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def rebuild_error_report(model: str) -> None:
    rows = list(csv.DictReader((D1 / model / "results.csv").open(encoding="utf-8")))
    n = len(rows)
    n_api = sum(1 for r in rows if r.get("error_type") == "api_failure")
    n_valid = n - n_api
    correct = sum(1 for r in rows if _truthy(r.get("is_correct")))
    errors = Counter(r.get("error_type", "unknown") for r in rows)
    lats = [_f(r["total_latency_ms"]) for r in rows if r.get("total_latency_ms") not in ("", None)]
    avg = sum(lats) / n if n else 0.0
    valid = [r for r in rows if r.get("error_type") != "api_failure"]
    vn = len(valid) if valid else 1
    report = {
        "n_tasks": n,
        "n_valid_tasks": n_valid,
        "n_api_failures": n_api,
        "accuracy": correct / n if n else 0,
        "accuracy_excl_api_failures": correct / n_valid if n_valid else 0,
        "error_distribution": dict(errors),
        "avg_latency_ms": round(avg, 1),
        "total_cost_usd": 0.0,
        "tier_breakdown": {
            "t1_numeric_avg": round(sum(_f(r["tier1_numeric"]) for r in valid) / vn, 4),
            "t2_llm_semantic_avg": round(sum(_f(r["tier2_llm_semantic"]) for r in valid) / vn, 4),
            "final_score_avg": round(sum(_f(r["final_score"]) for r in valid) / vn, 4),
            "dealbreakers_triggered": sum(1 for r in valid if _truthy(r.get("dealbreaker_triggered"))),
        },
    }
    (D1 / model / "error_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_summary(rerun_models: dict) -> None:
    sp = D1 / "summary.json"
    summary = json.loads(sp.read_text(encoding="utf-8"))
    for model in MODELS:
        new_correct = int(round(rerun_models[model]["accuracy"] * 50))
        mod = summary["models"][model]
        old_correct = mod["per_domain"]["bfcl"]["correct"]
        old_wrong = 50 - old_correct
        new_wrong = 50 - new_correct
        d_correct = new_correct - old_correct
        if d_correct == 0 and new_wrong == old_wrong:
            continue
        ed = mod["error_distribution"]
        old_label = "api_failure" if model == "qwen3.8-flash" else "complete_failure"
        ed[old_label] = ed.get(old_label, 0) - old_wrong
        if ed[old_label] <= 0:
            ed.pop(old_label, None)
        if new_wrong > 0:
            ed["complete_failure"] = ed.get("complete_failure", 0) + new_wrong
        ed["correct"] = ed.get("correct", 0) + d_correct
        mod["per_domain"]["bfcl"]["correct"] = new_correct
        n_api = ed.get("api_failure", 0)
        mod["n_api_failures"] = n_api
        mod["n_valid_tasks"] = N_TASKS - n_api
        correct_total = ed.get("correct", 0)
        mod["accuracy"] = correct_total / N_TASKS
        mod["accuracy_excl_api_failures"] = correct_total / (N_TASKS - n_api) if (N_TASKS - n_api) else 0
    sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    rerun = json.loads((RERUN / "bfcl_rerun_summary.json").read_text(encoding="utf-8"))
    for model in MODELS:
        merge_bfcl_rows(model)
        rebuild_error_report(model)
        print(f"{model:18} bfcl -> {int(round(rerun['models'][model]['accuracy']*50))}/50")
    update_summary(rerun["models"])
    print("aligned: results.csv + error_report.json + summary.json")
