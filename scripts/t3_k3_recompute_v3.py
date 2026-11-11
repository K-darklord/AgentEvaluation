#!/usr/bin/env python3
"""Recompute v3 final scores + transition metrics from the v3 sidecar.

This is the v3 counterpart of scripts/t3_k3_adjudicate_and_recompute.py.
Scoring logic (final / settle / mode / vote winners, paired McNemar, transition
EIR/ECR/P_act/P_flip, by-answer-form split, solver cost) is byte-for-byte the same
as the v2 run; the ONLY difference is that the per-round correctness verdicts are
read from the already-frozen v3 sidecar instead of being recomputed (no truncation
rule re-run, no K=3 adjudication re-run).

Inputs : experiments/hle400/t3/is_correct_t3_sidecar_v3.json (per-round verdicts)
         experiments/hle400_{A,A2,A3,C3,C2,A2PRIME}/.../loop_trajectories.jsonl
         (current, post-api-failure-rerun trajectories; row counts verified equal
          to the v3 sidecar)
Outputs: experiments/hle400/t3/t3_final_scores_v3.json
         experiments/hle400/t3/transition_metrics_v3.json
"""
import json
import sys
from pathlib import Path
from collections import Counter
from math import comb

sys.path.insert(0, ".")
from src.score_hle_arms import load_index, read_traj, _settle_idx, _mode_idx, _key

T3 = Path("experiments/hle400/t3")
ARMS = {"A": ["init"], "A2": ["init", "final", "settle", "mode"], "A3": ["init", "vote"], "C3": ["init", "final", "settle", "mode"], "C2": ["init", "final", "settle", "mode"], "A2P": ["init", "final", "settle", "mode"]}
# Arms whose critic is an independent LLM call (bank-free C2 included). Template/placebo
# critic arms (A2, future A2P) make zero LLM critic calls and must NOT be hardcoded here.
LLM_CRITIC_ARMS = {"C3", "A3C3", "C2"}
idx = load_index(Path("data/raw/hle/hle_400_new.jsonl"))


def _traj_dir(a):
    # C2 and A2P ran on the payg endpoint (deepseek-v4-flash-payg); the other four arms on token-plan.
    return "deepseek-v4-flash-payg" if a in ("C2", "A2P") else "deepseek-v4-flash"


def _exp_dir(a):
    return "hle400_A2PRIME" if a == "A2P" else f"hle400_{a}"


traj = {a: read_traj(Path(f"experiments/{_exp_dir(a)}/{_traj_dir(a)}/loop_trajectories.jsonl")) for a in ARMS}
side = json.load(open(T3 / "is_correct_t3_sidecar_v3.json"))["arms"]


# ---- winners (verbatim from t3_k3_adjudicate_and_recompute.py)
def winner_idx(arm, met, meta, task):
    rs = task["rounds"]
    if met == "init": return 0
    if met == "final": return len(rs) - 1
    if met == "settle": return _settle_idx(meta, task)
    if met == "mode": return _mode_idx(meta, task)
    if met == "vote":
        s = rs[1:]; v = Counter()
        for j, r in enumerate(s):
            k = _key(meta, r)
            if k is not None: v[k] += 1
        if not v: return 1 if s else None
        wk = v.most_common(1)[0][0]
        return 1 + next(j for j, r in enumerate(s) if _key(meta, r) == wk)
    raise ValueError(met)


correct = {}
scores = {}
for arm, mets in ARMS.items():
    for met in mets:
        c = set()
        for tid, task in traj[arm].items():
            wi = winner_idx(arm, met, idx[tid], task)
            if wi is None or wi < 0: continue
            if side[arm][tid][wi]["c"]: c.add(tid)
        correct[f"{arm}.{met}"] = c
        scores[f"{arm}.{met}"] = {"correct": len(c), "n": 400, "acc": round(len(c) / 400, 4)}


def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


pairs = [("C3.final", "A3.vote"), ("C3.mode", "A3.vote"), ("C3.final", "A2.final"), ("C3.mode", "A2.mode"), ("A2.final", "A3.vote"), ("A2.mode", "A3.vote"), ("C3.final", "A.init"), ("A3.vote", "A.init"), ("A2.final", "A.init"), ("C3.final", "C2.final"), ("C3.mode", "C2.mode"), ("C2.final", "A3.vote"), ("C2.mode", "A3.vote"), ("C2.final", "A2.final"), ("C2.mode", "A2.mode"), ("C2.final", "A.init"), ("C2.mode", "A.init"), ("A2P.final", "C2.final"), ("A2P.mode", "C2.mode"), ("A2P.final", "A3.vote"), ("A2P.mode", "A3.vote"), ("A2P.final", "A2.final"), ("A2P.mode", "A2.mode"), ("A2P.final", "A.init"), ("A2P.mode", "A.init")]
paired = {}
for x, y in pairs:
    b, c = len(correct[x] - correct[y]), len(correct[y] - correct[x])
    paired[f"{x} vs {y}"] = {"only_left": b, "only_right": c, "both": len(correct[x] & correct[y]), "mcnemar_p": round(mcnemar(b, c), 4)}

