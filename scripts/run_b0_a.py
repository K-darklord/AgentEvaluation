#!/usr/bin/env python3
"""B0 candidate-set first-answer run (A arm: greedy T=0, single shot, no loop).

Runs qwen3.8-flash-payg once per question on the three sampled candidate sets
(GSM8K 200 / BBEH 805 / OlymMATH 200; see scripts/sample_b0_candidate_sets.py).
Closed-book, no tools, no feedback. Records final answer, hidden CoT, finish_reason
('length' => truncated), per-question prompt/completion/reasoning tokens and api_failure.
Scoring is done separately (rule-based), NOT here.

Checkpoint-resumable: already-written task_ids are skipped, so a restart re-bills nothing.

Usage: python3 scripts/run_b0_a.py [gsm8k|bbeh|olymmath|all] [--conc N]
"""
from __future__ import annotations
import argparse, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _load_env():
    """Load .env into os.environ (same keys the run_*.sh scripts source)."""
    env = REPO / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()  # before importing src.config: config reads api keys at import time

from src import config
from src.agent import HuggingFaceAgent

MODEL_NAME = "qwen3.8-flash-payg"
OUT_DIR = REPO / "experiments" / f"b0_A_{MODEL_NAME}"

SETS = {
    "gsm8k": REPO / "data/raw/b0/gsm8k_b0_200.jsonl",
    "bbeh": REPO / "data/raw/b0/bbeh_b0_805.jsonl",
    "olymmath": REPO / "data/raw/b0/olymmath_b0_200.jsonl",
}

SYSTEM_PROMPTS = {
    "gsm8k": (
        "You are solving a grade-school math word problem. Think through the solution, "
        "then give ONLY the final numeric answer. Put the final numeric answer inside "
        "\\boxed{...}, for example \\boxed{18}. Do not include units, currency symbols, "
        "thousands separators, or any text outside the box."
    ),
    "bbeh": (
        "You are answering a reasoning question. If it is multiple-choice, respond with "
        "ONLY the option letter (for example \"A\"). Otherwise respond with the short "
        "answer (a number, a single word, or a short phrase). Do not include any "
        "reasoning or explanation."
    ),
    "olymmath": (
        "You are solving an olympiad math problem. The answer may be an integer, a "
        "fraction, or a mathematical expression. Give ONLY the final answer inside "
        "\\boxed{...}, for example \\boxed{948}. Do not include any explanation outside "
        "the box."
    ),
}

_write_lock = threading.Lock()


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_force_no_proxy()


def _load_questions(path: Path) -> list[dict]:
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    return rows


def _load_done(path: Path) -> set:
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["task_id"])
            except Exception:
                continue
    return done


def _solve_once(agent: HuggingFaceAgent, messages: list[dict], max_attempts: int = 5):
    """Single closed-book text generation with whole-question retry on api failure."""
    last_err = ""
    for _ in range(max_attempts):
        try:
            content, reasoning, resp = agent._call_llm_text(messages)
            u = getattr(resp, "usage", None)
            return {
                "content": content or "",
                "reasoning": reasoning or "",
                "finish_reason": getattr(resp, "finish_reason", "") or "",
                "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
                "reasoning_tokens": getattr(u, "reasoning_tokens", 0) or 0,
                "api_failure": False,
            }
        except Exception as e:
            last_err = str(e)
            time.sleep(1.0)
    return {
        "content": "", "reasoning": "", "finish_reason": "",
        "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
        "api_failure": True,
    }


def run_benchmark(benchmark: str, agent: HuggingFaceAgent, conc: int) -> None:
    questions = _load_questions(SETS[benchmark])
    out_path = OUT_DIR / f"{benchmark}.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = _load_done(out_path)
    pending = [q for q in questions if q["task_id"] not in done]
    sys_prompt = SYSTEM_PROMPTS[benchmark]
    print(f"[{benchmark}] {len(questions)} total, {len(done)} done, {len(pending)} pending", flush=True)

    n_fail = 0
    n_trunc = 0

    def work(q: dict) -> dict:
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": q["question"]},
        ]
        r = _solve_once(agent, messages)
        rec = {
            "task_id": q["task_id"], "benchmark": benchmark,
            "task": q.get("task", ""), "split": q.get("split", ""),
            "question": q["question"], "gold_answer": q["gold_answer"],
            "final_answer": r["content"], "reasoning_content": r["reasoning"],
            "finish_reason": r["finish_reason"],
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "reasoning_tokens": r["reasoning_tokens"],
            "api_failure": r["api_failure"],
            "system_prompt": sys_prompt,
        }
        return rec

    with ThreadPoolExecutor(max_workers=conc) as ex:
        futures = [ex.submit(work, q) for q in pending]
        for i, fut in enumerate(as_completed(futures), 1):
            rec = fut.result()
            if rec["api_failure"]:
                n_fail += 1
            if rec["finish_reason"] == "length":
                n_trunc += 1
            with _write_lock:
                with out_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 20 == 0 or i == len(pending):
                print(f"  [{benchmark}] {i}/{len(pending)} (fail={n_fail}, trunc={n_trunc})", flush=True)

    print(f"[{benchmark}] DONE: wrote {len(pending)} new records (fail={n_fail}, trunc={n_trunc}) -> {out_path}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", nargs="?", default="all", choices=["all", "gsm8k", "bbeh", "olymmath"])
    ap.add_argument("--conc", type=int, default=40)
    args = ap.parse_args()

    entry = config.PHASE1_MODELS[MODEL_NAME]
    agent = HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"],
        max_tokens=entry.get("max_tokens", config.REASONING_BENCH_MAX_TOKENS),
        temperature=0.0, seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"),
    )

    benches = ["gsm8k", "bbeh", "olymmath"] if args.which == "all" else [args.which]
    for b in benches:
        run_benchmark(b, agent, args.conc)
    print("B0_A_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
