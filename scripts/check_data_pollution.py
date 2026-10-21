"""
check_data_pollution.py
=======================
Round-level pollution audit for collected trajectories.

Two modes
---------
1. Manual (default): ``--dirs`` names the experiment dirs to audit (later dirs
   override the same ``task_id``). Use for a one-off check.
2. Auto (``--auto``): scan ``experiments/`` for ``{a3,c}_gpqa_full_{model}_*``
   dirs, group by (arm, model), merge by date (re-run wins), and print ONE
   authoritative per-(arm, model) table for the target window. This is the
   SINGLE SOURCE OF TRUTH for "is this arm polluted / how many clean".
   Do NOT trust memory/notes numbers — always re-run this and read its output.

Two clean-ness views (this is the whole point; mixing them caused prior errors)
-------------------------------------------------------------------------------
* **final-answer view** (DEFAULT): a question is ``clean`` iff its LAST
  committed_answer parses to a valid letter (Markdown-wrapped ``**D**`` recovers
  to ``D``). This is the right view for A3/C **final accuracy** (majority-vote
  mode / settle), because only the final committed value matters.
  ``fail`` = last committed is an LLM-error/quota blob; ``prose`` = last
  committed is unparseable prose (e.g. glm leaking hidden CoT as ``Looking``).

* **strict view** (``--strict``): a question is ``clean`` only if EVERY round's
  committed_answer is a bare single letter. Use this for Stage-B **transition
  trajectory** work, where every round's answer is input to the evaluator.

The default (final-answer) view is what DATA_TRACKER.md's "clean" should mean.

Usage::

    python3 scripts/check_data_pollution.py --auto
    python3 scripts/check_data_pollution.py --auto --task-offset 1 --num-tasks 50
    python3 scripts/check_data_pollution.py --dirs experiments/a3_gpqa_full_qwen_20261013 experiments/a3_gpqa_full_qwen_20261014_rerun --model-dir qwen3.8-flash
"""
from __future__ import annotations

import argparse
import json
import os
import re
import string
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ARM_LABEL = {"a3": "A3", "c": "C"}
MODEL_SUBDIR = {
    "qwen": "qwen3.8-flash",
    "glm": "glm-5.3",
    "deepseek": "deepseek-v4-flash",
}

_WASTE_MARKERS = ("LLM error", "Connection error", "quota", "429")


def _load(path: Path) -> list[dict]:
    recs: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    return recs


def _normalize_letter(x) -> str | None:
    """Recover a single letter: 'D' -> 'D', '**D**' -> 'D', '(D)' -> 'D'."""
    if not isinstance(x, str):
        return None
    s = x.strip()
    if len(s) == 1 and s in string.ascii_uppercase:
        return s
    m = re.fullmatch(r"\**\[?\(?[:'\"]?([A-Z])[:'\"]?\)?\]?\.?\**", s)
    if m:
        return m.group(1)
    return None


def _last_committed(record: dict) -> str:
    c = None
    for rd in record.get("rounds", []):
        ca = rd.get("committed_answer")
        if ca is not None and str(ca).strip():
            c = ca
    return str(c or "").strip()


def classify_final(record: dict, letters: str) -> str:
    """Final-answer view: clean/fail/prose/empty based on the LAST committed answer."""
    if not record.get("rounds"):
        return "empty"
    s = _last_committed(record)
    if s == "":
        return "empty"
    if any(m in s for m in _WASTE_MARKERS):
        return "fail"
    norm = _normalize_letter(s.upper())
    if norm is not None and norm in letters:
        return "clean"
    return "prose"


def classify_strict(record: dict, letters: str) -> str:
    """Strict view: clean only if EVERY round is a bare letter (no mkd, no prose)."""
    rounds = record.get("rounds") or []
    if not rounds:
        return "empty"
    states = []
    for rd in rounds:
        if rd.get("api_failure"):
            states.append("fail")
            continue
        ans = rd.get("committed_answer")
        if isinstance(ans, str) and len(ans.strip()) == 1 and ans.strip() in letters:
            states.append("clean")
        elif _normalize_letter(ans if isinstance(ans, str) else "") is not None:
            states.append("mkd")
        else:
            states.append("prose")
    if all(s == "fail" for s in states):
        return "fail"
    if all(s in ("clean", "mkd") for s in states) and any(s == "mkd" for s in states):
        return "mkd"
    if all(s == "clean" for s in states):
        return "clean"
    if any(s == "fail" for s in states):
        return "fail"
    return "prose"


