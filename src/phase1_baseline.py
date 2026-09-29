"""
phase1_baseline.py
==================
Phase-1 probe d1-baseline driver (temp=0, single seed, deterministic).

Runs every reachable model in config.PHASE1_MODELS over the 150-Q probe set
(math 50 + logic 50 + finance 50), scores each run with the domain-aware
evaluator, and writes a per-model + per-domain summary (the raw dimensions for a
later capability-matrix decomposition: model x question-set x error-type x score).

Notes:
  - config.PHASE1_MODELS stores `api_key`; HuggingFaceAgent expects `token`. We map it.
  - When HF_TOKEN is absent, (a) deepseek-v4-flash has an empty key and is skipped, and
    (b) the finance T2 LLM-judge falls back to deterministic rubric coverage.
  - macOS system proxy (127.0.0.1:3213) breaks the openai SDK (httpx) TLS to cloud
    endpoints; we force no-proxy so requests go direct (curl needed --noproxy for the
    same reason).
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_phase1_tasks
from src.evaluator import Evaluator
from src.runner import run_evaluation

REPO_ROOT = Path(__file__).resolve().parents[1]


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213), which otherwise stalls the
    openai SDK's TLS handshake to DashScope/Zhipu even though direct HTTP works."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _domain_of(task_id: str) -> str:
    if task_id.startswith("gsm8k_"):
        return "math"
    if task_id.startswith("math500_"):
        return "math500"
    if task_id.startswith("logic_"):
        return "logic"
    if task_id.startswith("mmlu_pro_"):
        return "mmlu_pro"
    if task_id.startswith("fab_"):
        return "finance"
    if task_id.startswith("bfcl_"):
        return "bfcl"
    return "other"


def run_phase1_baseline(tiers=None, concurrency=None, num_tasks=0, skip_empty_key=True) -> dict:
    _force_no_proxy()

    tasks = load_phase1_tasks()
    if num_tasks:
        tasks = tasks[:num_tasks]
    if concurrency is None:
        concurrency = config.RUNNER_CONCURRENCY

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = REPO_ROOT / "experiments" / f"d1_baseline_{run_id}"
    out_root.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_id": run_id,
        "n_tasks": len(tasks),
        "temperature": 0.0,
        "seed": None,
        "concurrency": concurrency,
        "t2_judge": config.T2_JUDGE_MODEL if config.T2_JUDGE_API_KEY else "rule-based fallback (no judge key)",
        "models": {},
    }

    for name, entry in config.PHASE1_MODELS.items():
        tier = entry["tier"]
        if tiers and tier not in tiers:
            continue
        api_key = (entry.get("api_key") or "").strip()
        if skip_empty_key and not api_key:
            print(f"[skip] {name} [{tier}]: empty api_key")
            continue

        model_dir = out_root / name
        agent = HuggingFaceAgent(
            model=entry["model"],
            token=api_key,
            base_url=entry["base_url"],
            max_tokens=1024,
            temperature=0.0,
            seed=None,
            enable_thinking=entry.get("enable_thinking"),
        )
        print(f"\n=== [{tier}] {name} model_id={entry['model']} base_url={entry['base_url']} ===")
        run_evaluation(agent, tasks=tasks, output_dir=model_dir, run_id=name, concurrency=concurrency)

        report = Evaluator(output_dir=model_dir).score(traj_path=model_dir / "trajectories.jsonl")

        per_domain = {d: [0, 0] for d in ("math", "math500", "logic", "mmlu_pro", "finance", "bfcl", "other")}
        errors: dict[str, int] = {}
        results_csv = model_dir / "results.csv"
        if results_csv.exists():
            with results_csv.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    d = _domain_of(row["task_id"])
                    per_domain[d][1] += 1
                    if str(row.get("is_correct", "")).strip().lower() in ("true", "1", "yes"):
                        per_domain[d][0] += 1
                    et = row.get("error_type", "unknown")
                    errors[et] = errors.get(et, 0) + 1

        summary["models"][name] = {
            "tier": tier,
            "model_id": entry["model"],
            "declared_temperature": 0.0,
            "seed": None,
            "thinking": entry.get("thinking", "unknown"),
            "accuracy": report["accuracy"],
            "accuracy_excl_api_failures": report["accuracy_excl_api_failures"],
            "n_valid_tasks": report["n_valid_tasks"],
            "n_api_failures": report["n_api_failures"],
            "per_domain": {d: {"correct": v[0], "n": v[1]} for d, v in per_domain.items()},
            "error_distribution": errors,
        }

    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== D1 baseline summary -> {out_root / 'summary.json'} ===")
    for name, r in summary["models"].items():
        pd = " | ".join(f"{d}={v['correct']}/{v['n']}" for d, v in r["per_domain"].items() if v["n"])
        print(f"  {name:<16} [{r['tier']:<4}] acc={r['accuracy']:.2%} "
              f"(valid={r['n_valid_tasks']}, api_fail={r['n_api_failures']})")
        print(f"        per_domain: {pd}")
    return summary


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only_tiers = args or None
    num_tasks = int(os.getenv("PHASE1_NUM_TASKS", "0") or 0)
    run_phase1_baseline(tiers=only_tiers, num_tasks=num_tasks)
