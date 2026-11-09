"""hle_t3_stage.py — T3 stage (offline, independent): answer-equivalence clustering.

Purpose (EVALUATION_STANDARD §5 T3 + user decision "聚类 and T3 is a separate stage"):

    Part A — answer clustering. Merge open-form candidates that are the SAME answer
    written differently (gold-FREE, deterministic, zero-LLM, reproducible). The merge
    only affects the OFFLINE evaluator aggregators — A3 majority vote, A2 settle/mode,
    C3 settle/mode — never the in-loop early-stop, and never the raw trajectories.

    Part B — representative winner changes. For each aggregator, re-derive the winning
    round under the clustered key vs the raw key and record every task whose winner
    moves.

Reads the frozen trajectories and hle_400_new.jsonl only. Writes nothing over the
originals; all outputs go to experiments/hle400/t3/.

Run (from the project root):
    python3 <this_file> --no-score      # clustering + winner-change report, zero LLM
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))

from src.run_feedback_loop import _early_stop_key  # noqa: E402

try:
    import sympy  # noqa: E402
except Exception as e:  # pragma: no cover
    print(f"[fatal] sympy import failed: {e}")
    raise SystemExit(1)


# --------------------------------------------------------------------------
# gold-free deterministic canonical form
# --------------------------------------------------------------------------

def _numeric_canonical(s: str):
    """Merge numeric-ish strings that are EXACTLY the same value expressed
    differently: fractions vs decimals, scientific notation vs decimal, powers vs
    their expansion, thousands separators. Only pure-number/arithmetic strings are
    touched (no letters, no units) so prose / unit / symbolic answers are never
    collapsed. Returns a comparable key or None (leave as-is)."""
    t = str(s).replace(",", "").strip()
    if not t:
        return None
    # only digits, whitespace, + - * / ^ ( ) . e E — no letters => no units/prose
    if not re.fullmatch(r"[\d\s+\-*/^().eE]+", t):
        return None
    if not re.search(r"\d", t):
        return None
    try:
        expr = sympy.sympify(t)
        if not expr.is_number:
            return None
        n = sympy.nsimplify(expr)
        if n.is_Integer:
            return ("int", int(n))
        if n.is_Rational:
            return ("frac", (int(n.p), int(n.q)))
        # irrational (e.g. 2^0.5): high-precision float; identical value -> identical float
        return ("num", float(n.evalf(18)))
    except Exception:
        return None


def cluster_key(answer_type: str, shape: str, existing_key):
    """Equivalence class of a round's answer, given its existing early-stop key.

    existing_key comes from _early_stop_key and is one of:
        None | ("int", v) | ("letter", v) | ("raw", norm_str)
    Only the "raw" branch (open-form: symbol/word/text + mc letters > E) is further
    canonicalised; int / letter are already canonical."""
    if existing_key is None:
        return None
    fam, val = existing_key
    if fam == "int":
        return ("int", val)
    if fam == "letter":
        return ("letter", str(val).upper())
    s = val  # already _norm_ans'd
    if answer_type == "multipleChoice":
        m = re.fullmatch(r"\(?([A-Za-z])\)?\.?", s)
        if m:
            return ("letter", m.group(1).upper())
    num = _numeric_canonical(s)
    if num is not None:
        return num
    return ("raw", s)


# --------------------------------------------------------------------------
# self-test (deterministic; fail fast if the equivalence engine regresses)
# --------------------------------------------------------------------------

def _selftest() -> None:
    pairs = [
        (("exactMatch", "symbol", ("raw", "24/25")), ("exactMatch", "symbol", ("raw", "0.96"))),
        (("exactMatch", "int",    ("raw", "2^81")), ("exactMatch", "int",    ("raw", "2417851639229258349412352"))),
        (("exactMatch", "int",    ("raw", "1,000")), ("exactMatch", "int",    ("raw", "1000"))),
        (("exactMatch", "int",    ("raw", "1e-3")), ("exactMatch", "int",    ("raw", "0.001"))),
        (("multipleChoice", "mc", ("raw", "(H)")), ("multipleChoice", "mc", ("raw", "h"))),
    ]
    for (at1, sh1, k1), (at2, sh2, k2) in pairs:
        c1 = cluster_key(at1, sh1, k1)
        c2 = cluster_key(at2, sh2, k2)
        assert c1 == c2, f"selftest FAIL: {k1!r}->{c1!r} != {k2!r}->{c2!r}"
    # negative checks (must NOT collapse)
    neg = [
        (("exactMatch", "text", ("raw", "cut off of lfc > 4")), ("exactMatch", "text", ("raw", "cut off of lfc > 5"))),
        (("exactMatch", "symbol", ("raw", "3.9 μgy")), ("exactMatch", "symbol", ("raw", "3.92e-6"))),
    ]
    for (at1, sh1, k1), (at2, sh2, k2) in neg:
        c1 = cluster_key(at1, sh1, k1)
        c2 = cluster_key(at2, sh2, k2)
        assert c1 != c2, f"selftest FAIL (should differ): {k1!r} == {k2!r}"
    print("[selftest] equivalence engine OK")


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

def load_index(data_path: Path) -> dict:
    idx = {}
    with data_path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            idx[f"hle_{i:03d}"] = {
                "question": str(d.get("question", "")).strip(),
                "gold": str(d.get("answer", "")).strip(),
                "answer_type": str(d.get("answer_type", "")).strip(),
                "shape": str(d.get("shape", "")).strip(),
            }
    return idx


def read_traj(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r
    return out


# --------------------------------------------------------------------------
# aggregator primitives (key function parameterised)
# --------------------------------------------------------------------------

def _key_of(keyfn):
    def f(meta, rec):
        k = _early_stop_key("hle", meta["gold"], rec.get("final_answer", ""),
                            rec.get("reasoning_content", ""),
                            rec.get("finish_reason", ""))[0]
        return keyfn(meta["answer_type"], meta["shape"], k)
    return f


RAW_KEY = _key_of(lambda at, sh, k: k)               # identity = current behaviour
CLUSTER_KEY = _key_of(cluster_key)                    # equivalence clustering


def _settle_idx(keyfn, meta, task):
    rounds = task.get("rounds", [])
    if not rounds:
        return None
    keys = [keyfn(meta, r) for r in rounds]
    n = len(keys)
    i = n - 1
    while i >= 0:
        j = i
        while j - 1 >= 0 and keys[j - 1] == keys[j]:
            j -= 1
        if i - j + 1 >= 3:
            return j
        i = j - 1
    return None


def _mode_idx(keyfn, meta, task):
    rounds = task.get("rounds", [])
    if not rounds:
        return -1
    keys = [keyfn(meta, r) for r in rounds]
    cnt = {}
    latest = {}
    for i, k in enumerate(keys):
        if k is None:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        latest[k] = i
    if not cnt:
        return -1
    best = max(cnt, key=lambda k: (cnt[k], latest[k]))
    return latest[best]


def _vote_idx(keyfn, meta, task):
    """A3 majority vote over rounds[1:] (A-seeded round-0 excluded). Tie -> earliest."""
    rounds = task.get("rounds", [])
    samples = rounds[1:]
    votes = Counter()
    order = {}
    for i, r in enumerate(samples):
        k = keyfn(meta, r)
        if k is not None:
            votes[k] += 1
            order.setdefault(k, i)
    if not votes:
        return -1
    winner = max(votes, key=lambda k: (votes[k], -order[k]))
    return 1 + order[winner]


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-score", action="store_true",
                    help="clustering + winner-change report only (zero LLM)")
    ap.add_argument("--data", default="data/raw/hle/hle_400_new.jsonl")
    ap.add_argument("--base", default="experiments")
    ap.add_argument("--prefix", default="hle400")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--outdir", default="experiments/hle400/t3")
    args = ap.parse_args()

    _selftest()

    base = ROOT / args.base
    meta_idx = load_index(ROOT / args.data)

    def traj(arm):
        return read_traj(base / f"{args.prefix}_{arm}" / args.model / "loop_trajectories.jsonl")

    tA2, tA3, tC3 = traj("A2"), traj("A3"), traj("C3")
    common = sorted(set(tC3) & set(meta_idx))
    print(f"[{args.prefix}] index={len(meta_idx)} A2={len(tA2)} A3={len(tA3)} C3={len(tC3)} common={len(common)}")

    # aggregated outputs
    cluster_log = []      # tasks where any merge happened
    winner_changes = []   # tasks whose aggregator winner moved raw->cluster

    summary = {"slice": args.prefix, "n_common": len(common),
               "merged_tasks": 0, "merged_pairs": 0,
               "winner_changed": {"A2_settle": 0, "A2_mode": 0,
                                  "A3_vote": 0, "C3_settle": 0, "C3_mode": 0}}

    aggregators = [
        ("A2", "settle", tA2, _settle_idx),
        ("A2", "mode",   tA2, _mode_idx),
        ("C3", "settle", tC3, _settle_idx),
        ("C3", "mode",   tC3, _mode_idx),
        ("A3", "vote",   tA3, _vote_idx),
    ]

    # per-task evaluation of clustering effect
    for t in common:
        meta = meta_idx[t]
        changed_for_task = {}
        merged_classes_for_task = {}

        for arm, metric, trajdict, _fn in aggregators:
            if t not in trajdict:
                continue
            task = trajdict[t]
            rounds = task.get("rounds", [])
            raw_keys = [RAW_KEY(meta, r) for r in rounds]
            clu_keys = [CLUSTER_KEY(meta, r) for r in rounds]

            # record merges (only interested in raw -> cluster collapsing)
            clsmap = {}
            for i, (rk, ck) in enumerate(zip(raw_keys, clu_keys)):
                if rk is None or ck is None:
                    continue
                clsmap.setdefault(ck, []).append((i, rk))
            collapsed = {ck: members for ck, members in clsmap.items()
                         if len({rk for _, rk in members}) > 1}
            if collapsed:
                merged_classes_for_task[f"{arm}_{metric}"] = {
                    "n_classes_collapsed": len(collapsed),
                    "classes": [
                        {"cluster": _json_key(ck),
                         "rounds": [i for i, _ in members],
                         "raw_values": [_json_key(rk) for _, rk in members]}
                        for ck, members in collapsed.items()
                    ],
                }

            # winner under each key
            rw = _fn(RAW_KEY, meta, task)
            cw = _fn(CLUSTER_KEY, meta, task)
            if rw != cw:
                changed_for_task[f"{arm}_{metric}"] = {
                    "raw_winner_round": rw,
                    "cluster_winner_round": cw,
                    "raw_winner_answer": _ans(rounds, rw),
                    "cluster_winner_answer": _ans(rounds, cw),
                }
                summary["winner_changed"][f"{arm}_{metric}"] += 1

        if merged_classes_for_task:
            summary["merged_tasks"] += 1
            cluster_log.append({
                "task_id": t,
                "answer_type": meta["answer_type"],
                "shape": meta["shape"],
                "gold": meta["gold"],
                "merges": merged_classes_for_task,
            })
        if changed_for_task:
            winner_changes.append({
                "task_id": t,
                "answer_type": meta["answer_type"],
                "shape": meta["shape"],
                "gold": meta["gold"],
                "changes": changed_for_task,
            })

    summary["winner_changed_total"] = sum(summary["winner_changed"].values())

    # count raw->cluster pairs collapsed (for reporting)
    total_collapsed = 0
    for rec in cluster_log:
        for arm_metric, v in rec["merges"].items():
            for c in v["classes"]:
                total_collapsed += len(c["raw_values"]) - 1
    summary["merged_pairs"] = total_collapsed

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    (outdir / "cluster_log.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in cluster_log) + ("\n" if cluster_log else ""),
        encoding="utf-8")
    (outdir / "winner_changes.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in winner_changes) + ("\n" if winner_changes else ""),
        encoding="utf-8")
    (outdir / "cluster_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # report
    print("\n=== T3 answer-clustering report (no-score) ===")
    print(f"  tasks with >=1 merge      : {summary['merged_tasks']}")
    print(f"  raw->cluster pairs merged : {summary['merged_pairs']}")
    print(f"  winner changes            : {summary['winner_changed']}")
    print(f"  total winner changes      : {summary['winner_changed_total']}")
    if winner_changes:
        print(f"\n  sample winner changes (first 30):")
        for w in winner_changes[:30]:
            print(f"    {w['task_id']} [{w['answer_type']}/{w['shape']}] gold={w['gold']!r}")
            for am, c in w["changes"].items():
                print(f"        {am}: raw r{c['raw_winner_round']}={c['raw_winner_answer']!r} "
                      f"-> cluster r{c['cluster_winner_round']}={c['cluster_winner_answer']!r}")
    print(f"\n  outputs -> {outdir}")
    print("  re-score (--score) not run in this pass.")


def _json_key(k):
    if k is None:
        return None
    fam, val = k
    if isinstance(val, (tuple, list)):
        val = list(val)
    return [fam, val]


def _ans(rounds, i):
    if i is None or i < 0 or i >= len(rounds):
        return None
    return rounds[i].get("final_answer", "")


if __name__ == "__main__":
    main()