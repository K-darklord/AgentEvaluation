#!/usr/bin/env python3
"""Re-judge the ERR (never-judged) entries in astra_verdicts_confirm.jsonl.

Entries whose served_model starts with 'ERR' were stored as c=False after a failed
judge call; they were never actually judged. Re-call the grader for exactly those
entries and replace them with real verdicts. All other lines are kept unchanged.
If any re-judge still fails after retries, nothing is written and the script exits
non-zero (never write an interface error as a verdict).

Run: python3 scripts/fix_astra_err.py [--workers N] [--limit K]
"""
from __future__ import annotations
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "gen_confirm", str(AGENT_ROOT / "scripts/gen_t3_sidecar_confirm.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

T3 = AGENT_ROOT / "experiments/hle400/t3"
CACHE = T3 / "astra_verdicts_confirm.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0, help="re-judge at most K entries (0 = all)")
    args = ap.parse_args()

    idx = gen.load_confirm_index()
    lines = CACHE.read_text(encoding="utf-8").splitlines()

    errs = []  # (line_index, dict)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        d = json.loads(line)
        if str(d.get("served_model", "")).startswith("ERR"):
            errs.append((i, d))
    if args.limit > 0:
        errs = errs[: args.limit]

    print(f"ERR entries to re-judge: {len(errs)}", flush=True)
    if not errs:
        print("nothing to do")
        return 0

    def process(item):
        i, d = item
        tid, fa = d["task_id"], d["final_answer"]
        m = idx[tid]
        verdict, served = gen.astra_judge(m["question"], m["gold"], fa)
        return i, {"task_id": tid, "final_answer": fa, "c": verdict,
                   "served_model": served}

    results = {}
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, it): it for it in errs}
        for n, fut in enumerate(as_completed(futs), 1):
            i, d = futs[fut]
            try:
                ri, rec = fut.result()
                results[ri] = rec
            except Exception as e:  # noqa: BLE001
                failures.append((d["task_id"], d["final_answer"], f"{type(e).__name__}: {e}"))
            if n % 200 == 0 or n == len(futs):
                print(f"  re-judged {n}/{len(futs)} (fail {len(failures)})", flush=True)

    out_lines = []
    for i, line in enumerate(lines):
        if i in results:
            out_lines.append(json.dumps(results[i], ensure_ascii=False))
        else:
            out_lines.append(line)
    tmp = CACHE.with_name(CACHE.name + ".tmp")
    tmp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    tmp.replace(CACHE)
    print(f"replaced {len(results)} ERR entries; {len(failures)} still failing", flush=True)

    if failures:
        print(f"FAILED {len(failures)} re-judges (left as ERR, re-run to retry):", file=sys.stderr)
        for tid, fa, err in failures[:20]:
            print(f"  {tid} {fa[:40]!r} -> {err}", file=sys.stderr)
        return 1
    print("all ERR entries re-judged successfully", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
