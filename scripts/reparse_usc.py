#!/usr/bin/env python3
"""Offline reparse of usc_result.jsonl per spec section 6.1, then retry flipped.

Two modes:
  --report-only : offline only. Recompute parse_ok with the strict rule, print the
                  before/after failure counts per arm, and write the flipped list to
                  _usc_reparse_flipped.json. No API calls, no file rewrite.
  (default)     : backup the file, offline reparse, retry the flipped records once
                  (spec 6.1: retry once, else fall back to plain vote), rewrite the
                  file with an `endpoint` field on every record, and print the report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))
sys.path.insert(0, str(AGENT_ROOT / "scripts"))

import s2_usc as s2  # noqa: E402
from src import config
from src.score_hle_arms import load_index  # noqa: E402

OUT = AGENT_ROOT / "experiments/hle400/t3/usc_result.jsonl"
INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
BACKUP = OUT.with_name("usc_result.jsonl.pre_reparse_bak")
FLIPPED = AGENT_ROOT / "experiments/hle400/t3/_usc_reparse_flipped.json"


def load_records():
    recs = []
    for line in OUT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        recs.append(json.loads(line))
    return recs


def reparse_record(d):
    """Strict reparse. Returns (new_parse_ok, new_selected_round)."""
    ct = d.get("completion_tokens") or 0
    if ct >= s2.MAX_TOKENS:
        return False, None
    n = s2.parse_selection(d.get("raw_output") or "")
    order = d.get("order") or []
    if n is not None and 1 <= n <= len(order):
        return True, order[n - 1]
    return False, None


def report(recs):
    before = Counter()
    after = Counter()
    flipped = []
    for d in recs:
        arm = d["arm"]
        old_ok = bool(d.get("parse_ok"))
        new_ok, _sel = reparse_record(d)
        if not old_ok:
            before[arm] += 1
        if not new_ok:
            after[arm] += 1
        if old_ok and not new_ok:
            flipped.append({"task_id": d["task_id"], "arm": arm})
    print("=== reparse report (before -> after parse failure counts) ===")
    arms = sorted(set(before) | set(after))
    print(f"{'arm':<8}{'before_fail':>12}{'after_fail':>12}{'delta':>8}")
    for a in arms:
        b, af = before.get(a, 0), after.get(a, 0)
        print(f"{a:<8}{b:>12}{af:>12}{af - b:>8}")
    print(f"{'TOTAL':<8}{sum(before.values()):>12}{sum(after.values()):>12}"
          f"{sum(after.values()) - sum(before.values()):>8}")
    print(f"flipped (old parse_ok=True -> new False): {len(flipped)}")
    for f in flipped:
        print(f"  {f['task_id']} {f['arm']}")
    return flipped


def retry_flipped(recs, flipped):
    """Retry each flipped record once (spec 6.1), else fall back to plain vote."""
    if not flipped:
        return {}
    import concurrent.futures
    import src.run_feedback_loop as rfl
    rfl._force_no_proxy()

    idx = load_index(INDEX)
    by_key = {(d["task_id"], d["arm"]): d for d in recs}
    rounds_cache = {}
    for f in flipped:
        arm = f["arm"]
        if arm not in rounds_cache:
            rounds_cache[arm] = s2.load_rounds(s2.ARMS[arm])

    def one(f):
        tid, arm = f["task_id"], f["arm"]
        rounds = rounds_cache[arm][tid]
        rec = by_key[(tid, arm)]
        new_rec = s2.retry_once(tid, arm, idx[tid]["question"],
                                rec["order"], rounds, idx[tid])
        print(f"  retried {tid} {arm}: parse_ok={new_rec['parse_ok']} "
              f"endpoint={new_rec['endpoint']}", flush=True)
        return (tid, arm), new_rec

    results = OrderedDict()
    ex = concurrent.futures.ThreadPoolExecutor(
        max_workers=config.RUNNER_CONCURRENCY)
    try:
        futs = {ex.submit(one, f): f for f in flipped}
        for fut in concurrent.futures.as_completed(futs):
            try:
                key, new_rec = fut.result()
            except s2.AbortError as e:
                print(f"ABORT during retry: {e}", file=sys.stderr)
                ex.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as e:
                f = futs[fut]
                print(f"  ERROR {f['task_id']} {f['arm']}: {e}", flush=True)
                continue
            results[key] = new_rec
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return results


def apply(recs, retried):
    """Add endpoint field to every record; replace flipped records with retried."""
    out = []
    for d in recs:
        key = (d["task_id"], d["arm"])
        if key in retried:
            out.append(retried[key])
        else:
            d = dict(d)
            d.setdefault("endpoint", s2.ENDPOINT_TOKEN_PLAN)
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    recs = load_records()
    print(f"loaded {len(recs)} records from {OUT}")
    flipped = report(recs)

    if args.report_only:
        FLIPPED.write_text(json.dumps(flipped, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"flipped list -> {FLIPPED}")
        return 0

    if not BACKUP.exists():
        BACKUP.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup -> {BACKUP}")
    else:
        print(f"backup already exists -> {BACKUP}")

    retried = retry_flipped(recs, flipped)
    final = apply(recs, retried)

    tmp = OUT.with_name("usc_result.jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for d in final:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    os.replace(tmp, OUT)
    print(f"rewrote {len(final)} records -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
