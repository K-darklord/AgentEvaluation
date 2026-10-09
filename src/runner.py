"""
runner.py
=========
主循环：遍历 benchmark -> 调用 agent -> 记录 trajectory -> 落盘。

输出（数据线核心产物）:
  output/trajectories.jsonl   每行一条完整 trajectory（含每步 tool 调用）
  output/run_summary.csv       每行一个 task 的聚合指标（用于 scorer / 画图）

设计要点：runner 只负责「跑 + 记录」，不做评分（评分交给 evaluator.py）。
"""
from __future__ import annotations
import csv
import json
import os
from datetime import datetime
from pathlib import Path

import concurrent.futures

from src import config
from src.benchmark import (
    load_tasks,
    load_fab_questions,
    load_gsm8k_questions,
    load_logic_questions,
    load_phase1_tasks,
)
from src.agent import BaseAgent, AgentResult, RuleBasedFinanceAgent


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"

# Per-model list prices in CNY per 1M tokens: (input, output). Used for cost
# accounting [P2.0]. Sources: Aliyun Bailian (阿里云百炼) list prices for
# deepseek-v4-flash-0731 / qwen3.8-flash; glm-5.3 is not listed on Bailian, so
# its documented upper-bound price (docs/RESEARCH_PLAN.md §5.2) is used.
MODEL_PRICES_CNY = {
    "deepseek-v4-flash-0731": (1.0, 2.0),
    "qwen3.8-flash": (0.8, 2.7),
    "glm-5.3": (8.0, 28.0),
}


def _cost_cny(model_name: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """CNY cost from token usage; None when the model price is unknown."""
    price = MODEL_PRICES_CNY.get(model_name)
    if price is None:
        return None
    in_price, out_price = price
    return round(prompt_tokens / 1e6 * in_price + completion_tokens / 1e6 * out_price, 6)


def run_evaluation(
    agent: BaseAgent,
    tasks=None,
    output_dir: Path = OUTPUT_DIR,
    run_id: str | None = None,
    concurrency: int | None = None,
) -> dict:
    tasks = list(tasks or load_tasks())
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    if concurrency is None:
        concurrency = max(1, config.RUNNER_CONCURRENCY)

    traj_path = output_dir / "trajectories.jsonl"
    sum_path = output_dir / "run_summary.csv"

    # Task-level parallelism only: each task's internal tool loop stays sequential.
    # Results are collected by index so trajectory/CSV output order is reproducible.
    def _solve_one(item):
        idx, task = item
        try:
            return idx, agent.solve(task)
        except Exception as e:
            # Isolate failures: one bad task must not abort the whole run.
            err = AgentResult(
                task_id=getattr(task, "task_id", f"task_{idx}"),
                model_name=getattr(agent, "name", "unknown"),
            )
            err.final_answer = f"Error: {e}"
            err.error = str(e)
            return idx, err

    results = [None] * len(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        for idx, result in ex.map(_solve_one, enumerate(tasks)):
            results[idx] = result

    rows = []
    with traj_path.open("w", encoding="utf-8") as ft:
        for task, result in zip(tasks, results):
            record = {
                "run_id": run_id,
                "task_id": task.task_id,
                "category": task.category,
                "difficulty": task.difficulty,
                "prompt": task.prompt,
                "gold_answer": task.gold_answer,
                "final_answer": result.final_answer,
                "tool_calls": result.tool_calls,
                "total_latency_ms": result.total_latency_ms,
                "total_cost_usd": result.total_cost_usd,
                "prompt_tokens": result.total_prompt_tokens,
                "completion_tokens": result.total_completion_tokens,
                "reasoning_tokens": result.reasoning_tokens,
                "cost_cny": _cost_cny(result.model_name, result.total_prompt_tokens, result.total_completion_tokens),
                "model_name": result.model_name,
                "seed": result.seed,
                "trajectory": result.trajectory,   # 完整轨迹：归因分析的原料
                "metadata": task.metadata,
                "api_failure": result.api_failure,
            }
            ft.write(json.dumps(record, ensure_ascii=False) + "\n")

            rows.append({
                "run_id": run_id,
                "task_id": task.task_id,
                "category": task.category,
                "difficulty": task.difficulty,
                "gold_answer": task.gold_answer,
                "final_answer": result.final_answer,
                "tool_calls": result.tool_calls,
                "latency_ms": result.total_latency_ms,
                "cost_usd": result.total_cost_usd,
                "prompt_tokens": result.total_prompt_tokens,
                "completion_tokens": result.total_completion_tokens,
                "reasoning_tokens": result.reasoning_tokens,
                "cost_cny": _cost_cny(result.model_name, result.total_prompt_tokens, result.total_completion_tokens),
                "model": result.model_name,
                "seed": result.seed,
                "metadata": json.dumps(task.metadata, ensure_ascii=False),
            })

    # 汇总 CSV
    with sum_path.open("w", newline="", encoding="utf-8") as fs:
        writer = csv.DictWriter(fs, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total_prompt = sum(r["prompt_tokens"] for r in rows)
    total_completion = sum(r["completion_tokens"] for r in rows)
    total_reasoning = sum(r["reasoning_tokens"] for r in rows)
    total_cny = sum(r["cost_cny"] or 0.0 for r in rows)
    print(f"✅ Run {run_id} done. {len(rows)} tasks (concurrency={concurrency}).")
    print(f"   trajectories: {traj_path}")
    print(f"   summary:      {sum_path}")
    print(f"   tokens:       prompt={total_prompt} completion={total_completion} "
          f"reasoning={total_reasoning}")
    print(f"   cost:         ¥{total_cny:.4f} (list prices)")
    return {
        "run_id": run_id,
        "n": len(rows),
        "traj_path": str(traj_path),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "reasoning_tokens": total_reasoning,
        "cost_cny": round(total_cny, 6),
    }


if __name__ == "__main__":
    # I support env-driven agent and benchmark selection:
    #   AGENTEVALUATION_AGENT=openai python runner.py   (use OpenAI API upper bound)
    #   AGENTEVALUATION_BENCH=fab python runner.py      (use FAB public dataset)
    agent_name = os.getenv("AGENTEVALUATION_AGENT", "rule").lower()
    bench_name = os.getenv("AGENTEVALUATION_BENCH", "mini").lower()

    if agent_name == "openai":
        from src.agent import OpenAIAgent
        agent = OpenAIAgent()
    elif agent_name == "hf":
        from src.agent import HuggingFaceAgent
        agent = HuggingFaceAgent()
    else:
        from src.agent import RuleBasedFinanceAgent
        agent = RuleBasedFinanceAgent()

    if bench_name == "fab":
        tasks = load_fab_questions()
    elif bench_name == "gsm8k":
        tasks = load_gsm8k_questions()
    elif bench_name == "logic":
        tasks = load_logic_questions()
    elif bench_name in ("phase1", "all"):
        tasks = load_phase1_tasks()
    else:
        tasks = load_tasks()

    # Allow limiting number of tasks for quick testing
    num_tasks = os.environ.get("AGENTEVALUATION_NUM_TASKS")
    if num_tasks:
        tasks = tasks[:int(num_tasks)]

    print(f"[runner] agent={agent_name} bench={bench_name} tasks={len(tasks)}")
    run_evaluation(agent, tasks=tasks)
