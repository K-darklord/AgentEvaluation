"""stage_b_evaluator.py
=======================
Stage B step 2: the recursive self-review evaluator (RSI locking).

Consumes the transition view emitted by ``transition_extract.py`` and, for each
**non-settled** task (the Stage-B target slice), asks the *target model itself* to
judge its own transition trace WITHOUT the original question text and WITHOUT the
gold answer. The evaluator then aggregates the model's verdict into a locked answer
or an abstention.

Cut mechanism (replaces the consistency 0-10 score -- 2026-10-19):

1. **Evaluator rebuilds the prompt** (deterministic, no LLM): for each answer-switch
   (an edge whose committed answer changes), the self-reported rationale of the target
   round is listed together with the from -> to answer the switch crosses.
2. **Target model judges the switch (RSI)**: WITHOUT the question and WITHOUT the gold
   answer, the *same model that produced the trajectory* reads the rationale and gives
   a binary verdict per switch -- KEEP (change justified -> trust the NEW answer) or
   CUT (change not justified -> revert to the OLD answer).
3. **Aggregation** turns the per-switch verdicts into one locked answer. A "node" is a
   maximal run of the same committed answer (an answer-fragment), so each switch sits
   on the boundary between two nodes.

   Strategies (run each separately, do not overwrite, for comparison):

   deterministic (no LLM):
   - ``mode``: majority vote over committed candidates (ties -> latest appearance).
   - ``final``: the last committed answer in the chain.
   - ``settle``: trailing run of 3 identical committed answers, else abstain.

   LLM RSI self-review (judged from the rationale + FULL hidden CoT):
   - ``conservative_cut_final``: high-precision, UNSURE-biased CUT. UNSURE is the safe
     default (keeps both); CUT only when CERTAIN the change is wrong. An all-UNSURE
     trace degrades to ``final`` (safe baseline); otherwise elimination + mode.
   - ``conservative_cut_mode``: same judge, same elimination+mode, but the all-UNSURE
     trace degrades to ``mode`` (majority vote) instead of ``final``.
   - ``rubric_cut``: three-dimension judge (rev 4): disconnection / contradiction /
     error (three independent 0..10 dimensions per switch), scored over the transition's
     reasoning process, not the answer; any dim >=6 must carry open evidence else zeroed;
     total = max dims; score>=cut_bar -> CUT else UNSURE; no threshold baked in (raw
     per-dim scores recorded for offline clustering).

Scoring (offline, against gold, for validation only) is TWO ORTHOGONAL dimensions:

1. **normal accuracy** -- the decision is scored like any other grader: `correct`
   iff the locked answer equals gold. Answering wrong OR abstaining are both scored
   as not-correct (an abstention does not answer the question).

2. **metacognition (extra)** -- an ADDITIONAL, independent assessment of whether the
   evaluator can detect "the model has no correct answer" from the activation truth:
     - activated (gold appeared -> a correct answer exists)  -> expect ANSWER, not UNSURE
     - never     (gold never appeared -> no correct answer)  -> expect honest UNSURE

   `meta_correct` is whether the answer/abstain BEHAVIOR matches that activation
   truth. It is reported alongside accuracy, not folded into it.

Token accounting: every RSI self-review call records prompt/completion/reasoning
tokens per task (``prompt_tokens`` / ``completion_tokens`` / ``reasoning_tokens``) so
the full pipeline cost is recoverable offline without rerunning the experiment.

Usage:
  python3 src/stage_b_evaluator.py \
      --transitions /tmp/trans_ds.jsonl \
      --model deepseek-v4-flash \
      --out /tmp/stageb_ds.jsonl \
      [--strategy mode|final|settle|conservative_cut_final|conservative_cut_mode|rubric_cut] [--limit 3] [--rubric-threshold 8]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_dotenv() -> None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK.

    2026-10-20: stage_b_evaluator.py was missing this bypass; its judge calls were
    routing through the sandbox proxy and hanging (connection to localhost:3213 with
    zero forward progress), unlike run_feedback_loop.py which connects directly.
    """
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_force_no_proxy()

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402


