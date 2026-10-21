"""
offline_argmin_check.py
=======================
Zero-cost offline check: does the weak critic's P(wrong) proxy (``error_score``)
let us pick the most-correct state out of the n round-answers already produced by
the feedback loop? Compares selection policies over the candidate states on disk
— no API, no model loading.

Policies per task (over its ``rounds``):
  first   : round 0 answer
  last    : final round answer (current production behaviour)
  argmin  : state with MIN error_score ("least likely wrong")
  argmax  : state with MAX error_score (inverted sanity check)
  oracle  : any round correct (the activation ceiling P_act)

The error_score is RE-computed per state via ``WeakCritic.error_score`` (gold-free)
rather than read from the trajectory, where it is stored offset to the *previous*
answer and is null for round 0.

Reproducibility: deterministic, one command:  python3 src/offline_argmin_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

from build_weak_critic import WeakCritic, _family_base_rates  # noqa: E402


def load_bank() -> list[dict]:
    p = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def evaluate_traj(path: Path, critic: WeakCritic) -> None:
    per_task: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                per_task.append(json.loads(line))

    n = first = last = argmin_ok = argmax_ok = oracle = 0
    var_tasks = var_first = var_last = var_argmin = var_oracle = 0
    tie_all = 0  # tasks where every state shares the same error_score (no spread)

    for t in per_task:
        fam = t.get("family")
        if not fam:
            continue  # weak critic has no leaves for this family
        rounds = t["rounds"]
        if not rounds:
            continue
        n += 1

        # re-compute a gold-free error_score for every candidate state
        scored = []
        for i, r in enumerate(rounds):
            es = critic.error_score(fam, t.get("prompt", ""), r.get("final_answer"),
                                    exclude_task_ids={t["task_id"]})
            scored.append((i, es, bool(r.get("is_correct"))))

        ok_first = scored[0][2]
        ok_last = scored[-1][2]
        ok_any = any(s[2] for s in scored)
        i_min = min(scored, key=lambda s: s[1])[0]
        i_max = max(scored, key=lambda s: s[1])[0]
        ok_argmin = rounds[i_min]["is_correct"]
        ok_argmax = rounds[i_max]["is_correct"]

        first += ok_first
        last += ok_last
        argmin_ok += ok_argmin
        argmax_ok += ok_argmax
        oracle += ok_any

        es_vals = [s[1] for s in scored]
        if max(es_vals) - min(es_vals) <= 1e-9:
            tie_all += 1
        else:
            var_tasks += 1
            var_first += ok_first
            var_last += ok_last
            var_argmin += ok_argmin
            var_oracle += ok_any

    pct = lambda x, d: (x / d) if d else 0.0  # noqa: E731
    print(f"\n=== {path.relative_to(ROOT)} ===")
    print(f"    usable tasks (family known): {n}")
    print(f"    acc first           : {pct(first, n):.2%}  ({first}/{n})")
    print(f"    acc last            : {pct(last, n):.2%}  ({last}/{n})")
    print(f"    acc argmin(P_wrong) : {pct(argmin_ok, n):.2%}  ({argmin_ok}/{n})")
    print(f"    acc argmax(P_wrong) : {pct(argmax_ok, n):.2%}  ({argmax_ok}/{n})  [inverted sanity]")
    print(f"    acc oracle (P_act)  : {pct(oracle, n):.2%}  ({oracle}/{n})")
    print(f"    --- spread diagnostic (per-state error_score varies) ---")
    print(f"    tasks with spread   : {var_tasks}/{n}  (no-spread/tie: {tie_all})")
    print(f"    acc first  (spread) : {pct(var_first, var_tasks):.2%}")
    print(f"    acc last   (spread) : {pct(var_last, var_tasks):.2%}")
    print(f"    acc argmin (spread) : {pct(var_argmin, var_tasks):.2%}")
    print(f"    acc oracle (spread) : {pct(var_oracle, var_tasks):.2%}")


def main() -> None:
    critic = WeakCritic(load_bank(), base_rates=_family_base_rates())

    targets = [
        ROOT / "experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_C_pilot_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
        # early phase-1 treatment run (3 models, 250 tasks); arm field predates the
        # arm tag in the directory name but defaults to C (critic feedback).
        ROOT / "experiments/feedback_loop_20261006_173715/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/glm-5.3/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/qwen3.8-flash/loop_trajectories.jsonl",
    ]
    for p in targets:
        if p.exists():
            evaluate_traj(p, critic)
        else:
            print(f"\n[skip] missing: {p}")


if __name__ == "__main__":
    main()
