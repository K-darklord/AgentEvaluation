"""probe_thinking_budget.py
==========================
One-shot probe to find the minimal thinking_budget that stops HLE finish_reason=length.

Root cause (2026-10-28): thinking_budget=8192 forces deepseek-v4-flash to stop hidden CoT
prematurely on hard HLE items; the model then spills the unfinished step-by-step reasoning
into the visible channel, overflowing REASONING_CONTENT_MARGIN=8192 and hard-truncating
(completion_tokens = 16384 = 8192 thinking + 8192 content).

This drive the SAME system prompt + question as run_feedback_loop (HLE closed-book text
path), holding content_margin at the current 8192, and sweeps thinking_budget over
{16384, 32768} on the 3 heaviest repeatedly-truncated tasks. It prints finish_reason +
token counts so we can pick the smallest budget that yields finish_reason=stop.

Usage:  python3 scripts/probe_thinking_budget.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"; os.environ["no_proxy"] = "*"

from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_hle_questions

PROBE_IDS = {"hle_017", "hle_021", "hle_030"}
THINKING_BUDGETS = [16384, 32768]

HLE_SYSTEM = (
    "You are answering a difficult knowledge question. Provide ONLY the "
    "final answer in the form the question requests (a number, a symbolic "
    "or LaTeX expression, a word, or a short phrase). Do not include any "
    "reasoning, explanation, or preamble."
)


def main() -> int:
    tasks = [t for t in load_hle_questions() if t.task_id in PROBE_IDS]
    tasks.sort(key=lambda t: t.task_id)
    entry = config.PHASE1_MODELS["deepseek-v4-flash"]

    for tb in THINKING_BUDGETS:
        agent = HuggingFaceAgent(
            model=entry["model"], token=entry.get("api_key"), base_url=entry["base_url"],
            max_tokens=config.REASONING_BENCH_MAX_TOKENS, temperature=0.0, seed=None,
            enable_thinking=entry.get("enable_thinking"),
            thinking_budget=tb, content_margin=config.REASONING_CONTENT_MARGIN,
        )
        print(f"\n== thinking_budget={tb} (content_margin={config.REASONING_CONTENT_MARGIN}) ==", flush=True)
        for task in tasks:
            messages = [
                {"role": "system", "content": HLE_SYSTEM},
                {"role": "user", "content": task.prompt},
            ]
            try:
                content, reasoning, resp = agent._call_llm_text(messages)
                u = getattr(resp, "usage", None)
                ct = getattr(u, "completion_tokens", 0) if u else -1
                rt = getattr(u, "reasoning_tokens", 0) if u else -1
                fr = getattr(resp, "finish_reason", None)
                vis = (content or "").strip()[:120].replace("\n", " ")
                print(f"  {task.task_id}: finish={fr!r} ct={ct} rt={rt} visible_head={vis!r}", flush=True)
            except Exception as e:
                print(f"  {task.task_id}: ERROR {type(e).__name__}: {str(e)[:200]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())