# ---- named selector strategies (run each separately; do not overwrite) ----
# 2026-10-20: canonical 6 strategies over the multi-answer switch space.
#   deterministic (no LLM):  mode / final / settle
#   LLM RSI self-review:      conservative_cut_final / conservative_cut_mode / rubric_cut
# (rationale_cut family dropped 2026-10-20: pure-rationale KEEP/CUT was too aggressive;
#  conservative cot_tail feed replaced with full hidden CoT.)
STRATEGIES = {
    "mode": {
        "name": "mode",
        "aggregate": "deterministic",
        "deterministic": "mode",
        "desc": "majority vote over committed candidates (ties -> latest appearance); no LLM",
    },
    "final": {
        "name": "final",
        "aggregate": "deterministic",
        "deterministic": "final",
        "desc": "last committed answer in the chain; no LLM",
    },
    "settle": {
        "name": "settle",
        "aggregate": "deterministic",
        "deterministic": "settle",
        "desc": "trailing run of 3 identical committed answers, else abstain; no LLM",
    },
    "conservative_cut_final": {
        "name": "conservative_cut_final",
        "aggregate": "conservative_cut_final",
        "desc": "high-precision, UNSURE-biased CUT; all-UNSURE falls back to final (last committed answer), else elimination+mode",
    },
    "conservative_cut_mode": {
        "name": "conservative_cut_mode",
        "aggregate": "conservative_cut_mode",
        "desc": "high-precision, UNSURE-biased CUT; all-UNSURE falls back to mode (majority vote), else elimination+mode",
    },
    "rubric_cut": {
        "name": "rubric_cut",
        "aggregate": "rubric_cut",
        "desc": "three-dimension judge (rev 4): disconnection/contradiction/error 0..10 per switch scored over the transition's reasoning process; any dim >=6 must carry open evidence else zeroed; total=max dims; score>=cut_bar -> CUT else UNSURE (raw per-dim scores recorded for offline clustering)",
    },
}

# conservative_cut family: same UNSURE-biased KEEP/CUT/UNSURE judge, differing only in
# the degenerate all-UNSURE fallback (final vs mode). Share one prompt + elimination+mode.
_CONSERVATIVE_AGGS = ("conservative_cut_final", "conservative_cut_mode")

# rubric_cut also uses elimination+mode with an all-UNSURE -> final fallback, but its
# judge is the rubric-scored prompt (signed score threshold) rather than bare KEEP/CUT/UNSURE.
_ELIM_FALLBACK_AGGS = _CONSERVATIVE_AGGS + ("rubric_cut",)


def score(decision: str | None, rec: dict) -> dict:
    """Two orthogonal scores (offline, gold, validation only).

    dim 1 -- normal accuracy: correct iff the locked answer equals gold.
    dim 2 -- metacognition: whether answer/abstain matches the activation truth
             (activated -> expect ANSWER; never -> expect honest UNSURE).
    """
    gold = rec.get("gold")
    candidates = rec.get("candidates", [])
    activated = gold is not None and gold in candidates
    correct = (decision is not None and decision == gold)
    meta_correct = (decision is not None) if activated else (decision is None)
    return {"activated": activated, "correct": correct, "meta_correct": meta_correct}


# ---- RSI self-review call config ----
_CUT_MAX_TOKENS = int(os.getenv("RSI_CUT_MAX_TOKENS", "16384"))
# How much of the FULL hidden CoT the rubric judge sees per switch (chars). The old
# 400-char cot_tail was the reason rubric scores hovered near 0 (no derivable error).
# 0 = no cap (dump the whole reasoning_content); a positive value keeps head+tail.
_RUBRIC_COT_CAP = int(os.getenv("RUBRIC_COT_CAP", "0"))
# 2026-10-20: the rubric judge is a mechanical 7-rule VERIFIER, not a solver. With
# deepseek-v4-flash's model-default thinking ON, feeding the FULL hidden CoT makes the
# judge re-derive everything in its own hidden CoT until the output cap, emitting ZERO
# visible score lines (aime_018: 3x16384 reasoning tokens, raw="", malformed). Fix:
# keep thinking ON but cap it with thinking_budget (the repo's sanctioned stop-and-commit
# mechanism) and reserve a ROOMY visible-content window so the N per-switch score lines
# fit -- the default 64-token window only fits one option letter. Does NOT disable
# thinking (per project stance). _RSI_JUDGE_CONTENT_MARGIN = tokens AFTER the CoT cap.
_RSI_JUDGE_CONTENT_MARGIN = int(os.getenv("RSI_JUDGE_CONTENT_MARGIN", "1024"))

# KEEP/CUT/UNSURE verdict per switch (parsed for the conservative_cut family). UNSURE
# keeps both neighboring nodes (no deletion); see _elimination_mode_lock allow_unsure.
_VERDICT_RE = re.compile(r"\b(KEEP|CUT|UNSURE)\s+r?(\d+)\s*->\s*r?(\d+)", re.IGNORECASE)


def _mode_answer(rec: dict) -> str | None:
    """Deterministic selector 'mode': majority vote over committed candidates,
    ties broken by latest appearance in the chain (mirrors analyze_settle_and_transitions
    mode_answer). Self-contained (counts from rounds) so it does not depend on the
    frequency/votes field variant."""
    ans_seq = [r.get("ans") for r in rec.get("rounds", [])]
    cands = list(rec.get("candidates", []) or [])
    if not cands:
        return None
    freq = Counter(a for a in ans_seq if a is not None)
    last_idx: dict = {}
    for i, a in enumerate(ans_seq):
        last_idx[a] = i
    return max(cands, key=lambda a: (freq.get(a, 0), last_idx.get(a, -1)))


