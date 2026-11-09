#!/usr/bin/env python3
"""Offline re-derivation of the rubric_ce locked verdict under the FROZEN standard
(score_hle_arms._key), unified with C3 mode / A3 vote / qcut.

Identity = freeze-key two-stage rule: a length-truncated int/letter round recovers its
key from the CoT tail via `_early_stop_key` and STILL votes; the frozen scorer marks the
winning round wrong only when the key's LAST occurrence round is truncated (sidecar
s=="trunc"). No judge is called: the per-switch error scores already stored in
experiments/hle400/t3/c3_rubric_ce.jsonl are re-mapped onto the freeze-key switch set,
the elimination lock is re-run on the freeze-key runs, and the locked key is re-scored
against sidecar-v2 (`last_key_correct`).

The gold used for the freeze key is the loop trajectory's ``gold_answer`` (NOT the
transition record's lowercased/format-stripped ``gold``; 56 tasks diverge on casing).

Usage:
  python3 scripts/recompute_evaluator_offline.py \
      --eval experiments/hle400/t3/c3_rubric_ce.jsonl \
      --transitions experiments/hle400/t3/c3_transitions.jsonl \
      --loop experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl \
      --sidecar experiments/hle400/t3/is_correct_t3_sidecar_v2.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.stage_b_evaluator import (  # noqa: E402
    _elimination_mode_lock, _score_to_verdict, _VOTE_MODE,
)
from src.score_hle_arms import _key  # noqa: E402

CUT_BAR = 8.0


def load_jsonl(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r
    return out


# ------------------------------------------------------------------ freeze-key helpers
def sidecar_correct(slist, i):
    return bool(slist[i].get("c")) if 0 <= i < len(slist) else False


def freeze_keys(gold, loop_rec):
    """Per-round frozen answer identity — exactly score_hle_arms `_key`."""
    meta = {"gold": gold}
    return [_key(meta, r) for r in loop_rec.get("rounds", [])]


def encode(k):
    """Canonical string identity for a key tuple (None stays None = no commit)."""
    return None if k is None else json.dumps(k, ensure_ascii=False, separators=(",", ":"))


def decode(s):
    return None if s is None else tuple(json.loads(s))


def last_key_correct(keys, slist, k):
    """Correctness under the frozen two-stage rule: the key's LAST occurrence round
    decides via sidecar v2; a truncated last occurrence is wrong."""
    for i in range(len(keys) - 1, -1, -1):
        if keys[i] == k:
            return sidecar_correct(slist, i)
    return False


def freeze_switches(keys):
    """(from_i, to_i) edges whose frozen key changes between consecutive non-None keys."""
    out = []
    for i in range(1, len(keys)):
        if keys[i - 1] is None or keys[i] is None:
            continue
        if keys[i - 1] != keys[i]:
            out.append((i - 1, i))
    return out


def freeze_mode_key(keys):
    """Majority key, tie -> latest occurrence (mirrors `_mode_idx`)."""
    cnt: dict = {}
    latest: dict = {}
    for i, k in enumerate(keys):
        if k is None:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        latest[k] = i
    if not cnt:
        return None
    return max(cnt, key=lambda k: (cnt[k], latest[k]))


def build_key_rec(keys):
    """A transition-shaped rec whose `ans` is the encoded key (None = no commit), so the
    existing `_mode_answer` / `_elimination_mode_lock` operate on freeze-key identity."""
    rounds = [{"r": i, "ans": encode(keys[i])} for i in range(len(keys))]
    cands = []
    for k in keys:
        e = encode(k)
        if e is not None and e not in cands:
            cands.append(e)
    return {"rounds": rounds, "candidates": cands}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(ROOT / "experiments/hle400/t3/c3_rubric_ce.jsonl"))
    ap.add_argument("--transitions", default=str(ROOT / "experiments/hle400/t3/c3_transitions.jsonl"))
    ap.add_argument("--loop", default=str(ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    ap.add_argument("--weight-by", default="round", choices=["round", "fragment"])
    args = ap.parse_args()

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    c3 = side["arms"]["C3"]
    trans = load_jsonl(Path(args.transitions))
    loop = load_jsonl(Path(args.loop))
    evald = load_jsonl(Path(args.eval))
    all_tasks = sorted(c3.keys())

    # (1) frozen baseline: old verdict scored under old (ans + 剔 trunc) chain, sidecar.
    old_correct = 0
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        r = evald.get(tid)
        v = (r.get("verdict") if r is not None and r.get("verdict") is not None
             else (t.get("final_ans") if t is not None else None))
        if t is None or v is None:
            continue
        for i, rr in enumerate(t.get("rounds", [])):
            if rr.get("ans") == v:
                old_correct += 1 if sidecar_correct(slist, i) else 0
                break
    print(f"[baseline] old evaluator (ans chain, sidecar) = {old_correct}/{len(all_tasks)}")

    # (2) freeze-key recompute: mode + evaluator under the unified standard.
    status = Counter()
    new_verdicts: dict = {}
    mode_correct = 0
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        lp = loop.get(tid)
        if t is None or lp is None:
            continue
        gold = lp.get("gold_answer", "") or t.get("gold", "")
        keys = freeze_keys(gold, lp)

        mk = freeze_mode_key(keys)
        mode_correct += 1 if last_key_correct(keys, slist, mk) else 0

        uniq = []
        for k in keys:
            if k is not None and k not in uniq:
                uniq.append(k)

        if len(uniq) < 2:
            v = uniq[0] if uniq else None
            new_verdicts[tid] = v
            status["single_answer"] += 1
            continue

        switches = freeze_switches(keys)
        r = evald.get(tid)
        st_ps = r.get("per_switch", {}) if r is not None else {}
        cuts = {}
        for e in switches:
            key = f"{e[0]}->{e[1]}"
            cuts[e] = _score_to_verdict(st_ps[key], CUT_BAR) if key in st_ps else "UNSURE"

        key_rec = build_key_rec(keys)
        if not switches:
            verdict = mk
            st = "no_switch_edges_mode"
        elif all(v_ == "UNSURE" for v_ in cuts.values()):
            verdict = mk
            st = "all_unsure_fallback_mode"
        else:
            enc, info = _elimination_mode_lock(
                key_rec, cuts, allow_unsure=True, tie_break="mode",
                vote_mode=_VOTE_MODE, weight_by=args.weight_by)
            verdict = decode(enc)
            st = info["status"]
        new_verdicts[tid] = verdict
        status[st] += 1

    # (3) score freeze-key evaluator via last_key_correct.
    eval_correct = 0
    changed = []
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        lp = loop.get(tid)
        if t is None or lp is None:
            continue
        gold = lp.get("gold_answer", "") or t.get("gold", "")
        keys = freeze_keys(gold, lp)
        v = new_verdicts.get(tid)
        eval_correct += 1 if last_key_correct(keys, slist, v) else 0
        r = evald.get(tid)
        old_v = (r.get("verdict") if r is not None and r.get("verdict") is not None
                 else (t.get("final_ans") if t is not None else None))
        if v != old_v:
            changed.append((tid, old_v, v))

    print(f"[freeze-key] mode      = {mode_correct}/{len(all_tasks)}")
    print(f"[freeze-key] evaluator = {eval_correct}/{len(all_tasks)}")
    print(f"[freeze-key] lock_status distribution = {dict(status)}")
    print(f"[freeze-key] verdict-changed tasks = {len(changed)}")
    for tid, o, n in changed[:60]:
        print(f"    {tid}: {o!r} -> {n!r}")


if __name__ == "__main__":
    main()
