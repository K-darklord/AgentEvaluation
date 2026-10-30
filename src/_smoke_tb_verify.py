# Smoke: verify the CONFIG-driven thinking_budget actually reaches the agent's
# solve (not a hardcoded value). Mirrors run_feedback_loop's agent construction.
import os, sys
from pathlib import Path
ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"src"))
for line in (ROOT/".env").read_text().splitlines():
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

entry = config.PHASE1_MODELS["deepseek-v4-flash"]
tb = entry.get("thinking_budget")
print(f"config thinking_budget = {tb}  (must be 32768)")

# Identical to run_feedback_loop.py (NO explicit content_margin -> agent default).
agent = HuggingFaceAgent(
    model=entry["model"],
    token=entry.get("api_key"),
    base_url=entry["base_url"],
    max_tokens=config.REASONING_BENCH_MAX_TOKENS,
    temperature=0.0,
    seed=None,
    enable_thinking=entry.get("enable_thinking"),
    thinking_budget=tb,
)
print(f"agent.thinking_budget = {agent.thinking_budget}")
print(f"agent.content_margin = {getattr(agent, 'content_margin', 'N/A')}")

TARGET = "hle_019"  # known 16384-truncator; must now stop at 32768
all_tasks = load_hle_questions()
task = next(t for t in all_tasks if t.task_id == TARGET)
r = agent.solve(task, feedback=None)
print(
    f"{task.task_id}  finish={r.finish_reason!r}  "
    f"reasoning_tokens={r.reasoning_tokens}  "
    f"completion_tokens={r.total_completion_tokens}  "
    f"api_failure={r.api_failure}  answer={(r.final_answer or '')[:60]!r}"
)
print("DONE")