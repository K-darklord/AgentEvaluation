"""analyze_hle_activation.py
============================
Unified H1 (activation) analysis under the frozen scorer_LLM_rescue standard.

Replaces the earlier round-based EIR/ECR (denominators = #correct rounds vs #wrong
rounds, mismatched ~10x) with two base-consistent quantities:

  1) item-level net transition   (base = #tasks)
       corrected = #(init wrong -> final right)
       flipped   = #(init right  -> final wrong)
       identity  : final = init + corrected - flipped   (aligns with final accuracy)

  2) transition-based EIR / ECR  (base = #answer-changing transitions, SAME for both)
       EIR       = #(correct -> wrong answer change)
       ECR       = #(wrong   -> correct answer change)
       unchanged = #(answer changed, correctness unchanged)

Plus reachability / activation rate:
      P_act = P(correct answer appears in >=1 round of the loop), rescue-graded.

Every quantity uses ``score_hle`` (rescue = max(T1, LLM-judge)) so activation / EIR /
ECR / final accuracy share ONE standard.

Modes: --mode t1 (fast) | rescue (judge on T1-missed rows, disk-cached to --cache).
Judge calls are thread-pooled (--threads) and memoized to --cache for resume.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _force_no_proxy() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_load_dotenv()
_force_no_proxy()

from collections import Counter  # noqa: E402
from src.hle_scorer import score_hle, score_t1  # noqa: E402
from src.run_feedback_loop import _early_stop_key  # noqa: E402

FAMILY = "hle"


def load_index(data_path: Path) -> dict:
    idx: dict = {}
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
    out: dict = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["task_id"]] = r
    return out


def _key(meta: dict, rec: dict):
    return _early_stop_key(FAMILY, meta["gold"], rec.get("final_answer", ""),
                           rec.get("reasoning_content", ""),
                           rec.get("finish_reason", ""))[0]


def _score_one(meta: dict, resp: str, mode: str) -> bool:
    if mode == "t1":
        return score_t1(meta["gold"], meta["answer_type"], meta["shape"], resp or "")
    return score_hle(meta["question"], meta["gold"], meta["answer_type"],
                     meta["shape"], resp or "")["correct"]


class RoundScorer:
    def __init__(self, cache_path: Path | None, mode: str, threads: int):
        self.mode = mode
        self.threads = threads
        self.cache: dict = {}
        self.cache_path = cache_path
        self.lock = threading.Lock()
        if cache_path is not None and cache_path.exists():
            try:
                self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}

    @staticmethod
    def _ck(slice_name, arm, task_id, idx):
        return f"{slice_name}|{arm}|{task_id}|{idx}"

    def _get(self, ck):
        with self.lock:
            v = self.cache.get(ck)
        return bool(v["correct"]) if v is not None else None

    def _put(self, ck, correct):
        with self.lock:
            self.cache[ck] = {"correct": bool(correct)}

    def round_score(self, slice_name, arm, task_id, meta, rec, idx) -> bool:
        ck = self._ck(slice_name, arm, task_id, idx)
        v = self._get(ck)
        if v is not None:
            return v
        correct = _score_one(meta, rec.get("final_answer", ""), self.mode)
        self._put(ck, correct)
        return correct

    def prefetch(self, specs):
        """specs: list of (slice_name, arm, task_id, meta, rec, idx). Judge in parallel."""
        missing = [sp for sp in specs if self._get(self._ck(*sp[:3], sp[-1])) is None]

        def work(sp):
            slice_name, arm, task_id, meta, rec, idx = sp
            ck = self._ck(slice_name, arm, task_id, idx)
            correct = _score_one(meta, rec.get("final_answer", ""), self.mode)
            self._put(ck, correct)
            return correct

        if missing:
            with ThreadPoolExecutor(max_workers=self.threads) as ex:
                for _ in ex.map(work, missing):
                    pass

    def flush(self):
        if self.cache_path is None:
            return
        with self.lock:
            data = dict(self.cache)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.cache_path)


def _collect_specs(slice_name, arm, meta_idx, traj):
    specs = []
    for t in sorted(set(traj) & set(meta_idx)):
        meta, task = meta_idx[t], traj[t]
        rounds = task.get("rounds", [])
        specs.extend((slice_name, arm, t, meta, r, i) for i, r in enumerate(rounds))
    return specs


def loop_analysis(scorer, slice_name, arm, meta_idx, traj):
    common = sorted(set(traj) & set(meta_idx))
    init_c = final_c = pact = 0
    corrected = flipped = stay_correct = stay_wrong = 0
    eir = ecr = unchanged = 0
    n_rounds = 0
    for t in common:
        meta, task = meta_idx[t], traj[t]
        rounds = task.get("rounds", [])
        if not rounds:
            continue
        keys = [_key(meta, r) for r in rounds]
        corr = [scorer.round_score(slice_name, arm, t, meta, r, i)
                for i, r in enumerate(rounds)]
        n_rounds += len(corr)
        s0, s1 = corr[0], corr[-1]
        init_c += s0
        final_c += s1
        pact += any(corr)
        if (not s0) and s1:
            corrected += 1
        elif s0 and (not s1):
            flipped += 1
        elif s0 and s1:
            stay_correct += 1
        else:
            stay_wrong += 1
        for i in range(1, len(corr)):
            if keys[i - 1] == keys[i]:
                continue
            before, after = corr[i - 1], corr[i]
            if before and (not after):
                eir += 1
            elif (not before) and after:
                ecr += 1
            else:
                unchanged += 1
    n = len(common)
    transitions = eir + ecr + unchanged
    return {
        "n": n, "n_rounds": n_rounds,
        "init": round(init_c / n, 4) if n else 0.0,
        "final": round(final_c / n, 4) if n else 0.0,
        "P_act": round(pact / n, 4) if n else 0.0,
        "item_net": {
            "corrected": corrected, "flipped": flipped,
            "stay_correct": stay_correct, "stay_wrong": stay_wrong,
            "net": corrected - flipped,
            "identity_ok": (final_c == init_c + corrected - flipped),
        },
        "transition_rates": {
            "EIR": eir, "ECR": ecr, "unchanged": unchanged, "base": transitions,
            "EIR_rate": round(eir / transitions, 4) if transitions else 0.0,
            "ECR_rate": round(ecr / transitions, 4) if transitions else 0.0,
        },
    }


def a3_analysis(scorer, slice_name, meta_idx, traj):
    common = sorted(set(traj) & set(meta_idx))
    n = len(common)
    vote_c = 0
    reach_c = 0
    for t in common:
        meta, task = meta_idx[t], traj[t]
        rounds = task.get("rounds", [])
        if not rounds:
            continue
        keys = [_key(meta, r) for r in rounds]
        corr = [scorer.round_score(slice_name, "A3", t, meta, r, i)
                for i, r in enumerate(rounds)]
        reach_c += any(corr)
        cnt = Counter(k for k in keys if k is not None)
        if cnt:
            winner_key = cnt.most_common(1)[0][0]
            winner_rec = next((r for r, k in zip(rounds, keys) if k == winner_key), rounds[0])
            vote_c += _score_one(meta, winner_rec.get("final_answer", ""), scorer.mode)
    return {"n": n, "vote": round(vote_c / n, 4) if n else 0.0,
            "P_act": round(reach_c / n, 4) if n else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--base", default="experiments")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--arms", default="C3,A2,A3")
    ap.add_argument("--mode", default="t1", choices=["t1", "rescue"])
    ap.add_argument("--cache", default=None)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = ROOT / args.base
    meta_idx = load_index(ROOT / args.data)
    scorer = RoundScorer(Path(args.cache) if args.cache else None, args.mode, args.threads)

    def traj(arm):
        return read_traj(base / f"{args.prefix}_{arm}" / args.model / "loop_trajectories.jsonl")

    # arm label is canonical (upper) for analysis/cache; directory uses raw arg case
    # (pilot dirs are lowercase hle_pilot_a3/c3; hle150 dirs are uppercase hle150_A3/C3).
    raw_arms = args.arms.split(",")
    arm_trajs = {raw: traj(raw) for raw in raw_arms}          # dir arm (raw case)
    label_of = {raw: raw.upper() for raw in raw_arms}         # canonical label
    for raw, t in arm_trajs.items():
        print(f"[{args.prefix}.{label_of[raw]}] mode={args.mode} tasks={len(t)} "
              f"valid={len(set(t) & set(meta_idx))}",
              flush=True)

    # Prefetch every (round) score in parallel (rescue -> judge only on T1-missed).
    specs = []
    for raw, t in arm_trajs.items():
        specs.extend(_collect_specs(args.prefix, label_of[raw], meta_idx, t))
    print(f"prefetching {len(specs)} round-scores...", flush=True)
    scorer.prefetch(specs)
    scorer.flush()
    print("prefetch done", flush=True)

    res = {}
    for raw, t in arm_trajs.items():
        label = label_of[raw]
        if label in ("C3", "A2"):
            res[label] = loop_analysis(scorer, args.prefix, label, meta_idx, t)
        elif label == "A3":
            res[label] = a3_analysis(scorer, args.prefix, meta_idx, t)

    scorer.flush()
    print("\n=== H1 activation (unified %s) ===" % args.mode)
    print(json.dumps({"slice": args.prefix, "mode": args.mode, "arms": res},
                     indent=2, ensure_ascii=False))

    if args.out:
        outpath = ROOT / args.out
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(json.dumps({"slice": args.prefix, "mode": args.mode,
                                       "arms": res}, indent=2, ensure_ascii=False),
                           encoding="utf-8")
        print(f"\nsummary -> {outpath}")


if __name__ == "__main__":
    main()
