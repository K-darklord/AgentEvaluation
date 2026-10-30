import json, os, sys
from pathlib import Path
ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"src"))
for line in (ROOT/".env").read_text().splitlines():
    line=line.strip()
    if line and not line.startswith("#") and "=" in line:
        k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"):
    os.environ.pop(k,None)
os.environ["NO_PROXY"]="*"; os.environ["no_proxy"]="*"
from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_hle_questions

TARGETS = ["hle_007", "hle_019", "hle_020", "hle_021", "hle_026", "hle_030", "hle_031", "hle_036"]

entry = config.PHASE1_MODELS["deepseek-v4-flash"]
agent = HuggingFaceAgent(
    model=entry["model"],
    token=entry.get("api_key"),
    base_url=entry["base_url"],
    max_tokens=config.REASONING_BENCH_MAX_TOKENS,
    temperature=0.0,
    seed=None,
    enable_thinking=entry.get("enable_thinking"),
    thinking_budget=32768,
    content_margin=8192,
)

all_tasks = load_hle_questions()
tasks = [t for t in all_tasks if t.task_id in TARGETS]
print(f"probe targets: {[t.task_id for t in tasks]}  (tb=32768, margin=8192)")

for task in tasks:
    r = agent.solve(task, feedback=None)
    ans = (r.final_answer or "").replace("\n", " ").strip()
    print(
        f"{task.task_id}  finish={r.finish_reason!r}  "
        f"reasoning_tokens={r.reasoning_tokens}  "
        f"completion_tokens={r.total_completion_tokens}  "
        f"api_failure={r.api_failure}  answer={ans[:60]!r}"
    )
print("DONE")