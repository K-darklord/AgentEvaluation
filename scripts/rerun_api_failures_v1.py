#!/usr/bin/env python3
"""V1 variance api_failure whole-task rerun (docs/RUN_VARIANCE_SPEC.md).

Same rule as scripts/rerun_api_failures.py (rule 1: any trajectory with an
api_failure round is invalid -> rerun the WHOLE task), but for the V1 confirm set:
  - loads the first confirm batch hle_401..800 (not hle_001..400),
  - supports A2PY (--max-rounds 100 + token-yoked budget from YOKE_BUDGET_FILE).
Round-0 is reused from the A arm (--a-source = conf_A), matching the V1 runs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.run_feedback_loop as rfl  # noqa: E402
from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402
from src.benchmark import load_hle_questions  # noqa: E402
from src.strong_critic import StrongCritic  # noqa: E402

TIER = "C"
EARLY_STOP_N = 3
MAX_TOKENS = config.REASONING_BENCH_MAX_TOKENS


def build_agent(model: str, temperature: float):
    entry = config.PHASE1_MODELS[model]
    return HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=MAX_TOKENS, temperature=temperature,
        seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"))


def build_critic(model: str, arm: str):
    if arm == "C2":
        return StrongCritic.load(model, bank_free=True)
    return None


def load_bad_tasks(traj_path: Path):
    bad = []
    for line in traj_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        fr = [r.get("round") for r in d.get("rounds", []) if r.get("api_failure")]
        if fr:
            bad.append((d["task_id"], fr))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="C2 / A2P")
    ap.add_argument("--model", default="qwen3.8-flash-payg")
    ap.add_argument("--traj", required=True, help="trajectory file to repair")
    ap.add_argument("--a-source", default="", help="A arm trajectory (round-0 source)")
    ap.add_argument("--max-rounds", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    rfl._force_no_proxy()
    traj_path = Path(args.traj)
    a_source = Path(args.a_source) if args.a_source else None

    agent = build_agent(args.model, 0.0)
    critic = build_critic(args.model, args.arm)

    tasks = load_hle_questions(AGENT_ROOT / "data/raw/hle/hle_confirm_s1.jsonl",
                               start_id=401)
    task_by_id = {t.task_id: t for t in tasks}

    a_round0 = {}
    if a_source is not None and a_source.exists():
        a_round0 = rfl._load_a_round0_by_task(a_source)

    yoke_budget = rfl._load_yoke_budget() if args.arm == "A2P" else None

    bad = load_bad_tasks(traj_path)
    if args.limit:
        bad = bad[: args.limit]
    if not bad:
        print(f"[rerun-v1] {args.arm}: nothing to do", flush=True)
        return 0

    print(f"[rerun-v1] {args.arm} max_rounds={args.max_rounds} model={args.model} "
          f"bad_tasks={len(bad)}", flush=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = traj_path.with_name(traj_path.name + f".bak_apifail_v1_{ts}")
    shutil.copy2(traj_path, bak)
    print(f"[rerun-v1] backup -> {bak}", flush=True)

    records = [json.loads(l) for l in traj_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rec_by_id = {r["task_id"]: r for r in records}

    def run_full(tid):
        task = task_by_id.get(tid)
        if task is None:
            return None, f"task not found: {tid}"
        a0 = a_round0.get(tid)
        rec = rfl._run_task_loop(agent, critic, task, TIER, args.max_rounds,
                                 EARLY_STOP_N, args.arm, "off", None, None, a0,
                                 yoke_budget)
        if any(r.get("api_failure") for r in rec.get("rounds", [])):
            return None, f"still has api_failure: {tid}"
        rec["endpoint"] = args.model
        return rec, None

    def _work(item):
        tid, _failed_rounds = item
        try:
            rec, err = run_full(tid)
            return tid, rec, err, None
        except rfl.InterfaceAbortError as e:
            return tid, None, None, f"{e}"
        except Exception as e:  # noqa: BLE001
            return tid, None, f"{type(e).__name__}: {e}", None

    results = {}
    errors = {}
    abort_msg = None
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(_work, item) for item in bad]
        for fut in as_completed(futures):
            tid, rec, err, abt = fut.result()
            if abt is not None:
                abort_msg = abt
                print(f"  ABORT {tid}: {abt}", flush=True)
                for f in futures:
                    f.cancel()
                break
            if err:
                errors[tid] = err
                print(f"  ERROR {tid}: {err}", flush=True)
            else:
                results[tid] = rec
                done += 1
                print(f"  {done}/{len(bad)} {tid} done", flush=True)

    if abort_msg is not None:
        print(f"[rerun-v1] aborted: {abort_msg}", flush=True)
        return 1

    for tid, val in results.items():
        rec_by_id[tid] = val

    out_lines = [json.dumps(rec_by_id.get(r["task_id"], r), ensure_ascii=False) for r in records]
    traj_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    remaining = [t for t, _fr in load_bad_tasks(traj_path)]
    print(f"[rerun-v1] {args.arm}: done={done} errors={len(errors)} "
          f"remaining_api_failure={len(remaining)}", flush=True)
    if errors:
        print(f"[rerun-v1] {args.arm} errors: {errors}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
