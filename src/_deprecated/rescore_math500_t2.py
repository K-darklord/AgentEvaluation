"""rescore_math500_t2.py
======================
T2 (registered intervention) rescue for MATH-500 false negatives left after T1b.

For each math500 row still judged WRONG by the deterministic T1 grafter, ask the
deepseek-v4-pro judge to read the full model response, extract the FINAL answer, and
compare it to the KNOWN gold (CORRECT / INCORRECT). Rows the judge flips to correct are
written back to results.csv, error_report.json, and the merged summary.json (a surgical
math500-only update plus a per-model `math500_t2_rescue` before/after record).

The judge key is loaded from .env (TOKEN_PLAN_API_KEY / T2_JUDGE_API_KEY) — never
hard-coded. The macOS system proxy is bypassed, matching phase1_baseline._force_no_proxy.

Run:  python3 src/rescore_math500_t2.py
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "experiments" / "d1_baseline_20260928_201128"
MATHSRC = ROOT / "data" / "raw" / "math500_test.jsonl"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
PASS = 0.5  # config.FINAL_PASS_THRESHOLD


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _force_no_proxy() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_load_dotenv()
_force_no_proxy()

from src.evaluator import _score_t2_extract_judge  # noqa: E402


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_prompt_index() -> dict:
    idx = {}
    with MATHSRC.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            idx[f"math500_{i:03d}"] = d.get("problem", "").strip()
    return idx


def rescore_model(model_dir: Path, prompt_idx: dict) -> dict:
    csv_path = model_dir / "results.csv"
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    judged = flips = 0
    for r in rows:
        if not r["task_id"].startswith("math500_"):
            continue
        if _truthy(r["is_correct"]):
            continue  # T2 only rescues rows T1 already judged wrong
        judged += 1
        row = {
            "prompt": prompt_idx.get(r["task_id"], ""),
            "gold_answer": r["gold_answer"],
            "final_answer": r["final_answer"],
        }
        s = _score_t2_extract_judge(row)
        verdict = "CORRECT" if s >= PASS else "incorrect"
        if s >= PASS:
            flips += 1
            r["is_correct"] = "True"
            r["error_type"] = "correct"
            r["tier2_llm_semantic"] = "1.0"
            r["final_score"] = "1.0"
        print(f"    {r['task_id']}: T2={verdict}")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    n_api = sum(1 for r in rows if r.get("error_type") == "api_failure")
    n_valid = n - n_api
    correct = sum(1 for r in rows if _truthy(r.get("is_correct")))
    errors = Counter(r.get("error_type", "unknown") for r in rows)
    lats = [_f(r["total_latency_ms"]) for r in rows if r.get("total_latency_ms") not in ("", None)]
    avg_latency = sum(lats) / n if n else 0.0
    valid = [r for r in rows if r.get("error_type") != "api_failure"]
    vn = len(valid) if valid else 1
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
            "t1_numeric_avg": round(sum(_f(r["tier1_numeric"]) for r in valid) / vn, 4),
            "t2_llm_semantic_avg": round(sum(_f(r["tier2_llm_semantic"]) for r in valid) / vn, 4),
            "final_score_avg": round(sum(_f(r["final_score"]) for r in valid) / vn, 4),
            "dealbreakers_triggered": sum(1 for r in valid if _truthy(r.get("dealbreaker_triggered"))),
        },
    }
    (model_dir / "error_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"judged": judged, "flips": flips}


def update_summary(flips_by_model: dict) -> None:
    sp = D1 / "summary.json"
    summary = json.loads(sp.read_text(encoding="utf-8"))
    for model, flips in flips_by_model.items():
        m = summary["models"][model]
        before = m["per_domain"]["math500"]["correct"]
        m["per_domain"]["math500"]["correct"] += flips
        m["error_distribution"]["correct"] = m["error_distribution"].get("correct", 0) + flips
        m["error_distribution"]["numeric_error"] = m["error_distribution"].get("numeric_error", 0) - flips
        n = m["n_valid_tasks"] + m["n_api_failures"]
        m["accuracy"] = m["error_distribution"]["correct"] / n if n else 0
        m["accuracy_excl_api_failures"] = m["error_distribution"]["correct"] / m["n_valid_tasks"] if m["n_valid_tasks"] else 0
        m["math500_t2_rescue"] = {"before": before, "after": before + flips, "delta": flips}
    sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    prompt_idx = load_prompt_index()
    flips_by_model = {}
    for model in MODELS:
        print(f"[{model}]")
        res = rescore_model(D1 / model, prompt_idx)
        flips_by_model[model] = res["flips"]
        print(f"  judged={res['judged']}  flips={res['flips']}")
    update_summary(flips_by_model)
    print(f"TOTAL flips: {sum(flips_by_model.values())}")
    print("Wrote: per-model results.csv + error_report.json, and summary.json")
