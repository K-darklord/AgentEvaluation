"""
Isolate the C3 critic (lever-1) effect: hold round-0 (answer + hidden CoT) FIXED and
compare the critic WITH vs WITHOUT the solver's CoT, offline (no re-solve).

Why: the C3-v2 vs C3 loop comparison is confounded by round-0 non-determinism
(5/19 init flips across runs) and by transient C2-fallback. To answer "does feeding
the CoT actually make the critic's check more instantiated / actionable", we freeze
the (question, committed answer, hidden reasoning) snapshot from the C3 baseline
trajectories and invoke the SAME critic (strong_critic.feedback) twice:
  no_cot    : reasoning=""  (old C3 behaviour)
  with_cot  : reasoning = round-0 hidden CoT tail  (C3-v2 behaviour)

Output: one JSONL record per task with {task_id, gold, answer, no_cot:[{id,suspicion,check}],
with_cot:[...]}. Reads raw `directions` so the `check` field is preserved (the public
feedback() drops `check` from its structured tuple).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# --- replicate run_feedback_loop's env bootstrap (api key + no proxy) ---
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
          "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from src.strong_critic import StrongCritic, _extract_json, SYSTEM  # noqa: E402
from src.benchmark import (  # noqa: E402
    load_gpqa_questions, load_new_discrimination_tasks, load_phase1_tasks,
)

# The 7 round-0-wrong tasks of the C3 baseline (init0 set); activation is the lever.
TARGETS = ["mmlu_pro_033", "aime_021", "gpqa_028", "gpqa_048",
           "gpqa_103", "gpqa_095", "gpqa_163"]

C3_BASE = {
    "phase1": "feedback_loop_C3_flip19_phase1_20261022",
    "new": "feedback_loop_C3_flip19_new_20261022",
    "gpqa": "feedback_loop_C3_flip19_gpqa_20261022",
}


def load_round0() -> dict:
    out = {}
    for d in C3_BASE.values():
        p = ROOT / "experiments" / d / "deepseek-v4-flash" / "loop_trajectories.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            r0 = t["rounds"][0]
            out[t["task_id"]] = {"answer": r0["final_answer"],
                                 "reasoning": r0.get("reasoning_content", "") or ""}
    return out


def load_tasks() -> dict:
    idx = {}
    for t in load_phase1_tasks() + load_new_discrimination_tasks() + load_gpqa_questions(limit=None):
        idx[t.task_id] = t
    return idx


def call_critic(critic, question, answer, reasoning):
    user = critic._build_user(question, answer, reasoning)
    content, _r, _info = critic._agent._call_llm_text(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
    parsed = _extract_json(content)
    if not parsed:
        return None
    return parsed.get("directions", [])


def main():
    critic = StrongCritic.load("deepseek-v4-flash")
    round0 = load_round0()
    tasks = load_tasks()
    out_path = ROOT / "experiments" / "_analysis" / "c3v2_isolate_cot_20261023.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for tid in TARGETS:
            task = tasks[tid]
            r0 = round0[tid]
            rec = {
                "task_id": tid,
                "gold": task.gold_answer,
                "answer": r0["answer"],
                "reasoning_len": len(r0["reasoning"]),
                "no_cot": call_critic(critic, task.prompt, r0["answer"], ""),
                "with_cot": call_critic(critic, task.prompt, r0["answer"], r0["reasoning"]),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[done] {tid}: no_cot={len(rec['no_cot'] or [])} with_cot={len(rec['with_cot'] or [])}")
    print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()