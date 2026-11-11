#!/usr/bin/env python3
"""TBD-4b (N2): replay C3 bank-aware critic calls to measure REAL token usage.

Mirror of E2 (`scripts/e2_c2_critic_token_replay.py`) applied to the C3 critic
(`StrongCritic(bank_free=False)`). The C3 critic discards its usage object at runtime, so
its token cost in `docs/_token_cost_autogen.md` §2 is a char-based *estimate*. This script
closes the gap the same way E2 did for C2: replay a fixed seed sample of C3 feedback rounds
through the frozen bank-aware config and read the actual prompt / completion / reasoning
tokens from the streaming usage object.

Method (identical to E2):
  - Load `experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl`.
  - Collect every feedback round (round >= 1). For round i the critic critiqued round
    (i-1)'s `final_answer` + `reasoning_content` (matches `_run_task_loop`).
  - Sample K=50 rounds with a fixed seed.
  - Reconstruct the EXACT prompt via `StrongCritic._build_user` (truncates reasoning to
    `CRITIC_REASONING_BUDGET`, embeds the answer-free level-3 bank vocabulary) plus
    `SYSTEM`, then call `critic._agent._call_llm_text` once per sample.
  - Aggregate means, extrapolate to 2288 feedback rounds, report a reasoning-token range.

Endpoint note: the C3 critic ran on the token-plan route (`deepseek-v4-flash`), which is
now 429 (insufficient quota). The payg alias (`deepseek-v4-flash-payg`) serves the SAME
`deepseek-v4-flash-0731` weights on the same Bailian backend, so token counts are
identical; only billing differs (see `src/config.py`). We therefore load the bank keyed to
`deepseek-v4-flash` and issue the replay through the payg endpoint.

Reproducibility: fixed seed, T=0, frozen config (thinking_budget 16384, content_margin
1024 => max_tokens 17408, bank_free=False)."""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
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

from src.strong_critic import StrongCritic, SYSTEM  # noqa: E402
from src.egte_critic import Level3Critic  # noqa: E402
from src import config  # noqa: E402

TRAJ = ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"
BANK_MODEL = "deepseek-v4-flash"        # bank identity (level3_bank_deepseek-v4-flash.json)
ENDPOINT_MODEL = "deepseek-v4-flash-payg"  # replay route (same weights, token-plan 429)
K = 50
SEED = 42
TOTAL_FEEDBACK_ROUNDS = 2288


