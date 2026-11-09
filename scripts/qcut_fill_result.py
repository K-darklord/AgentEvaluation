#!/usr/bin/env python3
"""qcut_fill_result.py — fill experiments/hle400/t3/qcut_result.jsonl (Judge-R+ / Q-CUT).

Reproduces the FROZEN Q-CUT judge contract (same card prompt + verbatim anchor rule as
the original run) and appends the missing verdicts so the edge-level audit
(scripts/judge_conditional_test.py) sees a verdict on every decisive edge of every
multi-answer task. Unlike the original runner, it does NOT skip margin>=2 tasks — the
margin>=2 skip is a provable no-op for the *decision* but leaves decisive edges without
a verdict, so those tasks are judged here as well.

Format: one row per candidate ENTRY move (task_id/from_r/to_r/verdict CUT|NO_CUT),
N=1 call per move — byte-identical fields to the existing qcut_result.jsonl. Resume is
idempotent: keys whose judge call already completed (error is None) are skipped; new
rows are appended incrementally and the file is re-sorted at the end.

Usage:
  python3 scripts/qcut_fill_result.py --limit 3                          # smoke: 3 moves
  python3 scripts/qcut_fill_result.py --model deepseek-v4-flash-payg --concurrency 2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import threading
import time
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


def build_manifest(recs_by_tid: dict, side_c3: dict, loop_by_tid: dict):
    """Yield (tid, rec, keys, move) for every candidate entry move of every
    multi-answer, margin<=1 task (margin>=2 is a structural no-op: one subtraction
    can't flip). Candidates/votes/mode are computed over FROZEN keys (issue 1: key
    space, not the transition string), so the manifest matches `_mode_idx` exactly."""
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
        if len(counts) < 2:
            continue
        em = entry_moves(rec, keys)
        for k, (from_r, to_r, t) in em.items():
            reasoning = t.get("reasoning") or ""
            if not reasoning and 0 <= to_r < len(rec.get("rounds", [])):
                reasoning = rec["rounds"][to_r].get("reasoning") or ""
            yield tid, rec, keys, {
                "task_id": tid,
                "candidate": k,
                "from_r": from_r,
                "to_r": to_r,
                "old": t.get("from"),
                "new": t.get("to"),
                "check": check_for(rec, t, to_r),
                "reasoning": reasoning,
                "c_a": votes.get(k, 0),
            }


# --------------------------------------------------------------------- judge
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')


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


def build_card(move: dict, question: str, char_cap: int) -> tuple[str, bool]:
    card_lines = number_lines(move["reasoning"])
    disp, covered = display_lines(card_lines, char_cap)
    check = move["check"] or "(none)"
    card = [
        "QUESTION:",
        question,
        "",
        f"The solver changed its committed answer at round {move['to_r']}:",
        f"  previous answer (round {move['from_r']}): {move['old']}",
        f"  new answer (round {move['to_r']}):        {move['new']}",
        "Before this change, a reviewer asked the solver to check:",
        f"  {check}",
        f"Round {move['to_r']} reasoning (numbered [Lxxx] lines):",
        disp,
        "",
        "Find ONE step that makes the NEW answer definitely wrong. Do NOT solve the",
        "problem or judge the previous answer. Cite a SHORT fragment, not a sentence.",
        "",
        "falsifier classes:",
        "  ARITH       arithmetic/computation: wrong value, sign, substitution, or formula; a line that is false",
        "  CONSTRAINT  the NEW answer violates a condition stated in the QUESTION",
        "  COUNT       a counting mistake (objects / permutations / combinations)",
        "  FORM        the NEW answer's form/units violate a condition stated in the QUESTION",
        "  NONE        no such step",
        "",
        "ANCHORING RULE (decisive):",
        "  - set line to the [Lxxx] whose text contains your objection.",
        "  - copy 'fragment' character-for-character from that exact line, at most 40",
        "    characters; never rewrite, paraphrase, or reformat.",
        "  - for CONSTRAINT or FORM you may instead set line=QUESTION and copy the",
        "    fragment from the QUESTION text above.",
        "  - if the objection cannot be tied to text that is actually there, output NONE.",
        "",
        "Output exactly:",
        "  falsifier: ARITH | CONSTRAINT | COUNT | FORM | NONE",
        "  line: L0xx | QUESTION",
        "  fragment: up to 40 characters copied exactly from the cited line (empty when NONE)",
        "  claim: <one sentence: which quantity/relation is wrong and why>",
    ]
    return "\n".join(card), covered


def parse_falsifier(text: str) -> dict:
    text = text or ""
    f = re.search(r"falsifier\s*:\s*(ARITH|CONSTRAINT|COUNT|FORM|NONE)", text, re.IGNORECASE)
    ln = re.search(r"line\s*:\s*(QUESTION|L\d+)", text, re.IGNORECASE)
    fr = re.search(r"fragment\s*:\s*([^\n]*)", text, re.IGNORECASE)
    cl = re.search(r"claim\s*:\s*([^\n]*)", text, re.IGNORECASE)
    return {
        "falsifier": (f.group(1).upper() if f else None),
        "line": (ln.group(1).upper() if ln else None),
        "fragment": (_clean_frag(fr.group(1)) if fr else None),
        "claim": (cl.group(1).strip() if cl else None),
    }


def verify_anchor(falsifier, line, fragment, qtext, lines) -> tuple[bool, float | None]:
    """(ok, rel_pos). ok iff the citation verifies mechanically: falsifier declared,
    line exists (or QUESTION for CONSTRAINT/FORM), and fragment (whitespace-normalized)
    is a substring of that line/question."""
    fs = (falsifier or "").upper()
    if fs in ("", "NONE"):
        return False, None
    frag = norm_math(_clean_frag(fragment) or "")
    if not frag:
        return False, None
    anchor = None
    rel = None
    if (line or "").upper() == "QUESTION":
        if fs in ("CONSTRAINT", "FORM"):
            anchor = qtext
    else:
        m = re.match(r"L(\d+)", (line or "").upper())
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(lines):
                anchor = lines[idx]
                rel = idx / len(lines) if lines else 0.0
    if anchor is None:
        return False, None
    if frag not in norm_math(anchor):
        return False, None
    return True, rel


def call_judge(agent: HuggingFaceAgent, card: str) -> dict:
    try:
        content, _reasoning, _usage = agent._call_llm_text(
            [{"role": "user", "content": card}], max_tokens=_CUT_MAX_TOKENS)
    except Exception as e:
        return {"raw": None, "error": str(e), "tokens": (0, 0, 0)}
    return {"raw": content, "error": None, "tokens": _usage_tokens(_usage)}


# ------------------------------------------------------------------ scoring
def decide(keys: list, cuts_by_key: dict, cut_weight: int) -> dict:
    """R1-R3 -> {pick, mode, score, intervened} over FROZEN keys (issue 1)."""
    votes, latest = freeze_votes(keys)
    cands = list(votes.keys())
    mode = max(cands, key=lambda k: (votes.get(k, 0), latest.get(k, -1))) if cands else None
    score = {k: votes.get(k, 0) - cut_weight * cuts_by_key.get(k, 0) for k in cands}
    pick = max(cands, key=lambda k: (score[k], latest.get(k, -1))) if cands else None
    return {"pick": pick, "mode": mode, "score": score, "intervened": pick != mode}


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
    ap.add_argument("--model", default="deepseek-v4-flash-payg")
    ap.add_argument("--char-cap", type=int, default=64000)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="smoke: max pending moves to judge (0 = all)")
    args = ap.parse_args()

    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    side_c3 = side["arms"]["C3"]
    recs_by_tid = load_jsonl(Path(args.transitions))
    loop_by_tid = load_jsonl(Path(args.loop))
    q_by_tid = {tid: rec.get("question", "") for tid, rec in recs_by_tid.items()}

    # Every multi-answer task's candidate entry moves (margin>=2 included: decisive edges
    # on those tasks still need a verdict for the edge-level audit).
    all_moves = list(build_manifest(recs_by_tid, side_c3, loop_by_tid))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    entry = config.PHASE1_MODELS[args.model]
    result_path = out_dir / "qcut_result.jsonl"

    # done = keys whose judge call actually completed (error is None). A failed/429 row
    # must be re-run, never skipped.
    done = {}
    if result_path.exists():
        for line in result_path.read_text(encoding="utf-8").splitlines():
            try:
                rr = json.loads(line)
            except Exception:
                continue
            if rr.get("error") is None:
                done[(rr.get("task_id"), rr.get("from_r"), rr.get("to_r"))] = rr

    pending = [(tid, rec, m) for tid, rec, _keys, m in all_moves
               if (tid, m["from_r"], m["to_r"]) not in done]
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

    # The agent already retries transient 429s with backoff. Here we guard the residual
    # errors, hard-stopping on billing/auth so money is never silently burned.
    _FATAL = ("insufficient_quota", "insufficient balance", "insufficient quota",
              "unauthenticated", "invalid_api_key", "invalid api key", "authentication",
              "billing", "quota", "balance", "401", "403")
    # DashScope public-compatible endpoint applies a server-side content inspection.
    # These blocks are deterministic (content, not quota/transient): no retry, record
    # the key and keep going so the remaining moves still complete.
    _CONTENT_BLOCK = ("data_inspection_failed", "inappropriate content",
                      "data inspection")

    blocked = []

    def run_one(pack):
        tid, rec, m = pack
        ag = getattr(_tls, "agent", None)
        if ag is None:
            ag = make_agent()
            _tls.agent = ag
        card, covered = build_card(m, q_by_tid.get(tid, ""), args.char_cap)
        res = call_judge(ag, card)
        if res["error"] is not None:
            err_l = res["error"].lower()
            if any(k in err_l for k in _FATAL):
                raise RuntimeError(
                    f"[fatal] billing/auth error on {tid} ({m['from_r']}->{m['to_r']}): {res['error']}")
            if any(k in err_l for k in _CONTENT_BLOCK):
                blocked.append((tid, m["from_r"], m["to_r"], res["error"][:160]))
                return None
            time.sleep(2.0)
            res = call_judge(ag, card)
            if res["error"] is not None:
                raise RuntimeError(
                    f"[error] judge call failed on {tid} ({m['from_r']}->{m['to_r']}): {res['error']}")
        p = parse_falsifier(res["raw"])
        ok, rel = verify_anchor(p["falsifier"], p["line"], p["fragment"],
                                q_by_tid.get(tid, ""), number_lines(m["reasoning"]))
        row = dict(m)
        row["model"] = entry.get("model")
        row["endpoint"] = args.model
        row["char_cap"] = args.char_cap
        row["covered"] = covered
        row.update(p)
        row["verdict"] = "CUT" if (p.get("falsifier") not in (None, "NONE")) else "NO_CUT"
        row["hit"] = ok
        row["frag_ok"] = ok
        row["rel_pos"] = rel
        row["error"] = None
        row["raw"] = res["raw"]
        row["pt"], row["ct"], row["rt"] = res["tokens"]
        return row

    total_pending = len(pending)
    write_lock = threading.Lock()
    done_cnt = [0]

    def _emit(row):
        if row is None:
            return
        line = json.dumps(row, ensure_ascii=False) + "\n"
        with write_lock:
            with result_path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
            done_cnt[0] += 1
            print(f"[progress] {done_cnt[0]}/{total_pending} {row.get('task_id')} "
                  f"from_r={row.get('from_r')} to_r={row.get('to_r')} "
                  f"verdict={row.get('verdict')}", flush=True)

    failed = None
    if pending:
        worker = args.concurrency or 2
        print(f"[start] pending={total_pending} worker={worker} model={args.model}", flush=True)
        if worker <= 1 or total_pending <= 1:
            for p in pending:
                try:
                    _emit(run_one(p))
                except Exception as e:  # noqa: BLE001
                    failed = e
                    break
        else:
            with ThreadPoolExecutor(max_workers=worker) as ex:
                futs = [ex.submit(run_one, p) for p in pending]
                for fut in as_completed(futs):
                    try:
                        _emit(fut.result())
                    except Exception as e:  # noqa: BLE001
                        failed = e
                        break
    if failed is not None:
        print(f"[abort] {failed}", flush=True)
        sys.exit(1)

    # Final sorted, deduplicated rewrite so the file stays byte-stable and ordered.
    uniq = {}
    for line in result_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rr = json.loads(line)
        except Exception:
            continue
        uniq[(rr.get("task_id"), rr.get("from_r"), rr.get("to_r"))] = rr
    with result_path.open("w", encoding="utf-8") as f:
        for k in sorted(uniq):
            f.write(json.dumps(uniq[k], ensure_ascii=False) + "\n")

    if blocked:
        print(f"[blocked] content-inspected moves (skipped): {len(blocked)}", flush=True)
        for b in blocked:
            print(f"  {b[0]} {b[1]}->{b[2]}", flush=True)
    tasks = sorted({r["task_id"] for r in uniq.values()})
    vc = Counter(r.get("verdict") for r in uniq.values())
    errs = [r for r in uniq.values() if r.get("error")]
    print(f"[done] moves={len(uniq)} tasks={len(tasks)} verdicts={dict(vc)} errors={len(errs)}")


# -------------------------------------------------------------------- report
def report(recs_by_tid, side_c3, loop_by_tid, rows, tids, split, cut_weight):
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

    cuts_by_tid = defaultdict(dict)
    for r in rows:
        cuts_by_tid[r["task_id"]][_ckey(r)] = 1 if r.get("hit") else 0

    # task-level accuracy
    pm = {"pick": 0, "mode": 0, "n": 0, "intervened": 0}
    b, c = 0, 0  # discordant pairs for McNemar (pick vs mode)
    for tid in sorted(tids):
        keys, side = _frozen_view(tid)
        d = decide(keys, cuts_by_tid[tid], cut_weight)
        pm["n"] += 1
        pick_ok = last_key_correct(keys, side, d["pick"])
        mode_ok = last_key_correct(keys, side, d["mode"])
        if pick_ok:
            pm["pick"] += 1
        if mode_ok:
            pm["mode"] += 1
        if d["intervened"]:
            pm["intervened"] += 1
        if pick_ok and not mode_ok:
            b += 1
        elif not pick_ok and mode_ok:
            c += 1

    # move-level judge stats (only rows belonging to this split's tasks)
    tidset = set(tids)
    srows = [r for r in rows if r["task_id"] in tidset]
    declared_cut = hit_cut = false_cut = cut_err = frag_fail = 0
    covered = 0
    fs_counter = Counter()
    rel_positions = []
    for r in srows:
        if r.get("covered"):
            covered += 1
        falsifier = r.get("falsifier")
        if falsifier not in (None, "NONE"):
            declared_cut += 1
            fs_counter[falsifier] += 1
            if r.get("hit"):
                hit_cut += 1
                if _row_correct(r):
                    false_cut += 1
                else:
                    cut_err += 1
            else:
                frag_fail += 1
        if r.get("rel_pos") is not None:
            rel_positions.append(r["rel_pos"])
    n_err_move = sum(1 for r in srows if not _row_correct(r))
    recall = cut_err / n_err_move if n_err_move else 0.0
    precision = (hit_cut - false_cut) / hit_cut if hit_cut else 0.0
    false_cut_rate = false_cut / hit_cut if hit_cut else 0.0
    hit_rate = hit_cut / declared_cut if declared_cut else 0.0

    n = pm["n"]
    if n == 0:
        print(f"[{split}] no eligible tasks (weight={cut_weight}); nothing to report.")
        return
    print("=" * 74)
    print(f"Q-CUT  split={split}  cut_weight={cut_weight}  tasks={n}  moves={len(srows)}")
    print("=" * 74)
    print(f"  mode acc      = {pm['mode']:3d} / {n} = {pm['mode']/n:.4f}")
    print(f"  Q-CUT acc     = {pm['pick']:3d} / {n} = {pm['pick']/n:.4f}")
    print(f"  delta vs mode = {pm['pick']-pm['mode']:+d} tasks   (intervened {pm['intervened']})")
    print(f"  McNemar (vs mode) p = {mcnemar(b, c):.4f}   (b={b} c={c})")
    print()
    print(f"  [judge] declared-CUT={declared_cut}  verified-CUT={hit_cut}  hit-rate={hit_rate:.4f}")
    print(f"  [judge] fragment-fail={frag_fail}")
    print(f"  [judge] false-CUT={false_cut}  precision={precision:.4f}  false-CUT-rate={false_cut_rate:.4f}")
    print(f"  [judge] recall={recall:.4f}  ({cut_err} correct-CUT / {n_err_move} wrong-NEW moves)")
    print(f"  [judge] full-coverage rate={covered/len(srows):.4f}"
          f"  ({covered}/{len(srows)} untruncated)" if srows else "  [judge] no moves")
    if fs_counter:
        print(f"  [judge] falsifier dist = {dict(sorted(fs_counter.items()))}")
        for fs in sorted(fs_counter):
            vc = sum(1 for r in srows if r.get("falsifier") == fs and r.get("hit"))
            dfc = sum(1 for r in srows if r.get("falsifier") == fs and r.get("hit")
                      and _row_correct(r))
            print(f"    {fs:11s}: declared={fs_counter[fs]:3d}  verified={vc:3d}  false-CUT={dfc:3d}")
    if rel_positions:
        rel_positions.sort()
        q = statistics.quantiles(rel_positions, n=4) if len(rel_positions) >= 4 else rel_positions
        print(f"  [judge] fragment rel-pos  median={statistics.median(rel_positions):.3f}  "
              f"quartiles={[round(x, 3) for x in q]}")


if __name__ == "__main__":
    main()
