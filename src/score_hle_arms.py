"""score_hle_arms.py
===================
Unified HLE arm comparison under the frozen standard (DRAFT.md §3.0 / PPT P7).

Arms (all graded by the same scorer_LLM_rescue):
  A    = bare re-solve, T=0, single answer            -> accuracy
  A2   = fixed neutral placebo loop (T=0)             -> init / final / settle / mode
  A3   = self-consistency (T=0.7, N=10) majority vote -> init / vote
  A3C3 = A3-seeded round-0 + C3 loop                  -> init / final / settle / mode / evaluator
  C3   = strong critic (in-loop) + evaluator (offline) -> init / final / settle / mode / evaluator

Metric definitions (§3.0): init=round-0, final=last, settle=trailing 3-identical-commit
(abstain if none), mode=majority committed answer (tie->latest), evaluator=rubric_ce
locked verdict (multi-answer; single-answer -> C3 final).

NOTE: pilot (50) and hle150 (150) use DIFFERENT jsonl orders, so their hle_001.. ids are
different questions and must never be merged. Run one slice at a time.

Run:
  python3 src/score_hle_arms.py --data data/raw/hle/hle_50_pilot.jsonl  --prefix hle_pilot --rubric experiments/hle_pilot_c3/c3_rubric_ce.jsonl
  python3 src/score_hle_arms.py --data data/raw/hle/hle_150_new.jsonl --prefix hle150      --rubric experiments/hle150_C3/c3_rubric_ce.jsonl
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

from src.hle_scorer import score_hle  # noqa: E402
from src.run_feedback_loop import _early_stop_key  # noqa: E402

FAMILY = "hle"
EARLY_STOP_N = 3


def load_index(data_path: Path) -> dict:
    idx: dict = {}
    with data_path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            idx[f"hle_{i:03d}"] = {
                "question": str(d.get("question", "")).strip(),
                "gold": str(d.get("answer", "")).strip(),
                "answer_type": str(d.get("answer_type", "")).strip(),
                "shape": str(d.get("shape", "")).strip(),
            }
    return idx


def read_traj(path: Path) -> dict:
    out: dict = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r
    return out


def load_rubric(path: Path) -> dict:
    out: dict = {}
    if not path or not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r.get("verdict")
    return out


def _score(meta: dict, resp: str) -> dict:
    return score_hle(meta["question"], meta["gold"],
                     meta["answer_type"], meta["shape"], resp or "")


def _truncated_wrong() -> dict:
    """Score a length-truncated winner as wrong (no-commit), bypassing the T2 judge.

    A winning round with finish_reason == "length" holds a budget-truncated fragment,
    not a clean commit; it is scored wrong uniformly across all arms/metrics and is
    never sent to the judge."""
    return {"correct": False, "t1_correct": False, "judge_correct": None,
            "agreement": None, "disagreement": None}


def _key(meta: dict, rec: dict):
    return _early_stop_key(FAMILY, meta["gold"], rec.get("final_answer", ""),
                           rec.get("reasoning_content", ""),
                           rec.get("finish_reason", ""))[0]


def _round_score(meta: dict, rounds: list, i: int) -> dict:
    if 0 <= i < len(rounds):
        if rounds[i].get("finish_reason", "") == "length":
            return _truncated_wrong()
        return _score(meta, rounds[i].get("final_answer", ""))
    return _score(meta, "")


def _settle_idx(meta: dict, task: dict) -> int | None:
    rounds = task.get("rounds", [])
    if not rounds:
        return None
    keys = [_key(meta, r) for r in rounds]
    n = len(keys)
    i = n - 1
    while i >= 0:
        if keys[i] is None:        # a no-commit round is not a settle anchor
            i -= 1
            continue
        j = i
        while j - 1 >= 0 and keys[j - 1] == keys[j]:
            j -= 1
        if i - j + 1 >= EARLY_STOP_N:
            return j
        i = j - 1
    return None


def _mode_idx(meta: dict, task: dict) -> int:
    rounds = task.get("rounds", [])
    if not rounds:
        return -1
    keys = [_key(meta, r) for r in rounds]
    cnt: dict = {}
    latest: dict = {}
    for i, k in enumerate(keys):
        if k is None:              # a no-commit round is not a candidate (mirrors _majority_vote)
            continue
        cnt[k] = cnt.get(k, 0) + 1
        latest[k] = i
    if not cnt:
        return -1
    best = max(cnt, key=lambda k: (cnt[k], latest[k]))
    return latest[best]


def _agg(scores: list[dict]) -> dict:
    n = len(scores) or 1
    c = sum(1 for s in scores if s["correct"])
    t1 = sum(1 for s in scores if s["t1_correct"])
    fn = sum(1 for s in scores if s["disagreement"] == "FN")
    judge = sum(1 for s in scores if s["judge_correct"] is not None)
    return {"n": len(scores), "accuracy": round(c / n, 4),
            "t1_accuracy": round(t1 / n, 4), "judge_n": judge, "fn_rescued": fn}


def _majority_vote(meta: dict, task: dict) -> dict:
    """A3 canonical majority vote (tie -> first-encountered) over the n-1 i.i.d.
    T>0 samples (rounds[1:]). Round 0 is the A-seeded deterministic init anchor
    (A3's `init`), NOT a vote: A must not enter the self-consistency pool."""
    rounds = task.get("rounds", [])
    samples = rounds[1:]  # exclude the A-seeded round-0 anchor
    if not samples:
        return _score(meta, "")
    votes: Counter = Counter()
    for r in samples:
        k = _key(meta, r)
        if k is not None:
            votes[k] += 1
    winner_rec = samples[0] if samples else None
    if votes:
        winner_key = votes.most_common(1)[0][0]
        winner_rec = next((r for r in samples if _key(meta, r) == winner_key), samples[0])
    if winner_rec.get("finish_reason", "") == "length":
        return _truncated_wrong()
    return _score(meta, winner_rec.get("final_answer", ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--base", default="experiments")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--rubric", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--rows", default=None)
    args = ap.parse_args()

    base = ROOT / args.base
    meta_idx = load_index(ROOT / args.data)

    def traj(arm: str) -> dict:
        return read_traj(base / f"{args.prefix}_{arm}" / args.model / "loop_trajectories.jsonl")

    tA, tA2, tA3, tA3C3, tC3 = traj("A"), traj("A2"), traj("A3"), traj("A3C3"), traj("C3")
    rubric = load_rubric(ROOT / args.rubric) if args.rubric else {}
    common = sorted(set(tC3) & set(meta_idx))
    print(f"[{args.prefix}] index={len(meta_idx)} A={len(tA)} A2={len(tA2)} A3={len(tA3)} "
          f"A3C3={len(tA3C3)} C3={len(tC3)} rubric={len(rubric)} common={len(common)}")

    # per-arm per-task correct arrays (aligned to `common`)
    def arr_from_fn(fn):
        return [fn(t)["correct"] for t in common]

    res: dict = {}

    def build_loop(traj_dict, tasks):
        init = []; final = []; settle = []; mode = []
        for t in tasks:
            meta, task = meta_idx[t], traj_dict[t]
            rounds = task.get("rounds", [])
            init.append(_round_score(meta, rounds, 0))
            final.append(_round_score(meta, rounds, len(rounds) - 1))
            si = _settle_idx(meta, task)
            settle.append(_round_score(meta, rounds, si) if si is not None else _score(meta, ""))
            mode.append(_round_score(meta, rounds, _mode_idx(meta, task)))
        return {"init": init, "final": final, "settle": settle, "mode": mode}

    # A: single bare answer
    res["A"] = [_score(meta_idx[t], tA[t]["rounds"][0]["final_answer"])
                for t in common if t in tA]
    # A2
    a2_tasks = [t for t in common if t in tA2]
    res["A2"] = build_loop(tA2, a2_tasks)
    # A3
    a3_tasks = [t for t in common if t in tA3]
    res["A3"] = {"init": [_round_score(meta_idx[t], tA3[t]["rounds"], 0) for t in a3_tasks],
                 "vote": [_majority_vote(meta_idx[t], tA3[t]) for t in a3_tasks]}
    # A3C3
    a3c3_tasks = [t for t in common if t in tA3C3]
    res["A3C3"] = build_loop(tA3C3, a3c3_tasks)
    # C3
    res["C3"] = build_loop(tC3, common)
    # evaluator
    def eval_for(traj_dict, tasks):
        return [_score(meta_idx[t], rubric[t] or "") if t in rubric
                else _round_score(meta_idx[t], traj_dict[t]["rounds"],
                                  len(traj_dict[t]["rounds"]) - 1)
                for t in tasks]
    if rubric:
        res["C3_eval"] = eval_for(tC3, common)
        res["A3C3_eval"] = eval_for(tA3C3, a3c3_tasks)

    print("\n=== arm accuracy (scorer_LLM_rescue) ===")
    def show(name, block):
        if isinstance(block, list):
            print(f"  {name:<14}: {_agg(block)}")
        else:
            for k, v in block.items():
                print(f"  {name}.{k:<11}: {_agg(v)}")
    for k, v in res.items():
        show(k, v)

    out = {"slice": args.prefix, "n": len(common),
           "arms": {k: (_agg(v) if isinstance(v, list) else {kk: _agg(vv) for kk, vv in v.items()})
                    for k, v in res.items()}}
    outpath = ROOT / (args.out or f"{args.base}/{args.prefix}/hle_arms.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsummary -> {outpath}")

    if args.rows:
        rp = ROOT / args.rows
        rp.parent.mkdir(parents=True, exist_ok=True)
        with rp.open("w", encoding="utf-8") as f:
            for i, t in enumerate(common):
                row = {"task_id": t, "gold": meta_idx[t]["gold"],
                       "answer_type": meta_idx[t]["answer_type"],
                       "shape": meta_idx[t]["shape"]}
                # C3 anchor metrics aligned by index into `common`
                for arm, block in res.items():
                    if isinstance(block, list):
                        row[arm] = block[i]["correct"] if i < len(block) else None
                    else:
                        # loop arms: build_loop preserves `common` order for C3; for A2/A3C3
                        # the task lists are subsets — fall back to C3-aligned only for C3
                        pass
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"rows -> {rp}")


if __name__ == "__main__":
    main()
