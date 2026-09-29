"""
diagnose_capacity_matrix.py
===========================
Phase 1 (probe) build-before-burn item 1: information-sufficiency audit of the
capability-matrix tensor  model x task-family x error-type.

Purpose
-------
Before building the critique reference library (error taxonomy), check whether
the d1_baseline data carries enough signal to anchor per-family error classes.
This script is read-only: it loads results.csv + trajectories.jsonl and reports
diagnostics. No API, no model loading.

Diagnostics emitted
-------------------
  D1  per (family, model): correct / wrong counts and the exact error-type mix.
  D2  error-class richness per family (how many DISTINCT non-correct labels).
  D3  anchoring sufficiency: for each family, number of wrong questions (raw material
      for the error taxonomy) vs. the >=5 per-class threshold named in the plan.
  D4  ceiling / degenerate detection: families with ~100% accuracy (no error signal)
      or with only a single non-correct label (binary, no discrimination).
  D5  between-model discrimination within family (are error profiles identical?).

Authoritative data: experiments/d1_baseline_20260928_201128/ (math/math500/finance/bfcl),
plus experiments/mmlu_pro_int16_full/ for mmlu_pro (INT-16 letter-only MCQ rerun).
"""
from __future__ import annotations
import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "experiments" / "d1_baseline_20260928_201128"
INT16 = ROOT / "experiments" / "mmlu_pro_int16_full"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]

# task_id prefix -> task family (taxonomy axis of the capability matrix)
PREFIX2FAMILY = {
    "gsm8k": "math",
    "math500": "math500",
    "mmlu": "mmlu_pro",
    "fab": "finance",
    "bfcl": "bfcl",
}
FAMILY_ORDER = ["math", "math500", "mmlu_pro", "finance", "bfcl"]
# non-correct error labels present in the current evaluator (see _label_row_tiered)
ERROR_LABELS = ["numeric_error", "complete_failure", "factual_contradiction",
                "qualitative_incomplete", "api_failure"]


def family_of(task_id: str) -> str:
    for prefix, fam in PREFIX2FAMILY.items():
        if task_id.startswith(prefix + "_"):
            return fam
    return "other"


def load_results_csv(model: str, base: Path = D1) -> list[dict]:
    with open(base / model / "results.csv") as f:
        return list(csv.DictReader(f))


def main() -> None:
    # tensor[(family, model, error_type)] = count
    tensor = defaultdict(lambda: Counter())
    for model in MODELS:
        for row in load_results_csv(model):
            fam = family_of(row["task_id"])
            tensor[(fam, model)][row["error_type"]] += 1

    # D1 + D2 + D5: full cross-tab from d1_baseline (mmlu_pro here is pre-INT16)
    print("=" * 78)
    print("D1/D2  model x family x error-type cross-tab (d1_baseline)")
    print("=" * 78)
    for fam in FAMILY_ORDER:
        print(f"\n[{fam}]")
        for model in MODELS:
            c = tensor[(fam, model)]
            total = sum(c.values())
            correct = c["correct"]
            errs = {lbl: c[lbl] for lbl in ERROR_LABELS if c[lbl] > 0}
            err_str = ", ".join(f"{lbl}={n}" for lbl, n in errs.items())
            print(f"  {model:<18} correct={correct:>3}/{total:<3}  errors={{{err_str}}}")

    # D3/D4: anchoring sufficiency + ceiling / degenerate detection
    print("\n" + "=" * 78)
    print("D3/D4  anchoring sufficiency + degeneracy (exclude api_failure as non-signal)")
    print("=" * 78)
    report = {}
    for fam in FAMILY_ORDER:
        wrong_by_model = {}
        label_richness = {}
        for model in MODELS:
            c = tensor[(fam, model)]
            total = sum(c.values())
            wrong = total - c["correct"] - c["api_failure"]   # real, signal-carrying errors
            wrong_by_model[model] = wrong
            # distinct non-correct error labels (excluding api_failure)
            real_labels = {lbl for lbl in ERROR_LABELS if lbl != "api_failure" and c[lbl] > 0}
            label_richness[model] = sorted(real_labels)

        n_wrong_total = sum(wrong_by_model.values())
        n_models_with_error = sum(1 for w in wrong_by_model.values() if w > 0)
        rich = set().union(*label_richness.values())

        # ceiling: every model >=95% correct
        accs = {m: tensor[(fam, m)]["correct"] / max(1, sum(tensor[(fam, m)].values()))
                for m in MODELS}
        ceiling = all(a >= 0.95 for a in accs.values())
        # degenerate: only one distinct non-correct label across all models
        degenerate = len(rich) <= 1

        anchors = {lbl: sum(tensor[(fam, m)][lbl] for m in MODELS if lbl != "api_failure")
                   for lbl in ERROR_LABELS if lbl != "api_failure"}
        anchors = {lbl: n for lbl, n in anchors.items() if n > 0}

        status = []
        if ceiling:
            status.append("CEILING(no error signal)")
        if degenerate:
            status.append("DEGENERATE(single error label)")
        if n_models_with_error == 0:
            status.append("NO-WRONG-QUESTIONS")

        report[fam] = {
            "wrong_total": n_wrong_total,
            "wrong_per_model": wrong_by_model,
            "distinct_labels": sorted(rich),
            "anchored_error_counts": anchors,
            "ceiling": ceiling,
            "degenerate": degenerate,
        }
        print(f"\n[{fam}]  wrong_total={n_wrong_total}  distinct_labels={sorted(rich)}")
        print(f"        wrong_per_model={wrong_by_model}")
        print(f"        anchored_error_counts={anchors}")
        print(f"        flag={' '.join(status) if status else 'OK(>=2 labels, has error signal)'}")

    # D5: between-model discrimination within family
    print("\n" + "=" * 78)
    print("D5  between-model discrimination (do error profiles differ within family?)")
    print("=" * 78)
    for fam in FAMILY_ORDER:
        profiles = {}
        for model in MODELS:
            c = tensor[(fam, model)]
            total = max(1, sum(c.values()))
            profiles[model] = tuple(sorted(
                (lbl, round(c[lbl] / total, 3)) for lbl in c if lbl != "correct"
            ))
        distinct_profiles = len(set(profiles.values()))
        print(f"  [{fam:<10}] distinct error-profiles across models = {distinct_profiles}")

    # mmlu_pro INT-16 authoritative numbers (letter-only MCQ prompt)
    print("\n" + "=" * 78)
    print("NOTE  mmlu_pro under INT-16 (authoritative; d1_baseline mmlu is pre-INT16)")
    print("=" * 78)
    with open(INT16 / "summary.json") as f:
        s = json.load(f)
    for model in MODELS:
        m = s["models"][model]
        print(f"  {model:<18} correct={m['correct']:>2}/{m['n']}  (pre-INT16 before={s['before_accuracy'][model]})")

    # write machine-readable report
    out = ROOT / "experiments" / "d1_baseline_20260928_201128" / "capacity_matrix_diagnosis.json"
    payload = {
        "run": "d1_baseline_20260928_201128",
        "note": "error_type is the CURRENT coarse evaluator label, not the critique taxonomy.",
        "families": report,
    }
    with open(out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