def _in_window(tid: str, args) -> bool:
    if args.task_prefix and not tid.startswith(args.task_prefix + "_"):
        return False
    if args.task_offset is not None:
        try:
            idx = int(tid.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            return False
        lo = args.task_offset
        hi = (lo + args.num_tasks - 1) if args.num_tasks else None
        if idx < lo or (hi is not None and idx > hi):
            return False
    return True


def discover_groups() -> dict[tuple[str, str], list[tuple[int, str]]]:
    exp = REPO_ROOT / "experiments"
    groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    pat = re.compile(r"^(a3|c)_gpqa_full_(qwen|glm|deepseek)_(\d+)(?:_rerun)?$")
    for name in sorted(os.listdir(exp)):
        m = pat.match(name)
        if not m:
            continue
        arm, model, date = m.group(1), m.group(2), int(m.group(3))
        groups.setdefault((arm, model), []).append((date, name))
    for key in groups:
        groups[key].sort()
    return groups


def audit(target_ids: list[str], dirs: list[str], subdir: str, letters: str, strict: bool) -> dict:
    merged: dict[str, dict] = {}
    for d in dirs:
        p = REPO_ROOT / "experiments" / d / subdir / "loop_trajectories.jsonl"
        if not p.exists():
            continue
        for r in _load(p):
            tid = r.get("task_id")
            if tid in target_ids:
                merged[tid] = r  # later dir overrides same task_id
    buckets: dict[str, list[str]] = {}
    fn = classify_strict if strict else classify_final
    for tid in target_ids:
        if tid not in merged:
            buckets.setdefault("missing", []).append(tid)
            continue
        b = fn(merged[tid], letters)
        buckets.setdefault(b, []).append(tid)
    return buckets


def run_auto(args) -> None:
    letters = args.letters
    prefix = args.task_prefix
    offset = args.task_offset if args.task_offset is not None else 51
    num = args.num_tasks if args.num_tasks is not None else 148
    target = [f"{prefix}_{i:03d}" for i in range(offset, offset + num)]

    groups = discover_groups()
    if not groups:
        print("[warn] no {a3,c}_gpqa_full_{model}_* dirs found in experiments/")
        return

    view = "strict (every-round bare letter)" if args.strict else "final-answer (last committed parseable)"
    print(f"=== AUTO: {prefix}_{offset:03d}-{offset + num - 1:03d} ({num} tasks) | view: {view} ===")
    print(f"{'arm':<3} {'model':<8} {'clean':>5} {'fail':>5} {'prose':>5} {'mkd':>4} {'missing':>7}  dirs")
    print("-" * 78)
    for (arm, model) in sorted(groups):
        dirs = [d for _date, d in groups[(arm, model)]]
        b = audit(target, dirs, MODEL_SUBDIR[model], letters, args.strict)
        clean = len(b.get("clean", []))
        fail = len(b.get("fail", []))
        prose = len(b.get("prose", []))
        mkd = len(b.get("mkd", []))
        missing = len(b.get("missing", []))
        print(f"{ARM_LABEL[arm]:<3} {model:<8} {clean:>5} {fail:>5} {prose:>5} {mkd:>4} {missing:>7}  {len(dirs)}")

    print("\n--- bad ids per arm (generate --tasks from these, never a whole range) ---")
    for (arm, model) in sorted(groups):
        b = audit(target, [d for _d, d in groups[(arm, model)]], MODEL_SUBDIR[model], letters, args.strict)
        bad = []
        for bucket in ("fail", "prose", "missing"):
            bad.extend(b.get(bucket, []))
        if bad:
            joined = ",".join(sorted(bad))
            if len(bad) > 40:
                joined = ",".join(sorted(bad)[:40]) + f" ...(+{len(bad) - 40})"
            print(f"{ARM_LABEL[arm]:<3} {model:<8} ({len(bad)}): {joined}")


def run_manual(args) -> None:
    records: list[dict] = []
    for d in args.dirs:
        p = REPO_ROOT / d / args.model_dir / "loop_trajectories.jsonl"
        if not p.exists():
            print(f"[warn] missing {p}")
            continue
        records.extend(_load(p))

    merged = {}
    for r in records:
        tid = r.get("task_id")
        if tid and _in_window(tid, args):
            merged[tid] = r

    fn = classify_strict if args.strict else classify_final
    buckets = {}
    for tid in sorted(merged):
        b = fn(merged[tid], args.letters)
        buckets.setdefault(b, []).append(tid)

    total = len(merged)
    print(f"audited {total} questions across {args.dirs}")
    for b in ("clean", "fail", "prose", "mkd", "empty"):
        ids = sorted(buckets.get(b, []))
        print(f"\n[{b}] {len(ids)}")
        print("  " + ", ".join(ids) if ids else "  (none)")
    print("\nclean (OK) =", len(buckets.get("clean", [])), "/", total)


def main() -> None:
    ap = argparse.ArgumentParser(description="Round-level pollution audit.")
    ap.add_argument("--auto", action="store_true", help="auto-discovery arm table")
    ap.add_argument("--dirs", nargs="+", default=None, help="experiment dirs (manual mode)")
    ap.add_argument("--model-dir", default="qwen3.8-flash", help="model subdir (manual mode)")
    ap.add_argument("--letters", default="ABCD", help="valid bare-answer letters")
    ap.add_argument("--task-prefix", default="gpqa", help="audit only this task prefix")
    ap.add_argument("--task-offset", type=int, default=None, help="1-based start (auto default 51)")
    ap.add_argument("--num-tasks", type=int, default=None, help="window size (auto default 148)")
    ap.add_argument("--strict", action="store_true",
                    help="strict every-round bare-letter view (for Stage-B trajectories)")
    args = ap.parse_args()

    if args.auto:
        run_auto(args)
    else:
        if not args.dirs:
            ap.error("--dirs required in manual mode (or pass --auto)")
        run_manual(args)


if __name__ == "__main__":
    main()