# ---- transitions (verbatim)
trans = {}
for arm in ARMS:
    per_task = {}
    eir_n = eir_d = ecr_n = ecr_d = 0
    for tid, task in traj[arm].items():
        meta = idx[tid]; rs = task["rounds"]; sv = side[arm][tid]
        cor = [s["c"] for s in sv]
        keys = [_key(meta, r) for r in rs]
        switches = []
        for i in range(1, len(rs)):
            if keys[i] != keys[i - 1]:
                switches.append({"round": i, "from_correct": cor[i - 1], "to_correct": cor[i], "from_key": str(keys[i - 1]), "to_key": str(keys[i]), "critic_direction": bool(rs[i - 1].get("critic_direction"))})
            if cor[i - 1]:
                eir_d += 1; eir_n += (not cor[i])
            else:
                ecr_d += 1; ecr_n += cor[i]
        si = _settle_idx(meta, task); mi = _mode_idx(meta, task)
        per_task[tid] = {"n_rounds": len(rs), "init_correct": cor[0], "final_correct": cor[-1],
                         "settle_correct": (cor[si] if si is not None else None), "mode_correct": (cor[mi] if mi >= 0 else None),
                         "p_act": any(cor), "p_flip": any(cor) and not cor[-1], "n_switches": len(switches),
                         "wrong_to_correct": sum(1 for s in switches if (not s["from_correct"]) and s["to_correct"]),
                         "correct_to_wrong": sum(1 for s in switches if s["from_correct"] and not s["to_correct"]),
                         "per_round_correct": cor, "switches": switches}
    n = len(per_task)
    trans[arm] = {"summary": {"P_act": round(sum(t["p_act"] for t in per_task.values()) / n, 4),
                              "P_flip": round(sum(t["p_flip"] for t in per_task.values()) / n, 4),
                              "EIR": round(eir_n / eir_d, 4) if eir_d else None, "EIR_num_den": [eir_n, eir_d],
                              "ECR": round(ecr_n / ecr_d, 4) if ecr_d else None, "ECR_num_den": [ecr_n, ecr_d],
                              "init_acc": round(sum(t["init_correct"] for t in per_task.values()) / n, 4),
                              "final_acc": round(sum(t["final_correct"] for t in per_task.values()) / n, 4),
                              "mean_rounds": round(sum(t["n_rounds"] for t in per_task.values()) / n, 2),
                              "tasks_with_switch": sum(1 for t in per_task.values() if t["n_switches"]),
                              "wrong_to_correct_switches": sum(t["wrong_to_correct"] for t in per_task.values()),
                              "correct_to_wrong_switches": sum(t["correct_to_wrong"] for t in per_task.values())},
                  "tasks": per_task}

init_set = correct["A.init"]
lost_gained = {k: {"kept_init_correct": len(init_set & v), "lost": sorted(init_set - v), "gained": len(v - init_set)} for k, v in correct.items()}

# ---- cost (solver tokens only) and answer-form split (verbatim)
cost = {}
for arm in ARMS:
    tot = sum(r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) for t in traj[arm].values() for r in t["rounds"])
    rounds = sum(len(t["rounds"]) for t in traj[arm].values())
    critic_calls = (sum(1 for t in traj[arm].values() for r in t["rounds"][1:]
                        if r.get("critic_direction") or r.get("critic_fallback"))
                    if arm in LLM_CRITIC_ARMS else 0)
    cost[arm] = {"solver_tokens_total": tot, "solver_rounds": rounds,
                 "critic_calls_llm": critic_calls, "critic_calls_unlogged": critic_calls,  # legacy alias
                 "solver_tokens_per_correct": {m: round(tot / scores[f"{arm}.{m}"]["correct"]) for m in ARMS[arm]}}
form = {}
mc = {t for t, m in idx.items() if m["answer_type"] == "multipleChoice"}
for k, c in correct.items():
    form[k] = {"mcq_correct": len(c & mc), "mcq_n": len(mc), "mcq_acc": round(len(c & mc) / len(mc), 4),
               "open_correct": len(c - mc), "open_n": 400 - len(mc), "open_acc": round(len(c - mc) / (400 - len(mc)), 4)}

json.dump({"scores": scores, "paired": paired, "vs_shared_init": lost_gained, "cost_solver_only": cost, "by_answer_form": form}, open(T3 / "t3_final_scores_v3.json", "w"), indent=1)
json.dump(trans, open(T3 / "transition_metrics_v3.json", "w"))

print("\n== winner-level accuracy (v3)")
for k, v in scores.items(): print(f"  {k:10s} {v['correct']:4d}  {v['acc']:.4f}")
print("\n== paired")
for k, v in paired.items(): print(f"  {k:24s} L{v['only_left']:3d} R{v['only_right']:3d} both{v['both']:4d} p={v['mcnemar_p']}")
print("\n== vs shared init")
for k, v in lost_gained.items(): print(f"  {k:10s} kept {v['kept_init_correct']:3d} lost {len(v['lost']):3d} gained {v['gained']:3d}")
print("\n== transitions")
for a, t in trans.items(): print(" ", a, t["summary"])
