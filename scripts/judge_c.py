#!/usr/bin/env python3
"""judge_c.py — the "recovery" judge (judge-C, docs/EVALUATOR_FINAL_DESIGN.md sec.3).

For every switch edge (consecutive non-None freeze-key change, `freeze_switches`),
judge-C reviews the CRITIC'S FEEDBACK about the OLD round (not the NEW round). It asks
one question: is the defect the critic alleges actually present in the OLD
answer/reasoning, and is it sufficient to overturn the OLD answer?

  input   = QUESTION text + critic suspicion + critic check (one round of feedback)
            + the OLD round's answer + reasoning tail (the object of the feedback).
            NO new round, NO gold, NO answer key.
  output  = verdict in { OVER | WARRANTED | UNSURE } + a <=40-char verbatim fragment
            copied from the OLD round (required for OVER and WARRANTED).
  glue    = OVER / WARRANTED must back-link verbatim; a judgement that cannot cite
            degrades to UNSURE.

N=2 order swap: each edge is judged twice; the second card presents the suspicion and
check in swapped order. A non-UNSURE verdict is taken only if BOTH runs agree.

Final per-edge verdict (aggregate of the two runs):
    OVER         both runs OVER
    WARRANTED    both runs WARRANTED
    UNSURE       anything else (mismatch / citation fail / mixed / unparsable)

Edge labels (for LR estimation / report only, NOT shown to the judge):
    fix   = W->R (wrong OLD -> correct NEW)
    break = R->W (correct OLD -> wrong NEW)
    other = W->W' or R->R' (non-decisive)
from sidecar-v2 per-round correctness (is_correct_t3_sidecar_v2.json).

Usage:
  python3 judge_c.py --moves-only              # dump full edge manifest, no judge
  python3 judge_c.py --split dev --limit 3     # smoke: first 3 dev edges
  python3 judge_c.py --split all               # full 1201 edges x N=2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import qcut_run as q                       # noqa: E402  (shared frozen helpers)
from src.agent import HuggingFaceAgent     # noqa: E402
from src import config                     # noqa: E402
from src.stage_b_evaluator import _usage_tokens  # noqa: E402

_CUT_MAX_TOKENS = int(os.getenv("RSI_CUT_MAX_TOKENS", "16384"))
_RSI_JUDGE_CONTENT_MARGIN = int(os.getenv("RSI_JUDGE_CONTENT_MARGIN", "1024"))


# Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK. The
# openai client defaults to httpx trust_env=True and would otherwise route every
# judge call through the dead local proxy (=> "Connection error."). Mirrors
# run_feedback_loop._force_no_proxy; runs once before any client is built.
def _force_no_proxy() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


# ------------------------------------------------------------------ edge manifest
def freeze_switches(keys):
    """(from_r, to_r) edges whose frozen key changes between consecutive non-None keys.
    Mirrors recompute_evaluator_offline.freeze_switches exactly."""
    out = []
    for i in range(1, len(keys)):
        if keys[i - 1] is None or keys[i] is None:
            continue
        if keys[i - 1] != keys[i]:
            out.append((i - 1, i))
    return out


def critic_items(rec_round: dict) -> list:
    """critic_direction items (suspicion + check + archetype) stored on the round that
    PRODUCED the feedback. Each round i's critic_direction reviews round i-1's answer."""
    out = []
    for it in rec_round.get("critic_direction") or []:
        sus = (it.get("suspicion") or "").strip()
        chk = (it.get("check") or "").strip()
        if sus or chk:
            out.append({
                "archetype": it.get("archetype_name") or it.get("archetype_id") or "(none)",
                "suspicion": sus,
                "check": chk,
            })
    return out


def edge_label(cfrom: bool, cto: bool) -> str:
    if (not cfrom) and cto:
        return "fix"
    if cfrom and (not cto):
        return "break"
    return "other"


def build_manifest(trans_by_tid: dict, side_c3: dict, loop_by_tid: dict):
    """Yield one dict per switch edge (all 1201), with question + critic feedback +
    OLD round text + sidecar label, in stable (task_id, from_r, to_r) order."""
    for tid in sorted(loop_by_tid):
        loop_rec = loop_by_tid[tid]
        trans_rec = trans_by_tid.get(tid)
        if trans_rec is None:
            continue
        sl = side_c3.get(tid, [])
        gold = loop_rec.get("gold_answer", "") or trans_rec.get("gold", "")
        keys = q.freeze_round_keys(gold, loop_rec)

        # rounds aligned 1:1 between loop and transitions (same count/order)
        loop_rounds = loop_rec.get("rounds", [])
        trans_rounds = trans_rec.get("rounds", [])

        for (from_r, to_r) in freeze_switches(keys):
            cfrom = q.sidecar_correct(sl, from_r)
            cto = q.sidecar_correct(sl, to_r)

            # OLD round text (the object of the critic's feedback)
            old_answer = ""
            old_reasoning = ""
            if 0 <= from_r < len(loop_rounds):
                old_answer = loop_rounds[from_r].get("final_answer", "") or ""
                old_reasoning = loop_rounds[from_r].get("reasoning_content", "") or ""
            if not old_answer and 0 <= from_r < len(trans_rounds):
                old_answer = trans_rounds[from_r].get("ans", "") or ""
            if not old_reasoning and 0 <= from_r < len(trans_rounds):
                old_reasoning = trans_rounds[from_r].get("reasoning", "") or ""

            # critic feedback reviewing round from_r is stored on round to_r
            items = []
            if 0 <= to_r < len(loop_rounds):
                items = critic_items(loop_rounds[to_r])
            if not items and 0 <= to_r < len(trans_rounds):
                items = critic_items(trans_rounds[to_r])

            yield {
                "task_id": tid,
                "from_r": from_r,
                "to_r": to_r,
                "label": edge_label(cfrom, cto),
                "old_answer": old_answer,
                "old_reasoning": old_reasoning,
                "critic": items,
            }


# ------------------------------------------------------------------ judge card
def _render_critic(items: list, swap: bool) -> str:
    """One feedback block: suspicion + check (order depends on swap) for each item."""
    blocks = []
    for i, it in enumerate(items):
        sus = it["suspicion"] or "(none)"
        chk = it["check"] or "(none)"
        if swap:
            a_lbl, a_txt = "CHECK (how the critic says to verify it):", chk
            b_lbl, b_txt = "SUSPICION (what the critic asserts is wrong):", sus
        else:
            a_lbl, a_txt = "SUSPICION (what the critic asserts is wrong):", sus
            b_lbl, b_txt = "CHECK (how the critic says to verify it):", chk
        tag = "" if len(items) == 1 else f"[{i + 1}] "
        blocks.append(f"{tag}{a_lbl}\n  {a_txt}\n{tag}{b_lbl}\n  {b_txt}")
    return "\n".join(blocks)


def build_card(move: dict, question: str, char_cap: int, swap: bool) -> str:
    old_answer = (move["old_answer"] or "").strip() or "(none)"
    old_reasoning, _covered = q._cap(move["old_reasoning"] or "", char_cap)
    critic_block = _render_critic(move["critic"], swap)
    return "\n".join([
        "QUESTION:",
        question,
        "",
        "A reviewer (critic) examined a solver's answer to the above question and",
        "raised a suspicion about a defect, with a verification instruction. Below are",
        "the critic's feedback and the SOLVER'S OLD ANSWER + REASONING (the object of",
        "that feedback). The solver's NEW (post-feedback) answer is NOT shown.",
        "",
        critic_block,
        "",
        "OLD ANSWER:",
        old_answer,
        "",
        "OLD REASONING (may be truncated; head and tail preserved):",
        (old_reasoning or "(none)"),
        "",
        "Your task: decide whether the critic's alleged defect is ACTUALLY PRESENT in the",
        "OLD answer/reasoning AND sufficient to overturn the OLD answer.",
        "",
        "  OVER       -> the alleged defect is absent from the OLD answer/reasoning; OR it",
        "                is present but does NOT actually change the final answer; OR it",
        "                concerns something the question never required.",
        "  WARRANTED  -> the defect IS present in the OLD answer/reasoning AND it is",
        "                enough to make the OLD answer wrong / untenable.",
        "  UNSURE     -> cannot determine from the material shown.",
        "",
        "ANCHORING RULE (decisive):",
        "  - Copy the fragment of the OLD answer/reasoning (at most 40 characters,",
        "    verbatim, character-for-character) that your judgment rests on.",
        "  - WARRANTED: cite the OLD text that contains the defect.",
        "  - OVER: cite the OLD text that shows the accusation is absent / harmless / off-topic.",
        "  - If you cannot cite the exact OLD text, output UNSURE. Never paraphrase.",
        "",
        "Output exactly:",
        "  verdict: OVER | WARRANTED | UNSURE",
        "  fragment: <verbatim <=40 chars from OLD; empty if UNSURE>",
        "  because: <one sentence>",
    ])


# ------------------------------------------------------------------ parse / verify
def parse_verdict(text: str) -> dict:
    text = text or ""
    v = re.search(r"verdict\s*:\s*(OVER|WARRANTED|UNSURE)", text, re.IGNORECASE)
    fr = re.search(r"fragment\s*:\s*([^\n]*)", text, re.IGNORECASE)
    bc = re.search(r"because\s*:\s*([^\n]*)", text, re.IGNORECASE)
    return {
        "verdict": (v.group(1).upper() if v else None),
        "fragment": (q._clean_frag(fr.group(1)) if fr else None),
        "because": (bc.group(1).strip() if bc else None),
    }


# Greek + LaTeX command map used ONLY for cite matching (kept local so qcut_run's
# norm_math is untouched). Verifier fix 2026-11-06.
_GREEK_CITE = {
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ", "\\epsilon": "ε",
    "\\theta": "θ", "\\mu": "μ", "\\nu": "ν", "\\pi": "π", "\\rho": "ρ",
    "\\sigma": "σ", "\\tau": "τ", "\\phi": "φ", "\\psi": "ψ", "\\omega": "ω",
    "\\lambda": "λ", "\\eta": "η", "\\kappa": "κ", "\\zeta": "ζ", "\\xi": "ξ",
}


def _norm_cite(s: str) -> str:
    """v2 cite normalization: drop LaTeX horizontal-space tokens, map Greek / frac-style
    commands to unicode, then remove ALL whitespace so a verbatim fragment survives
    notation / spacing drift. (Verifier fix 2026-11-06.)"""
    s = s or ""
    for sp in ("\\quad", "\\qquad", "\\,", "\\;", "\\!", "\\:", "\\ "):
        s = s.replace(sp, "")
    for k, v in _GREEK_CITE.items():
        s = s.replace(k, v)
    for cmd in ("\\cos", "\\sin", "\\tan", "\\frac", "\\mathrm", "\\left",
                "\\right", "\\boxed", "\\displaystyle", "\\dot", "\\log",
                "\\ln", "\\exp"):
        s = s.replace(cmd, cmd[1:])
    s = s.replace("\\cdot", "·")
    return re.sub(r"\s+", "", s)


def verify_cite(verdict: str, fragment: str, old_text: str):
    """v2 (2026-11-06): verbatim match passes; length is NOT a veto (only reported as
    cite_too_long via a wide 400-char cap against whole-block paste). Returns
    (cited_ok, cite_too_long, reason). UNSURE needs no fragment."""
    if verdict == "UNSURE":
        return (True, False, "unsure-no-cite")
    if verdict not in ("OVER", "WARRANTED"):
        return (False, False, "bad-verdict")
    clean = q._clean_frag(fragment) or ""
    if not clean:
        return (False, False, "empty-fragment")
    too_long = len(clean) > 400
    hit = _norm_cite(clean) in _norm_cite(old_text) if clean else False
    return (hit, too_long, "hit" if hit else "no-match")


def run_state(verdict: str, cited_ok: bool) -> str:
    if verdict == "UNSURE":
        return "UNSURE"
    if verdict in ("OVER", "WARRANTED"):
        return verdict if cited_ok else "UNSURE"
    return "UNSURE"


def aggregate(s1: str, s2: str) -> str:
    if s1 == "OVER" and s2 == "OVER":
        return "OVER"
    if s1 == "WARRANTED" and s2 == "WARRANTED":
        return "WARRANTED"
    return "UNSURE"


def reverify_row(r):
    """Re-derive cited_ok/state/final from the stored judge raw output under the v2
    verifier. Judge raw fields (verdict/fragment/because/raw) are NOT touched — only the
    post-hoc verifier decision changes, so the rule is identical for already-run and
    to-be-run edges."""
    old_text = (r.get("old_answer") or "") + "\n" + (r.get("old_reasoning") or "")
    for c in r.get("calls", []):
        c["verify_version"] = 2
        if c.get("error") is not None:
            c["cited_ok"] = False
            c["cite_too_long"] = False
            c["cite_reason"] = "error"
            c["state"] = "UNSURE"
            continue
        v = c.get("verdict")
        ok, too_long, reason = verify_cite(v, c.get("fragment"), old_text)
        c["cited_ok"] = ok
        c["cite_too_long"] = too_long
        c["cite_reason"] = reason
        c["state"] = run_state(v, ok)
    st = [c.get("state") for c in r.get("calls", [])]
    r["final"] = aggregate(st[0] if len(st) >= 1 else "UNSURE",
                           st[1] if len(st) >= 2 else "UNSURE")
    r["verify_version"] = 2
    return r


# ------------------------------------------------------------------ judge call
def call_judge(agent: HuggingFaceAgent, card: str) -> dict:
    try:
        content, _reasoning, _usage = agent._call_llm_text(
            [{"role": "user", "content": card}], max_tokens=_CUT_MAX_TOKENS)
    except Exception as e:
        return {"raw": None, "error": str(e), "tokens": (0, 0, 0)}
    return {"raw": content, "error": None, "tokens": _usage_tokens(_usage)}


# ------------------------------------------------------------------ report
def report(rows, split):
    n = len(rows)
    if n == 0:
        print(f"[{split}] no switch edges; nothing to report.")
        return
    vc = Counter(r["final"] for r in rows)
    lc = Counter(r["label"] for r in rows)
    dev_edges = [r for r in rows if q._is_dev(r["task_id"]) and r["label"] != "other"]
    n_dev = len(dev_edges)
    n_correct = 0
    for r in dev_edges:
        if r["final"] == "OVER" and r["label"] == "break":
            n_correct += 1
        if r["final"] == "WARRANTED" and r["label"] == "fix":
            n_correct += 1

    print("=" * 74)
    print(f"judge-C  split={split}  switch edges={n}")
    print("=" * 74)
    print(f"  label dist = {dict(lc)}")
    print(f"  final verdict dist = {dict(vc)}")
    print(f"    OVER      = {vc.get('OVER', 0)}")
    print(f"    WARRANTED = {vc.get('WARRANTED', 0)}")
    print(f"    UNSURE    = {vc.get('UNSURE', 0)}")
    print()
    if n_dev:
        e1 = n_correct / n_dev
        print(f"  [E1] dev decisive accuracy = {e1:.3f} ({n_correct}/{n_dev})  baseline 0.5")
    else:
        print("  [E1] no dev decisive edges in this split")


# ---------------------------------------------------------------------- main
def main():
    _force_no_proxy()
    ap = argparse.ArgumentParser()
    ap.add_argument("--transitions", default=str(ROOT / "experiments/hle400/t3/c3_transitions.jsonl"))
    ap.add_argument("--loop", default=str(ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    ap.add_argument("--out-dir", default=str(ROOT / "experiments/hle400/t3"))
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--char-cap", type=int, default=6000, help="char budget for OLD reasoning (head 60pct + tail 40pct)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="smoke: first N edges in the split")
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--moves-only", action="store_true", help="emit manifest only, no judge calls")
    ap.add_argument("--result", default="judge_c_verdicts.jsonl", help="verdict output filename (in --out-dir)")
    ap.add_argument("--reverify-only", action="store_true",
                    help="re-run v2 verifier over existing verdict file; no judge calls")
    args = ap.parse_args()

    if args.reverify_only:
        out_dir0 = Path(args.out_dir)
        out_dir0.mkdir(parents=True, exist_ok=True)
        rp = out_dir0 / args.result
        rows = []
        if rp.exists():
            for line in rp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        rows = [reverify_row(r) for r in rows]
        rows.sort(key=lambda r: (r.get("task_id", ""), r.get("from_r", -1),
                                  r.get("to_r", -1)))
        with rp.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[reverify-only] v2 verifier applied to {len(rows)} edges "
              "(judge raw output untouched; verifier rule changed only)")
        return

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    side_c3 = side["arms"]["C3"]
    trans_by_tid = q.load_jsonl(Path(args.transitions))
    loop_by_tid = q.load_jsonl(Path(args.loop))
    q_by_tid = {tid: rec.get("question", "") for tid, rec in trans_by_tid.items()}

    all_rows = list(build_manifest(trans_by_tid, side_c3, loop_by_tid))
    rows = [r for r in all_rows
            if (args.split == "all" or q._is_dev(r["task_id"]) == (args.split == "dev"))]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.moves_only:
        dev_rows = [r for r in all_rows if q._is_dev(r["task_id"])]
        test_rows = [r for r in all_rows if not q._is_dev(r["task_id"])]
        (out_dir / "judge_c_dev_moves.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dev_rows), encoding="utf-8")
        (out_dir / "judge_c_test_moves.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in test_rows), encoding="utf-8")
        n_empty_critic = sum(1 for r in all_rows if not r["critic"])
        n_empty_reason = sum(1 for r in all_rows if not (r["old_reasoning"] or "").strip())
        print(f"[moves-only] total switch edges = {len(all_rows)}  dev={len(dev_rows)}  test={len(test_rows)}")
        print(f"[moves-only] empty critic feedback = {n_empty_critic}")
        print(f"[moves-only] empty old reasoning = {n_empty_reason}")
        lc = Counter(r["label"] for r in all_rows)
        print(f"[moves-only] label dist = {dict(lc)}")
        ci = Counter(len(r["critic"]) for r in all_rows)
        print(f"[moves-only] critic items per edge dist = {dict(ci)}")
        return

    entry = config.PHASE1_MODELS[args.model]
    result_path = out_dir / args.result
    # done = only edges whose BOTH judge calls really reached the API (error is None).
    # A 429 edge has a row in result_path but error != None, so it must be re-run, not
    # skipped: key-in-file alone is NOT "done". ("done" is about the judge CALL, not
    # about verdict parse; a success-but-unparsable call is still a completed call.)
    done = {}
    if result_path.exists():
        for line in result_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rr = json.loads(line)
            except Exception:
                continue
            calls = rr.get("calls") or []
            real = [c for c in calls if c.get("error") is None]
            if len(real) >= 2:
                done[(rr.get("task_id"), rr.get("from_r"), rr.get("to_r"))] = rr

    pending = [r for r in rows
               if (r["task_id"], r["from_r"], r["to_r"]) not in done]
    if args.limit:
        pending = pending[:args.limit]

    _tls = threading.local()

    def make_agent():
        return HuggingFaceAgent(
            model=entry["model"], token=entry.get("api_key"),
            base_url=entry["base_url"], max_tokens=1024, temperature=0.0,
            seed=None, enable_thinking=entry.get("enable_thinking"),
            thinking_budget=entry.get("thinking_budget"),
            content_margin=_RSI_JUDGE_CONTENT_MARGIN)

    def run_one(r):
        tid = r["task_id"]
        ag = getattr(_tls, "agent", None)
        if ag is None:
            ag = make_agent()
            _tls.agent = ag
        question = q_by_tid.get(tid, "")
        old_text = (r["old_answer"] or "") + "\n" + (r["old_reasoning"] or "")
        out = dict(r)
        out["calls"] = []
        for swap in (False, True):
            card = build_card(r, question, args.char_cap, swap)
            res = call_judge(ag, card)
            rec = {"swap": swap}
            if res["error"] is not None:
                rec.update({"verdict": None, "fragment": None, "because": None,
                            "state": "UNSURE", "cited_ok": False, "error": res["error"],
                            "cite_too_long": False, "cite_reason": "error",
                            "verify_version": 2})
            else:
                p = parse_verdict(res["raw"])
                cited_ok, too_long, reason = verify_cite(p["verdict"], p["fragment"], old_text)
                rec.update(p)
                rec["state"] = run_state(p["verdict"], cited_ok)
                rec["cited_ok"] = cited_ok
                rec["cite_too_long"] = too_long
                rec["cite_reason"] = reason
                rec["error"] = None
                rec["verify_version"] = 2
            rec["raw"] = res["raw"]
            rec["pt"], rec["ct"], rec["rt"] = res["tokens"]
            out["calls"].append(rec)
        out["final"] = aggregate(out["calls"][0]["state"], out["calls"][1]["state"])
        return out

    rows_out = list(done.values())
    total_pending = len(pending)
    completed = [0]
    new_rows = []
    write_lock = threading.Lock()

    def _emit(row):
        # Incremental checkpoint: append + flush every completed edge so progress is
        # observable in the log ([progress]) and output file (wc -l), not one final write.
        line = json.dumps(row, ensure_ascii=False) + "\n"
        with write_lock:
            with result_path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
            completed[0] += 1
            new_rows.append(row)
            print(f"[progress] {completed[0]}/{total_pending}  "
                  f"{row.get('task_id')} from_r={row.get('from_r')}", flush=True)

    if pending:
        worker = args.concurrency or int(os.getenv("RSI_EVAL_CONCURRENCY", "4"))
        print(f"[start] pending={total_pending} worker={worker}", flush=True)
        if worker <= 1 or len(pending) <= 1:
            for r in pending:
                _emit(run_one(r))
        else:
            with ThreadPoolExecutor(max_workers=worker) as ex:
                futs = [ex.submit(run_one, r) for r in pending]
                for fut in as_completed(futs):
                    _emit(fut.result())
        rows_out.extend(new_rows)

    uniq = {(r["task_id"], r["from_r"], r["to_r"]): r for r in rows_out}
    with result_path.open("w", encoding="utf-8") as f:
        for k in sorted(uniq):
            f.write(json.dumps(uniq[k], ensure_ascii=False) + "\n")

    report(list(uniq.values()), args.split)


if __name__ == "__main__":
    main()