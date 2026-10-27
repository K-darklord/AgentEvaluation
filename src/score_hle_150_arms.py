"""score_hle_150_arms.py
=======================
Offline scorer for the 150-question NEW HLE run (5 arms), under the same
scorer_LLM_rescue protocol as the 50-question pilot (T1 exact-match + T2 one-way
LLM judge FN rescue; the judge never overturns a correct T1).

Arms scored:
  A        = bare T=0 single answer        -> round-0 committed answer
  A2       = form placebo loop             -> last feedback round
  A3       = self-consistency (N=10,T=0.7) -> majority vote (score_a3)
  C3       = strong critic loop            -> last feedback round (strong only)
  C3+eval  = C3 + rubric_ce evaluator      -> rubric verdict (multi-answer),
                                             else last round (single-answer)
  A3C3     = A3-seeded + C3 loop           -> last feedback round (strong only)
  A3C3+eval= A3C3 + rubric_ce evaluator    -> rubric verdict (multi-answer),
                                             else last round (single-answer)

Run (HLE_DATA_PATH must point at the 150-queue jsonl):
  HLE_DATA_PATH=data/raw/hle/hle_150_new.jsonl python3 src/score_hle_150_arms.py \
      --a experiments/hle150_A --a2 experiments/hle150_A2 \
      --a3 experiments/hle150_A3 --a3c3 experiments/hle150_A3C3 \
      --c3 experiments/hle150_C3 \
      --rubric-c3 experiments/hle150_C3/c3_rubric_ce.jsonl \
      --rubric-a3c3 experiments/hle150_A3C3/a3c3_rubric_ce.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


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

from score_hle_pilot import load_tasks_index, read_trajectory, score_a3  # noqa: E402
from src.hle_scorer import score_hle  # noqa: E402


def load_rubric_verdicts(path: Path) -> dict[str, str | None]:
    """task_id -> locked verdict string (None => abstain)."""
    out: dict[str, str | None] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r.get("verdict")
    return out


def score(meta: dict, response: str) -> dict:
    return score_hle(meta["question"], meta["gold"],
                     meta["answer_type"], meta["shape"], response or "")


def _agg(rows: list[dict]) -> dict:
    n = len(rows) or 1
    correct = sum(1 for r in rows if r["correct"])
    t1 = sum(1 for r in rows if r["t1_correct"])
    judge = [r for r in rows if r["judge_correct"] is not None]
    fn = sum(1 for r in rows if r["disagreement"] == "FN")
    return {
        "n": len(rows),
        "accuracy": round(correct / n, 4),
        "t1_accuracy": round(t1 / n, 4),
        "judge_n": len(judge),
        "fn_rescued": fn,
    }


def _traj_path(exp_dir: str, model: str) -> Path:
    return ROOT / exp_dir / model / "loop_trajectories.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="experiments/hle150_A")
    ap.add_argument("--a2", default="experiments/hle150_A2")
    ap.add_argument("--a3", default="experiments/hle150_A3")
    ap.add_argument("--a3c3", default="experiments/hle150_A3C3")
    ap.add_argument("--c3", default="experiments/hle150_C3")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--rubric-c3", default=None, help="C3 rubric_ce verdict JSONL")
    ap.add_argument("--rubric-a3c3", default=None, help="A3C3 rubric_ce verdict JSONL")
    ap.add_argument("--out", default=None, help="output JSON path")
    args = ap.parse_args()

    meta_idx = load_tasks_index()
    traj = {}
    for label, d in (("a", args.a), ("a2", args.a2), ("a3", args.a3),
                     ("a3c3", args.a3c3), ("c3", args.c3)):
        traj[label] = read_trajectory(_traj_path(d, args.model))
        print(f"[{label}] {len(traj[label])} trajectories <- {d}")

    rubric_c3 = load_rubric_verdicts(Path(args.rubric_c3)) if args.rubric_c3 else {}
    rubric_a3c3 = load_rubric_verdicts(Path(args.rubric_a3c3)) if args.rubric_a3c3 else {}
    print(f"rubric verdicts: c3={len(rubric_c3)} a3c3={len(rubric_a3c3)}")

    common = sorted(set(traj["a3"]) & set(traj["c3"]) & set(meta_idx))

    A, A2, A3V, C3S, C3R, A3C3S, A3C3R = [], [], [], [], [], [], []
    for tid in common:
        meta = meta_idx[tid]
        at = traj["a"][tid]
        a2t = traj["a2"][tid]
        a3t = traj["a3"][tid]
        a3c3t = traj["a3c3"][tid]
        c3t = traj["c3"][tid]

        A.append(score(meta, at["rounds"][0].get("final_answer", "")))
        A2.append(score(meta, a2t["rounds"][-1].get("final_answer", "")))
        A3V.append(score(meta, score_a3(meta, a3t)["winner"].get("final_answer", "")))
        C3S.append(score(meta, c3t["rounds"][-1].get("final_answer", "")))
        A3C3S.append(score(meta, a3c3t["rounds"][-1].get("final_answer", "")))

        # rubic locked verdict (multi-answer) else strong final (single-answer)
        c3_final = rubric_c3.get(tid) if tid in rubric_c3 else c3t["rounds"][-1].get("final_answer", "")
        a3c3_final = rubric_a3c3.get(tid) if tid in rubric_a3c3 else a3c3t["rounds"][-1].get("final_answer", "")
        C3R.append(score(meta, c3_final or ""))
        A3C3R.append(score(meta, a3c3_final or ""))

    print(f"\n=== HLE 150 (scorer_LLM_rescue, n={len(common)}) ===")
    results = {
        "n": len(common),
        "A": _agg(A),
        "A2": _agg(A2),
        "A3_vote": _agg(A3V),
        "C3_strong": _agg(C3S),
        "C3_eval": _agg(C3R),
        "A3C3_strong": _agg(A3C3S),
        "A3C3_eval": _agg(A3C3R),
    }
    for k, v in results.items():
        if k == "n":
            continue
        print(f"  {k:14s}: {v}")

    out = results
    outpath = Path(args.out) if args.out else (_traj_path(args.a, args.model).parent.parent / "hle150_scores.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nscores -> {outpath}")


if __name__ == "__main__":
    main()