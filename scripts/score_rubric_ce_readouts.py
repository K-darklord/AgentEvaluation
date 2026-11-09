"""score_rubric_ce_readouts.py
===============================
Freeze-time audit of the rubric_ce evaluator on HLE-400 C3 (FROZEN_DATA.md v2 / §7 item 1).

Scores the evaluator's locked answer with the SAME sidecar-v2 per-round rules used by
every other arm (is_correct_t3_sidecar_v2.json), NOT the evaluator's internal
`decision == gold` exact-match (that field is only a validation aid). Produces the
three §7 readouts:

  1. eliminator on/off  = evaluator accuracy vs C3.mode (delta = the eliminator gain)
  2. false-CUT rate     = among the evaluator's CUT verdicts, the fraction that
                          discarded a NEW answer that sidecar-v2 says was correct
                          (CUT on switch from_r->to_r reverts to OLD; a CUT is "false"
                          iff sidecar[to_r] is correct).
  3. recovery of the 19 init-correct tasks that C3.final lost.

Single-answer tasks (0 or 1 distinct committed candidate) are never sent to the judge;
for those the evaluator's locked answer is the trace's final committed answer
(= C3.final), matching FROZEN_DATA.md §1 note "single-answer -> C3 final".

Usage:
    python3 scripts/score_rubric_ce_readouts.py \
        --eval experiments/hle400/t3/c3_rubric_ce.jsonl \
        --transitions experiments/hle400/t3/c3_transitions.jsonl \
        --sidecar experiments/hle400/t3/is_correct_t3_sidecar_v2.json \
        --scores experiments/hle400/t3/t3_final_scores_v2.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# C3.mode = 154 / 400 (frozen, FROZEN_DATA.md §1, post-None-bug-fix). No-eliminator baseline.
MODE_CORRECT = 154
MODE_ACC = MODE_CORRECT / 400.0


def load_jsonl(path: Path) -> dict:
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


def sidecar_correct(side_list, i: int) -> bool:
    if 0 <= i < len(side_list):
        return bool(side_list[i]["c"])
    return False


def build_ans_map(trans, side_list):
    rounds = trans.get("rounds", []) if trans is not None else []
    m: dict = {}
    for i, rnd in enumerate(rounds):
        ans = rnd.get("ans")
        if ans is None:
            continue
        m.setdefault(ans, sidecar_correct(side_list, i))
    return m


def recompute_mode(trans, side_list):
    rounds = trans.get("rounds", []) if trans is not None else []
    keys = [r.get("ans") for r in rounds]
    cnt = Counter(a for a in keys if a is not None)
    if not cnt:
        return None, False
    latest: dict = {}
    m: dict = {}
    for i, a in enumerate(keys):
        if a is not None and a not in latest:
            latest[a] = i
        if a is not None and a not in m:
            m[a] = sidecar_correct(side_list, i)
    best = max(cnt, key=lambda k: (cnt[k], latest[k]))
    return best, m.get(best, False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(ROOT / "experiments/hle400/t3/c3_rubric_ce.jsonl"))
    ap.add_argument("--transitions", default=str(ROOT / "experiments/hle400/t3/c3_transitions.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    ap.add_argument("--scores", default=str(ROOT / "experiments/hle400/t3/t3_final_scores_v2.json"))
    args = ap.parse_args()

    sidecar = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    c3 = sidecar["arms"]["C3"]
    trans = load_jsonl(Path(args.transitions))
    evals = load_jsonl(Path(args.eval))
    scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    lost19 = list(scores["vs_shared_init"]["C3.final"]["lost"])

    all_tasks = sorted(c3.keys())
    n = len(all_tasks)

    def effective_verdict(tid: str):
        r = evals.get(tid)
        if r is not None and r.get("verdict") is not None:
            return r["verdict"], r.get("lock_status", "n/a")
        t = trans.get(tid)
        return (t.get("final_ans") if t is not None else None), "single_answer"

    eval_correct = 0
    on_correct = on_n = 0
    off_correct = off_n = 0
    internal_agree = 0
    internal_total = 0
    mode_recomp_correct = 0
    for tid in all_tasks:
        slist = c3.get(tid, [])
        t = trans.get(tid)
        verdict, lock = effective_verdict(tid)
        m = build_ans_map(t, slist)
        ok = m.get(verdict, False)
        if ok:
            eval_correct += 1
        if lock == "single_answer":
            pass
        elif str(lock).startswith("all_unsure_fallback"):
            off_n += 1
            off_correct += 1 if ok else 0
        else:
            on_n += 1
            on_correct += 1 if ok else 0
        r = evals.get(tid)
        if r is not None:
            internal_total += 1
            if bool(r.get("correct")) == ok:
                internal_agree += 1
        _, mc = recompute_mode(t, slist)
        mode_recomp_correct += 1 if mc else 0

    eval_acc = eval_correct / n if n else 0.0
    delta = eval_acc - MODE_ACC

    total_cut = 0
    false_cut = 0
    keep_count = 0
    unsure_count = 0
    for tid, r in evals.items():
        slist = c3.get(tid, [])
        for edge, v in (r.get("cuts") or {}).items():
            if v == "CUT":
                total_cut += 1
                try:
                    to_s = edge.split("->")[1].strip()
                    to_r = int(to_s)
                except (ValueError, IndexError):
                    continue
                if sidecar_correct(slist, to_r):
                    false_cut += 1
            elif v == "KEEP":
                keep_count += 1
            elif v == "UNSURE":
                unsure_count += 1
    false_cut_rate = false_cut / total_cut if total_cut else 0.0

    recovered = [tid for tid in lost19
                 if build_ans_map(trans.get(tid), c3.get(tid, [])).get(effective_verdict(tid)[0], False)]
    recovered_n = len(recovered)

    print("=" * 70)
    print("rubric_ce (freeze-time readouts, sidecar-v2 scoring) — C3, n = %d" % n)
    print("=" * 70)
    print()
    print("[readout 1] eliminator on/off = evaluator vs C3.mode")
    print("  C3.mode        = %d / %d = %.4f   (frozen baseline)" % (MODE_CORRECT, n, MODE_ACC))
    print("  C3.evaluator   = %d / %d = %.4f" % (eval_correct, n, eval_acc))
    print("  delta          = %+.4f  (%+d tasks)" % (delta, eval_correct - MODE_CORRECT))
    print("  -- on/off split (multi-answer tasks only) --")
    if on_n:
        print("  eliminator ON  = %d / %d = %.4f  (locked via elimination)" % (on_correct, on_n, on_correct / on_n))
    if off_n:
        print("  eliminator OFF = %d / %d = %.4f  (all-UNSURE -> mode fallback)" % (off_correct, off_n, off_correct / off_n))
    print()
    print("[readout 2] false-CUT rate (per-switch CUT verdicts)")
    print("  CUT total      = %d" % total_cut)
    print("  false CUT      = %d   (discarded a NEW answer sidecar-v2 says is correct)" % false_cut)
    print("  true  CUT      = %d   (correctly rejected a wrong switch)" % (total_cut - false_cut))
    print("  KEEP           = %d" % keep_count)
    print("  UNSURE         = %d" % unsure_count)
    print("  false-CUT rate = %.4f" % false_cut_rate)
    print()
    print("[readout 3] recovery of the 19 init-correct tasks C3.final lost")
    print("  recovered      = %d / %d" % (recovered_n, len(lost19)))
    print("  recovered ids  = %s" % (", ".join(recovered) if recovered else "none"))
    print()
    print("[cross-checks]")
    print("  internal exact-match agrees with sidecar on %d/%d eval rows" % (internal_agree, internal_total))
    print("  recomputed mode (tie->latest) = %d / %d  (frozen=154)" % (mode_recomp_correct, n))


if __name__ == "__main__":
    main()
