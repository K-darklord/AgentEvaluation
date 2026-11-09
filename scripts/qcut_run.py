#!/usr/bin/env python3
"""qcut_run.py — Q-CUT three-bucket evaluator (question-visible, cited, replacement).

Margin-layered replacement: instead of a subtractive cut, the judge classifies each
non-mode candidate's most-recent ENTRY move against the MODE's entry move on three
tiers -- better / equal / worse -- with a verbatim line-anchored quote as evidence.

  margin = V0 - V1  (V0 = top votes, V1 = runner-up votes, over FROZEN keys).
  margin >= 3  -> mode wins directly (no judge).
  margin <  3  -> judge the competitive surface C = { a : votes(a) >= V1 } (non-mode).
      better / worse must back-link verbatim (<=40 chars) into the cited numbered line
      of the REFERENCE (better) or CANDIDATE (worse) reasoning; evidence-fail -> equal.

  R1  better bucket B = { a : bucket(a) == better }.
  R2  trigger(|B|, V0):  gte -> |B| >= V0 ;  gt -> |B| > V0.
  R3  if trigger and B non-empty -> pick = argmax over B (votes, then strength).
      else                       -> pick = mode.

The judge is called ONCE per move; gte vs gt is compared at report time (no re-calls).
Scoring uses the SAME sidecar-v2 per-round rules as every other arm
(is_correct_t3_sidecar_v2.json), NOT judge-vs-gold exact match.

Usage:
  python3 scripts/qcut_run.py --moves-only --limit 3   # manifest only, no judge
  python3 scripts/qcut_run.py --split dev  --limit 3   # smoke: 3 even tasks
  python3 scripts/qcut_run.py --split dev              # full dev  (even)
  python3 scripts/qcut_run.py --split test             # full test (odd)
  python3 scripts/qcut_run.py --split all              # full, judge once (if unmade)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import comb
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

from src.agent import HuggingFaceAgent          # noqa: E402
from src import config                          # noqa: E402
from src.stage_b_evaluator import _usage_tokens  # noqa: E402
from src.score_hle_arms import _key  # noqa: E402

_CUT_MAX_TOKENS = int(os.getenv("RSI_CUT_MAX_TOKENS", "16384"))
_RSI_JUDGE_CONTENT_MARGIN = int(os.getenv("RSI_JUDGE_CONTENT_MARGIN", "1024"))


# ------------------------------------------------------------------ helpers
def _norm(s: str) -> str:
    return " ".join((s or "").split())


_GREEK = {
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ", "\\epsilon": "ε",
    "\\theta": "θ", "\\mu": "μ", "\\nu": "ν", "\\pi": "π", "\\rho": "ρ",
    "\\sigma": "σ", "\\tau": "τ", "\\phi": "φ", "\\psi": "ψ", "\\omega": "ω",
    "\\lambda": "λ", "\\eta": "η", "\\kappa": "κ", "\\zeta": "ζ", "\\xi": "ξ",
}


def norm_math(s: str) -> str:
    """Whitespace-normalize then map common LaTeX to Unicode symbols so a short
    fragment survives surface notation drift (\\theta vs θ) with no semantic
    relaxation. Applied to BOTH fragment and anchor."""
    s = _norm(s)
    for k, v in _GREEK.items():
        s = s.replace(k, v)
    for cmd in ("\\cos", "\\sin", "\\tan", "\\frac", "\\mathrm", "\\left",
                "\\right", "\\boxed", "\\displaystyle", "\\dot", "\\log",
                "\\ln", "\\exp"):
        s = s.replace(cmd, cmd[1:])
    s = s.replace("\\cdot", "·")
    return s


def _clean_frag(s):
    """Strip decoration (quotes, angle-brackets, backticks) around a fragment, never
    truncate or normalize content."""
    if not s:
        return None
    s = s.strip().strip('"“”\'`').strip().strip('<>').strip().strip('"“”\'`').strip()
    return s or None


def _cap(s: str, cap: int) -> tuple[str, bool]:
    """head 60% + tail 40% when over cap; returns (text, fully_covered)."""
    if len(s) <= cap:
        return s, True
    head = int(cap * 0.6)
    tail = cap - head
    return s[:head] + " …[truncated]… " + s[-tail:], False


def _task_num(tid: str) -> int:
    m = re.search(r"(\d+)$", tid)
    return int(m.group(1)) if m else 0


def _is_dev(tid: str) -> bool:
    return _task_num(tid) % 2 == 0


def load_jsonl(path: Path) -> dict:
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


def sidecar_correct(side_list, i: int) -> bool:
    if 0 <= i < len(side_list):
        return bool(side_list[i]["c"])
    return False


def freeze_round_keys(gold: str, loop_rec: dict) -> list:
    """Per-round frozen answer identity — exactly score_hle_arms `_key`
    (imported from score_hle_arms). A truncated int/letter round still
    yields a CoT-recovered key, so it VOTES; the frozen scorer only marks the winning
    round wrong afterwards (two-stage rule, issue-1 root cause = key space)."""
    meta = {"gold": gold}
    return [_key(meta, r) for r in loop_rec.get("rounds", [])]


def freeze_votes(keys: list):
    """(votes, latest) over frozen keys, skipping None. Mirrors `_mode_idx` exactly
    (a truncated int/letter round votes through its CoT-recovered key)."""
    votes: dict = {}
    latest: dict = {}
    for i, k in enumerate(keys):
        if k is None:
            continue
        votes[k] = votes.get(k, 0) + 1
        latest[k] = i
    return votes, latest


def last_key_correct(keys: list, side_list: list, k) -> bool:
    """Correctness under the frozen two-stage rule: the key's LAST occurrence round
    decides via sidecar v2. A truncation as the last occurrence is wrong even if an
    earlier same-key round was correct (issue 3 / 154 alignment)."""
    for i in range(len(keys) - 1, -1, -1):
        if keys[i] == k:
            return sidecar_correct(side_list, i)
    return False


def entry_moves(rec: dict, keys: list) -> dict:
    """frozen-key -> (from_r, to_r, transition) of its MOST-RECENT entry move.

    An entry move for a candidate is a transition whose `to_r`-round frozen key equals
    it (NOT the transition's display string `to`, which can diverge from the frozen key
    on CoT-recovered letter rounds). Most-recent = largest to_r; a round-0-only
    candidate has no entry move and is omitted (round-0 structural protection)."""
    entry: dict = {}
    for t in rec.get("transitions", []):
        to_r = t.get("to_r")
        if to_r is None or not (0 <= to_r < len(keys)):
            continue
        k = keys[to_r]
        if k is None:
            continue
        if k not in entry or to_r > entry[k][1]:
            entry[k] = (t.get("from_r"), to_r, t)
    return entry


def check_for(rec: dict, t: dict, to_r: int) -> str | None:
    """critic_direction[0].check for the to_r-round record (off-by-one: stored at
    round to_r, reviewing the to_r-1 answer). Prefer the transition's in-band
    critic_direction, fall back to rounds[to_r]."""
    if t.get("critic_direction"):
        for item in t["critic_direction"]:
            if item.get("check"):
                return item["check"]
    rnds = rec.get("rounds", [])
    if 0 <= to_r < len(rnds):
        cd = rnds[to_r].get("critic_direction")
        if cd:
            for item in cd:
                if item.get("check"):
                    return item["check"]
    return None


def iter_tasks(recs_by_tid: dict, side_c3: dict, loop_by_tid: dict):
    """Yield (tid, rec, keys, votes, latest, mode, V0, V1, margin) for every
    multi-answer task (>=2 distinct frozen keys), in sorted order. This is the FULL
    task set used by decide/report; the judge only sees the margin<3 subset (see
    build_manifest). Vote/mode computed over FROZEN keys (issue 1), matching
    `_mode_idx`."""
    for tid in sorted(recs_by_tid):
        rec = recs_by_tid[tid]
        lrec = loop_by_tid.get(tid)
        if lrec is None:
            continue
        gold = lrec.get("gold_answer", "") or rec.get("gold", "")
        keys = freeze_round_keys(gold, lrec)
        votes, latest = freeze_votes(keys)
        cands = list(votes.keys())
        if len(cands) < 2:
            continue
        counts = sorted(((votes.get(k, 0), k) for k in cands),
                        key=lambda x: (x[0], latest.get(x[1], -1)), reverse=True)
        mode = max(cands, key=lambda k: (votes.get(k, 0), latest.get(k, -1)))
        V0 = counts[0][0]
        V1 = counts[1][0] if len(counts) >= 2 else 0
        yield tid, rec, keys, votes, latest, mode, V0, V1, V0 - V1


def build_manifest(recs_by_tid: dict, side_c3: dict, loop_by_tid: dict):
    """Yield (tid, rec, keys, move) for every NON-MODE candidate entry move of every
    margin<3 task (margin>=3 -> mode wins directly, no judge). Each move carries the
    MODE's entry transition as the reference; the judge classifies the candidate's
    derivation as better / equal / worse relative to the mode. Only the competitive
    surface C = { non-mode a : votes(a) >= V1 } is judged (below-runner candidates can't
    flip a top-2 race). Vote/mode over FROZEN keys (issue 1). A round-0-only mode has
    no entry move -> no reference -> task skipped (mode keeps)."""
    for tid, rec, keys, votes, latest, mode, V0, V1, margin in \
            iter_tasks(recs_by_tid, side_c3, loop_by_tid):
        if margin >= 3:
            continue
        em = entry_moves(rec, keys)

        def _reasoning_of(t, to_r):
            r = t.get("reasoning") or ""
            if not r and 0 <= to_r < len(rec.get("rounds", [])):
                r = rec["rounds"][to_r].get("reasoning") or ""
            return r

        def _entry_of(k):
            e = em.get(k)
            if e is None:
                return None
            f_r, t_r, t = e
            return {
                "from_r": f_r,
                "to_r": t_r,
                "old": t.get("from"),
                "new": t.get("to"),
                "reasoning": _reasoning_of(t, t_r),
            }
        mode_entry = _entry_of(mode)
        if mode_entry is None:
            continue
        for k, (from_r, to_r, t) in em.items():
            if k == mode:
                continue
            if votes.get(k, 0) < V1:
                continue
            yield tid, rec, keys, {
                "task_id": tid,
                "candidate": k,
                "mode": mode,
                "is_mode": False,
                "from_r": from_r,
                "to_r": to_r,
                "old": t.get("from"),
                "new": t.get("to"),
                "check": check_for(rec, t, to_r),
                "reasoning": _reasoning_of(t, to_r),
                "c_a": votes.get(k, 0),
                "margin": margin,
                "V0": V0,
                "mode_entry": mode_entry,
            }


# --------------------------------------------------------------------- judge
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
_DIMS = ("disconnection", "contradiction", "error")


def number_lines(text: str) -> list[str]:
    """Split reasoning into small, citable spans: paragraphs on blank lines first,
    then over-long paragraphs on sentence boundaries. Returns the ordered lines."""
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    lines: list[str] = []
    for p in paras:
        if len(p) <= 500:
            lines.append(p)
        else:
            for seg in _SENT_SPLIT.split(p):
                seg = seg.strip()
                if seg:
                    lines.append(seg)
    return lines


def display_lines(lines: list[str], char_cap: int) -> tuple[str, bool]:
    """Render numbered [L001].. lines, truncating head+tail when over budget. Line
    ids stay stable against the FULL line list. Returns (display_text, covered)."""
    head_budget = int(char_cap * 0.6)
    tail_budget = char_cap - head_budget
    head: list[str] = []
    used = 0
    for i, ln in enumerate(lines):
        tag = f"[L{i + 1:03d}] {ln}"
        if used + len(tag) + 1 > head_budget:
            break
        head.append(tag)
        used += len(tag) + 1
    tail: list[str] = []
    tused = 0
    for j in range(len(lines) - 1, len(head) - 1, -1):
        tag = f"[L{j + 1:03d}] {lines[j]}"
        if tused + len(tag) + 1 > tail_budget:
            break
        tail.append(tag)
        tused += len(tag) + 1
    tail.reverse()
    omitted = len(lines) - len(head) - len(tail)
    if omitted <= 0:
        return "\n".join(head), True
    return "\n".join(head + [f"  [... {omitted} lines omitted ...]"] + tail), False


def _render_transition(label, from_r, to_r, old, new, check, reasoning, char_cap):
    lines = number_lines(reasoning)
    disp, covered = display_lines(lines, char_cap)
    out = [
        f"{label} TRANSITION (round {from_r} -> {to_r}):",
        f"  previous answer (round {from_r}): {old}",
        f"  new answer (round {to_r}):        {new}",
    ]
    if check:
        out.append(f"  reviewer asked to check: {check}")
    out.append("  reasoning (numbered [Lxxx] lines):")
    out.append(disp)
    return "\n".join(out), covered


def build_card(move: dict, question: str, char_cap: int) -> tuple[str, bool]:
    me = move["mode_entry"]
    cand_block, cand_covered = _render_transition(
        "CANDIDATE", move["from_r"], move["to_r"], move["old"], move["new"],
        move["check"], move["reasoning"], char_cap)
    ref_block, _ = _render_transition(
        "REFERENCE (mode)", me["from_r"], me["to_r"], me["old"], me["new"],
        None, me["reasoning"], char_cap)
    card = [
        "QUESTION:",
        question,
        "",
        "You are shown TWO self-correction transitions produced by the SAME solver on",
        "this question. Compare the CANDIDATE transition's REASONING PROCESS against the",
        "REFERENCE (mode) transition's. Do NOT solve the problem. Do NOT judge whether an",
        "answer is right or wrong -- judge whether the derivation that produced the change",
        "is stronger or weaker.",
        "",
        cand_block,
        "",
        ref_block,
        "",
        "Weigh three dimensions in your head -- do NOT print any score for them:",
        "  disconnection  the reasoning never actually reaches the NEW answer (a",
        "                 justification break); it stops short or hand-waves OLD->NEW",
        "  contradiction  the reasoning contradicts itself, or the derived conclusion",
        "                 disagrees with the NEW answer",
        "  error          a substantive mistake located in the derivation (computation,",
        "                 sign, wrong mechanism)",
        "",
        "Then decide: relative to the REFERENCE (mode) transition, is the CANDIDATE",
        "transition's reasoning BETTER, EQUAL, or WORSE?",
        "  better   the candidate's derivation is clearly stronger than the reference's",
        "  equal    the two are of comparable strength (neither clearly better)",
        "  worse    the candidate's derivation is clearly weaker than the reference's",
        "",
        "EVIDENCE RULE (decisive):",
        "  better -> cite the line [Lxxx] in the REFERENCE (mode) reasoning where the",
        "            reference's flaw sits, and copy its wording VERBATIM (<=40 chars).",
        "  worse  -> cite the line [Lxxx] in the CANDIDATE reasoning where the",
        "            candidate's flaw sits, and copy its wording VERBATIM (<=40 chars).",
        "  equal  -> line: none, quote: empty.",
        "  The quote must appear verbatim inside the numbered line you cite; otherwise,",
        "  say equal.",
        "",
        "Output exactly:",
        "  relation: better | equal | worse",
        "  dimension: disconnection | contradiction | error | none",
        "  line: <[Lxxx] from REFERENCE (if better) or CANDIDATE (if worse); else none>",
        "  quote: <verbatim from that one line, <=40 chars; else empty>",
        "  because: <one sentence>",
        "  strength: <integer 0..5; 0=equal/unsure, 1=weak, 5=very strong confidence in the relation>",
    ]
    return "\n".join(card), cand_covered


def parse_pairwise(text: str) -> dict:
    text = text or ""
    rel = re.search(r"relation\s*:\s*(better|equal|worse)", text, re.IGNORECASE)
    dim = re.search(r"dimension\s*:\s*(disconnection|contradiction|error|none)", text, re.IGNORECASE)
    ln = re.search(r"line\s*:\s*([^\n]*)", text, re.IGNORECASE)
    qt = re.search(r"quote\s*:\s*([^\n]*)", text, re.IGNORECASE)
    bc = re.search(r"because\s*:\s*([^\n]*)", text, re.IGNORECASE)
    st = re.search(r"strength\s*:\s*(\d+)", text, re.IGNORECASE)
    return {
        "relation": (rel.group(1).lower() if rel else None),
        "dimension": (dim.group(1).lower() if dim else None),
        "line": (ln.group(1).strip() if ln else None),
        "quote": (_clean_frag(qt.group(1)) if qt else None),
        "because": (bc.group(1).strip() if bc else None),
        "strength": (min(5, max(0, int(st.group(1)))) if st else None),
    }


def _line_index(line_tag, n_lines):
    """[Lxxx] or bare integer -> 0-based line index, or None."""
    if line_tag is None:
        return None
    m = re.search(r"L?(\d+)", str(line_tag))
    if not m:
        return None
    idx = int(m.group(1)) - 1
    if 0 <= idx < n_lines:
        return idx
    return None


def verify_pairwise(relation, dimension, line, quote, reasoning, ref_reasoning) -> tuple[bool, float | None]:
    """(ok, rel_pos). For better -> quote must back-link verbatim into REFERENCE (mode)
    reasoning; for worse -> into candidate reasoning. equal needs no evidence (ok=True,
    rel_pos None). <=40-char VERBATIM fragment of the specific numbered [Lxxx] line
    cited (line + fragment back-link -- no whole-reasoning substring dodge)."""
    if relation == "equal":
        return True, None
    if relation not in ("better", "worse"):
        return False, None
    if dimension not in _DIMS:
        return False, None
    frag = norm_math(_clean_frag(quote) or "")
    if not frag:
        return False, None
    if len(frag) > 40:
        return False, None
    target = reasoning if relation == "worse" else (ref_reasoning or "")
    lines = number_lines(target)
    idx = _line_index(line, len(lines))
    if idx is None:
        return False, None
    if frag not in norm_math(lines[idx]):
        return False, None
    rel = idx / len(lines) if lines else 0.0
    return True, rel


def bucket_of(relation, dimension, hit) -> str:
    """Three-tier bucket relative to the mode. Evidence-fail degrades to 'equal'."""
    if relation in ("better", "worse") and dimension in _DIMS and hit:
        return relation
    return "equal"


def call_judge(agent: HuggingFaceAgent, card: str) -> dict:
    try:
        content, _reasoning, _usage = agent._call_llm_text(
            [{"role": "user", "content": card}], max_tokens=_CUT_MAX_TOKENS)
    except Exception as e:
        return {"raw": None, "error": str(e), "tokens": (0, 0, 0)}
    return {"raw": content, "error": None, "tokens": _usage_tokens(_usage)}


# ------------------------------------------------------------------ scoring
def decide(keys: list, bucket_by_key: dict, replace_op: str, strength_by_key: dict | None = None) -> dict:
    """Margin-layered replacement over FROZEN keys (issue 1).

      margin >= 3 -> pick = mode (direct, no judge).
      margin <  3 -> better = { a : bucket(a) == better };
                     trigger = (len(better) >= V0) if replace_op == "gte"
                               else     (len(better) >  V0);
                     trigger & better non-empty -> pick = argmax over better
                                                   (votes, then strength);
                     else                        -> pick = mode.
    """
    votes, latest = freeze_votes(keys)
    cands = list(votes.keys())
    counts = sorted(((votes.get(k, 0), k) for k in cands),
                    key=lambda x: (x[0], latest.get(x[1], -1)), reverse=True)
    mode = counts[0][1] if counts else None
    V0 = counts[0][0] if counts else 0
    V1 = counts[1][0] if len(counts) >= 2 else 0
    margin = V0 - V1
    if margin >= 3:
        return {"pick": mode, "mode": mode, "margin": margin, "V0": V0,
                "better": [], "n_better": 0, "triggered": False,
                "intervened": False}
    better = [k for k in cands if k != mode and bucket_by_key.get(k) == "better"]
    n_better = len(better)
    triggered = (n_better >= V0) if replace_op == "gte" else (n_better > V0)
    if triggered and better:
        sk = strength_by_key or {}
        pick = max(better, key=lambda k: (votes.get(k, 0), sk.get(k, 0)))
    else:
        pick = mode
    return {"pick": pick, "mode": mode, "margin": margin, "V0": V0,
            "better": better, "n_better": n_better, "triggered": triggered,
            "intervened": pick != mode}


def mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    s = sum(comb(n, i) for i in range(min(b, c) + 1)) * (0.5 ** n)
    return min(1.0, 2 * s)


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transitions", default=str(ROOT / "experiments/hle400/t3/c3_transitions.jsonl"))
    ap.add_argument("--loop", default=str(ROOT / "experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl"))
    ap.add_argument("--sidecar", default=str(ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"))
    ap.add_argument("--out-dir", default=str(ROOT / "experiments/hle400/t3"))
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--char-cap", type=int, default=64000)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="smoke: first N eligible tasks in the split")
    ap.add_argument("--split", choices=["dev", "test", "all"], default="all")
    ap.add_argument("--moves-only", action="store_true", help="emit manifests only, no judge calls")
    ap.add_argument("--result", default="qcut_threebucket_result.jsonl", help="verdict output filename (in --out-dir)")
    args = ap.parse_args()

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    side_c3 = side["arms"]["C3"]
    recs_by_tid = load_jsonl(Path(args.transitions))
    loop_by_tid = load_jsonl(Path(args.loop))
    q_by_tid = {tid: rec.get("question", "") for tid, rec in recs_by_tid.items()}

    # full task set (every multi-answer task, incl. margin>=3) in stable order
    def eligible_tids():
        for tid, rec, _keys, _votes, _latest, _mode, _V0, _V1, _margin in \
                iter_tasks(recs_by_tid, side_c3, loop_by_tid):
            if args.split != "all" and _is_dev(tid) != (args.split == "dev"):
                continue
            yield tid, rec

    seen_tasks: list[str] = []
    for tid, rec in eligible_tids():
        if tid not in seen_tasks:
            seen_tasks.append(tid)
    if args.limit:
        seen_tasks = seen_tasks[:args.limit]
    keep = set(seen_tasks)

    all_moves = list(build_manifest(recs_by_tid, side_c3, loop_by_tid))
    moves = [(tid, rec, m) for tid, rec, _keys, m in all_moves
             if (args.split == "all" or _is_dev(tid) == (args.split == "dev")) and tid in keep]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.moves_only:
        dev_rows = [m for tid, rec, _keys, m in all_moves if _is_dev(tid)]
        test_rows = [m for tid, rec, _keys, m in all_moves if not _is_dev(tid)]
        (out_dir / "qcut_threebucket_dev_moves.jsonl").write_text(
            "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in dev_rows), encoding="utf-8")
        (out_dir / "qcut_threebucket_test_moves.jsonl").write_text(
            "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in test_rows), encoding="utf-8")
        print(f"[moves-only] dev={len(dev_rows)} test={len(test_rows)} moves -> qcut_threebucket_{{dev,test}}_moves.jsonl")
        return

    entry = config.PHASE1_MODELS[args.model]
    result_path = out_dir / args.result
    done_rows = {}
    if result_path.exists():
        for line in result_path.read_text(encoding="utf-8").splitlines():
            try:
                rr = json.loads(line)
            except Exception:
                continue
            done_rows[(rr.get("task_id"), rr.get("from_r"), rr.get("to_r"))] = rr

    pending = [(tid, rec, m) for tid, rec, m in moves
               if (tid, m["from_r"], m["to_r"]) not in done_rows]

    _tls = threading.local()

    def make_agent():
        return HuggingFaceAgent(
            model=entry["model"], token=entry.get("api_key"),
            base_url=entry["base_url"], max_tokens=1024, temperature=0.0,
            seed=None, enable_thinking=entry.get("enable_thinking"),
            thinking_budget=entry.get("thinking_budget"),
            content_margin=_RSI_JUDGE_CONTENT_MARGIN)

    def run_one(pack):
        tid, rec, m = pack
        row = dict(m)
        row.pop("mode_entry", None)
        if m.get("mode_entry") is None:
            row.update({"relation": None, "dimension": None, "quote": None,
                        "because": None, "bucket": "equal", "hit": False,
                        "strength": 0, "rel_pos": None, "covered": True,
                        "error": None, "raw": None, "char_cap": args.char_cap,
                        "pt": 0, "ct": 0, "rt": 0})
            return row
        ag = getattr(_tls, "agent", None)
        if ag is None:
            ag = make_agent()
            _tls.agent = ag
        card, covered = build_card(m, q_by_tid.get(tid, ""), args.char_cap)
        res = call_judge(ag, card)
        row["char_cap"] = args.char_cap
        row["covered"] = covered
        if res["error"] is not None:
            row["relation"] = None
            row["dimension"] = None
            row["quote"] = None
            row["because"] = None
            row["bucket"] = "equal"
            row["hit"] = False
            row["strength"] = 0
            row["rel_pos"] = None
            row["error"] = res["error"]
        else:
            p = parse_pairwise(res["raw"])
            ok, rel = verify_pairwise(p["relation"], p["dimension"], p["line"],
                                      p["quote"], m["reasoning"],
                                      m["mode_entry"]["reasoning"])
            row.update(p)
            row["bucket"] = bucket_of(p.get("relation"), p.get("dimension"), ok)
            row["hit"] = ok
            row["strength"] = p.get("strength") or 0
            row["rel_pos"] = rel
            row["error"] = None
        row["raw"] = res["raw"]
        row["pt"], row["ct"], row["rt"] = res["tokens"]
        return row

    rows = list(done_rows.values())
    if pending:
        worker = args.concurrency or int(os.getenv("RSI_EVAL_CONCURRENCY", "4"))
        if worker <= 1 or len(pending) <= 1:
            new_rows = [run_one(p) for p in pending]
        else:
            with ThreadPoolExecutor(max_workers=worker) as ex:
                futs = [ex.submit(run_one, p) for p in pending]
                new_rows = [f.result() for f in as_completed(futs)]
            new_rows.sort(key=lambda r: (r["task_id"], r["from_r"], r["to_r"]))
        rows.extend(new_rows)

    key_of = lambda r: (r["task_id"], r["from_r"], r["to_r"])  # noqa: E731
    uniq = {key_of(r): r for r in rows}
    with result_path.open("w", encoding="utf-8") as f:
        for k in sorted(uniq):
            f.write(json.dumps(uniq[k], ensure_ascii=False) + "\n")

    report(recs_by_tid, side_c3, loop_by_tid, list(uniq.values()), seen_tasks, args.split)


# -------------------------------------------------------------------- report
def report(recs_by_tid, side_c3, loop_by_tid, rows, tids, split):
    def _ckey(r):
        return tuple(r["candidate"]) if isinstance(r["candidate"], list) else r["candidate"]

    _view_cache = {}

    def _frozen_view(tid):
        if tid not in _view_cache:
            lrec = loop_by_tid.get(tid)
            gold = (lrec.get("gold_answer", "") if lrec else "") or recs_by_tid[tid].get("gold", "")
            keys = freeze_round_keys(gold, lrec) if lrec else []
            _view_cache[tid] = (keys, side_c3.get(tid, []))
        return _view_cache[tid]

    def _row_correct(r):
        keys, side = _frozen_view(r["task_id"])
        return last_key_correct(keys, side, _ckey(r))

    bucket_by_tid = defaultdict(dict)
    strength_by_tid = defaultdict(dict)
    for r in rows:
        bucket_by_tid[r["task_id"]][_ckey(r)] = r.get("bucket")
        strength_by_tid[r["task_id"]][_ckey(r)] = r.get("strength", 0)

    tidset = set(tids)
    tasks = {
        tid: (keys, votes, latest, mode, V0, V1, margin)
        for tid, rec, keys, votes, latest, mode, V0, V1, margin
        in iter_tasks(recs_by_tid, side_c3, loop_by_tid) if tid in tidset
    }

    def _solve(replace_op):
        agg = {"pick": 0, "mode": 0, "n": 0, "intervened": 0}
        b = c = 0
        gain = loss = 0
        better_n_dist = Counter()
        for tid in sorted(tids):
            if tid not in tasks:
                continue
            keys, side = _frozen_view(tid)
            _keys, votes, latest, mode, V0, V1, margin = tasks[tid]
            d = decide(keys, bucket_by_tid[tid], replace_op, strength_by_tid[tid])
            agg["n"] += 1
            pick_ok = last_key_correct(keys, side, d["pick"])
            mode_ok = last_key_correct(keys, side, d["mode"])
            agg["pick"] += pick_ok
            agg["mode"] += mode_ok
            if d["intervened"]:
                agg["intervened"] += 1
            if pick_ok and not mode_ok:
                b += 1
                if d["intervened"]:
                    gain += 1
            elif not pick_ok and mode_ok:
                c += 1
                if d["intervened"]:
                    loss += 1
            if margin < 3:
                better_n_dist[d["n_better"]] += 1
        return agg, b, c, gain, loss, better_n_dist

    # move-level judge stats
    srows = [r for r in rows if r["task_id"] in tidset]
    bucket_counter = Counter()
    declared = Counter()
    evidence_fail = 0
    better_correct = better_total = 0
    covered = 0
    rel_positions = []
    for r in srows:
        if r.get("covered"):
            covered += 1
        rel = r.get("relation")
        if rel:
            declared[rel] += 1
        bucket = r.get("bucket")
        bucket_counter[bucket] += 1
        if bucket == "equal" and rel in ("better", "worse"):
            evidence_fail += 1
        if bucket == "better":
            better_total += 1
            if _row_correct(r):
                better_correct += 1
        if r.get("rel_pos") is not None:
            rel_positions.append(r["rel_pos"])

    n = len(tids)
    print("=" * 74)
    print(f"Q-CUT three-bucket  split={split}  tasks={n}  judge-moves={len(srows)}")
    print("=" * 74)

    for op in ("gte", "gt"):
        agg, b, c, gain, loss, better_n_dist = _solve(op)
        if agg["n"] == 0:
            continue
        sign = ">=" if op == "gte" else ">"
        print(f"[replace-op={op}]  trigger = |better| {sign} V0")
        print(f"  mode acc      = {agg['mode']:3d} / {agg['n']} = {agg['mode']/agg['n']:.4f}")
        print(f"  Q-CUT acc     = {agg['pick']:3d} / {agg['n']} = {agg['pick']/agg['n']:.4f}")
        print(f"  delta vs mode = {agg['pick']-agg['mode']:+d}   (intervened {agg['intervened']} | gain {gain} loss {loss})")
        print(f"  McNemar p = {mcnemar(b, c):.4f}  (b={b} c={c})")
        print(f"  [judge] |better| dist = {dict(sorted(better_n_dist.items()))}")

    print()
    print("  [judge] bucket dist =", dict(sorted(bucket_counter.items())))
    print("  [judge] declared    =", dict(sorted(declared.items())))
    print(f"  [judge] evidence-fail (better/worse -> equal) = {evidence_fail}")
    if better_total:
        print(f"  [judge] better-bucket candidate correct = {better_correct}/{better_total} = {better_correct/better_total:.4f}")
    if srows:
        print(f"  [judge] full-coverage rate = {covered/len(srows):.4f}  ({covered}/{len(srows)})")
    else:
        print("  [judge] no moves")
    if rel_positions:
        rel_positions.sort()
        q = statistics.quantiles(rel_positions, n=4) if len(rel_positions) >= 4 else rel_positions
        print(f"  [judge] quote rel-pos  median={statistics.median(rel_positions):.3f}  quartiles={[round(x, 3) for x in q]}")


if __name__ == "__main__":
    main()
