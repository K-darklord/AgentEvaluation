"""
low_confidence_profiling.py
===========================
Zero-cost offline profiling of the C-arm loop trajectories, aimed at ONE question:
what characterises the tasks the model gets WRONG at the end — and in particular
the "low-confidence" ones (flat answer mode)?

For each task we compute, gold-free except the stored is_correct flags:
  - family, n_rounds, n_uniq (distinct normalised answers)
  - concentration = freq(argmax answer)/n_rounds  (1 = always same answer)
  - final_correct, correct_appeared (any round correct), start_correct (round0)
  - modal_answer_is_correct (does the most frequent answer coincide with a correct
    answer anywhere)
  - critic signal: max error_score over rounds, and max evidence
Then we bucket final-WRONG tasks by:
  - SHARP wrong (concentration >= 0.6): confidently stuck on a wrong answer
  - FLAT  wrong (concentration <= 0.5): no dominant answer (model truly uncertain)
and cross-tabulate with activation (did the correct answer ever appear).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]

def _norm(s):
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")

FILES = [
    ROOT / "experiments/feedback_loop_20261006_173715/deepseek-v4-flash/loop_trajectories.jsonl",
    ROOT / "experiments/feedback_loop_20261006_173715/glm-5.3/loop_trajectories.jsonl",
    ROOT / "experiments/feedback_loop_20261006_173715/qwen3.8-flash/loop_trajectories.jsonl",
    ROOT / "experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
]

def analyze(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    per_fam = defaultdict(lambda: {"n":0,"wrong":0,"sharp_wrong":0,"flat_wrong":0,
                                   "activated_wrong":0,"wrong_activated":0})
    conc_correct, conc_wrong = [], []
    ev_correct, ev_wrong = [], []
    sharp_wrong_activated = 0
    sharp_wrong_total = 0
    flat_wrong_activated = 0
    flat_wrong_total = 0

    for t in rows:
        fam = t.get("family") or "unknown"
        rounds = t.get("rounds", [])
        if not rounds:
            continue
        seq = [_norm(r.get("final_answer")) for r in rounds]
        corr = [bool(r.get("is_correct")) for r in rounds]
        n = len(seq)
        final_correct = corr[-1]
        correct_appeared = any(corr)
        start_correct = corr[0]
        cnt = Counter(seq)
        conc = cnt.most_common(1)[0][1] / n
        n_uniq = len(cnt)
        # modal answer is "correct" if ANY round carrying that answer is correct
        modal_ans = cnt.most_common(1)[0][0]
        modal_is_correct = any(c for a, c in zip(seq, corr) if a == modal_ans)
        # critic signal max across rounds
        evs = [r.get("evidence") for r in rounds]
        es = [r.get("error_score") for r in rounds]
        ev = max((x for x in evs if x is not None), default=None)
        esmax = max((x for x in es if x is not None), default=None)

        f = per_fam[fam]
        f["n"] += 1
        if final_correct:
            conc_correct.append(conc)
            if ev is not None: ev_correct.append(ev)
        else:
            f["wrong"] += 1
            conc_wrong.append(conc)
            if esmax is not None: ev_wrong.append(esmax)
            sharp = conc >= 0.6
            flat = conc <= 0.5
            if sharp: f["sharp_wrong"] += 1; sharp_wrong_total += 1
            if flat:  f["flat_wrong"] += 1; flat_wrong_total += 1
            if correct_appeared:
                f["wrong_activated"] += 1
                if sharp: sharp_wrong_activated += 1
                if flat:  flat_wrong_activated += 1

    def mean(x): return sum(x)/len(x) if x else 0.0
    print(f"\n{'='*70}\n{path.relative_to(ROOT)}\n{'='*70}")
    total = sum(v["n"] for v in per_fam.values())
    total_wrong = sum(v["wrong"] for v in per_fam.values())
    print(f"  tasks={total}  final-wrong={total_wrong}  "
          f"final-acc={1-total_wrong/total:.2%}")
    print(f"\n  [concentration: modal_share/rounds]  (1=always same answer)")
    print(f"    FINAL CORRECT: mean={mean(conc_correct):.3f}  n={len(conc_correct)}")
    print(f"    FINAL WRONG  : mean={mean(conc_wrong):.3f}  n={len(conc_wrong)}")
    print(f"\n  [critic max error_score per task]  (higher = critic signalled error)")
    print(f"    FINAL CORRECT: mean={mean(ev_correct):.4f}")
    print(f"    FINAL WRONG  : mean={mean(ev_wrong):.4f}")
    print(f"\n  [WRONG tasks split by mode sharpness]")
    print(f"    SHARP wrong (conc>=0.6): {sharp_wrong_total}/{total_wrong} = "
          f"{sharp_wrong_total/total_wrong:.1%}  (of which correct-ever-appeared: "
          f"{sharp_wrong_activated}/{sharp_wrong_total})")
    print(f"    FLAT  wrong (conc<=0.5): {flat_wrong_total}/{total_wrong} = "
          f"{flat_wrong_total/total_wrong:.1%}  (of which correct-ever-appeared: "
          f"{flat_wrong_activated}/{flat_wrong_total})")
    print(f"\n  [per family]")
    print(f"    {'family':<10}{'n':>5}{'wrong':>6}{'sharpW':>7}{'flatW':>6}"
          f"{'actW':>6}  (sharpW=confidently-wrong, flatW=no-mode wrong, "
          f"actW=correct-ever-appeared)")
    for fam in sorted(per_fam, key=lambda x:-per_fam[x]["n"]):
        f = per_fam[fam]
        if f["n"] == 0: continue
        print(f"    {fam:<10}{f['n']:>5}{f['wrong']:>6}{f['sharp_wrong']:>7}"
              f"{f['flat_wrong']:>6}{f['wrong_activated']:>6}")

for p in FILES:
    if p.exists():
        analyze(p)
    else:
        print(f"MISSING: {p}")