def _flat(s: str, cap: int | None = None) -> str:
    """Collapse internal whitespace to single spaces (keeps one-line-per-transition
    prompt format); optionally truncate head+tail for token control.

    ``cap == 0`` (or ``None``) means no truncation. A positive cap keeps the first
    ``cap//2`` and last ``cap//2`` chars, so a full reasoning chain keeps BOTH the
    problem setup AND the concluding commit (a pure head-slice would drop the commit,
    re-introducing the thin-evidence bug that muted the rubric scores)."""
    s = " ".join((s or "").split())
    if cap and len(s) > cap:
        half = cap // 2
        return s[:half] + " …[truncated]… " + s[-half:]
    return s


def _usage_tokens(meta) -> tuple[int, int, int]:
    """Extract (prompt, completion, reasoning) token counts from a _call_llm_text
    return (a SimpleNamespace carrying .usage)."""
    u = getattr(meta, "usage", None)
    if u is None:
        return (0, 0, 0)
    return (getattr(u, "prompt_tokens", 0) or 0,
            getattr(u, "completion_tokens", 0) or 0,
            getattr(u, "reasoning_tokens", 0) or 0)


def _rat_by_to(rec: dict) -> dict[int, str]:
    rounds = rec.get("rounds", [])
    return {r["r"]: (r.get("rationale") or "").strip() for r in rounds[1:]}


def _reasoning_by_to(rec: dict) -> dict[int, str]:
    """FULL hidden CoT per round index. The 400-char ``cot_tail`` was too thin an
    evidence slice for the rubric judge (it usually just re-states the commit), so
    the rubric prompt reads the whole ``reasoning`` field (falling back to cot_tail
    for records extracted before full reasoning was emitted)."""
    rounds = rec.get("rounds", [])
    return {r["r"]: (r.get("reasoning") or r.get("cot_tail") or "").strip()
            for r in rounds[1:]}


def _switch_edges(rec: dict) -> list[tuple[int, int]]:
    """Edges whose committed answer actually changes. Only these need a KEEP/CUT
    judgement -- a hold (same answer carried) changes nothing."""
    rounds = rec.get("rounds", [])
    out: list[tuple[int, int]] = []
    for k in range(1, len(rounds)):
        frm, to = rounds[k - 1]["r"], rounds[k]["r"]
        if rounds[k - 1].get("ans") != rounds[k].get("ans"):
            out.append((frm, to))
    return out


def _ans_fragments(rec: dict) -> list[dict]:
    """Split the raw committed-answer chain into maximal runs of equal value (None
    counts as its own value). Returns, in order, one dict per run:
    {ans, rounds:[r, ...]}."""
    rounds = rec.get("rounds", [])
    frags: list[dict] = []
    for r in rounds:
        a = r.get("ans")
        if not frags or frags[-1]["ans"] != a:
            frags.append({"ans": a, "rounds": [r["r"]]})
        else:
            frags[-1]["rounds"].append(r["r"])
    return frags


def build_forced_cut_prompt(rec: dict, switches: list[tuple[int, int]], allow_unsure: bool = False) -> str:
    """Forced re-ask for still-undecided switches (conservative_cut family). Feeds the
    same full hidden CoT evidence as the main conservative prompt (2026-10-20: cot_tail
    dropped -- feed the whole derivation, not a 400-char tail)."""
    rat = _rat_by_to(rec)
    cot = _reasoning_by_to(rec)
    rounds = rec.get("rounds", [])
    ans_by_r = {r["r"]: r.get("ans") for r in rounds}
    verdicts = "KEEP / CUT / UNSURE" if allow_unsure else "KEEP / CUT"
    lines = [
        f"You MUST give a verdict for EACH switch below ({verdicts}). One line each,",
        "in order:",
    ]
    if allow_unsure:
        lines.append("  KEEP r<i>->r<j>   /   CUT r<i>->r<j>   /   UNSURE r<i>->r<j>")
    else:
        lines.append("  KEEP r<i>->r<j>   /   CUT r<i>->r<j>")
    lines += [
        "",
        "Switches:",
    ]
    for frm, to in switches:
        a_old, a_new = ans_by_r.get(frm), ans_by_r.get(to)
        r = _flat(rat.get(to), 1000) or "(no reason)"
        c = _flat(cot.get(to), _RUBRIC_COT_CAP) or "(no hidden reasoning)"
        lines.append(f"  r{frm}->r{to}  OLD={a_old}  NEW={a_new}")
        lines.append(f"      reason      : {r}")
        lines.append(f"      hidden_steps: {c}")
    return "\n".join(lines)


