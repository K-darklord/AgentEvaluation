"""
trajectory_behavior_study.py
============================
Post-activation behaviour study of the n-round feedback loop, answering:
  Q1. which revisions drive ACTIVATION (wrong -> correct)?
  Q2. which revisions drive DERIVATION (correct -> wrong)?
  Q3. does a model mostly DRIFT, or OSCILLATE, between answers?
  Q4. what does a correct -> wrong revision look like?

Gold-free and zero-API: reads loop_trajectories.jsonl only. Every adjacent
round pair (r-1 -> r) is one "revision". The weak-critic signal that TRIGGERED
that revision is stored (offset) on round r's evidence/error_score/no_signal/top3.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _norm_ans(s) -> str:
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return t.strip(".,;:!?")


def classify_seq(ans_seq):
    """uniq, oscillating (a value recurs after a different value intervenes), drifting
    (every revision introduces a never-before-seen value)."""
    n = len(ans_seq)
    uniq = len(set(ans_seq))
    osc = False
    seen = {}
    for i, a in enumerate(ans_seq):
        if a in seen and i - seen[a] > 1 and len(set(ans_seq[seen[a]+1:i])) > 0:
            osc = True
        seen.setdefault(a, i)
    drift = ans_seq and all(
        ans_seq[i] == ans_seq[i-1] or ans_seq[i] not in set(ans_seq[:i])
        for i in range(1, n))
    return uniq, osc, drift


def _num(s):
    m = re.search(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", str(s or ""))
    return float(m.group()) if m else None


def summarize(path: Path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

    # transition matrix keyed by (prev_correct, curr_correct)
    trans = Counter()          # (p, c) -> count   (True=correct)
    trans_changed = Counter()  # (p, c) -> count where answer actually changed
    # feedback trigger stats per transition class
    ev = defaultdict(list)      # evidence
    no_sig = Counter()          # no_signal count
    leaf = defaultdict(Counter) # top1 leaf
    # Q4: magnitude of changes on correct->wrong revisions
    cw_mags = []

    seq_stats = []  # per-task (uniq, osc, drift)

    for t in rows:
        fam = t.get("family")
        if not fam:
            continue
        rounds = t["rounds"]
        ans = [_norm_ans(r.get("final_answer")) for r in rounds]
        seq_stats.append(classify_seq(ans))
        for i in range(1, len(rounds)):
            p = bool(rounds[i-1]["is_correct"])
            c = bool(rounds[i]["is_correct"])
            changed = ans[i] != ans[i-1]
            trans[(p, c)] += 1
            trans_changed[(p, c)] += int(changed)
            # trigger = weak-critic signal on round i (about round i-1 answer)
            e = rounds[i].get("evidence")
            ns = rounds[i].get("no_signal")
            top3 = rounds[i].get("top3") or []
            if e is not None:
                ev[(p, c)].append(e)
            no_sig[(p, c)] += int(bool(ns))
            if top3:
                leaf[(p, c)][top3[0]["leaf"]] += 1
            if changed and p and not c:  # correct -> wrong
                o, n2 = _num(ans[i-1]), _num(ans[i])
                if o is not None and n2 is not None:
                    cw_mags.append(abs(n2 - o))

    n_tasks = len(seq_stats)
    n_osc = sum(1 for _, o, _ in seq_stats if o)
    n_drift = sum(1 for _, _, d in seq_stats if d)
    avg_uniq = sum(u for u, _, _ in seq_stats) / n_tasks if n_tasks else 0.0

    def mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    print(f"\n===== {path.relative_to(ROOT)} =====")
    print(f"  tasks={n_tasks}")
    print(f"\n  [transition matrix]  prev->curr   total (changed)")
    for (p, c), lbl in [((True, True), 'C->C stay-correct'),
                        ((True, False), 'C->W 偏离'),
                        ((False, True), 'W->C 激活'),
                        ((False, False), 'W->W stay-wrong')]:
        n = trans[(p, c)]; nc = trans_changed[(p, c)]
        pct = f"{nc}/{n}={nc/n:.0%}" if n else "-"
        print(f"    {lbl:<18} n={n:<5} changed  {pct}")

    def fb(p, c, name):
        n = trans[(p, c)]
        if not n:
            print(f"    {name}: no transitions")
            return
        ns = no_sig[(p, c)]
        top1 = leaf[(p, c)].most_common(3)
        top1s = ", ".join(f"{l}({c_})" for l, c_ in top1) or "-"
        print(f"    {name}: n={n}  no_signal={ns}/{n}={ns/n:.0%}  "
              f"evidence_mean={mean(ev[(p, c)]):.3f}  top1_leaf=[{top1s}]")

    print(f"\n  [Q1 激活来源 W->C]");  fb(False, True, "  W->C")
    print(f"     对照 W->W (没激活)");  fb(False, False, "  W->W")
    print(f"\n  [Q2 偏离来源 C->W]");  fb(True, False, "  C->W")
    print(f"     对照 C->C (没偏离)"); fb(True, True, "  C->C")

    print(f"\n  [Q3 摇摆 vs 漂移]")
    print(f"     oscillating tasks : {n_osc}/{n_tasks} = {n_osc/n_tasks:.1%}")
    print(f"     drifting   tasks  : {n_drift}/{n_tasks} = {n_drift/n_tasks:.1%}")
    print(f"     avg unique answers/task: {avg_uniq:.2f}")

    print(f"\n  [Q4 正确->错 的修改幅度]  n={len(cw_mags)}")
    if cw_mags:
        cw_mags.sort()
        q = lambda p: cw_mags[min(len(cw_mags)-1, int(p*len(cw_mags)))]
        print(f"     magnitude median={q(.5):.3g} p90={q(.9):.3g} max={cw_mags[-1]:.3g}")


def main():
    targets = [
        ROOT / "experiments/feedback_loop_C_20261008/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/deepseek-v4-flash/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/glm-5.3/loop_trajectories.jsonl",
        ROOT / "experiments/feedback_loop_20261006_173715/qwen3.8-flash/loop_trajectories.jsonl",
    ]
    for p in targets:
        if p.exists():
            summarize(p)
        else:
            print(f"[skip] {p}")


if __name__ == "__main__":
    main()
