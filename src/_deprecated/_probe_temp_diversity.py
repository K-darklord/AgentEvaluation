import json, re, os, sys
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
from src.benchmark import load_new_discrimination_tasks

def norm(s): return re.sub(r"\s+"," ",str(s or "").strip().lower()).strip(".,;:!?")

cpath = ROOT/"experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl"
hard = []
for l in open(cpath):
    t=json.loads(l); seq=[norm(r["final_answer"]) for r in t["rounds"]]
    if len(set(seq))>=3:  # genuinely oscillated under C feedback => uncertain
        hard.append(t["task_id"])
hard=hard[:4]
print("hard task ids:", [h.split('_')[-1] for h in hard])
tasks=[t for t in load_new_discrimination_tasks() if t.task_id in hard]

entry=config.PHASE1_MODELS["deepseek-v4-flash"]
for temp in (0.7, 1.0):
    agent=HuggingFaceAgent(model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=config.REASONING_BENCH_MAX_TOKENS,
        temperature=temp, seed=None, enable_thinking=entry.get("enable_thinking"))
    print(f"\n== T={temp} ==")
    for task in tasks:
        ans=[]
        for _ in range(5):
            r=agent.solve(task, feedback=None)
            ans.append(norm(r.final_answer))
        print(f"  {task.task_id}  n_uniq={len(set(ans))}  counts={ {a:ans.count(a) for a in set(ans)} }")
