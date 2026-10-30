"""scan_truncated_reasoning.py
==============================
Annotate (flag) tasks in previously-run reasoning-benchmark arms that must be
re-run under the new config.

Detection (per task record in loop_trajectories.jsonl), a task is BAD if any
round has:
  - api_failure == True, OR
  - finish_reason == "length", OR
  - finish_reason absent/None AND completion_tokens >= max_tokens (old records).

Legacy-format arms (10-06/10-07, no token/finish_reason fields) cannot assess
truncation and are listed under `legacy_arms` for transparency.

Each directory is categorized so the caller can choose the re-run scope:
  canonical / flip19 / stageb / oscpilot / legacy.

Output: experiments/queue_rerun_reasoning.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP = REPO_ROOT / "experiments"
OUT = EXP / "queue_rerun_reasoning.json"
CANONICAL_OUT = EXP / "queue_rerun_reasoning_canonical.json"
MODEL = "deepseek-v4-flash"
REASONING_FAMILIES = {"gpqa", "aime", "bbh", "mmlu_pro", "math", "math500"}
SKIP_NAME_TOKENS = ("hle", "smoke", "seedtest")
SKIP_DIR_TOKENS = ("_deprecated", "archive", "_analysis")


def _is_skip_dir(name: str) -> bool:
    l = name.lower()
    return any(t in l for t in SKIP_NAME_TOKENS)


def _category(name: str, max_tokens) -> str:
    if max_tokens is None:
        return "legacy"
    if "flip19" in name:
        return "flip19"
    if "stageb" in name:
        return "stageb"
    if "oscpilot" in name:
        return "oscpilot"
    return "canonical"


def _arm_dirs() -> list[Path]:
    """All arm dirs that sit directly under experiments/ or the nested
    experiments/experiments/ (the a3_new / a3_phase1 A3-arm runs live there)."""
    dirs = []
    for root in (EXP, EXP / "experiments"):
        if not root.is_dir():
            continue
        for d in root.iterdir():
            if not d.is_dir():
                continue
            if d.name.startswith("."):
                continue
            if any(t in d.name for t in SKIP_DIR_TOKENS):
                continue
            if _is_skip_dir(d.name):
                continue
            if (d / "loop_summary.json").exists():
                dirs.append(d)
    return dirs


def scan() -> dict:
    entries = []
    legacy_arms: list[str] = []
    for arm_dir in sorted(_arm_dirs()):
        try:
            summary = json.loads((arm_dir / "loop_summary.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        models = summary.get("models", {})
        if MODEL not in models:
            continue
        max_tokens = summary.get("max_tokens")
        run_id = summary.get("run_id", arm_dir.name)
        traj = arm_dir / MODEL / "loop_trajectories.jsonl"
        if not traj.exists():
            continue
        cat = _category(arm_dir.name, max_tokens)
        if max_tokens is None:
            # legacy format: no token accounting -> cannot assess truncation
            has_api_fail = False
            for raw in traj.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("family") in REASONING_FAMILIES and any(
                        r.get("api_failure") for r in rec.get("rounds", [])):
                    has_api_fail = True
                    break
            if has_api_fail:
                legacy_arms.append(f"{arm_dir.name} (has api_failure)")
            else:
                legacy_arms.append(arm_dir.name)
            continue
        for raw in traj.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            family = rec.get("family")
            if family not in REASONING_FAMILIES:
                continue
            task_id = rec.get("task_id")
            bad_rounds = 0
            api_fail = False
            truncated = False
            for r in rec.get("rounds", []):
                is_fail = bool(r.get("api_failure"))
                fr = r.get("finish_reason")
                ct = r.get("completion_tokens")
                is_trunc = (fr == "length") or (fr is None and isinstance(ct, int) and ct >= max_tokens)
                if is_fail:
                    api_fail = True
                if is_trunc:
                    truncated = True
                if is_fail or is_trunc:
                    bad_rounds += 1
            if bad_rounds == 0:
                continue
            reason = "both" if (api_fail and truncated) else ("api_failure" if api_fail else "truncate")
            entries.append({
                "benchmark": family,
                "arm": rec.get("arm"),
                "run_id": run_id,
                "arm_dir": arm_dir.name,
                "category": cat,
                "model": MODEL,
                "max_tokens": max_tokens,
                "task_id": task_id,
                "reason": reason,
                "n_bad_rounds": bad_rounds,
            })

    benchmarks: dict[str, dict] = {}
    for e in entries:
        fam = e["benchmark"]
        b = benchmarks.setdefault(fam, {"arms": {}, "unique_tasks": []})
        b["arms"].setdefault(e["arm_dir"], 0)
        b["arms"][e["arm_dir"]] += 1
    for fam, b in benchmarks.items():
        b["unique_tasks"] = sorted({e["task_id"] for e in entries if e["benchmark"] == fam})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "n_arm_dirs": len(entries) and len({e['arm_dir'] for e in entries}),
        "n_entries": len(entries),
        "benchmarks": benchmarks,
        "entries": entries,
        "legacy_arms": sorted(set(legacy_arms)),
    }


def _canonical_subset(result: dict) -> dict:
    """Final re-run queue: canonical main-arm entries only (flip19/stageb/oscpilot
    are variant ablations whose questions are already covered by the main arms)."""
    entries = [e for e in result["entries"] if e["category"] == "canonical"]
    benchmarks: dict[str, dict] = {}
    for e in entries:
        fam = e["benchmark"]
        b = benchmarks.setdefault(fam, {"arms": {}, "unique_tasks": []})
        b["arms"].setdefault(e["arm_dir"], 0)
        b["arms"][e["arm_dir"]] += 1
    for fam, b in benchmarks.items():
        b["unique_tasks"] = sorted({e["task_id"] for e in entries if e["benchmark"] == fam})
    return {
        "generated_at": result["generated_at"],
        "model": result["model"],
        "scope": "canonical",
        "n_entries": len(entries),
        "n_arm_dirs": len({e["arm_dir"] for e in entries}),
        "benchmarks": benchmarks,
        "entries": entries,
    }


def main() -> int:
    result = scan()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    canonical = _canonical_subset(result)
    CANONICAL_OUT.write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"wrote {CANONICAL_OUT} (canonical only)")
    print(f"bad entries (task x arm): {result['n_entries']}")
    print(f"canonical entries: {canonical['n_entries']}")
    print("\ncanonical per-benchmark unique bad tasks:")
    for fam in sorted(canonical["benchmarks"]):
        u = canonical["benchmarks"][fam]["unique_tasks"]
        print(f"  {fam:10s} unique={len(u):4d}")
    print("\nper-benchmark unique bad tasks:")
    for fam in sorted(result["benchmarks"]):
        u = result["benchmarks"][fam]["unique_tasks"]
        print(f"  {fam:10s} unique={len(u):4d}")
    print("\nper-arm (category | arm_dir -> count):")
    from collections import defaultdict
    bycat = defaultdict(list)
    for e in result["entries"]:
        bycat[e["category"]].append(e)
    for cat in sorted(bycat):
        print(f"[{cat}]")
        cnt = defaultdict(int)
        for e in bycat[cat]:
            cnt[(e["benchmark"], e["arm_dir"])] += 1
        for (fam, arm), n in sorted(cnt.items()):
            print(f"    {fam:10s} {arm:55s} {n}")
    print("\nlegacy arms (no token accounting):")
    for a in result["legacy_arms"]:
        print(f"    {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())