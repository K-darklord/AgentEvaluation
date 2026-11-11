#!/usr/bin/env python3
"""check_rationale_health.py
============================
Gate between 30-task Stage-B batches: verify that the transition self-report
(rationale) is actually being CAPTURED, before spending more tokens on the next
batch. Reads a loop_trajectories.jsonl (or every such file under a run dir) and
reports, for feedback rounds (round >= 1) only, how many rationales are:
  full      -- >= MIN_RAT_LEN chars (a real sentence was collected)
  fragment  -- 1..MIN_RAT_LEN-1 chars (hidden-CoT truncation, e.g. "I"/"The")
  empty     -- "" (no self-report was produced/extracted)
Round 0 (baseline) has no feedback so it is excluded.

Exit codes: 0 = PASS (all channels healthy), 1 = FAIL (empty or fragment rate
over budget), 2 = usage error / no data.

Usage:
  python3 scripts/check_rationale_health.py --dir experiments/run_dir
  python3 scripts/check_rationale_health.py --file path/loop_trajectories.jsonl
  python3 scripts/check_rationale_health.py --dir ... --min-len 15 \
      --max-empty-frac 0.25 --max-frag-frac 0.15
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MIN_RAT_LEN = 12          # below this a rationale is a CoT-truncation fragment
DEFAULT_MAX_EMPTY = 0.25  # allow <=25% empty feedback rounds
DEFAULT_MAX_FRAG = 0.15   # allow <=15% fragment feedback rounds


def scan_file(path: Path) -> tuple[dict, str | None]:
    full = frag = empty = 0
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        for rd in r.get("rounds", []):
            if rd.get("round", 0) < 1:
                continue
            rat = (rd.get("rationale") or "").strip()
            if not rat:
                empty += 1
            elif len(rat) < MIN_RAT_LEN:
                frag += 1
            else:
                full += 1
    stats = {"full": full, "fragment": frag, "empty": empty,
             "total": full + frag + empty, "n_tasks": len(rows)}
    return stats, None


def find_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return list(target.rglob("loop_trajectories.jsonl"))
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dir", type=Path)
    g.add_argument("--file", type=Path)
    ap.add_argument("--min-len", type=int, default=MIN_RAT_LEN)
    ap.add_argument("--max-empty-frac", type=float, default=DEFAULT_MAX_EMPTY)
    ap.add_argument("--max-frag-frac", type=float, default=DEFAULT_MAX_FRAG)
    a = ap.parse_args()

    files = find_files(a.dir or a.file)
    if not files:
        print("FAIL: no loop_trajectories.jsonl found (batch still running or empty)")
        return 2

    ok = True
    for f in sorted(files):
        stats, _err = scan_file(f)
        s = stats
        tot = s["total"] or 1
        empty_f = s["empty"] / tot
        frag_f = s["fragment"] / tot
        bad = empty_f > a.max_empty_frac or frag_f > a.max_frag_frac
        ok = ok and (not bad)
        verdict = "PASS" if not bad else "FAIL"
        print(f"[{verdict}] {f.parent.parent.name}/{f.parent.name}: "
              f"fb={s['total']} full={s['full']} frag={s['fragment']} empty={s['empty']} "
              f"(empty={empty_f:.0%}>{a.max_empty_frac:.0%}? frag={frag_f:.0%}>{a.max_frag_frac:.0%}?)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
