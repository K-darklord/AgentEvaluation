#!/usr/bin/env python3
"""Node-level re-vote of the rubric_ce evaluator (offline, freeze-key identity).

Same frozen identity + sidecar-v2 scoring as recompute_evaluator_offline.py, but the
elimination lock is replaced by a NODE (per-round) vote: a switch verdict re-weights
only its two boundary rounds, leaving a run's interior rounds at full 1.0 weight.
Contrast with the fragment lock, which collapses a whole run into one multiplier.

Usage:
  python3 scripts/recompute_evaluator_node.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "reco", ROOT / "scripts" / "recompute_evaluator_offline.py")
reco = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reco)

CUT_BAR = reco.CUT_BAR
_VOTE_MODE = reco._VOTE_MODE


def node_lock(keys, cuts, allow_unsure=True, tie_break="directional", vote_mode="max", mode=None):
    """Node (per-round) vote: a switch verdict re-weights only its two boundary nodes."""
    n = len(keys)
    left_score = [None] * n    # node i as the NEW side of its left switch (i-1 -> i)
    right_score = [None] * n   # node i as the OLD side of its right switch (i -> i+1)
    undecided = 0
    combine_min = (vote_mode == "min")
    unsure_w = 0.0 if vote_mode == "0" else 0.5
    for (frm, to), v in cuts.items():
        if v == "CUT":
            right_score[frm] = 1.0
            left_score[to] = 0.0
        elif v == "KEEP":
            right_score[frm] = 0.0
            left_score[to] = 1.0
        else:  # UNSURE
            if not allow_unsure:
                undecided += 1
            elif unsure_w == 0.0:
                continue
            else:
                right_score[frm] = unsure_w
                left_score[to] = unsure_w
    if undecided:
        return None, {"status": "undecided_switch"}
    weight = {}
    for i, k in enumerate(keys):
        if k is None:
            continue
        present = [s for s in (left_score[i], right_score[i]) if s is not None]
        m = 1.0 if not present else (min(present) if combine_min else max(present))
        weight[k] = weight.get(k, 0.0) + m
    if not weight:
        return None, {"status": "no_survivors"}
    max_w = max(weight.values())
    top = [a for a, w in weight.items() if w == max_w]
    if len(top) == 1:
        return top[0], {"status": "locked_majority"}
    if tie_break == "mode":
        return mode, {"status": "tie_fallback_mode"}
    if tie_break == "directional":
        pref = {}
        for (frm, to), v in cuts.items():
            if v == "CUT":
                a = keys[frm]
            elif v == "KEEP":
                a = keys[to]
            else:
                continue
            if a is not None:
                pref[a] = pref.get(a, 0) + 1
        if pref:
            choice = max(top, key=lambda a: pref.get(a, 0))
            if pref.get(choice, 0) > 0:
                return choice, {"status": "locked_directional"}
    return None, {"status": "tie_abstain"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(ROOT / "experiments/hle400/t3/c3_rubric_ce.jsonl"))
    ap.add_argument("--transitions", default=str(ROOT / "experiments/hle400/t3/c3_transitions.jsonl"))
    ap.add_argument("--loop", default=str(ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    ap.add_argument("--vote-mode", default=_VOTE_MODE)
    args = ap.parse_args()

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    c3 = side["arms"]["C3"]
    trans = reco.load_jsonl(Path(args.transitions))
    loop = reco.load_jsonl(Path(args.loop))
    evald = reco.load_jsonl(Path(args.eval))
    all_tasks = sorted(c3.keys())

    status = Counter()
    mode_correct = 0
    new_verdicts = {}
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        lp = loop.get(tid)
        if t is None or lp is None:
            continue
        gold = lp.get("gold_answer", "") or t.get("gold", "")
        keys = reco.freeze_keys(gold, lp)
        mk = reco.freeze_mode_key(keys)
        mode_correct += 1 if reco.last_key_correct(keys, slist, mk) else 0

        uniq = []
        for k in keys:
            if k is not None and k not in uniq:
                uniq.append(k)

        if len(uniq) < 2:
            v = uniq[0] if uniq else None
            new_verdicts[tid] = v
            status["single_answer"] += 1
            continue

        switches = reco.freeze_switches(keys)
        r = evald.get(tid)
        st_ps = r.get("per_switch", {}) if r is not None else {}
        cuts = {}
        for e in switches:
            key = f"{e[0]}->{e[1]}"
            cuts[e] = reco._score_to_verdict(st_ps[key], CUT_BAR) if key in st_ps else "UNSURE"

        if not switches:
            verdict = mk
            st = "no_switch_edges_mode"
        elif all(v_ == "UNSURE" for v_ in cuts.values()):
            verdict = mk
            st = "all_unsure_fallback_mode"
        else:
            verdict, info = node_lock(
                keys, cuts, allow_unsure=True, tie_break="mode",
                vote_mode=args.vote_mode, mode=mk)
            st = info["status"]
        new_verdicts[tid] = verdict
        status[st] += 1

    eval_correct = 0
    changed = []
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        lp = loop.get(tid)
        if t is None or lp is None:
            continue
        gold = lp.get("gold_answer", "") or t.get("gold", "")
        keys = reco.freeze_keys(gold, lp)
        v = new_verdicts.get(tid)
        eval_correct += 1 if reco.last_key_correct(keys, slist, v) else 0
        r = evald.get(tid)
        old_v = (r.get("verdict") if r is not None and r.get("verdict") is not None
                 else (t.get("final_ans") if t is not None else None))
        if v != old_v:
            changed.append((tid, old_v, v))

    print(f"[node] vote_mode = {args.vote_mode}")
    print(f"[node] mode      = {mode_correct}/{len(all_tasks)}")
    print(f"[node] evaluator = {eval_correct}/{len(all_tasks)}")
    print(f"[node] lock_status distribution = {dict(status)}")
    print(f"[node] verdict-changed tasks = {len(changed)}")
    for tid, o, n in changed[:60]:
        print(f"    {tid}: {o!r} -> {n!r}")


if __name__ == "__main__":
    main()
