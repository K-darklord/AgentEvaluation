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
import time
from datetime import datetime
from pathlib import Path

import concurrent.futures
import concurrent.futures.thread as _cf_thread
import threading
import weakref

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


class _DaemonThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):
    """ThreadPoolExecutor that starts daemon worker threads.

    The stdlib pool starts *non*-daemon workers (Python 3.14), so a worker
    blocked on a hung socket read (which httpx read_timeout cannot always
    interrupt on reasoning endpoints) would otherwise block interpreter exit
    after we abandon the batch. Daemon workers let the process exit cleanly.
    """

    def _adjust_thread_count(self) -> None:
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            t = threading.Thread(
                name=thread_name,
                target=_cf_thread._worker,
                args=(
                    weakref.ref(self, weakref_cb),
                    self._create_worker_context(),
                    self._work_queue,
                ),
            )
            t.daemon = True
            t.start()
            self._threads.add(t)
            _cf_thread._threads_queues[t] = self._work_queue


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
    # Hard per-solve cap so a hung server request cannot stall the whole run.
    # httpx read_timeout does NOT fire on some reasoning endpoints (the server
    # holds the connection open), so an application-level cap is the only guard.
    # Each task gets its OWN deadline (recorded when it enters the in-flight batch);
    # a task whose request hangs past `solve_timeout` seconds is failed ALONE as
    # api_failure and the loop moves on to the next queued task. This replaces the
    # earlier batch-level abandon, which — on a single hung task — also drained every
    # not-yet-submitted (queued) task that would otherwise have completed fine.
    solve_timeout = float(os.getenv("AGENTEVALUATION_SOLVE_TIMEOUT", "180"))
    ex = _DaemonThreadPoolExecutor(max_workers=concurrency)
    try:
        it = enumerate(tasks)
        in_flight = {}   # future -> idx
        deadline = {}    # future -> monotonic per-task deadline

        def _submit_next():
            try:
                idx, task = next(it)
            except StopIteration:
                return
            fut = ex.submit(_solve_one, (idx, task))
            in_flight[fut] = idx
            deadline[fut] = time.monotonic() + solve_timeout

        def _fail_timeout(fut):
            # A single task hung: mark it api_failure, drop it from the in-flight
            # set, and immediately backfill the vacated slot with the next task.
            idx = in_flight.pop(fut)
            deadline.pop(fut, None)
            fut.cancel()
            err = AgentResult(
                task_id=getattr(tasks[idx], "task_id", f"task_{idx}"),
                model_name=getattr(agent, "name", "unknown"),
            )
            err.final_answer = "Timeout (hung server request)"
            err.api_failure = True
            err.error = f"solve exceeded {solve_timeout}s"
            err.total_latency_ms = int(solve_timeout * 1000)
            results[idx] = err
            _submit_next()

        for _ in range(concurrency):
            _submit_next()
        while in_flight:
            _now = time.monotonic()
            timed_out = [fut for fut, d in deadline.items() if d <= _now]
            if timed_out:
                for fut in timed_out:
                    _fail_timeout(fut)
                continue
            # Wait until either the next task completes or the earliest deadline
            # elapses (i.e. its task is hung); whichever comes first.
            wait_for = min(deadline.values()) - _now
            done, _ = concurrent.futures.wait(
                in_flight, timeout=wait_for,
                return_when=concurrent.futures.FIRST_COMPLETED)
            if not done:
                # The earliest deadline is now due; the timed_out branch on the next
                # iteration will drop exactly that hung task (never the whole batch).
                continue
            for fut in done:
                idx = in_flight.pop(fut)
                deadline.pop(fut, None)
                try:
                    _, result = fut.result()
                except Exception as e:
                    result = AgentResult(
                        task_id=getattr(tasks[idx], "task_id", f"task_{idx}"),
                        model_name=getattr(agent, "name", "unknown"),
                    )
                    result.final_answer = f"Error: {e}"
                    result.error = str(e)
                results[idx] = result
                _submit_next()
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

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
