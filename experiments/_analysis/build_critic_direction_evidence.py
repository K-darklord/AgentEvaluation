#!/usr/bin/env python3
"""Build the A2(placebo) vs C3(strong critic) critic-direction evidence table.

Evidence question: in the flip19 slice, does the C3 critic emit a *directional*
trigger (a concrete error-mechanism `suspicion`) that steers the solver, while
the A2 placebo emits no direction at all?

Source: feedback_loop_{A2,C3}_flip19_{gpqa,new,phase1}_20261022 (the two arms at
the same 2026-10-22 timestamp, so the comparison is not confounded by version).
Output: critic_direction_evidence.md (co-located).
"""
import glob
import json
import os

BASE = "experiments"
SUBSETS = ["gpqa", "new", "phase1"]


def load_arm(prefix):
    recs = {}
    for sub in SUBSETS:
        pat = f"{BASE}/feedback_loop_{prefix}_flip19_{sub}_20261022/*/loop_trajectories.jsonl"
        for f in glob.glob(pat):
            for line in open(f):
                o = json.loads(line)
                recs[o["task_id"]] = o
    return recs


def suspicion_text(cd):
    """Flatten a critic_direction list into a compact 'archetype :: suspicion' string."""
    if not cd:
        return None
    parts = []
    for s in cd:
        arch = s.get("archetype_name") or "?"
        susp = (s.get("suspicion") or "").strip()
        parts.append(f"{arch} :: {susp[:110]}")
    return " || ".join(parts)


def main():
    a2 = load_arm("A2")
    c3 = load_arm("C3")
    tids = sorted(set(a2) & set(c3), key=lambda t: (c3[t].get("family") or "", t))

    def sf(o):
        return f"{o['start_correct']}→{o['final_correct']}"

    lines = []
    A = lines.append

    A("# Critic-Direction Evidence — A2 (placebo) vs C3 (strong critic), flip19 slice")
    A("")
    A("> Data source: `feedback_loop_{A2,C3}_flip19_{gpqa,new,phase1}_20261022` (same 2026-10-22 timestamp).")
    A("> `critic_direction` is the structured trigger emitted by the critic at each round; the A2 placebo")
    A("> emits `None` (no direction) by design, the C3 strong critic emits `{archetype_name, suspicion}`.")
    A("> `s→f` = `start_correct → final_correct`. `correct_appeared` = the gold answer appeared in ≥1 round.")
    A("")

    # ---- overview table ----
    A("## 1. Overview: all 19 tasks, A2 vs C3")
    A("")
    A("| # | task_id | family | gold | A2 s→f | C3 s→f | C3 critic_direction rounds |")
    A("|---|---------|--------|------|--------|--------|----------------------------|")
    for i, t in enumerate(tids, 1):
        oa, oc = a2[t], c3[t]
        gold = oc.get("gold_answer") or oa.get("gold_answer") or ""
        fam = oc.get("family") or oa.get("family") or ""
        drounds = [r.get("round") for r in oc.get("rounds", []) if r.get("critic_direction")]
        A(f"| {i} | {t} | {fam} | {gold} | {sf(oa)} | {sf(oc)} | {drounds if drounds else '—'} |")
    A("")

    # ---- per-round detail for the direction-bearing flip cases ----
    A("## 2. Round-level `critic_direction` — C3 flip cases")
    A("")
    A("Flips are `start_correct=False → final_correct=True`. Rows show every round where the C3 critic")
    A("emitted a non-empty `suspicion`; the A2 placebo has no such column because it is `None` throughout.")
    A("")
    c3_flips = [t for t in tids if (not c3[t]["start_correct"]) and c3[t]["final_correct"]]
    for t in c3_flips:
        o = c3[t]
        A(f"### {t}  (gold = {o.get('gold_answer')})")
        A("")
        A("| round | answer | correct | critic_direction (suspicion) |")
        A("|---|---|---|---|")
        for r in o.get("rounds", []):
            cd = r.get("critic_direction")
            if not cd:
                continue
            A(f"| {r.get('round')} | {r.get('committed_answer')} | {r.get('is_correct')} | {suspicion_text(cd)} |")
        A("")
        for r in o.get("rounds", []):
            rat = (r.get("rationale") or "")
            if "reviewer" in rat.lower() or "feedback" in rat.lower():
                A(f"> solver attribution: _{rat.strip()[:220]}_")
                break
        A("")

    # ---- A2 placebo: show the direction is absent ----
    A("## 3. A2 placebo — no direction, even where the solver eventually flipped")
    A("")
    A("The A2 `critic_direction` field is `None` at every round. Where A2 still flips, the solver's own")
    A("rationale says the reviewer supplied no direction (so it re-explored unaided).")
    A("")
    a2_flips = [t for t in tids if (not a2[t]["start_correct"]) and a2[t]["final_correct"]]
    for t in a2_flips:
        o = a2[t]
        A(f"### {t}  (gold = {o.get('gold_answer')})")
        A("")
        A("| round | answer | correct | critic_direction | rationale (excerpt) |")
        A("|---|---|---|---|---|")
        for r in o.get("rounds", []):
            rat = (r.get("rationale") or "").strip()
            A(f"| {r.get('round')} | {r.get('committed_answer')} | {r.get('is_correct')} | {r.get('critic_direction')} | {rat[:160]} |")
        A("")

    # ---- caveat ----
    A("## 4. Confounds to state before using")
    A("")
    A("- **A2/C3 are separate runs**: `start_correct` differs on several tasks (e.g. gpqa_028/048, mmlu_pro_033")
    A("  are already `start_correct=True` in A2 but `False` in C3), so a raw flip-count comparison C3(5) vs A2(2)")
    A("  is **not** a clean causal contrast — it conflates sampling noise with the direction effect.")
    A("- The clean claim is **qualitative, per-round**: C3's critic emits a concrete `suspicion` tied to the")
    A("  current error and the solver cites that feedback in its change-of-answer rationale; A2 emits `None` and")
    A("  the solver states there is *no confident error direction* to act on.")
    A("- `critic_direction` is recorded as a sidecar of the freeze (structured `archetype + suspicion`), not the")
    A("  raw critic token stream; for the paper, refer to this field, not the paraphrased rationale.")
    A("")

    out = os.path.join(BASE, "_analysis", "critic_direction_evidence.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {out} ({len(lines)} lines)")
    print("C3 flips:", c3_flips)
    print("A2 flips:", a2_flips)


if __name__ == "__main__":
    main()