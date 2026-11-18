#!/usr/bin/env python3
"""Draw the B1 (second-benchmark) BBEH question lists.

Samples, per task, 80 questions that were NOT used in the B0 screening
(data/raw/b0/bbeh_b0_805.jsonl), with the FIXED seed 20261118 and never re-drawn.

  * BBEH-hard (10 tasks x 80 = 800): multistep_arithmetic, nycc, geometric_shapes,
    sportqa, hyperbaton, temporal_sequence, zebra_puzzles, linguini, sarc_triples,
    shuffled_objects.
  * BBEH-easy (3 tasks x 80 = 240): time_arithmetic, object_counting, boardgame_qa.

Reads no experiment output. Deterministic: re-running produces identical files.
Writes data/raw/b1/bbeh_hard_800.jsonl, bbeh_easy_240.jsonl and a manifest.

Usage: python3 scripts/sample_bbeh_b1.py
"""
from __future__ import annotations
import json, random
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = 20261118
BBEH_TASK_DIR = REPO / "data/raw/bbeh/bbeh/benchmark_tasks"
B0_BBEH = REPO / "data/raw/b0/bbeh_b0_805.jsonl"
PER_TASK = 80
OUT_DIR = REPO / "data/raw/b1"

HARD_TASKS = [
    "multistep_arithmetic", "nycc", "geometric_shapes", "sportqa", "hyperbaton",
    "temporal_sequence", "zebra_puzzles", "linguini", "sarc_triples", "shuffled_objects",
]
EASY_TASKS = ["time_arithmetic", "object_counting", "boardgame_qa"]


def _load_b0_used() -> dict[str, set[int]]:
    """Return {bbeh_<task>: set(source_index)} already drawn in B0 screening."""
    used: dict[str, set[int]] = {}
    if not B0_BBEH.exists():
        return used
    for line in B0_BBEH.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        task = str(d.get("task", ""))  # directory name, e.g. "bbeh_boardgame_qa"
        used.setdefault(task, set()).add(int(d.get("source_index", -1)))
    return used


def _sample(task_names: list[str], group: str, rng, used) -> list[dict]:
    out: list[dict] = []
    for tn in task_names:
        dname = f"bbeh_{tn}"
        td = BBEH_TASK_DIR / dname
        with (td / "task.json").open(encoding="utf-8") as f:
            data = json.load(f)
        examples = data["examples"]
        used_idxs = used.get(dname, set())
        remaining = [i for i in range(len(examples)) if i not in used_idxs]
        if len(remaining) < PER_TASK:
            raise SystemExit(f"[BBEH-B1] {dname}: only {len(remaining)} remaining < {PER_TASK}")
        idxs = rng.sample(remaining, PER_TASK)
        for j, i in enumerate(idxs):
            ex = examples[i]
            out.append({
                "task_id": f"bbeh_b1_{tn}_{j:03d}",
                "question": ex["input"].strip(),
                "gold_answer": str(ex.get("target", "")),
                "benchmark": "bbeh",
                "task": tn,
                "group": group,
                "difficulty": "Hard" if group == "hard" else "Easy",
                "source_index": i,
            })
    return out


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    used = _load_b0_used()
    rng = random.Random(SEED)
    hard = _sample(HARD_TASKS, "hard", rng, used)
    easy = _sample(EASY_TASKS, "easy", rng, used)

    hard_path = OUT_DIR / "bbeh_hard_800.jsonl"
    easy_path = OUT_DIR / "bbeh_easy_240.jsonl"
    _write(hard_path, hard)
    _write(easy_path, easy)

    manifest = {
        "rule": "B1 second-benchmark BBEH sampling, FIXED seed, never re-drawn; excludes B0-screened source_index",
        "seed": SEED,
        "excluded_source": str(B0_BBEH.relative_to(REPO)),
        "per_task": PER_TASK,
        "hard": {
            "n": len(hard),
            "tasks": HARD_TASKS,
            "per_task_distribution": dict(Counter(r["task"] for r in hard)),
            "file": str(hard_path.relative_to(REPO)),
        },
        "easy": {
            "n": len(easy),
            "tasks": EASY_TASKS,
            "per_task_distribution": dict(Counter(r["task"] for r in easy)),
            "file": str(easy_path.relative_to(REPO)),
        },
    }
    man_path = OUT_DIR / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")

    print("hard:", len(hard), "tasks:", len(HARD_TASKS), "->", hard_path.relative_to(REPO))
    print("easy:", len(easy), "tasks:", len(EASY_TASKS), "->", easy_path.relative_to(REPO))
    print("manifest ->", man_path.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
