"""
build_behavior_leaves.py
========================
L0 offline distillation (first-pass). Reverse-infer GENERALIZABLE wrong EXECUTION
BEHAVIORS from a wrong bank, to replace the degenerate format leaves
(non_letter_output / multiple_letters / wrong_option) the weak critic currently opens
for MCQ families (gpqa / mmlu_pro / bbh).

Core idea (error-guided sampling / RSI): at build time gold IS available, so for each
wrong answer we reverse-engineer WHAT EXECUTION BEHAVIOR produced it -- not "this
specific question was hard", but the reusable OPERATION / SHORTCUT / JUDGMENT STEP
that fails on a whole CLASS of such problems. That behavior is the candidate leaf:

  - wrong_behavior : the class-level wrong operation (verb phrase), reusable across
                     unseen questions of the same type. NEVER names this question's
                     specific molecule / compound / number / option text.
  - task_class     : the generalizable question type the behavior applies to.
  - trigger_hint   : a gold-free signature detectable at EXECUTION time (from the
                     question type + committed answer) that this behavior likely fired.
  - verify_hint    : a differential self-check the model can apply to its own answer,
                     generalizable and gold-free (never names the correct option).
  - evidence       : this-instance provenance ("what gave it away here"), for human
                     review only.

Scope (first-pass): gpqa only (49 wrong entries), so the emerging grain can be
reviewed by hand before expanding to mmlu_pro / bbh.

Reproducibility
---------------
- Deterministic inputs (fixed wrong bank), temperature = 0, fixed model config.
- One command: `python3 src/build_behavior_leaves.py` (add `--limit N` for a smoke run).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))


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
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_load_dotenv()
_force_no_proxy()

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402

BANK_PATH = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
OUT_DIR = ROOT / "experiments" / "l0_distill_v1"
DISTILL_MODEL = "deepseek-v4-flash"
DISTILL_VERSION = "v2.0"

# Visible-content window AFTER the hidden CoT cap. The distilled JSON needs more room
# than a single option letter (cf. stage_b_evaluator._RSI_JUDGE_CONTENT_MARGIN=1024).
CONTENT_MARGIN = int(os.getenv("L0_CONTENT_MARGIN", "1536"))
# Bounded hidden-CoT budget for the labeling call (inferring a behavior is cheaper
# than solving; we also tell the model NOT to re-solve).
THINKING_BUDGET = int(os.getenv("L0_THINKING_BUDGET", "4096"))

SYSTEM = (
    "You are a failure-behavior distillation analyst for a self-improving evaluator. "
    "Given a hard multiple-choice question, the model's WRONG answer, and the GOLD "
    "answer, reverse-infer the model's WRONG EXECUTION BEHAVIOR: the operation, "
    "shortcut, or judgment step the model applied that produced the wrong answer. "
    "The behavior MUST be a GENERALIZATION stated at the level of the problem CLASS "
    "(how to act on every question of this type), never this particular instance. "
    "Never name the specific molecule, compound, number, option text, or answer from "
    "THIS question in wrong_behavior / trigger_hint / verify_hint. Return JSON only."
)


def build_prompt(row: dict) -> str:
    prompt = row.get("prompt", "")
    wrong = row.get("final_answer", "")
    gold = row.get("gold_answer", "")
    return (
        "Question with options:\n"
        f"{prompt}\n\n"
        f"The model answered: {wrong}\n"
        f"The gold (correct) answer is: {gold}\n\n"
        "The wrong and gold answers are ALREADY GIVEN above. Do NOT re-solve or "
        "re-derive the question. Reverse-infer the generalizable WRONG EXECUTION "
        "BEHAVIOR behind the model's mistake, then return ONE JSON object with exactly "
        "these keys:\n"
        "{\n"
        "  \"task_class\": \"<short, generalizable question type this behavior applies "
        "to, e.g. 'molecular point-group identification MCQ'>\",\n"
        "  \"wrong_behavior\": \"<the reusable wrong OPERATION the model applied, a "
        "verb phrase that holds for ANY question of this class, e.g. 'assigns the "
        "point group from central-atom geometry only, ignoring substituent "
        "conformation'>\",\n"
        "  \"trigger_hint\": \"<an observable, gold-free signature at execution time "
        "(from question type + committed answer) that this behavior likely fired>\",\n"
        "  \"verify_hint\": \"<a differential self-check the model can apply to its "
        "OWN candidate answer, generalizable to this class and phrased WITHOUT naming "
        "the correct option>\",\n"
        "  \"evidence\": \"<ONE sentence of this-instance provenance: what in THIS "
        "question shows the behavior>\"\n"
        "}\n"
        "Output ONLY the JSON object, no prose."
    )


def _extract_json(content: str):
    """Pull the first JSON object out of a (possibly fenced) model reply."""
    if not content:
        return None
    # Strip ```json ... ``` fences.
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)
    else:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            content = m.group(0)
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def distill_one(row: dict, entry: dict) -> dict:
    agent = HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=1024, temperature=0.0,
        seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=THINKING_BUDGET, content_margin=CONTENT_MARGIN)
    content, reasoning, info = agent._call_llm_text(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": build_prompt(row)}])
    parsed = _extract_json(content)
    out = {
        "task_id": row["task_id"],
        "family": row["family"],
        "model": row["model"],
        "final_answer": row.get("final_answer", ""),
        "gold_answer": row.get("gold_answer", ""),
        "old_error_type": row.get("error_type", ""),
        "prompt": row.get("prompt", ""),
        "raw_reply": content,
        "task_class": parsed.get("task_class", "") if parsed else "",
        "wrong_behavior": parsed.get("wrong_behavior", "") if parsed else "",
        "trigger_hint": parsed.get("trigger_hint", "") if parsed else "",
        "verify_hint": parsed.get("verify_hint", "") if parsed else "",
        "evidence": parsed.get("evidence", "") if parsed else "",
        "parse_ok": parsed is not None,
        "finish_reason": getattr(info, "finish_reason", None),
    }
    return out


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="gpqa")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=config.RUNNER_CONCURRENCY)
    args = ap.parse_args()

    bank = [json.loads(l) for l in open(BANK_PATH, encoding="utf-8")]
    rows = [r for r in bank if r.get("family") == args.family]
    print(f"[load] {len(rows)} {args.family} wrong instances from {BANK_PATH.name}")
    if args.limit:
        rows = rows[: args.limit]
        print(f"[limit] running on first {len(rows)}")

    entry = config.PHASE1_MODELS[DISTILL_MODEL]
    print(f"[model] {entry['model']} (thinking ON, budget={THINKING_BUDGET}, "
          f"content_margin={CONTENT_MARGIN})")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"relabeled_{args.family}.jsonl"
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(distill_one, r, entry): r for r in rows}
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            results.append(res)
            print(f"[{i}/{len(rows)}] {res['task_id']} parse={res['parse_ok']} "
                  f"behavior={res['wrong_behavior'][:60]}")

    # Stable order by task_id for reproducibility.
    results.sort(key=lambda r: r["task_id"])
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- aggregate raw wrong_behavior distribution (for granularity review) ----
    by_behavior = defaultdict(list)
    for r in results:
        key = _norm(r["wrong_behavior"]) if r["wrong_behavior"] else "(unparsed)"
        by_behavior[key].append(r)

    print("\n" + "=" * 80)
    print(f"L0 distillation {DISTILL_VERSION} — {args.family} wrong-behavior distribution")
    print("=" * 80)
    print(f"{'wrong_behavior':<48}{'n':>4}   example task_ids")
    for beh, rs in sorted(by_behavior.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        tids = ", ".join(r["task_id"] for r in rs[:6])
        print(f"{beh[:48]:<48}{len(rs):>4}   {tids}")

    agg = {
        "distill_version": DISTILL_VERSION,
        "family": args.family,
        "model": entry["model"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_total": len(results),
        "n_parsed": sum(1 for r in results if r["parse_ok"]),
        "distribution": {
            beh: {
                "count": len(rs),
                "task_class": sorted({r["task_class"] for r in rs if r["task_class"]}),
                "task_ids": [r["task_id"] for r in rs],
            }
            for beh, rs in sorted(by_behavior.items(),
                                  key=lambda kv: (-len(kv[1]), kv[0]))
        },
    }
    agg_path = OUT_DIR / f"distribution_{args.family}.json"
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2, ensure_ascii=False)

    print(f"\n[written] {out_path}")
    print(f"[written] {agg_path}")


if __name__ == "__main__":
    main()