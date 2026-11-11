import json, os, sys
from pathlib import Path
ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
ALL = ["hle_007","hle_019","hle_020","hle_021","hle_026","hle_030","hle_031","hle_036"]
p = ROOT/"data/raw/hle/hle_50_pilot.jsonl"
for i, line in enumerate(p.open(), start=1):
    tid = f"hle_{i:03d}"
    if tid not in ALL:
        continue
    d = json.loads(line)
    q = str(d.get("question",""))
    a = str(d.get("answer",""))
    print(f"== {tid} ==")
    print(f"  subject={d.get('raw_subject')!r} category={d.get('category')!r} "
          f"answer_type={d.get('answer_type')!r} shape={d.get('shape')!r}")
    print(f"  question_chars={len(q)}  answer_chars={len(a)}  id={d.get('id')!r}")
    print(f"  question_head={q[:400]!r}")