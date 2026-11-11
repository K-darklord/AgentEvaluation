#!/usr/bin/env python3
"""G4 (E2 mirror): replay qwen C2 bank-free critic calls to measure REAL token usage.

Mirror of `scripts/e2_c2_critic_token_replay.py` (deepseek C2) applied to the qwen
replication C2 arm (`experiments/rep200_C2_qwen3.8-flash-payg/`). Same method, frozen
config, fixed seed. Differences from the deepseek E2 script:

  - Trajectory: `experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl`
  - Model: `qwen3.8-flash-payg` (DashScope pay-as-you-go), `StrongCritic.load(model, bank_free=True)`.
  - The sampling population is restricted to C2 rounds that actually issued an LLM critic
    call (`critic_direction` or `critic_fallback` non-empty), per the G4 spec.
  - The extrapolation total is read from the trajectory facts (E1 `critic_calls_llm`
    method: sum over rounds[1:] of `critic_direction` or `critic_fallback` non-empty).

Operational note: `_call_llm_text` retries transient errors 3x without backoff; the
DashScope DNS occasionally blips longer than that, so each replay call is wrapped in an
outer backoff retry and every completed call is checkpointed to a sidecar (resumable).
The measured tokens of a successful call are unchanged by retries/resume.

Reproducibility: fixed seed, T=0, frozen config (thinking_budget 16384, content_margin
1024 => max_tokens 17408, bank_free=True, payg endpoint)."""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


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

from src.strong_critic import StrongCritic, SYSTEM_BANK_FREE  # noqa: E402

TRAJ = ROOT / "experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl"
OUT_DIR = ROOT / "experiments/rep200_C2_qwen3.8-flash-payg"
CHECKPOINT = OUT_DIR / ".token_replay_checkpoint.jsonl"
MODEL = "qwen3.8-flash-payg"
K = 50
SEED = 42


