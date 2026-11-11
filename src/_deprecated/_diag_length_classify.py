# Local (zero-API) diagnosis: classify every finish_reason=length round in the
# A3 and C3 pilot arms as either "truncated concat answer" or "ramble/spill".
import json
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
pilot = [json.loads(l) for l in open(ROOT / "data/raw/hle/hle_50_pilot.jsonl") if l.strip()]

def task_info(tid):
    idx = int(tid.split("_")[1]) - 1
    return pilot[idx]

def ascii_ratio(s):
    if not s:
        return 0.0
    return sum(1 for c in s if c.isascii()) / len(s)

arms = ["hle_pilot_a3", "hle_pilot_c3"]
for arm in arms:
    p = ROOT / f"experiments/{arm}/deepseek-v4-flash/loop_trajectories.jsonl"
    for raw in open(p):
        if not raw.strip():
            continue
        rec = json.loads(raw)
        tid = rec.get("task_id")
        info = task_info(tid) if tid else {}
        for rd in rec.get("rounds", []):
            if rd.get("finish_reason") != "length":
                continue
            fa = rd.get("final_answer") or ""
            rt = rd.get("reasoning_content") or ""
            print(f"### {arm} {tid} round={rd.get('round')} "
                  f"type={info.get('answer_type')} shape={info.get('shape')} "
                  f"subject={info.get('raw_subject')}")
            print(f"  gold={info.get('answer','')[:130]!r}")
            print(f"  reasoning_tokens={rd.get('reasoning_tokens')} "
                  f"completion_tokens={rd.get('completion_tokens')} "
                  f"commit_source={rd.get('commit_source')}")
            print(f"  FINAL_ANSWER len={len(fa)} ascii_ratio={ascii_ratio(fa):.2f}: "
                  f"{fa[:420]!r}")
            print(f"  reasoning_tail: {rt[-240:]!r}")
            print()