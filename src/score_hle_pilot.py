"""score_hle_pilot.py
====================
Offline scorer for the HLE 50-question pilot: A3 (self-consistency majority vote)
vs C3 (strong-critic feedback loop).

The in-loop `is_correct` used deterministic T1 only (the T2 judge must stay OFFLINE).
This script reads the recorded trajectories, reconstructs the A3 majority vote over the
committed keys, and re-scores every committed answer with the full ``hle_scorer``
(T1 exact-match + T2 LLM judge) so the final numbers are cross-validated and the FP/FN
disagreements are auditable.

Run:  python3 src/score_hle_pilot.py --a3 experiments/hle_pilot_a3 --c3 experiments/hle_pilot_c3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from src.hle_scorer import score_hle, score_t1  # noqa: E402
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


def read_trajectory(path: Path) -> dict:
    """task_id -> full per-task record (rounds etc.)."""
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


def _judge(meta: dict, rec: dict) -> dict:
    # Judge reads only the committed final answer, never the CoT (scorer_LLM_rescue).
    return score_hle(meta["question"], meta["gold"],
                     meta["answer_type"], meta["shape"], rec.get("final_answer", ""))


def _commit_key(meta: dict, rec: dict):
    """Recompute the canonical committed key with the SAME logic the loop used."""
    return _early_stop_key(FAMILY, meta["gold"], rec.get("final_answer", ""),
                           rec.get("reasoning_content", ""),
                           rec.get("finish_reason", ""))


def score_a3(meta: dict, task: dict) -> dict:
    """Majority vote over the N i.i.d. samples (rounds), on the committed key.
    Ties -> first-encountered (consistent with the A3C3 in-loop vote)."""
    rounds = task["rounds"]
    votes = Counter()
    for rec in rounds:
        key, _src = _commit_key(meta, rec)
        if key is not None:
            votes[key] += 1
    winner_rec = rounds[0]
    if votes:
        winner_key = votes.most_common(1)[0][0]
        winner_rec = next((r for r in rounds
                           if _commit_key(meta, r)[0] == winner_key), rounds[0])
    sc = _judge(meta, winner_rec)
    return {"n_samples": len(rounds), "vote": sc, "winner": winner_rec}


def score_c3(meta: dict, task: dict) -> dict:
    """C3 final committed answer = last feedback round's response."""
    rounds = task["rounds"]
    final_rec = rounds[-1]
    sc = _judge(meta, final_rec)
    return {"n_rounds": len(rounds), "final": sc, "final_rec": final_rec}


def _agg(scored: list[dict]) -> dict:
    n = len(scored) or 1
    correct = sum(1 for s in scored if s["correct"])
    t1 = sum(1 for s in scored if s["t1_correct"])
    judge = [s for s in scored if s["judge_correct"] is not None]
    fn = sum(1 for s in scored if s["disagreement"] == "FN")
    return {
        "n": len(scored),
        "accuracy": round(correct / n, 4),
        "t1_accuracy": round(t1 / n, 4),
        "judge_n": len(judge),
        "fn_rescued": fn,
    }


def _score_task(task_id: str, meta_idx: dict, a3_traj: dict, c3_traj: dict):
    """Score all four arm rows for one task (the unit of parallelism)."""
    meta = meta_idx[task_id]
    a3t = a3_traj[task_id]
    c3t = c3_traj[task_id]
    return (_judge(meta, a3t["rounds"][0]),
            score_a3(meta, a3t)["vote"],
            _judge(meta, c3t["rounds"][0]),
            score_c3(meta, c3t)["final"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a3", default="experiments/hle_pilot_a3")
    ap.add_argument("--c3", default="experiments/hle_pilot_c3")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    meta_idx = load_tasks_index()
    a3_path = ROOT / args.a3 / args.model / "loop_trajectories.jsonl"
    c3_path = ROOT / args.c3 / args.model / "loop_trajectories.jsonl"
    a3_traj = read_trajectory(a3_path)
    c3_traj = read_trajectory(c3_path)
    print(f"loaded HLE index={len(meta_idx)} a3_traj={len(a3_traj)} "
          f"c3_traj={len(c3_traj)}")

    common = sorted(set(a3_traj) & set(c3_traj) & set(meta_idx))
    if args.limit:
        common = common[:args.limit]

    init_a3, vote_a3, init_c3, final_c3 = [], [], [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_score_task, tid, meta_idx, a3_traj, c3_traj)
                for tid in common]
        for fut in as_completed(futs):
            ia, va, ic, fc = fut.result()
            init_a3.append(ia)
            vote_a3.append(va)
            init_c3.append(ic)
            final_c3.append(fc)

    print("\n=== HLE pilot scored (T1 + T2 FN rescue) ===")
    print(f"tasks compared: {len(common)}")
    print(f"\nA3 (self-consistency, N=10 @ T=0.7) :")
    print(f"  init (round-0)        : {_agg(init_a3)}")
    print(f"  majority vote         : {_agg(vote_a3)}")
    print(f"\nC3 (strong critic @ T=0)        :")
    print(f"  init (round-0)        : {_agg(init_c3)}")
    print(f"  final (post-feedback) : {_agg(final_c3)}")

    # Headroom: the two arms' gain over their own init (the core comparison).
    def _xa(a):
        return a["accuracy"]
    a3_headroom = _xa(_agg(vote_a3)) - _xa(_agg(init_a3))
    c3_headroom = _xa(_agg(final_c3)) - _xa(_agg(init_c3))
    print(f"\nheadroom (accuracy) : A3-vote {a3_headroom:+.2%} | "
          f"C3-final {c3_headroom:+.2%}")

    out = {
        "n": len(common),
        "a3": {"init": _agg(init_a3), "vote": _agg(vote_a3)},
        "c3": {"init": _agg(init_c3), "final": _agg(final_c3)},
        "headroom": {"a3_vote_minus_init": round(a3_headroom, 4),
                    "c3_final_minus_init": round(c3_headroom, 4)},
    }
    outpath = ROOT / args.a3 / "hle_pilot_scores.json"
    outpath.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nscores -> {outpath}")


if __name__ == "__main__":
    main()