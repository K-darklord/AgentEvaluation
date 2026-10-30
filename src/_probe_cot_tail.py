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

TARGETS = ["hle_007","hle_019","hle_026","hle_031","hle_036"]

def repeat_flag(s):
    s = s[-1000:]
    for L in (200, 100, 64, 48, 32):
        if L > len(s) // 2:
            continue
        for i in range(len(s) - 2 * L + 1):
            seg = s[i:i+L]
            if seg in s[i+L:]:
                return f"REPEAT(L>={L})@offset{i}"
    return "no-repeat"

entry = config.PHASE1_MODELS["deepseek-v4-flash"]
agent = HuggingFaceAgent(model=entry["model"], token=entry.get("api_key"),
    base_url=entry["base_url"], max_tokens=config.REASONING_BENCH_MAX_TOKENS,
    temperature=0.0, seed=None, enable_thinking=entry.get("enable_thinking"),
    thinking_budget=32768, content_margin=8192)
tasks = [t for t in load_hle_questions() if t.task_id in TARGETS]
for task in tasks:
    r = agent.solve(task, feedback=None)
    cot = (r.reasoning_content or "").strip()
    print(f"===== {task.task_id} finish={r.finish_reason} rt={r.reasoning_tokens} "
          f"cot_chars={len(cot)} repeat={repeat_flag(cot)} =====")
    print(cot[-900:])
    print("----- END TAIL -----")
print("ALLDONE")