def build_conservative_cut_prompt(rec: dict, switches: list[tuple[int, int]]) -> str:
    """High-precision CUT prompt. Reorients the judge's burden: a CUT permanently
    discards the NEW answer on the right and falls back to the OLD answer on the left,
    so a bad cut loses a correct new answer. CUT ONLY a switch judged CERTAIN to have
    changed to the wrong answer; otherwise default to KEEP / UNSURE. When in doubt,
    do NOT cut."""
    rat = _rat_by_to(rec)
    cot = _reasoning_by_to(rec)
    rounds = rec.get("rounds", [])
    ans_by_r = {r["r"]: r.get("ans") for r in rounds}
    lines = [
        "You review your own self-correction trace WITHOUT the question and WITHOUT",
        "any ground-truth answer.",
        "",
        "UNSURE is the safe default: it changes nothing and keeps both answers. Use",
        "UNSURE for ANY switch you cannot adjudicate with real certainty, whether or",
        "not the change looks justified. Only act when you are CERTAIN:",
        "",
        "  UNSURE r<i>->r<j>   (default -- uncertain or generic reason -> keep both)",
        "  CUT    r<i>->r<j>   (CERTAIN the change is WRONG -> revert to OLD)",
        "  KEEP   r<i>->r<j>   (CERTAIN the change is JUSTIFIED -> trust NEW)",
        "",
        "Per switch you see the self-reported reason AND the hidden reasoning steps",
        "(full hidden CoT). Look for a COMPUTATION or REASONING error in either: a definite",
        "error is the only grounds to CUT.",
        "",
        "A CUT is destructive: it discards the NEW answer for the OLD, so a bad cut",
        "throws away a correct new answer. Prefer UNSURE over a guess in either",
        "direction.",
        "",
        "Write ONE line per switch, nothing else:",
        "",
        "Switches:",
    ]
    for frm, to in switches:
        a_old, a_new = ans_by_r.get(frm), ans_by_r.get(to)
        r = _flat(rat.get(to), 1000) or "(no reason)"
        c = _flat(cot.get(to), _RUBRIC_COT_CAP) or "(no hidden reasoning)"
        lines.append(f"  r{frm}->r{to}  OLD={a_old}  NEW={a_new}")
        lines.append(f"      reason      : {r}")
        lines.append(f"      hidden_steps: {c}")
    return "\n".join(lines)


# ---- rubric-scored judge (2026-10-20 rev 4: three-dimension) ----
# rev 4 keeps the 0..10 independent dims + evidence anchor from rev 3, but collapses
# the four categories into THREE (user-finalized 2026-10-20):
#   disconnection : justification break, judged at TWO layers -- (a) hidden CoT ->
#                   rationale (does the rationale faithfully summarize / is it derivable
#                   from the CoT?) and (b) rationale -> transition (does the rationale
#                   actually explain the OLD -> NEW change causally?).
#   contradiction : internal self-contradiction (within the CoT, within the rationale,
#                   or between the two).
#   error         : a meaningful substantive error in the hidden derivation (computation
#                   / sign / mechanism / ...), located by the judge ITSELF -- independent
#                   of the weak critic, whose top3 degenerates to format leaves for MCQ
#                   families (non_letter_output / wrong_option / multiple_letters).
# The weak_alert feed is dropped (D3 is independent). OLD/NEW labels stay as coherence
# anchors only. Raw per-dim scores are recorded; no threshold is baked in so the
# correct-vs-wrong transition gap can be measured offline first.
_RUBRIC_NAMES = [
    "disconnection",
    "contradiction",
    "error",
]

