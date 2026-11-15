#!/usr/bin/env python3
"""16-question alignment gate for the three third-model candidates (THIRD_MODEL_SPEC §3/§10).
Reports run-health ONLY: done/timeout, truncation rate, reasoning-token mean/max, latency.
No correctness is read or printed. Run: python3 scripts/gate_16_candidates.py
"""
import os, sys, time
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"; os.environ["no_proxy"] = "*"

from src import config
from src.agent import HuggingFaceAgent
from src.benchmark import load_hle_questions

GATE_IDS = ["hle_006","hle_007","hle_008","hle_009","hle_010","hle_012","hle_013","hle_015",
            "hle_016","hle_019","hle_020","hle_021","hle_023","hle_032","hle_038","hle_039"]

HLE_SYSTEM = ("You are answering a difficult knowledge question. Provide ONLY the "
              "final answer in the form the question requests (a number, a symbolic "
              "or LaTeX expression, a word, or a short phrase). Do not include any "
              "reasoning, explanation, or preamble.")

CANDIDATES = {
    "MiniMax-M2.5": {"model": "MiniMax-M2.5", "enable_thinking": True, "thinking_budget": 16384},
    "kimi-k2.5":    {"model": "kimi-k2.5",    "enable_thinking": True, "thinking_budget": 16384},
    "kimi-k2.6":    {"model": "kimi-k2.6",    "enable_thinking": True, "thinking_budget": 16384},
}


def main():
    all_tasks = {t.task_id: t for t in load_hle_questions()}
    tasks = [all_tasks[i] for i in GATE_IDS if i in all_tasks]
    print(f"gate tasks loaded: {len(tasks)} / 16", flush=True)
    for name, entry in CANDIDATES.items():
        agent = HuggingFaceAgent(
            model=entry["model"], token=os.environ.get("DASHSCOPE_API_KEY", ""),
            base_url=config.DASHSCOPE_BASE_URL,
            max_tokens=config.REASONING_BENCH_MAX_TOKENS, temperature=0.0, seed=None,
            enable_thinking=entry.get("enable_thinking"),
            thinking_budget=entry.get("thinking_budget"),
            content_margin=config.REASONING_CONTENT_MARGIN,
        )
        print(f"\n===== {name} 16-question gate =====", flush=True)
        done = 0; timeout = 0; truncated = 0
        rt_vals = []; lat_vals = []; reasoning_empty = 0; content_empty = 0
        for task in tasks:
            messages = [{"role": "system", "content": HLE_SYSTEM},
                        {"role": "user", "content": task.prompt}]
            t0 = time.time()
            try:
                content, reasoning, resp = agent._call_llm_text(messages)
                lat = time.time() - t0
                u = resp.usage
                ct = u.completion_tokens; rt = u.reasoning_tokens; fr = resp.finish_reason
                done += 1; lat_vals.append(lat); rt_vals.append(rt)
                if fr == "length":
                    truncated += 1
                if not (reasoning or "").strip():
                    reasoning_empty += 1
                if not (content or "").strip():
                    content_empty += 1
                print(f"  {task.task_id}: fr={fr} ct={ct} rt={rt} lat={lat:.0f}s "
                      f"reason_nonempty={bool((reasoning or '').strip())} "
                      f"content_nonempty={bool((content or '').strip())}", flush=True)
            except Exception as e:
                timeout += 1
                lat = time.time() - t0
                print(f"  {task.task_id}: ERROR {type(e).__name__} lat={lat:.0f}s {str(e)[:140]}", flush=True)
        if done:
            rt_mean = sum(rt_vals) / len(rt_vals)
            rt_max = max(rt_vals)
            lat_mean = sum(lat_vals) / len(lat_vals)
            trunc_rate = truncated / done
        else:
            rt_mean = rt_max = lat_mean = float("nan")
            trunc_rate = float("nan")
        print(f"  SUMMARY {name}: done={done}/16 timeout={timeout} "
              f"trunc_rate={truncated}/{done}={trunc_rate:.0%} "
              f"rt_mean={rt_mean:.0f} rt_max={rt_max} lat_mean={lat_mean:.0f}s "
              f"reasoning_empty={reasoning_empty} content_empty={content_empty}", flush=True)


if __name__ == "__main__":
    main()
