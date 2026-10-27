"""build_hle_wrong_bank.py
==========================
Extract A3 self-consistency WRONG instances from the HLE pilot trajectories and
emit them as EGTE wrong-bank rows (``family="hle"``) — the input the L1 -> L2 -> L3
distillation pipeline consumes (``build_behavior_leaves.py`` ->
``build_mechanism_levels.py``).

For each task we reproduce the A3 majority vote over the K=10 i.i.d. samples (the
SAME committed-key vote the in-loop A3 arm and ``score_hle_pilot.py`` use), take the
winning answer, and — only when it is WRONG — emit one row:

    {task_id, family, model, error_type, final_answer, gold_answer, prompt}

Wrongness uses ``score_hle`` (deterministic T1 exact-match, overridden by the offline
T2 LLM judge when available) so a T1 containment false-positive (e.g. a wrong list
that happens to contain the gold tokens) still lands in the bank.

Gold-free downstream: the distillation roles re-read only question + wrong answer +
gold from these rows; the answer-free mechanism is the OUTPUT, never this row's
answer text.

Offline usage (after the A3 run completes):

    python3 src/build_hle_wrong_bank.py \
        --a3 experiments/hle_pilot_a3 --model deepseek-v4-flash \
        --out experiments/error_taxonomy_v2/wrong_bank_hle.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _force_no_proxy() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_load_dotenv()
_force_no_proxy()

from src.benchmark import load_hle_questions  # noqa: E402
from src.hle_scorer import score_hle  # noqa: E402
from src.run_feedback_loop import _early_stop_key  # noqa: E402

FAMILY = "hle"


def load_tasks_index() -> dict:
    """task_id -> dict(question, gold, answer_type, shape)."""
    idx = {}
    for t in load_hle_questions():
        md = t.metadata or {}
        idx[t.task_id] = {
            "question": t.prompt,
            "gold": t.gold_answer,
            "answer_type": md.get("answer_type", ""),
            "shape": md.get("shape", ""),
        }
    return idx


def _full_response(rec: dict) -> str:
    cot = (rec.get("reasoning_content") or "").strip()
    ans = (rec.get("final_answer") or "").strip()
    if cot and ans:
        return cot + "\n\n" + ans
    return cot or ans


def _commit_key(meta: dict, rec: dict):
    return _early_stop_key(FAMILY, meta["gold"], rec.get("final_answer", ""),
                           rec.get("reasoning_content", ""),
                           rec.get("finish_reason", ""))


def majority_winner(meta: dict, task: dict):
    """Reproduce A3's committed-key majority vote; return the winning round or None."""
    rounds = task["rounds"]
    votes = Counter()
    for rec in rounds:
        key, _src = _commit_key(meta, rec)
        if key is not None:
            votes[key] += 1
    if not votes:
        return None
    winner_key = votes.most_common(1)[0][0]
    return next((r for r in rounds if _commit_key(meta, r)[0] == winner_key), rounds[0])


def read_trajectory(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[rec["task_id"]] = rec
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a3", default="experiments/hle_pilot_a3")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--out", default="experiments/error_taxonomy_v2/wrong_bank_hle.jsonl")
    args = ap.parse_args()

    meta_idx = load_tasks_index()
    traj = read_trajectory(ROOT / args.a3 / args.model / "loop_trajectories.jsonl")
    common = sorted(set(traj) & set(meta_idx))
    print(f"loaded index={len(meta_idx)} trajectory={len(traj)} -> common={len(common)}")

    rows = []
    skipped_no_commit = 0
    for task_id in common:
        meta = meta_idx[task_id]
        winner = majority_winner(meta, traj[task_id])
        if winner is None:
            skipped_no_commit += 1
            continue
        sc = score_hle(meta["question"], meta["gold"], meta["answer_type"],
                       meta["shape"], _full_response(winner))
        if sc["correct"]:
            continue
        rows.append({
            "task_id": task_id,
            "family": FAMILY,
            "model": args.model,
            "error_type": "",
            "final_answer": winner.get("final_answer", ""),
            "gold_answer": meta["gold"],
            "prompt": meta["question"],
        })

    rows.sort(key=lambda r: r["task_id"])
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[wrong bank] {len(rows)} wrong instances "
          f"(skipped {skipped_no_commit} no-commit) -> {out_path}")


if __name__ == "__main__":
    main()