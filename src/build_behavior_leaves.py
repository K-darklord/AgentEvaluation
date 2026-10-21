"""
build_behavior_leaves.py
========================
L0 offline distillation (first-pass). Reverse-infer GENERALIZABLE wrong EXECUTION
BEHAVIORS from a wrong bank, to replace the degenerate format leaves
(non_letter_output / multiple_letters / wrong_option) the weak critic currently opens
for MCQ families (gpqa / mmlu_pro / bbh).

This script implements the DISTILLATION role of **Error-Guided Test-Time Elimination
(EGTE)** — the re-anchored 2026-10-21 framing of the RSI loop. EGTE never trains a
reward model and never scores the *correct* path; it distills, from gold-annotated
errors, a finite set of *answer-free* WRONG EXECUTION BEHAVIORS that a separate
test-time evaluator uses to ELIMINATE wrong moves (not select the right one). Capability
therefore improves by *mechanism*, not by memorizing instance answers — the solver and
the evaluator roles are always SEPARATE calls.

The three EGTE roles and what this script (role 1 = distill) emits for the downstream
roles:

  - problem_class   : the generalizable question type the behavior applies to (metadata).
  - mechanism       : role 1 (distill) → the class-level wrong OPERATION, a verb phrase,
                      answer-free, reusable across unseen questions of the same type.
                      NEVER names this question's molecule / compound / number / option.
  - check_procedure : role 3 (review) → a differential, gold-free self-check that catches
                      the mechanism in a committed answer (never names the correct option).
  - trigger         : role 2 (check)   → a gold-free execution-time signature (question
                      type + committed answer) that suspects the mechanism fired.
  - evidence        : role 3 (review)  → one-sentence this-instance provenance, human
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
DISTILL_VERSION = "v3.0"

# Visible-content window AFTER the hidden CoT cap. The distilled JSON needs more room
# than a single option letter (cf. stage_b_evaluator._RSI_JUDGE_CONTENT_MARGIN=1024).
CONTENT_MARGIN = int(os.getenv("L0_CONTENT_MARGIN", "1536"))
# Bounded hidden-CoT budget for the labeling call (inferring a behavior is cheaper
# than solving; we also tell the model NOT to re-solve).
THINKING_BUDGET = int(os.getenv("L0_THINKING_BUDGET", "4096"))

SYSTEM = (
    "You are the DISTILLATION role of an Error-Guided Test-Time Elimination (EGTE) "
    "evaluator. EGTE never trains a reward model and never scores the correct "
    "reasoning path: at build time (gold available) it reverse-infers, from a WRONG "
    "answer, the class-level WRONG EXECUTION BEHAVIOR the model applied, and distills "
    "it into an answer-free mechanism + check_procedure that SEPARATE roles later use, "
    "at test time, to ELIMINATE that wrong move instead of selecting the correct one. "
    "The behavior MUST generalize to the problem CLASS (how to act on every question "
    "of this type), never this particular instance. Never name the specific molecule, "
    "compound, number, option text, or answer from THIS question in mechanism / "
    "check_procedure / trigger. Return JSON only."
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
        "re-derive the question. You are the DISTILLATION role: reverse-infer the "
        "generalizable WRONG EXECUTION BEHAVIOR and package it for two SEPARATE "
        "downstream roles — a test-time CHECK role that flags the error from the "
        "question + committed answer alone, and a REVIEW role that confirms it with "
        "evidence. Return ONE JSON object with exactly these keys:\n"
        "{\n"
        "  \"problem_class\": \"<short, generalizable question type this behavior applies "
        "to, e.g. 'molecular point-group identification MCQ'>\",\n"
        "  \"mechanism\": \"<the reusable wrong OPERATION the model applied, a verb "
        "phrase that holds for ANY question of this class, e.g. 'assigns the point group "
        "from central-atom geometry only, ignoring substituent conformation'>\",\n"
        "  \"check_procedure\": \"<a differential, gold-free self-check the REVIEW role "
        "applies to catch this mechanism, generalizable to this class and phrased "
        "WITHOUT naming the correct option>\",\n"
        "  \"trigger\": \"<a gold-free execution signature (from question type + "
        "committed answer) the CHECK role uses to suspect this mechanism fired>\",\n"
        "  \"evidence\": \"<ONE sentence of this-instance provenance for the REVIEW "
        "role: what in THIS question shows the mechanism>\"\n"
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
        "problem_class": parsed.get("problem_class", "") if parsed else "",
        "mechanism": parsed.get("mechanism", "") if parsed else "",
        "check_procedure": parsed.get("check_procedure", "") if parsed else "",
        "trigger": parsed.get("trigger", "") if parsed else "",
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
                  f"mechanism={res['mechanism'][:60]}")

    # Stable order by task_id for reproducibility.
    results.sort(key=lambda r: r["task_id"])
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- aggregate raw mechanism distribution (for granularity review) ----
    by_mechanism = defaultdict(list)
    for r in results:
        key = _norm(r["mechanism"]) if r["mechanism"] else "(unparsed)"
        by_mechanism[key].append(r)

    print("\n" + "=" * 80)
    print(f"L0 distillation {DISTILL_VERSION} — {args.family} mechanism distribution")
    print("=" * 80)
    print(f"{'mechanism':<48}{'n':>4}   example task_ids")
    for mech, rs in sorted(by_mechanism.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        tids = ", ".join(r["task_id"] for r in rs[:6])
        print(f"{mech[:48]:<48}{len(rs):>4}   {tids}")

    agg = {
        "distill_version": DISTILL_VERSION,
        "family": args.family,
        "model": entry["model"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_total": len(results),
        "n_parsed": sum(1 for r in results if r["parse_ok"]),
        "distribution": {
            mech: {
                "count": len(rs),
                "problem_class": sorted({r["problem_class"] for r in rs if r["problem_class"]}),
                "task_ids": [r["task_id"] for r in rs],
            }
            for mech, rs in sorted(by_mechanism.items(),
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