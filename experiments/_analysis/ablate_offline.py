"""
ablate_offline.py -- offline re-parse of the STAGE-B evaluator's three-vote knobs.

Loads already-committed ``per_switch`` rubric/v5 raw evidence and re-derives the
KEEP/CUT/UNSURE verdicts + elimination mode-lock under the 3-knob grid, WITHOUT any
new LLM call. This is the deterministic half of the Stage-B ablation (2026-10-26):

  knob 1  keep     : KEEP-vote on/off  (all-zero rubric transition -> KEEP vs UNSURE)
  knob 2  vote_mode: "max" (0.5 unsure, fold max) / "min" (0.5 unsure, fold min) /
                     "0" (no half vote, unsure inert)
  knob 3  weight_by: "round" (each round votes) / "fragment" (each run votes once)

Subset (user-finalized): flip + activated =
    ``correct_appeared is True`` AND ``len(candidates) >= 2``.

For rubric_cut / rubric_ce the full 2x3x2 = 12-cell grid applies. For rubric_v5 the
KEEP knob is N/A (v5 has its own conclusion-mismatch KEEP); only 3x2 = 6 cells apply.

Scoring reuses ``stage_b_evaluator.score`` (exact ``decision == gold`` acc and the
``activated -> expect-answer / never -> expect-abstain`` meta), i.e. the SAME metric as
the committed verdict files, so the baseline cell (keep=on, vote_mode=max,
weight_by=round) must reproduce the committed ``correct``/``verdict`` exactly.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src import stage_b_evaluator as SBE  # noqa: E402

_RUBRIC_DIMS = ("disconnection", "contradiction", "error")

# (rec.jsonl, verdict.jsonl, family-label) triplets. Strategy is read from each row.
DATASETS = [
    ("experiments/_analysis/stageb_flip19_holdgate/C3_flip19_new_baseline.rec.jsonl",
     "experiments/_analysis/stageb_flip19_holdgate/C3_flip19_new_baseline.verdict.jsonl",
     "flip19-new"),
    ("experiments/_analysis/stageb_flip19_holdgate/C3_flip19_new_baseline.rec.jsonl",
     "experiments/_analysis/stageb_flip19_holdgate/C3_flip19_new_baseline.rubric_ce.verdict.jsonl",
     "flip19-new"),
    ("experiments/_analysis/stageb_flip19_holdgate/C3_flip19_gpqa_baseline.rec.jsonl",
     "experiments/_analysis/stageb_flip19_holdgate/C3_flip19_gpqa_baseline.verdict.jsonl",
     "flip19-gpqa"),
    ("experiments/_analysis/stageb_flip19_holdgate/C3_flip19_gpqa_baseline.rec.jsonl",
     "experiments/_analysis/stageb_flip19_holdgate/C3_flip19_gpqa_baseline.rubric_ce.verdict.jsonl",
     "flip19-gpqa"),
    ("experiments/_analysis/hle_transitions.jsonl",
     "experiments/_analysis/hle_rubric_cut.jsonl",
     "hle"),
    ("experiments/_analysis/hle_transitions.jsonl",
     "experiments/_analysis/hle_rubric_ce.jsonl",
     "hle"),
    ("experiments/_analysis/hle_transitions.jsonl",
     "experiments/_analysis/hle_rubric_v5.jsonl",
     "hle"),
]


def _parse_edge(keystr: str) -> tuple[int, int]:
    a, b = keystr.split("->")
    return int(a.strip()), int(b.strip())


def _derive_cuts_rubric(per_switch: dict, strategy: str, keep: bool, cut_bar: float) -> dict:
    """Re-derive {edge: verdict} from raw rubric per_switch. Mirrors evaluate_one's
    ``_absorb`` for rubric_cut / rubric_ce, with the KEEP class toggled by ``keep``.
    ``per_switch`` keys are (from_r, to_r) int tuples (already parsed by the caller)."""
    cuts = {}
    for edge, v in per_switch.items():
        if v.get("collapse"):
            cuts[edge] = "UNSURE"
            continue
        dims = [v.get(d, 0.0) for d in _RUBRIC_DIMS]
        if keep and all(d == 0.0 for d in dims):
            cuts[edge] = "KEEP"
            continue
        if strategy == "rubric_ce":
            score = max(v.get("contradiction", 0.0), v.get("error", 0.0))
        else:
            score = max(v.get("disconnection", 0.0), v.get("contradiction", 0.0),
                        v.get("error", 0.0))
        cuts[edge] = "CUT" if score >= cut_bar else "UNSURE"
    return cuts


def _derive_cuts_v5(per_switch: dict, rec: dict) -> dict:
    ans_by_r = {r["r"]: r.get("ans") for r in rec.get("rounds", [])}
    cuts = {}
    for edge, v in per_switch.items():
        cuts[edge] = SBE._v5_to_verdict(v, ans_by_r.get(edge[0]), ans_by_r.get(edge[1]))
    return cuts


def redecide(rec: dict, per_switch: dict, strategy: str, keep: bool, cut_bar: float,
             vote_mode: str, weight_by: str) -> tuple[str | None, dict]:
    """Reproduce evaluate_one's rubric/v5 tail: derive cuts -> all-UNSURE -> mode, else
    elimination mode-lock with directional tie-break. Returns (verdict, info)."""
    switches = SBE._switch_edges(rec)
    ps = {_parse_edge(k): v for k, v in per_switch.items()}
    if set(switches) != set(ps.keys()):
        return None, {"status": "incomplete_per_switch"}

    if strategy == "rubric_v5":
        cuts = _derive_cuts_v5(ps, rec)
    else:
        cuts = _derive_cuts_rubric(ps, strategy, keep, cut_bar)

    n_sw = len(switches)
    n_unsure = sum(1 for v in cuts.values() if v == "UNSURE")
    if n_sw > 0 and n_unsure == n_sw:
        # all-UNSURE fallback (rubric strategies degrade to the settled mode).
        return SBE._mode_answer(rec), {"status": "all_unsure_fallback_mode"}

    return SBE._elimination_mode_lock(
        rec, cuts, allow_unsure=True, tie_break="directional",
        vote_mode=vote_mode, weight_by=weight_by)


def run():
    datasets = [(ROOT / r, ROOT / v, lab) for r, v, lab in DATASETS]
    for recp, verp, lab in datasets:
        # guard against missing/empty verdict files (e.g. phase1-baseline had none)
        if not verp.exists() or verp.stat().st_size == 0:
            print(f"[skip] {lab} {verp.name}: empty/missing")
            continue

        recs = {r["task_id"]: r for r in
                (json.loads(l) for l in open(recp, encoding="utf-8"))}
        verdicts = [json.loads(l) for l in open(verp, encoding="utf-8")]
        strat = verdicts[0]["strategy"]
        cut_bar = float(verdicts[0].get("rubric_threshold", 8.0) or 8.0)

        # subset: flip (>=2 candidates) AND activated (gold appeared in rounds)
        subset = []
        for row in verdicts:
            rec = recs.get(row["task_id"])
            if rec is None:
                continue
            if rec.get("correct_appeared") is not True:
                continue
            if len(rec.get("candidates", [])) < 2:
                continue
            subset.append((rec, row))

        print(f"\n===== {lab} / {strat}  (subset n={len(subset)}) =====")

        # ---- committed baseline (the "prior score" from the older committed run) ----
        committed_correct = sum(1 for _, row in subset if row.get("correct"))
        committed_meta = sum(1 for _, row in subset if row.get("meta_correct"))
        print(f"  [committed prior] acc={committed_correct / len(subset):.3f} "
              f"meta={committed_meta / len(subset):.3f}  (old code; may predate the "
              f"rev-5 KEEP rule / rev-8 fold -- see note)")

        # ---- full grid ----
        keep_grid = [True, False] if strat != "rubric_v5" else [True]
        header = "  KEEP   vote_mode  weight_by   n  acc    meta   lock-breakdown"
        print(header)
        for keep in keep_grid:
            for vm in ("max", "min", "0"):
                for wb in ("round", "fragment"):
                    n = 0
                    correct = 0
                    meta = 0
                    locks = Counter()
                    for rec, row in subset:
                        vd, info = redecide(rec, row.get("per_switch", {}), strat,
                                            keep=keep, cut_bar=cut_bar,
                                            vote_mode=vm, weight_by=wb)
                        sc = SBE.score(vd, rec)
                        n += 1
                        correct += sc["correct"]
                        meta += sc["meta_correct"]
                        locks[info["status"]] += 1
                    acc = correct / n if n else 0.0
                    met = meta / n if n else 0.0
                    lock_str = ", ".join(f"{k}={v}" for k, v in sorted(locks.items()))
                    keep_s = "on " if keep else "off"
                    print(f"  {keep_s:>4}   {vm:>6}     {wb:>7}  {n:>2}  "
                          f"{acc:.3f}  {met:.3f}  {lock_str}")


if __name__ == "__main__":
    run()