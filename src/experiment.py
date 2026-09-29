"""
experiment.py
=============
YAML-driven multi-seed experiment runner (reproducibility standard sections 2-4).

I load an experiment config from configs/*.yaml, run the benchmark once per seed,
each into its own directory (avoiding the file race documented in INT-05), score
each run, and aggregate accuracy as mean +/- std.

Output layout:
  experiments/<name>_<ts>/
    config.yaml                      # snapshot of the exact config used
    seed<seed>/trajectories.jsonl    # per-seed artifacts (run + score)
    seed<seed>/run_summary.csv
    seed<seed>/results.csv
    seed<seed>/error_report.json
    summary.json                     # {"accuracy_mean", "accuracy_std", "per_seed"}
"""
from __future__ import annotations

import json
import shutil
import statistics
from datetime import datetime
from pathlib import Path

import yaml

from src.agent import HuggingFaceAgent
from src.benchmark import (
    load_tasks,
    load_fab_questions,
    load_gsm8k_questions,
    load_logic_questions,
    load_phase1_tasks,
)
from src.evaluator import Evaluator
from src.runner import run_evaluation

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path) -> dict:
    """I load a YAML experiment config."""
    with open(Path(path), encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_experiment(config_path: str | Path, repo_root: Path = REPO_ROOT) -> dict:
    """I run a full multi-seed experiment and aggregate mean +/- std accuracy."""
    cfg = load_config(config_path)

    bench = str(cfg.get("benchmark", "fab")).lower()
    loaders = {
        "fab": load_fab_questions,
        "mini": load_tasks,
        "gsm8k": load_gsm8k_questions,
        "logic": load_logic_questions,
        "phase1": load_phase1_tasks,
        "all": load_phase1_tasks,
    }
    tasks = loaders.get(bench, load_tasks)()
    num_tasks = int(cfg.get("num_tasks", 0) or 0)
    if num_tasks:
        tasks = tasks[:num_tasks]

    seeds = [int(s) for s in cfg.get("seeds", [42])]
    concurrency = int(cfg.get("concurrency", 6))

    name = str(cfg.get("name", "experiment"))
    run_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    exp_dir = repo_root / "experiments" / run_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(config_path), exp_dir / "config.yaml")

    per_seed = []
    for seed in seeds:
        seed_dir = exp_dir / f"seed{seed}"
        agent = HuggingFaceAgent(
            model=cfg.get("model"),
            max_tokens=int(cfg.get("max_tokens", 1024)),
            temperature=float(cfg.get("temperature", 0.0)),
            seed=seed,
            max_steps=cfg.get("max_tool_calls"),
        )
        run_evaluation(agent, tasks=tasks, output_dir=seed_dir,
                       run_id=f"{name}_seed{seed}", concurrency=concurrency)

        report = Evaluator(output_dir=seed_dir).score(traj_path=seed_dir / "trajectories.jsonl")
        per_seed.append({
            "seed": seed,
            "accuracy": round(report["accuracy"], 4),
            "n_valid_tasks": report["n_valid_tasks"],
            "n_api_failures": report["n_api_failures"],
        })

    accs = [r["accuracy"] for r in per_seed]
    mean = sum(accs) / len(accs)
    std = statistics.stdev(accs) if len(accs) > 1 else 0.0

    summary = {
        "name": name,
        "config": str(config_path),
        "seeds": seeds,
        "n_tasks": len(tasks),
        "temperature": float(cfg.get("temperature", 0.0)),
        "accuracy_mean": round(mean, 4),
        "accuracy_std": round(std, 4),
        "per_seed": per_seed,
    }
    (exp_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n=== {name} (multi-seed) ===")
    for r in per_seed:
        print(f"  seed={r['seed']}: accuracy={r['accuracy']:.2%} "
              f"(valid={r['n_valid_tasks']}, api_fail={r['n_api_failures']})")
    print(f"  MEAN +/- STD = {mean:.2%} +/- {std:.2%}")
    print(f"  artifacts: {exp_dir}")
    return summary


if __name__ == "__main__":
    import sys
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "configs/fab_baseline.yaml"
    run_experiment(cfg_path)