# rev 4 (2026-10-20): THREE independent dimension scores per switch (one 0..10 each),
# plus an evidence anchor. A dimension >=6 with no located, quoteable error is not
# credible -> parser zeroes it. Replaces rev 3's four-dim set.
_DIM_SCORE_RE = re.compile(
    r"\b(disconnection|contradiction|error)\s*=\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE)
_EVIDENCE_RE = re.compile(r"\bevidence\s*=\s*\"([^\"]*)\"", re.IGNORECASE)
_EVIDENCE_BAR = 6.0  # a dimension >= this must carry open evidence, else it is zeroed


def build_rubric_cut_prompt(rec: dict, switches: list[tuple[int, int]]) -> str:
    """Three-dimension rubric prompt (rev 4). The judge scores the TRANSITION'S REASONING
    PROCESS, not whether the NEW answer is right, on THREE independent 0..10 dims:
      disconnection = justification break (hidden CoT -> rationale, and rationale -> OLD->NEW)
      contradiction = internal self-contradiction (within CoT / rationale / between them)
      error         = a meaningful substantive error located in the hidden steps
    Evidence-anchored: any dim >=6 must cite a located, quoteable error (evidence="..."),
    else the parser zeroes it. OLD/NEW labels are coherence anchors only. The weak_alert
    feed is dropped (the error dim is located independently, not via the weak critic)."""
    rat = _rat_by_to(rec)
    cot = _reasoning_by_to(rec)
    rounds = rec.get("rounds", [])
    ans_by_r = {r["r"]: r.get("ans") for r in rounds}
    lines = [
        "You review your OWN self-correction trace WITHOUT the question and WITHOUT any",
        "ground-truth answer.",
        "",
        "Judge the TRANSITION'S REASONING PROCESS -- the reported reason plus the hidden",
        "derivation steps that produced the switch -- NOT whether the NEW answer is right.",
        "The OLD/NEW labels below are only coherence anchors for two checks: whether the",
        "derivation actually reaches the NEW answer, and whether the reason explains the",
        "OLD -> NEW change.",
        "",
        "Score THREE dimensions independently, 0..10 each (0 = no such error / cannot tell,",
        "10 = certain):",
        "  disconnection=0..10  justification break. Check BOTH layers:",
        "                       (a) hidden steps -> reason: does the reason faithfully",
        "                           summarize what the hidden steps actually derived?",
        "                       (b) reason -> OLD->NEW: does the reason actually explain",
        "                           why the answer changed from OLD to NEW?",
        "  contradiction=0..10  the reason/hidden steps contradict themselves, or the derived",
        "                       conclusion disagrees with the NEW answer",
        "  error=0..10          a meaningful substantive error located IN the hidden steps",
        "                       (a computation slip, sign error, wrong mechanism, etc.)",
        "",
        "EVIDENCE RULE: any dimension scored >=6 MUST cite a located, quoteable error in the",
        "hidden steps. Put its exact wording in evidence=\"...\" at the end of the line. A",
        "dimension >=6 with NO located evidence is not credible -- leave that dimension at 0.",
        "",
        "Output ONE line per switch, nothing else:",
        "  r<i>->r<j> disconnection=<n> contradiction=<n> error=<n> [evidence=\"...\"]",
        "",
        "Switches:",
    ]
    for frm, to in switches:
        a_old, a_new = ans_by_r.get(frm), ans_by_r.get(to)
        r = _flat(rat.get(to), 1000) or "(no reason)"
        c = _flat(cot.get(to), _RUBRIC_COT_CAP) or "(no hidden reasoning)"
        lines.append(f"  r{frm}->r{to}  OLD={a_old}  NEW={a_new}")
        lines.append(f"      reason      : {r}")
        lines.append(f"      hidden_steps: {c}")
    return "\n".join(lines)


def _parse_rubric_verdicts(text: str) -> dict[tuple[int, int], dict]:
    """Extract {(from_r, to_r): {dim scores, evidence, score}} from a rev-4 rubric reply.
    One line per switch with THREE independent dimension scores; total = max dim. Any
    dimension >= _EVIDENCE_BAR without an open evidence="..." is not credible -> zeroed."""
    out: dict[tuple[int, int], dict] = {}
    if not text:
        return out
    edge_re = re.compile(r"\br?(\d+)\s*->\s*r?(\d+)", re.IGNORECASE)
    for line in text.splitlines():
        em = edge_re.search(line)
        if not em:
            continue
        frm, to = int(em.group(1)), int(em.group(2))
        dims = {d: 0.0 for d in _RUBRIC_NAMES}
        named = False
        for m in _DIM_SCORE_RE.finditer(line):
            dims[m.group(1).lower()] = float(m.group(2))
            named = True
        if not named:
            continue
        ev = _EVIDENCE_RE.search(line)
        evidence = ev.group(1).strip() if ev else None
        # evidence anchor: a high dim without a located error is not credible -> 0.
        for d in _RUBRIC_NAMES:
            if dims[d] >= _EVIDENCE_BAR and not evidence:
                dims[d] = 0.0
        entry = dict(dims)
        entry["evidence"] = evidence
        entry["score"] = max(dims[d] for d in _RUBRIC_NAMES)
        out[(frm, to)] = entry
    return out


def _score_to_verdict(v: dict, cut_bar: float) -> str:
    """Single-direction ERROR SCORE -> CUT / UNSURE. Only a HIGH score (>= cut_bar)
    CUTs; a low/missing score is UNSURE (keep/unsure merged). No KEEP class: the judge
    never affirmatively deletes the OLD side in this rev."""
    score = v.get("score")
    if score is None:
        return "UNSURE"
    return "CUT" if score >= cut_bar else "UNSURE"


def _parse_verdicts(text: str) -> dict[tuple[int, int], str]:
    """Extract {(from_r, to_r): verdict} from a KEEP/CUT/UNSURE reply.
    verdict is one of 'KEEP' | 'CUT' | 'UNSURE'."""
    if not text:
        return {}
    out: dict[tuple[int, int], str] = {}
    for m in _VERDICT_RE.finditer(text):
        verdict = m.group(1).upper()
        frm, to = int(m.group(2)), int(m.group(3))
        out[(frm, to)] = verdict
    return out


def _elimination_mode_lock(rec: dict, cuts: dict[tuple[int, int], str], allow_unsure: bool = False) -> tuple[str | None, dict]:
    """Elimination + strict mode over answer-fragments (the RSI "nodes").

    Each answer-switch sits on the boundary between two adjacent nodes:
      CUT   -> keep the LEFT node, delete the RIGHT (change unjustified).
      KEEP  -> delete the LEFT node, keep the RIGHT (change justified).
      UNSURE -> (only when allow_unsure) delete NEITHER; the transition is kept.
    A node deleted by ANY switch is out. After every switch is walked, the surviving
    nodes' non-None answers are counted and the strict mode locks; a tie (or no
    surviving non-None answer) abstains. None fragments never vote (2026-10-20 bug fix:
    a None node could previously tie/win the mode over a real letter).
    """
    rounds = rec.get("rounds", [])
    info: dict = {"status": "no_rounds", "fragments": [], "n_switch": 0}
    if not rounds:
        return None, info

    frags = _ans_fragments(rec)
    switches = _switch_edges(rec)
    info["fragments"] = frags
    info["n_switch"] = len(switches)

    if len(frags) == 1:
        info["status"] = "single_fragment"
        return frags[0]["ans"], info

    # round number -> fragment index, so each switch maps to its two neighboring nodes.
    frag_idx: dict[int, int] = {}
    for i, f in enumerate(frags):
        for r in f["rounds"]:
            frag_idx[r] = i

    deleted = [False] * len(frags)
    undecided = 0
    for frm, to in switches:
        v = cuts.get((frm, to))
        if v is None:
            undecided += 1
            continue
        left, right = frag_idx[frm], frag_idx[to]
        if v == "KEEP":
            deleted[left] = True       # keep RIGHT -> delete the LEFT node
        elif v == "CUT":
            deleted[right] = True      # CUT -> delete the RIGHT node
        else:                          # UNSURE
            if not allow_unsure:
                undecided += 1         # stray UNSURE in a binary run -> abstain
            # else: keep both -> delete nothing

    survivors = [frags[i] for i in range(len(frags)) if not deleted[i]]
    info["survivors"] = survivors
    info["n_switch_undecided"] = undecided

    if undecided:
        info["status"] = "undecided_switch"
        return None, info

    # mode over non-None survivor answers only (None never votes)
    valid = [f["ans"] for f in survivors if f["ans"] is not None]
    if not valid:
        info["status"] = "no_survivors"
        return None, info

    counts = Counter(valid)
    max_c = max(counts.values())
    top = [a for a, c in counts.items() if c == max_c]
    if len(top) == 1:
        info["status"] = "locked_majority"
        info["mode"] = top[0]
        return top[0], info

    info["status"] = "tie_abstain"
    info["tie_among"] = top
    return None, info


def _render_mc(rec: dict, cuts: dict[tuple[int, int], str] | None) -> list[str]:
    """Render the state chain; cuts=None -> raw, else annotate each switch KEEP/CUT."""
    rounds = rec.get("rounds", [])
    lines = []
    for k, r in enumerate(rounds):
        if k == 0:
            lines.append(f"r{r['r']}=({r['ans']})")
            continue
        frm, to = rounds[k - 1]["r"], r["r"]
        rat = (r.get("rationale") or "").strip()
        if cuts is None:
            lines.append(f"r{frm}->r{to}: {rat or '-'}")
            continue
        if rounds[k - 1].get("ans") == r.get("ans"):
            lines.append(f"r{frm}->r{to} (hold): {rat or '-'}")
        else:
            d = cuts.get((frm, to))
            mark = {"KEEP": "KEEP", "CUT": "CUT", "UNSURE": "UNSURE", None: "?"}.get(d, "?")
            lines.append(f"r{frm}->r{to} [{mark}]: {rat or '-'}")
    return lines


def evaluate_one(agent: HuggingFaceAgent, rec: dict, strategy: dict, rubric_threshold: float = 8.0) -> dict:
    agg = strategy.get("aggregate", "conservative_cut_final")

    # ---- deterministic selectors: no LLM call, verdict straight from the trace ----
    if agg == "deterministic":
        which = strategy.get("deterministic")
        if which == "mode":
            verdict = _mode_answer(rec)
        elif which == "final":
            verdict = rec.get("final_ans")
        else:  # settle
            verdict = rec.get("settled_ans")
        out = {
            "strategy": strategy["name"],
            "aggregate": agg,
            "task_id": rec["task_id"],
            "family": rec["family"],
            "gold": rec["gold"],
            "candidates": rec["candidates"],
            "raw": None,
            "parse_status": "n/a",
            "lock_status": "deterministic",
            "attempts": 0,
            "cuts": {},
            "n_switch": len(_switch_edges(rec)),
            "fragments": _ans_fragments(rec),
            "survivors": None,
            "mode": verdict if which == "mode" else None,
            "chosen_frag": None,
            "original_mc": _render_mc(rec, None),
            "final_mc": _render_mc(rec, None),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "per_switch": {},
            "coverage": None,
            "rubric_threshold": None,
            "verdict": verdict,
        }
        out.update(score(verdict, rec))
        return out

    # ---- LLM RSI self-review selectors ----
    is_rubric = (agg == "rubric_cut")
    allow_unsure = (agg in _CONSERVATIVE_AGGS) or is_rubric
    switches = _switch_edges(rec)
    cuts: dict[tuple[int, int], str] = {}
    per_switch: dict[tuple[int, int], dict] = {}
    raw = None
    attempts = 0
    undecided = list(switches)
    tok = [0, 0, 0]  # [prompt, completion, reasoning] accumulated across passes
    parse_fn = _parse_rubric_verdicts if is_rubric else _parse_verdicts

    def _absorb(content) -> None:
        nonlocal undecided
        got = parse_fn(content or "")
        for e, v in got.items():
            if is_rubric:
                per_switch[e] = v
                cuts[e] = _score_to_verdict(v, rubric_threshold)
            else:
                cuts[e] = v
        undecided = [e for e in undecided if e not in got]

    # Pass 1: open KEEP/CUT(/UNSURE) prompt over all answer-switches.
    if undecided:
        attempts += 1
        if is_rubric:
            p1 = build_rubric_cut_prompt(rec, undecided)
        else:  # conservative_cut family (rationale_cut dropped 2026-10-20)
            p1 = build_conservative_cut_prompt(rec, undecided)
        try:
            content, _reasoning, _usage = agent._call_llm_text(
                [{"role": "user", "content": p1}],
                max_tokens=_CUT_MAX_TOKENS,
            )
        except Exception as e:  # api_failure -> fall through to forced decide
            raw = f"<error: {e}>"
            content = None
        else:
            raw = content
            pt, ct, rt = _usage_tokens(_usage)
            tok[0] += pt
            tok[1] += ct
            tok[2] += rt
            _absorb(content)

    # Pass 2: forced re-ask for the still-undecided switches.
    while undecided and attempts < 3:
        attempts += 1
        forced = (build_rubric_cut_prompt(rec, undecided) if is_rubric
                  else build_forced_cut_prompt(rec, undecided, allow_unsure))
        try:
            content, _reasoning, _usage = agent._call_llm_text(
                [{"role": "user", "content": forced}],
                max_tokens=_CUT_MAX_TOKENS,
            )
        except Exception as e:
            raw = f"<error: {e}>"
            break
        raw = content
        pt, ct, rt = _usage_tokens(_usage)
        tok[0] += pt
        tok[1] += ct
        tok[2] += rt
        _absorb(content)

    parse_status = "malformed" if undecided else "ok"
    if agg in _ELIM_FALLBACK_AGGS and not undecided:
        # All-UNSURE fallback: no confident verdicts -> degrade to a safe deterministic
        # baseline (final or mode) instead of an abstain, which scores 0 on accuracy
        # (2026-10-20). A mixed trace still goes through elimination + mode.
        n_unsure = sum(1 for v in cuts.values() if v == "UNSURE")
        n_sw = len(switches)
        fallback = "mode" if agg.endswith("_mode") else "final"
        if n_sw > 0 and n_unsure == n_sw:
            info = {"status": f"all_unsure_fallback_{fallback}",
                    "fragments": _ans_fragments(rec),
                    "n_switch": n_sw,
                    "survivors": None,
                    "n_unsure": n_unsure}
            verdict = _mode_answer(rec) if fallback == "mode" else rec.get("final_ans")
        else:
            verdict, info = _elimination_mode_lock(rec, cuts, allow_unsure=True)
    else:
        verdict, info = _elimination_mode_lock(rec, cuts, allow_unsure=allow_unsure)

    out = {
        "strategy": strategy["name"],
        "aggregate": agg,
        "task_id": rec["task_id"],
        "family": rec["family"],
        "gold": rec["gold"],
        "candidates": rec["candidates"],
        "raw": raw,
        "parse_status": parse_status,
        "lock_status": info["status"],
        "attempts": attempts,
        "cuts": {f"{a}->{b}": v for (a, b), v in sorted(cuts.items())},
        "n_switch": info["n_switch"],
        "fragments": info["fragments"],
        "survivors": info.get("survivors"),
        "mode": info.get("mode"),
        "chosen_frag": info.get("chosen_frag"),
        "original_mc": _render_mc(rec, None),
        "final_mc": _render_mc(rec, cuts),
        "prompt_tokens": tok[0],
        "completion_tokens": tok[1],
        "reasoning_tokens": tok[2],
        "per_switch": {f"{a}->{b}": v for (a, b), v in sorted(per_switch.items())},
        "coverage": None,
        "rubric_threshold": rubric_threshold if is_rubric else None,
        "verdict": verdict,
    }
    out.update(score(verdict, rec))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transitions", required=True, type=Path)
    ap.add_argument("--model", required=True, help="key into config.PHASE1_MODELS (RSI: same model as trajectory)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--strategy", default="rubric_cut", choices=list(STRATEGIES.keys()),
                    help="named selector strategy (run each separately, do not overwrite)")
    ap.add_argument("--limit", type=int, default=0, help="smoke: only first N non-settle tasks")
    ap.add_argument("--concurrency", type=int, default=0, help="0 = config default")
    ap.add_argument("--rubric-threshold", type=float, default=8.0,
                    help="rubric_cut only: provisional CUT bar (score>=bar -> CUT, else UNSURE); raw scores are recorded regardless for offline clustering")
    args = ap.parse_args()

    strategy = STRATEGIES[args.strategy]
    entry = config.PHASE1_MODELS[args.model]
    # 2026-10-20: keep the judge's thinking ON but cap it with thinking_budget and a
    # roomy content window (see _RSI_JUDGE_CONTENT_MARGIN above), so the full-CoT rubric
    # prompt yields per-switch scores instead of a runaway hidden CoT that emits nothing.
    agent = HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=1024, temperature=0.0,
        seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=entry.get("thinking_budget"),
        content_margin=_RSI_JUDGE_CONTENT_MARGIN)

    recs = [json.loads(l) for l in open(args.transitions, encoding="utf-8")]
    # Stage-B target (new口径, 2026-10-19): MULTI-ANSWER tasks -- >=2 distinct committed
    # candidate answers -- trigger the RSI self-review, regardless of settle. The trigger
    # is the observable "multi-answer" fact (no gold needed). Single-answer tasks skip.
    recs = [r for r in recs if len(r.get("candidates", [])) >= 2]
    if args.limit:
        recs = recs[:args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(args.out, "w", encoding="utf-8") as fout:
        # serial smoke-first; concurrency is a fast-follow, not needed for correctness
        for i, rec in enumerate(recs, 1):
            res = evaluate_one(agent, rec, strategy, rubric_threshold=args.rubric_threshold)
            fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            fout.flush()
            rows.append(res)
            behavior = "answer" if res["verdict"] is not None else "abstain"
            print(f"[{i}/{len(recs)}] {res['task_id']} gold={res['gold']} "
                  f"verdict={res['verdict']} ({behavior}) lock={res['lock_status']} "
                  f"correct={res['correct']} meta={res['meta_correct']}", flush=True)

    tot = len(rows)
    if not tot:
        print("no candidate-bearing non-settle tasks to evaluate")
        return
    n_act = sum(1 for r in rows if r["activated"])
    n_never = tot - n_act
    acc = sum(1 for r in rows if r["correct"]) / tot
    meta = sum(1 for r in rows if r["meta_correct"]) / tot
    act_meta = sum(1 for r in rows if r["activated"] and r["meta_correct"])
    nvr_meta = sum(1 for r in rows if (not r["activated"]) and r["meta_correct"])
    tot_pt = sum(r["prompt_tokens"] for r in rows)
    tot_ct = sum(r["completion_tokens"] for r in rows)
    tot_rt = sum(r["reasoning_tokens"] for r in rows)
    print(f"\n=== Stage-B evaluator [{args.model}] strategy={args.strategy} on multi-answer slice (n={tot}) ===")
    print(f"  activated {n_act} / never {n_never}")
    print(f"  [dim1] accuracy          {acc:.3f}  ({sum(1 for r in rows if r['correct'])}/{tot})")
    print(f"  [dim2] metacognition     {meta:.3f}  ({sum(1 for r in rows if r['meta_correct'])}/{tot})")
    print(f"         - activated:      {act_meta}/{n_act}  (expect ANSWER)")
    print(f"         - never:          {nvr_meta}/{n_never}  (expect honest UNSURE)")
    print(f"  [tokens] prompt={tot_pt} completion={tot_ct} reasoning={tot_rt}")


if __name__ == "__main__":
    main()