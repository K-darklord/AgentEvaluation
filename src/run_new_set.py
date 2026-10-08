"""
run_new_set.py
==============
Driver for the NEW non-FAB discrimination set: AIME (math) + GPQA-Diamond
(science knowledge) + BBH (reasoning). These hard L1 questions were added
because the existing non-FAB families (GSM8K / MATH-500 / MMLU-Pro / BFCL)
saturate for mid-tier models.

Runs reachable Phase-1 models over the new set, scores each run with the
domain-aware evaluator, and writes a per-model + per-bench summary. Mirrors
src/phase1_baseline.py but sources tasks from load_new_discrimination_tasks().

Segmentation (to avoid wasting tokens): run one model per invocation, pinned to
the same run via NEW_SET_RUN_ID so all segments accumulate into one summary.json.

Env:
  NEW_SET_MODELS        comma-separated model names (default: all PHASE1_MODELS)
  NEW_SET_RUN_ID        pin the experiment dir timestamp across segments
  NEW_SET_RUN_PREFIX    experiment dir prefix (default: new_set)
  NEW_SET_N_PER_BENCH   AIME/GPQA questions each (default: PHASE1_N_PER_BENCH=50)
  NEW_SET_BBH_PER_TASK  BBH examples per task (default: 4)
  NEW_SET_RESCORE       when truthy, skip the agent and only re-score stored
                        trajectories with the current evaluator (zero API cost)
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """Load TOKEN_PLAN_API_KEY etc. from the repo .env (never committed).

    Must run BEFORE `from src import config`: config reads the key at import time.
    """
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.benchmark import load_new_discrimination_tasks  # noqa: E402
from src.evaluator import Evaluator  # noqa: E402
from src.runner import run_evaluation  # noqa: E402

_DOMAINS = ("aime", "gpqa", "bbh", "other")


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213), which otherwise stalls the
    openai SDK's TLS handshake to the Alibaba Token Plan endpoint."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _domain_of(task_id: str) -> str:
    if task_id.startswith("aime_"):
        return "aime"
    if task_id.startswith("gpqa_"):
        return "gpqa"
    if task_id.startswith("bbh_"):
        return "bbh"
    return "other"


def run_new_set(models=None, n_per_bench=None, bbh_per_task=None,
                concurrency=None, skip_empty_key=True, rescore=False) -> dict:
    _load_dotenv()
    _force_no_proxy()

    if n_per_bench is None:
        n_per_bench = int(os.getenv("NEW_SET_N_PER_BENCH", str(config.PHASE1_N_PER_BENCH)))
    if bbh_per_task is None:
        bbh_per_task = int(os.getenv("NEW_SET_BBH_PER_TASK", "4"))

    tasks = load_new_discrimination_tasks(n_per_bench=n_per_bench, bbh_per_task=bbh_per_task)
    if concurrency is None:
        concurrency = config.RUNNER_CONCURRENCY

    run_id = os.getenv("NEW_SET_RUN_ID") or datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = os.getenv("NEW_SET_RUN_PREFIX", "new_set")
    out_root = REPO_ROOT / "experiments" / f"{prefix}_{run_id}"
    out_root.mkdir(parents=True, exist_ok=True)

    if models:
        selected = [m for m in models if m in config.PHASE1_MODELS]
    else:
        selected = list(config.PHASE1_MODELS)

    summary_path = out_root / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary.setdefault("models", {})
    else:
        summary = {"models": {}}
    summary.update({
        "run_id": run_id,
        "bench": "new_set",
        "n_tasks": len(tasks),
        "n_per_bench": n_per_bench,
        "bbh_per_task": bbh_per_task,
        "temperature": 0.0,
        "seed": None,
        "concurrency": concurrency,
    })

    print(f"[new_set] run_id={run_id} tasks={len(tasks)} n_per_bench={n_per_bench} "
          f"bbh_per_task={bbh_per_task} models={selected}")

    for name in selected:
        entry = config.PHASE1_MODELS[name]
        tier = entry["tier"]
        model_dir = out_root / name
        traj_path = model_dir / "trajectories.jsonl"

        if rescore:
            # Zero-cost path: re-score stored trajectories with the current evaluator
            # (no API call), e.g. after an extractor fix.
            if not traj_path.exists():
                print(f"[skip] {name}: no trajectories.jsonl to rescore")
                continue
            print(f"\n=== [rescore] {name} [{tier}] ===")
        else:
            api_key = (entry.get("api_key") or "").strip()
            if skip_empty_key and not api_key:
                print(f"[skip] {name} [{tier}]: empty api_key")
                continue
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

        report = Evaluator(output_dir=model_dir).score(traj_path=traj_path)

        per_bench = {d: [0, 0] for d in _DOMAINS}
        errors: dict[str, int] = {}
        results_csv = model_dir / "results.csv"
        if results_csv.exists():
            with results_csv.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    b = _domain_of(row["task_id"])
                    per_bench[b][1] += 1
                    if str(row.get("is_correct", "")).strip().lower() in ("true", "1", "yes"):
                        per_bench[b][0] += 1
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
            "per_bench": {d: {"correct": v[0], "n": v[1]} for d, v in per_bench.items()},
            "error_distribution": errors,
        }
        # Persist after each model so a long run survives interruption and
        # successive segments accumulate into the same summary.
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== new-set summary -> {summary_path} ===")
    for name, r in summary["models"].items():
        pb = " | ".join(f"{d}={v['correct']}/{v['n']}" for d, v in r["per_bench"].items() if v["n"])
        print(f"  {name:<16} [{r['tier']:<4}] acc={r['accuracy']:.2%} "
              f"(valid={r['n_valid_tasks']}, api_fail={r['n_api_failures']})")
        print(f"        per_bench: {pb}")
    return summary


if __name__ == "__main__":
    sel = os.getenv("NEW_SET_MODELS", "").strip()
    models = [m.strip() for m in sel.split(",") if m.strip()] or None
    rescore = os.getenv("NEW_SET_RESCORE", "").strip().lower() not in ("", "0", "false")
    run_new_set(models=models, rescore=rescore)