def load_feedback_rounds() -> tuple[list[dict], int, int]:
    """Feedback rounds (round >= 1) that issued a real LLM critic call, with the exact
    prev-round inputs the critic saw. Returns (rounds, n_success, n_fallback) where the
    counts follow the E1 `critic_calls_llm` method on rounds[1:]."""
    out: list[dict] = []
    n_success = 0
    n_fallback = 0
    with open(TRAJ, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            prompt = rec["prompt"]
            rrs = rec["rounds"]
            for i, r in enumerate(rrs):
                if r.get("round", 0) < 1:
                    continue
                direction = r.get("critic_direction")
                fallback = r.get("critic_fallback")
                if not (direction or fallback):
                    continue
                if fallback:
                    n_fallback += 1
                else:
                    n_success += 1
                prev = rrs[i - 1]
                out.append({
                    "task_id": rec["task_id"],
                    "prompt": prompt,
                    "prev_answer": prev.get("final_answer") or "",
                    "prev_reasoning": prev.get("reasoning_content") or "",
                    "fb_round": r.get("round"),
                    "is_fallback": bool(fallback),
                })
    return out, n_success, n_fallback


def load_checkpoint() -> dict[tuple[str, int], dict]:
    done: dict[tuple[str, int], dict] = {}
    if not CHECKPOINT.exists():
        return done
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            done[(rec["task_id"], rec["fb_round"])] = rec
    return done


def replay_one(critic: StrongCritic, item: dict) -> dict:
    user = critic._build_user(item["prompt"], item["prev_answer"], item["prev_reasoning"])
    prompt_chars = len(SYSTEM_BANK_FREE) + len(user)
    msgs = [{"role": "system", "content": SYSTEM_BANK_FREE},
            {"role": "user", "content": user}]
    last_error = None
    for attempt in range(8):
        try:
            _content, _reasoning, info = critic._agent._call_llm_text(msgs)
            usage = info.usage
            return {
                "prompt_chars": prompt_chars,
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
                "reasoning_tokens": getattr(usage, "reasoning_tokens", 0) or 0,
            }
        except Exception as e:  # transient DashScope DNS/connection blips
            last_error = e
            time.sleep(min(2 ** attempt, 20))
    raise last_error


def _mean(xs):
    return statistics.fmean(xs)


def _ci(xs, z=1.96):
    """Normal CI half-width on the mean (finite sample, std/sqrt(n))."""
    n = len(xs)
    if n < 2:
        return 0.0
    return z * statistics.stdev(xs) / (n ** 0.5)


def main() -> None:
    all_rounds, n_success, n_fallback = load_feedback_rounds()
    total_calls = len(all_rounds)
    print(f"[G4] total critic LLM calls = {total_calls} "
          f"(success {n_success} + fallback {n_fallback})")
    rng = random.Random(SEED)
    sample = rng.sample(all_rounds, K)

    critic = StrongCritic.load(MODEL, bank_free=True)
    print(f"[G4] critic model = {critic.model['model']} "
          f"base_url = {critic.model['base_url']} "
          f"thinking_budget = {critic.model.get('thinking_budget')} "
          f"bank_free = {critic.bank_free}")

    done = load_checkpoint()
    results = []
    with open(CHECKPOINT, "a", encoding="utf-8") as ck:
        for idx, item in enumerate(sample, 1):
            key = (item["task_id"], item["fb_round"])
            if key in done:
                r = dict(done[key])
                r.pop("task_id", None)
                r.pop("fb_round", None)
                r.pop("is_fallback", None)
                print(f"  [{idx:02d}/{K}] {item['task_id']} r{item['fb_round']} "
                      f"(cached) pt={r['prompt_tokens']} ct={r['completion_tokens']} "
                      f"rt={r['reasoning_tokens']}")
            else:
                r = replay_one(critic, item)
                rec = dict(r)
                rec["task_id"] = item["task_id"]
                rec["fb_round"] = item["fb_round"]
                rec["is_fallback"] = item["is_fallback"]
                ck.write(json.dumps(rec) + "\n")
                ck.flush()
                print(f"  [{idx:02d}/{K}] {item['task_id']} r{item['fb_round']} "
                      f"pc={r['prompt_chars']} pt={r['prompt_tokens']} "
                      f"ct={r['completion_tokens']} rt={r['reasoning_tokens']}")
            r["task_id"] = item["task_id"]
            r["fb_round"] = item["fb_round"]
            results.append(r)

    pcs = [r["prompt_chars"] for r in results]
    pts = [r["prompt_tokens"] for r in results]
    cts = [r["completion_tokens"] for r in results]
    rts = [r["reasoning_tokens"] for r in results]

    print("\n[G4] === per-call means (n=%d) ===" % K)
    print(f"  prompt_chars   : mean={_mean(pcs):.1f} median={statistics.median(pcs):.1f} "
          f"min={min(pcs)} max={max(pcs)}")
    print(f"  prompt_tokens  : mean={_mean(pts):.1f}")
    print(f"  completion_tokens : mean={_mean(cts):.1f}")
    print(f"  reasoning_tokens  : mean={_mean(rts):.1f} "
          f"median={statistics.median(rts):.1f} min={min(rts)} max={max(rts)}")

    ext = {
        "prompt_tokens": _mean(pts) * total_calls,
        "completion_tokens": _mean(cts) * total_calls,
        "reasoning_tokens": _mean(rts) * total_calls,
    }
    rt_lo = (_mean(rts) - _ci(rts)) * total_calls
    rt_hi = (_mean(rts) + _ci(rts)) * total_calls
    total = ext["prompt_tokens"] + ext["completion_tokens"]

    print("\n[G4] === extrapolation to %d critic calls ===" % total_calls)
    print(f"  prompt_tokens    ~ {ext['prompt_tokens']/1e6:.2f} M")
    print(f"  completion_tokens ~ {ext['completion_tokens']/1e6:.2f} M")
    print(f"  reasoning_tokens ~ {ext['reasoning_tokens']/1e6:.2f} M "
          f"[95% CI {rt_lo/1e6:.2f} - {rt_hi/1e6:.2f} M]")
    print(f"  critic total (pt+ct) ~ {total/1e6:.2f} M")
    print(f"  (fallback rounds {n_fallback} already included in the population)")

    print("\n[G4] === four-column summary (arm / 50-call mean / extrapolated / range) ===")
    print(f"  arm=C2(qwen)  | 50-mean pt={_mean(pts):.0f} ct={_mean(cts):.0f} "
          f"rt={_mean(rts):.0f} | extrap pt={ext['prompt_tokens']/1e6:.2f}M "
          f"ct={ext['completion_tokens']/1e6:.2f}M rt={ext['reasoning_tokens']/1e6:.2f}M "
          f"| rt range {rt_lo/1e6:.2f}-{rt_hi/1e6:.2f}M")

    out_path = OUT_DIR / "token_replay_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "seed": SEED, "k": K, "total_critic_calls": total_calls,
            "success_rounds": n_success, "fallback_rounds": n_fallback,
            "model": MODEL,
            "per_call_means": {
                "prompt_chars": _mean(pcs),
                "prompt_tokens": _mean(pts),
                "completion_tokens": _mean(cts),
                "reasoning_tokens": _mean(rts),
            },
            "prompt_chars_dist": {
                "mean": _mean(pcs), "median": statistics.median(pcs),
                "min": min(pcs), "max": max(pcs),
            },
            "extrapolated": {
                "prompt_tokens": ext["prompt_tokens"],
                "completion_tokens": ext["completion_tokens"],
                "reasoning_tokens": ext["reasoning_tokens"],
                "reasoning_ci_lo": rt_lo,
                "reasoning_ci_hi": rt_hi,
                "critic_total_pt_plus_ct": total,
            },
        }, f, indent=2)
    print(f"\n[G4] saved -> {out_path}")

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
        print(f"[G4] removed checkpoint {CHECKPOINT.name}")


if __name__ == "__main__":
    main()