def load_feedback_rounds() -> list[dict]:
    """All feedback rounds (round >= 1) with the exact prev-round inputs the critic saw."""
    out: list[dict] = []
    with open(TRAJ, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            prompt = rec["prompt"]
            rrs = rec["rounds"]
            for i, r in enumerate(rrs):
                if r.get("round", 0) < 1:
                    continue
                prev = rrs[i - 1]
                out.append({
                    "task_id": rec["task_id"],
                    "prompt": prompt,
                    "prev_answer": prev.get("final_answer") or "",
                    "prev_reasoning": prev.get("reasoning_content") or "",
                    "fb_round": r.get("round"),
                })
    return out


def replay_one(critic: StrongCritic, item: dict) -> dict:
    user = critic._build_user(item["prompt"], item["prev_answer"], item["prev_reasoning"])
    prompt_chars = len(SYSTEM) + len(user)
    _content, _reasoning, info = critic._agent._call_llm_text(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": user}])
    usage = info.usage
    pt = getattr(usage, "prompt_tokens", 0) or 0
    ct = getattr(usage, "completion_tokens", 0) or 0
    rt = getattr(usage, "reasoning_tokens", 0) or 0
    return {
        "prompt_chars": prompt_chars,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "reasoning_tokens": rt,
    }


def _mean(xs):
    return statistics.fmean(xs)


def _ci(xs, z=1.96):
    n = len(xs)
    if n < 2:
        return 0.0
    return z * statistics.stdev(xs) / (n ** 0.5)


def main() -> None:
    all_rounds = load_feedback_rounds()
    print(f"[TBD-4b] total feedback rounds = {len(all_rounds)} "
          f"(expect {TOTAL_FEEDBACK_ROUNDS})")
    rng = random.Random(SEED)
    sample = rng.sample(all_rounds, K)

    critic = StrongCritic(
        Level3Critic.load(BANK_MODEL).entries,
        config.PHASE1_MODELS[ENDPOINT_MODEL],
        bank_free=False,
    )
    print(f"[TBD-4b] critic model = {critic.model['model']} "
          f"base_url = {critic.model['base_url']} "
          f"thinking_budget = {critic.model.get('thinking_budget')} "
          f"bank_free = {critic.bank_free}")

    results = []
    for idx, item in enumerate(sample, 1):
        r = replay_one(critic, item)
        r["task_id"] = item["task_id"]
        r["fb_round"] = item["fb_round"]
        results.append(r)
        print(f"  [{idx:02d}/{K}] {item['task_id']} r{item['fb_round']} "
              f"pc={r['prompt_chars']} pt={r['prompt_tokens']} "
              f"ct={r['completion_tokens']} rt={r['reasoning_tokens']}")

    pcs = [r["prompt_chars"] for r in results]
    pts = [r["prompt_tokens"] for r in results]
    cts = [r["completion_tokens"] for r in results]
    rts = [r["reasoning_tokens"] for r in results]

    print("\n[TBD-4b] === per-call means (n=%d) ===" % K)
    print(f"  prompt_chars   : mean={_mean(pcs):.1f} median={statistics.median(pcs):.1f} "
          f"min={min(pcs)} max={max(pcs)}")
    print(f"  prompt_tokens  : mean={_mean(pts):.1f}")
    print(f"  completion_tokens : mean={_mean(cts):.1f}")
    print(f"  reasoning_tokens  : mean={_mean(rts):.1f} "
          f"median={statistics.median(rts):.1f} min={min(rts)} max={max(rts)}")

    ext = {
        "prompt_tokens": _mean(pts) * TOTAL_FEEDBACK_ROUNDS,
        "completion_tokens": _mean(cts) * TOTAL_FEEDBACK_ROUNDS,
        "reasoning_tokens": _mean(rts) * TOTAL_FEEDBACK_ROUNDS,
    }
    rt_lo = (_mean(rts) - _ci(rts)) * TOTAL_FEEDBACK_ROUNDS
    rt_hi = (_mean(rts) + _ci(rts)) * TOTAL_FEEDBACK_ROUNDS
    total = ext["prompt_tokens"] + ext["completion_tokens"]

    print("\n[TBD-4b] === extrapolation to %d feedback rounds ===" % TOTAL_FEEDBACK_ROUNDS)
    print(f"  prompt_tokens    ~ {ext['prompt_tokens']/1e6:.2f} M")
    print(f"  completion_tokens ~ {ext['completion_tokens']/1e6:.2f} M")
    print(f"  reasoning_tokens ~ {ext['reasoning_tokens']/1e6:.2f} M "
          f"[95% CI {rt_lo/1e6:.2f} - {rt_hi/1e6:.2f} M]")
    print(f"  critic total (pt+ct) ~ {total/1e6:.2f} M")

    print("\n[TBD-4b] === four-column summary (arm / 50-call mean / extrapolated / range) ===")
    print(f"  arm=C3  | 50-mean pt={_mean(pts):.0f} ct={_mean(cts):.0f} "
          f"rt={_mean(rts):.0f} | extrap pt={ext['prompt_tokens']/1e6:.2f}M "
          f"ct={ext['completion_tokens']/1e6:.2f}M rt={ext['reasoning_tokens']/1e6:.2f}M "
          f"| rt range {rt_lo/1e6:.2f}-{rt_hi/1e6:.2f}M")

    out_path = ROOT / "experiments/hle400_C3/token_replay_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "seed": SEED, "k": K, "total_feedback_rounds": TOTAL_FEEDBACK_ROUNDS,
            "bank_model": BANK_MODEL, "endpoint_model": ENDPOINT_MODEL,
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
    print(f"\n[TBD-4b] saved -> {out_path}")


if __name__ == "__main__":
    main()
