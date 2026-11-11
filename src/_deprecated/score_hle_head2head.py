"""score_hle_head2head.py
==========================
Aligned A3-vs-C3 head-to-head under scorer_LLM_rescue (T1 match + T2 LLM rescue).

Scoring (matches hle_scorer.score_hle / EVALUATION_STANDARD S2/S7):
  - T1 (deterministic exact-match) is the PRIMARY, token-free signal.
  - T2 (LLM judge) is a ONE-WAY FN rescue ONLY: it re-reads rows T1 already
    marked wrong and may rescue an "answer present but extractor missed" case.
  - The judge NEVER audits a T1-correct row. Do NOT subtract "false positives":
    the bidirectional/AND judge (correct = t1 AND judge) was checked and rejected
    because the judge false-negatives on correctly-answered rows formatted
    differently -- it would overturn genuinely-correct T1 verdicts and deflate
    accuracy. Hence:

        correct = t1_correct  OR  (not t1_correct AND judge == CORRECT)

Arms (all judged with the identical scorer_LLM_rescue):
  A3.init          = A3 round-0 committed answer
  A3.final(vote)   = A3 majority vote (N=10 @ T=0.7) winner
  C3.init          = C3 round-0 committed answer
  C3.final(strong) = C3 last feedback-round answer (strong critic only, ablation)
  C3.final(rubric) = FULL C3 = strong critic (in-loop) + rubric evaluator (offline):
                       multi-answer tasks -> rubric locked verdict (strategy-selectable);
                       single-answer tasks -> strong critic final (no candidate pool).

Run:
  python3 src/score_hle_head2head.py \
      --a3 experiments/hle_pilot_a3 --c3 experiments/hle_pilot_c3 \
      --rubric experiments/_analysis/hle_rubric_ce.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from score_hle_pilot import (  # noqa: E402
    load_tasks_index, read_trajectory, score_a3,
)
from src.hle_scorer import score_hle  # noqa: E402


def load_rubric_verdicts(path: Path) -> dict[str, str | None]:
    """task_id -> locked verdict string (None => abstain)."""
    out: dict[str, str | None] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r.get("verdict")
    return out


def score(meta: dict, response: str) -> dict:
    """scorer_LLM_rescue: T1 primary, judge rescues FN only. Returns score_hle dict."""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a3", default="experiments/hle_pilot_a3")
    ap.add_argument("--c3", default="experiments/hle_pilot_c3")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--rubric", nargs="*", default=[],
                    help="rubric verdict JSONL files; filename stem tags each strategy")
    args = ap.parse_args()

    meta_idx = load_tasks_index()
    a3_traj = read_trajectory(ROOT / args.a3 / args.model / "loop_trajectories.jsonl")
    c3_traj = read_trajectory(ROOT / args.c3 / args.model / "loop_trajectories.jsonl")
    rubric = {Path(p).stem: load_rubric_verdicts(Path(p)) for p in args.rubric}

    common = sorted(set(a3_traj) & set(c3_traj) & set(meta_idx))
    multi = sorted(set().union(*[set(m) for m in rubric.values()])) if rubric else set()
    single = sorted(set(common) - set(multi))

    a3_init, a3_vote, c3_init, c3_strong = [], [], [], []
    c3_rubric = {k: [] for k in rubric}
    for task_id in common:
        meta = meta_idx[task_id]
        a3t, c3t = a3_traj[task_id], c3_traj[task_id]
        a3_init.append(score(meta, a3t["rounds"][0].get("final_answer", "")))
        winner = score_a3(meta, a3t)["winner"]
        a3_vote.append(score(meta, winner.get("final_answer", "")))
        c3_init.append(score(meta, c3t["rounds"][0].get("final_answer", "")))
        c3_strong.append(score(meta, c3t["rounds"][-1].get("final_answer", "")))
        for k, m in rubric.items():
            if task_id in m:
                c3_rubric[k].append(score(meta, m[task_id] or ""))
            else:
                c3_rubric[k].append(score(meta, c3t["rounds"][-1].get("final_answer", "")))

    print(f"tasks={len(common)} (multi-answer={len(multi)} single-answer={len(single)})")
    print("\n=== HLE pilot: scorer_LLM_rescue (T1 match + T2 LLM rescue) ===")
    print("\nA3 (self-consistency, N=10 @ T=0.7):")
    print(f"  init (round-0)   : {_agg(a3_init)}")
    print(f"  final (majority) : {_agg(a3_vote)}")
    print("\nC3 (strong critic @ T=0):")
    print(f"  init (round-0)      : {_agg(c3_init)}")
    print(f"  final (strong only) : {_agg(c3_strong)}")
    for k in rubric:
        print(f"  final (strong+{k}) : {_agg(c3_rubric[k])}")

    # headroom = accuracy gain over the arm's own init (the core comparison)
    a3_hr = _agg(a3_vote)["accuracy"] - _agg(a3_init)["accuracy"]
    c3_hr = _agg(c3_strong)["accuracy"] - _agg(c3_init)["accuracy"]
    print(f"\nheadroom: A3-vote {a3_hr:+.2%} | C3-strong {c3_hr:+.2%}"
          + "".join(f" | C3-{k} {(_agg(c3_rubric[k])['accuracy'] - _agg(c3_init)['accuracy']):+.2%}"
                    for k in rubric))

    out = {
        "n": len(common),
        "n_multi": len(multi), "n_single": len(single),
        "a3": {"init": _agg(a3_init), "final_vote": _agg(a3_vote)},
        "c3": {"init": _agg(c3_init), "final_strong": _agg(c3_strong),
               "final_rubric": {k: _agg(c3_rubric[k]) for k in rubric}},
    }
    outpath = ROOT / args.a3 / "hle_pilot_head2head.json"
    outpath.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nhead-to-head -> {outpath}")


if __name__ == "__main__":
    main()
