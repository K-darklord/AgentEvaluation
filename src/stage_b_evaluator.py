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
        "desc": "three-dimension judge (rev 4): disconnection/contradiction/error 0..10 per switch scored over the transition's reasoning process; any dim >=6 must carry open evidence else zeroed; total=max dims; score>=cut_bar -> CUT else UNSURE (raw per-dim scores recorded for offline clustering); all-UNSURE -> mode; the error dim is backlinked against the answer-free L3 wrong-execution bank",
    },
    "rubric_ce": {
        "name": "rubric_ce",
        "aggregate": "rubric_ce",
        "desc": "rubric_cut variant (2026-10-25): same judge + lock, but the CUT-trigger score = max(contradiction,error), dropping the direction-agnostic disconnection (fires on both DERAIL and REPAIR) from the gate; disconnection is kept raw for offline audit.",
    },
    "rubric_v5": {
        "name": "rubric_v5",
        "aggregate": "rubric_v5",
        "desc": "structured judge (rev 5): separates evidence axis (old_support/new_support/error_* with backlink-verified quotes) from reflection axis (confidence). Only a backlinked error may CUT/KEEP; else UNSURE. Dup. output per-switch structured fields for offline gate tuning",
    },
}

# conservative_cut family: same UNSURE-biased KEEP/CUT/UNSURE judge, differing only in
# the degenerate all-UNSURE fallback (final vs mode). Share one prompt + elimination+mode.
_CONSERVATIVE_AGGS = ("conservative_cut_final", "conservative_cut_mode")

# rubric_cut also uses elimination+mode with an all-UNSURE -> mode fallback (mode =
# "stable state", since the judge only emits CUT and cannot delete r0; 2026-10-22).
_ELIM_FALLBACK_AGGS = _CONSERVATIVE_AGGS + ("rubric_cut", "rubric_v5", "rubric_ce")

# Mode-lock survive-score fold (ablation knob, 2026-10-26): "max" = 0.5 unsure + keep
# the higher flank (conservative, current default); "min" = 0.5 unsure + keep the lower
# flank (aggressive delete); "0" = no half vote (UNSURE inert, CUT/KEEP cast hard 0/1,
# fold max).
_VOTE_MODE = os.getenv("EGTE_VOTE_MODE", "max")


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

# Template scaffold tokens emitted by the transition-rationale collector
# (run_feedback_loop._TRANSITION_RATIONALE_SYSTEM / _NONE). The rubric judge was
# pattern-matching the literal "ERROR:" and "FIX:" in the self-reported reason and
# scoring error=8 off of them (bbh_0003: 8/8/8, evidence pulled verbatim from the FIX
# sentence "The new answer is correct because ..."), collapsing all three dims and
# erasing direction (a sound H->K fix and a wrong K->H regression scored identically).
# Rename the scaffolds to neutral semantics so the judge reads the self-report as a
# SELF-REPORT, never as located-error markers.
_REASON_SCAFFOLD_MAP = {
    "ERROR:": "claimed-prev-flaw:",
    "REASON:": "switch-motive:",
    "FIX:": "claimed-new-basis:",
    "BEFORE:": "prev-state:",
    "WHY:": "switch-motive:",
    "NOW:": "now-state:",
}


def _neutral_reason(s: str) -> str:
    """Replace the transition-rationale scaffold labels with neutral semantics so the
    rubric judge does not confuse self-justification wording with the `error` dim."""
    out = s or ""
    for k, v in _REASON_SCAFFOLD_MAP.items():
        out = re.sub(r"(?<![A-Za-z])" + re.escape(k), v, out, flags=re.IGNORECASE)
    return out


def _load_rubric_error_vocab(model: str, bank_dir: Path | None = None, cap_chars: int | None = None) -> str:
    """Load the answer-free L3 wrong-execution bank and format it as a judge check-list.

    The bank names GENERIC error archetypes (name/definition/check_procedure), never
    the correct answer, so it is safe to show the evaluator and leaks no gold. It gives
    the `error` dimension a prior: a located hidden-step error that instantiates a known
    archetype is credible, unlike the rev-4 judge's ungrounded "is there an error?" call.

    ``cap_chars`` truncates the whole block (head+tail) for token control; ``None`` = full
    bank. Returns "" if the bank is missing or empty (graceful no-op, rev-4 behaviour).
    """
    d = Path(bank_dir) if bank_dir else (REPO_ROOT / "experiments" / "l0_distill_v1")
    path = d / f"level3_bank_{model}.json"
    if not path.exists():
        return ""
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("entries", [])
    except (json.JSONDecodeError, OSError):
        return ""
    lines: list[str] = []
    for e in entries:
        name = (e.get("name") or e.get("id") or "").strip()
        if not name:
            continue
        df = " ".join((e.get("definition") or "").split())
        cp = " ".join((e.get("check_procedure") or "").split())
        s = f"- {name}: {df}"
        if cp:
            s += f"  CHECK: {cp}"
        lines.append(s)
    if not lines:
        return ""
    block = "\n".join(lines)
    if cap_chars and len(block) > cap_chars:
        half = cap_chars // 2
        block = block[:half] + "\n …[truncated error vocabulary]… \n" + block[-half:]
    return block


def _directed_check_lines(dc) -> list[str]:
    """Render the per-switch ``directed_check`` line(s) for one switch's critic directions.

    ``dc`` is either a single direction dict or a list of dicts, each carrying
    ``archetype_name`` (or ``archetype``/``id``), ``suspicion`` and -- when the strong
    critic grounded it in the solver CoT -- a concrete gold-free ``check``. The ``check``
    is the SAME signal the critic handed the solver, so the evaluator can CUT/keep against
    the shared anchor (breakpoint-3, 2026-10-24) instead of the self-report's narration.
    Missing ``check`` (e.g. the weak-critic fallback path) degrades to arch :: suspicion.
    """
    entries = dc if isinstance(dc, list) else [dc]
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        arch = e.get("archetype_name") or e.get("archetype") or e.get("id") or ""
        susp = e.get("suspicion") or ""
        check = e.get("check") or ""
        if not (arch or susp or check):
            continue
        s = f"      directed_check : {arch} :: {susp}" if (arch or susp) else "      directed_check : (unnamed)"
        if check:
            s += f" [verify: {check}]"
        out.append(s)
    return out


def _build_directed(rec: dict, sidecar: dict | None) -> dict[str, list[dict]]:
    """Assemble the rubric judge's ``directed`` map {str(to_round) -> [direction dicts]}.

    Primary source is now IN-BAND: each round's ``critic_direction`` (the strong critic's
    suspicion + check on the PREVIOUS answer -- the OLD side of the switch into this round),
    emitted by ``transition_extract`` and keyed by ``rounds[k]["r"]`` to match
    ``_switch_edges``. The external ``sidecar`` is still merged as an optional per-task
    override (back-compat with the pre-in-band --critic-sidecar experiment).
    """
    directed: dict[str, list] = {}
    rounds = rec.get("rounds", [])
    for k in range(1, len(rounds)):
        to = rounds[k].get("r")
        cd = rounds[k].get("critic_direction")
        if to is None or not cd:
            continue
        key = str(to)
        directed.setdefault(key, [])
        directed[key].extend(cd if isinstance(cd, list) else [cd])
    if sidecar:
        for rnd, val in (sidecar.get(rec.get("task_id"), {}) or {}).items():
            key = str(rnd)
            directed.setdefault(key, [])
            directed[key].extend(val if isinstance(val, list) else [val])
    return directed


def build_rubric_cut_prompt(rec: dict, switches: list[tuple[int, int]], directed: dict | None = None, blind: bool = False, error_vocab: str | None = None) -> str:
    """Three-dimension rubric prompt (rev 4). The judge scores the TRANSITION'S REASONING
    PROCESS, not whether the NEW answer is right, on THREE independent 0..10 dims:
      disconnection = justification break (hidden CoT -> rationale, and rationale -> OLD->NEW)
      contradiction = internal self-contradiction (within CoT / rationale / between them)
      error         = a meaningful substantive error located in the hidden steps
    Evidence-anchored: any dim >=6 must cite a located, quoteable error (evidence="..."),
    else the parser zeroes it. OLD/NEW labels are coherence anchors only. The weak_alert
    feed is dropped (the error dim is located independently, not via the weak critic).

    If ``error_vocab`` (the answer-free L3 wrong-execution bank, see
    ``_load_rubric_error_vocab``) is supplied, it is injected as a backlink check-list
    for the `error` dim: a located error that instantiates a named archetype is credible,
    replacing the rev-4 judge's ungrounded "is there an error?" call."""
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
        "The `reason` field is a SELF-REPORT of the change. Its `claimed-prev-flaw` clause",
        "says what the model THINKS was wrong with the old answer; its `claimed-new-basis`",
        "clause says why it THINKS the new answer is right. These are self-justifications",
        "-- NEVER treat their wording as located error evidence.",
        "",
        "Score THREE INDEPENDENT dimensions, 0..10 each (0 = no such problem / cannot",
        "tell, 10 = certain). They answer DIFFERENT questions, so they MUST NOT share a",
        "value by default: a high score on one does not raise the others. If you have no",
        "SPECIFIC, distinct evidence for a dimension, leave that dimension at 0.",
        "  disconnection=0..10  justification break. Check BOTH layers:",
        "                       (a) hidden steps -> reason: does the self-report faithfully",
        "                           summarize what the hidden steps actually derived?",
        "                       (b) reason -> OLD->NEW: does the self-report actually",
        "                           explain WHY the answer changed from OLD to NEW?",
        "  contradiction=0..10  the hidden steps or the self-report contradict THEMSELVES,",
        "                       or the derived conclusion disagrees with the NEW answer",
        "  error=0..10          a substantive error located ONLY in the hidden derivation",
        "                       steps (computation slip, sign error, wrong mechanism).",
        "                       Score this from hidden_steps ALONE -- NEVER from the",
        "                       self-report's claimed-prev-flaw / claimed-new-basis wording.",
        "",
        "DIRECTION RULE: the switch is a SOUND FIX (low error) when the hidden steps show",
        "the OLD derivation had a real error and the NEW steps re-derive cleanly. It is a",
        "BAD SWITCH (high error) when the NEW hidden steps themselves contain a substantive",
        "error that corrupts the NEW answer. Scoring `error` high merely because the",
        "self-report SAYS the old answer was wrong is a false positive.",
        "",
        "EVIDENCE RULE: any dimension scored >=6 MUST cite located, quoteable wording FROM",
        "the hidden steps. Put that exact wording in evidence=\"...\" at the end of the line.",
        "For `error`, evidence must be the specific erring step in hidden_steps, never a",
        "self-report sentence. A dimension >=6 with no such evidence is not credible --",
        "leave that dimension at 0.",
        "",
        "Output ONE line per switch, nothing else:",
        "  r<i>->r<j> disconnection=<n> contradiction=<n> error=<n> [evidence=\"...\"]",
    ]
    if error_vocab:
        lines += [
            "",
            "KNOWN ERROR VOCABULARY (answer-free wrong-execution archetypes, distilled from",
            "prior failures): use this ONLY as a check-list to NAME and GROUND a located error",
            "in hidden_steps. A located error that instantiates one of these archetypes is a",
            "credible `error`; it must STILL cite the specific hidden_steps wording in evidence,",
            "and you may also name the matching archetype. Do NOT raise `error` merely because",
            "an archetype exists -- only when the hidden_steps actually exhibit it.",
            "",
            error_vocab,
        ]
    if directed and not blind:
        lines += [
            "",
            "DIRECTED CHECK: a `directed_check` line names a suspicion a strong critic raised about",
            "the OLD answer, plus a `[verify: ...]` clause naming the concrete gold-free self-check the",
            "critic proposed. Treat both as a HYPOTHESIS to verify against hidden_steps: look",
            "specifically for whether the hidden steps CONFIRM or REFUTE that suspicion, and let that",
            "decide `error`/`contradiction` rather than trusting the self-report's framing.",
        ]
    if blind:
        lines += [
            "",
            "BLIND MODE: you are shown ONLY the hidden derivation steps, not the self-report",
            "`reason` and not any external critic suspicion. Derive every dimension from the",
            "hidden steps alone; do not infer polarity from how confidently a switch was narrated.",
        ]
    lines += ["", "Switches:"]
    for frm, to in switches:
        a_old, a_new = ans_by_r.get(frm), ans_by_r.get(to)
        r = _flat(_neutral_reason(rat.get(to)), 1000) or "(no reason)"
        c = _flat(cot.get(to), _RUBRIC_COT_CAP) or "(no hidden reasoning)"
        lines.append(f"  r{frm}->r{to}  OLD={a_old}  NEW={a_new}")
        if not blind:
            lines.append(f"      reason      : {r}")
        lines.append(f"      hidden_steps: {c}")
        if directed and not blind:
            lines += _directed_check_lines(directed.get(str(to)))
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
        # collapse guard: three dims collapsed to the SAME >=bar value means the judge
        # pattern-matched instead of distinguishing the dimensions (bbh_0003: 8/8/8 with
        # evidence pulled from the FIX sentence). Reject the whole verdict -> UNSURE.
        vals = [dims[d] for d in _RUBRIC_NAMES]
        collapsed = len(set(vals)) == 1 and vals[0] >= _EVIDENCE_BAR
        if collapsed:
            for d in _RUBRIC_NAMES:
                dims[d] = 0.0
            evidence = None
        entry = dict(dims)
        entry["evidence"] = evidence
        entry["collapse"] = collapsed
        entry["score"] = max(dims[d] for d in _RUBRIC_NAMES)
        out[(frm, to)] = entry
    return out


# ---- rubric_v5: structured evidence / reflection separation (2026-10-22) ----
# v5 separates TWO signal classes that rev-4 conflated:
#   evidence  axis -- locatable derivation steps that back a candidate answer
#                     (equations, numbers, named rules, causal steps). old_support /
#                     new_support / error_* measure THIS only.
#   reflection axis -- the model's meta narration (hesitation, critic echo, polarity
#                     self-report). This is a CONFIDENCE signal, NOT evidence. It never
#                     raises a support score (a confident wrong answer is real -- gpqa_
#                     031/049), but it calibrates how certain the lock may be; when
#                     evidence cannot separate the two sides, a hesitant reflection is
#                     the only honest ground left -> UNSURE.
#
# The judge output is structured; every error_* claim must BACKLINK to the hidden steps
# (a quoteable substring re-verified by the parser). A claim that cannot be located is
# dropped. This is the "independent judgement" mechanism: the judge cannot freely narrate
# a verdict -- it must re-quote the offending step and the parser verifies the quote.
_ECHO_HINT_RE = re.compile(
    r"\b(maybe|perhaps|possibly|might|likely|could\s+be|not\s+sure|uncertain|"
    r"need(?:\s+to)?\s+(?:examine|determine|scrutinize|re-?derive|check|verify|investigate)|"
    r"let[’']?s\s+(?:scrutinize|investigate|check|re-?derive)|"
    r"reviewer|suggestion|flagged|suspect|suspicious|double-?check)\b",
    re.IGNORECASE)
_FACT_ANCHOR_RE = re.compile(r"[=<>×÷+\-\d]|because|therefore|thus|so\s|since\s|implies",
                             re.IGNORECASE)


def _tag_echo(text: str) -> str:
    """Sentence-level [echo]/[fact] tag of the hidden derivation. A sentence is [echo]
    when it carries a meta/hesitation cue and NO fact anchor; [fact] when it carries a
    fact anchor. Untagged sentences are neutral. This deterministic pre-pass keeps
    reflection separated from evidence WITHOUT deleting the reason scaffold (unlike the
    failed blind M0, which stripped reason and lost the reason<->content disconnect)."""
    if not text:
        return text
    out: list[str] = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        s = sent.strip()
        if not s:
            continue
        echo = bool(_ECHO_HINT_RE.search(s)) and not _FACT_ANCHOR_RE.search(s)
        fact = bool(_FACT_ANCHOR_RE.search(s))
        if echo:
            out.append(f"[echo]{s}")
        elif fact:
            out.append(f"[fact]{s}")
        else:
            out.append(s)
    return " ".join(out)


def build_rubric_v5_prompt(rec: dict, switches: list[tuple[int, int]], directed: dict | None = None, blind: bool = False) -> str:
    """rubric_v5 structured judge: two separated axes (evidence vs reflection) with
    backlink-verifiable error claims. The judge does NOT re-derive the question; it
    locates internally-inconsistent steps and re-quotes them."""
    rat = _rat_by_to(rec)
    cot = _reasoning_by_to(rec)
    rounds = rec.get("rounds", [])
    ans_by_r = {r["r"]: r.get("ans") for r in rounds}
    lines = [
        "You review your OWN self-correction trace WITHOUT the question and WITHOUT any",
        "ground-truth answer.",
        "",
        "Two separate signal classes. Do NOT mix them:",
        "  [fact] --- derivation's locatable steps (equations, numbers, named rules,",
        "             causal 'because/therefore'). These are EVIDENCE.",
        "  [echo] --- meta narration (hesitation, 'reviewer said ...', polarity wording).",
        "             This is REFLECTION -- a confidence signal, NOT evidence. It must never",
        "             raise a support score by itself (a confident WRONG answer is real).",
        "",
        "For each switch, output ONLY the structured block below, nothing else:",
        "  r<i>->r<j>",
        "    old_support   : <0..10>",
        "    new_support   : <0..10>",
        "    error_old     : \"\" | \"<exact quote from the OLD derivation>\"",
        "    error_new     : \"\" | \"<exact quote from the NEW derivation>\"",
        "    conflict      : <0..10>",
        "    confidence    : hesitant | neutral | confident",
        "    old_conclusion      : \"\" | \"<single answer token the OLD derivation finally settles>\"",
        "    new_conclusion      : \"\" | \"<single answer token the NEW derivation finally settles>\"",
        "    old_conclusion_quote: \"\" | \"<exact quote where OLD settles on that token>\"",
        "    new_conclusion_quote: \"\" | \"<exact quote where NEW settles on that token>\"",
        "",
        "  THE DECIDING CHECK (conclusion-mismatch) -- this is a FACT-REPORT, not a judgement:",
        "      read the FINAL answer each side's derivation actually settles on, and quote the",
        "      sentence where it does. If the NEW derivation's settled conclusion DIFFERS from",
        "      the NEW answer label, that NEW answer is self-contradictory (logically wrong)",
        "      and must be cut. Same for OLD. You only REPORT what each derivation last",
        "      concludes -- you never judge WHICH answer is right.",
        "  old_support / new_support : how well the [fact] steps actually SUPPORT that",
        "      candidate answer (0 = no support / cannot tell, 10 = fully supported). Stored",
        "      for later gating; NOT used for the cut decision.",
        "  error_old / error_new     : a located, self-contradicting step in that answer's",
        "      derivation (computation slip, sign error, wrong rule). Quote it VERBATIM;",
        "      never use an [echo] sentence or the reason self-report here. Leave \"\" if",
        "      you cannot locate one. Stored for later gating; NOT decisive.",
        "  conflict      : internal self-contradiction within the switch (0..10).",
        "  confidence    : how confidently the trace itself was narrated, from [echo]/reason",
        "      ONLY. Stored; NOT decisive. 'confident' does NOT mean the answer is right.",
        "",
    ]
    if directed and not blind:
        lines.append("DIRECTED CHECK: treat any critic suspicion (and its [verify: ...] self-check) "
                     "as a HYPOTHESIS, verified ONLY against [fact] steps; it is never evidence by itself.")
    lines += ["", "Switches:"]
    for frm, to in switches:
        a_old, a_new = ans_by_r.get(frm), ans_by_r.get(to)
        r = _flat(_neutral_reason(rat.get(to)), 1000) or "(no reason)"
        c = _flat(cot.get(to), _RUBRIC_COT_CAP) or "(no hidden reasoning)"
        lines.append(f"  r{frm}->r{to}  OLD={a_old}  NEW={a_new}")
        if not blind:
            lines.append(f"      reason       : {r}")
        lines.append(f"      hidden_steps : {_tag_echo(c)}")
        if directed and not blind:
            lines += _directed_check_lines(directed.get(str(to)))
    return "\n".join(lines)


_V5_FIELD_RE = re.compile(
    r"\b(old_support|new_support|error_old|error_new|conflict|confidence|"
    r"old_conclusion|new_conclusion|old_conclusion_quote|new_conclusion_quote)\s*[:=]\s*(.+?)\s*$",
    re.IGNORECASE)


def _norm_ans(x) -> str | None:
    """Normalize an answer label to a canonical single token (A-Z letter, or a numeric
    value), for the conclusion-mismatch check. Edge case: a free-text label like
    'llm error: ...' normalizes to its leading letter -- acceptable for the MCQ families
    this run targets (labels are single letters/numbers)."""
    if x is None:
        return None
    m = re.match(r"[A-Za-z]|\d+(?:\.\d+)?", str(x).strip().strip('"').upper())
    return m.group(0).upper() if m else None


def _parse_rubric_v5_verdicts(text: str, cot_by_to: dict[int, str]) -> dict[tuple[int, int], dict]:
    """Parse rubric_v5 structured blocks. Each error_* claim must BACKLINK to the raw
    (untagged) hidden derivation; a quote that is not a verbatim substring is dropped
    (error stays None, backlink False). support/conflict parsed as float; confidence is
    one of hesitant/neutral/confident."""
    out: dict[tuple[int, int], dict] = {}
    if not text:
        return out
    edge_re = re.compile(r"\br?(\d+)\s*->\s*r?(\d+)")
    cur: tuple[int, int] | None = None
    for line in text.splitlines():
        em = edge_re.search(line)
        if em and "->" in line:
            frm, to = int(em.group(1)), int(em.group(2))
            cur = (frm, to)
            out[cur] = {
                "old_support": 0.0, "new_support": 0.0,
                "error_old": None, "error_new": None,
                "error_old_backlink": False, "error_new_backlink": False,
                "conflict": 0.0, "confidence": "neutral",
                "old_conclusion": None, "new_conclusion": None,
                "old_conclusion_backlink": False, "new_conclusion_backlink": False,
            }
            continue
        if cur is None:
            continue
        fm = _V5_FIELD_RE.search(line)
        if not fm:
            continue
        key, raw = fm.group(1).lower(), fm.group(2).strip()
        e = out[cur]
        if key in ("old_support", "new_support", "conflict"):
            try:
                e[key] = float(raw)
            except ValueError:
                pass
        elif key == "confidence":
            v = raw.strip().lower()
            e["confidence"] = v if v in ("hesitant", "neutral", "confident") else "neutral"
        elif key in ("error_old", "error_new"):
            q = raw.strip().strip('"') if raw else ""
            if q:
                cot_norm = _flat(cot_by_to.get(cur[1], ""))
                q_norm = _flat(q.replace("[fact]", "").replace("[echo]", "")
                               .replace("[", "").replace("]", ""))
                if q_norm and q_norm in cot_norm:
                    e[key] = q
                    e[key + "_backlink"] = True
                # else: dropped (no backlink) -- the claim is not independently located
        elif key in ("old_conclusion", "new_conclusion"):
            e[key] = raw.strip().strip('"') if raw else None
        elif key in ("old_conclusion_quote", "new_conclusion_quote"):
            q = raw.strip().strip('"') if raw else ""
            if q:
                cot_norm = _flat(cot_by_to.get(cur[1], ""))
                q_norm = _flat(q.replace("[fact]", "").replace("[echo]", "")
                               .replace("[", "").replace("]", ""))
                if q_norm and q_norm in cot_norm:
                    e[key.replace("_quote", "") + "_backlink"] = True
                # else: dropped (no backlink)
    return out


def _v5_to_verdict(v: dict, old_ans, new_ans) -> str:
    """v5.1 conclusion-mismatch rule: cut a side ONLY when its own derivation settles on
    a conclusion that DIFFERS from its answer label (a self-contradiction = logically wrong).
    Decisive and objective (deterministic label compare + backlinked quote), never the
    judge's 'which step is wrong' opinion. error_*/support/confidence are STORED, not decisive."""
    old_c = _norm_ans(v.get("old_conclusion"))
    new_c = _norm_ans(v.get("new_conclusion"))
    old_claim = _norm_ans(old_ans)
    new_claim = _norm_ans(new_ans)
    old_mismatch = (old_c is not None and old_claim is not None and old_c != old_claim
                    and v.get("old_conclusion_backlink"))
    new_mismatch = (new_c is not None and new_claim is not None and new_c != new_claim
                    and v.get("new_conclusion_backlink"))
    if new_mismatch and not old_mismatch:
        return "CUT"
    if old_mismatch and not new_mismatch:
        return "KEEP"
    return "UNSURE"


def _score_to_verdict(v: dict, cut_bar: float) -> str:
    """Three-dimension ERROR SCORE -> CUT / KEEP / UNSURE (rev 5, 2026-10-26).

      * all three dims (disconnection / contradiction / error) are 0.0 -> KEEP
        (the transition is clean; the NEW side survives, the OLD side drops). This is
        the previously-missing KEEP class for rubric_cut / rubric_ce.
      * score >= cut_bar -> CUT.
      * otherwise -> UNSURE.

    A missing score (no dims parsed) is UNSURE. The all-zero KEEP cannot collide with
    CUT because score = max(dims) = 0.0 < cut_bar whenever all three dims are zero.
    A "collapse" verdict (the judge pattern-matched identical >=bar dims and was
    zeroed by the parser) is UNSURE, not KEEP -- those three zeros are a rejection, not
    a genuine clean transition.
    """
    if v.get("collapse"):
        return "UNSURE"
    dims = [v.get(d, 0.0) for d in _RUBRIC_NAMES]
    if all(d == 0.0 for d in dims):
        return "KEEP"
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


def _elimination_mode_lock(rec: dict, cuts: dict[tuple[int, int], str], allow_unsure: bool = False, tie_break: str = "abstain", vote_mode: str = "max", weight_by: str = "round") -> tuple[str | None, dict]:
    """Round-weighted mode lock: KEEP/CUT/UNSURE verdicts re-weight each answer run (rev 8, 2026-10-26).

    Every answer-switch sits between two runs. A "run" is one maximal block of identical
    answers -- it IS the round-vote unit: a verdict on the switch re-weights every round
    of the two runs it separates (rounds sharing an answer also share the flanking
    verdicts, so they collapse into the same weight; no separate "fragment" concept).

    A verdict gives each of its two runs a survive-score:

        CUT    -> old side 1.0, new side 0.0  (change unjustified: old survives)
        KEEP   -> old side 0.0, new side 1.0  (change justified: new survives)
        UNSURE -> old side w,   new side w    (w = 0.5 half vote, or inert in "0" mode)

    Then each run folds its (left, right) flank scores into one multiplier, selected by
    ``vote_mode`` (the ablation knob):

        "max"  -> fold = max(flanks), w = 0.5  (conservative: deleted only if both flanks do)
        "min"  -> fold = min(flanks), w = 0.5  (aggressive: deleted if either flank does)
        "0"    -> no half vote (UNSURE inert), fold = max over the hard CUT/KEEP 0/1 flanks

    A run's votes = unit x multiplier, where unit = round_count (weight_by="round") or 1
    (weight_by="fragment"); the non-None answer with the highest total weight locks; None
    never votes. tie_break: "abstain" (default) abstains on a tie;
    "directional" locks the tied answer most-preferred by the judge's confident verdicts
    (CUT -> its LEFT "old" answer; KEEP -> its RIGHT "new" answer), no positional fallback.
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

    # Each switch re-weights BOTH of its neighboring runs with a survive-score; the fold
    # (max/min) and the UNSURE half-vote weight are set by ``vote_mode``.
    n = len(frags)
    left_score = [None] * n    # run i as the NEW side of its left switch
    right_score = [None] * n   # run i as the OLD side of its right switch
    undecided = 0
    combine_min = (vote_mode == "min")
    unsure_w = 0.0 if vote_mode == "0" else 0.5   # "0" = no half vote
    for frm, to in switches:
        v = cuts.get((frm, to))
        if v is None:
            undecided += 1
            continue
        old_i, new_i = frag_idx[frm], frag_idx[to]
        if v == "CUT":            # change unjustified: old survives, new dies
            right_score[old_i] = 1.0
            left_score[new_i] = 0.0
        elif v == "KEEP":         # change justified: new survives, old dies
            right_score[old_i] = 0.0
            left_score[new_i] = 1.0
        else:                     # UNSURE
            if not allow_unsure:
                undecided += 1    # stray UNSURE in a binary run -> abstain
            elif unsure_w == 0.0:
                continue          # "0" mode: no half vote, UNSURE keeps/deletes nothing
            else:
                right_score[old_i] = unsure_w
                left_score[new_i] = unsure_w

    # a run's weight = round_count x fold(present left/right score); here len(frags) > 1,
    # so every run has >= 1 adjacent switch.
    mult: list[float] = []
    for i in range(n):
        present = [s for s in (left_score[i], right_score[i]) if s is not None]
        if not present:
            mult.append(1.0)
        elif combine_min:
            mult.append(min(present))
        else:
            mult.append(max(present))

    info["survivors"] = [frags[i] for i in range(n) if mult[i] > 0.0]
    info["n_switch_undecided"] = undecided

    if undecided:
        info["status"] = "undecided_switch"
        return None, info

    # weight per answer = sum over its fragments of (round_count x multiplier); None
    # never votes.
    weight: dict = {}
    for i, f in enumerate(frags):
        a = f["ans"]
        if a is None:
            continue
        # weight_by="round" -> each round votes (len); "fragment" -> each run votes once (1).
        unit = len(f["rounds"]) if weight_by == "round" else 1
        weight[a] = weight.get(a, 0.0) + unit * mult[i]
    info["weights"] = weight

    if not weight:
        info["status"] = "no_survivors"
        return None, info

    max_w = max(weight.values())
    top = [a for a, w in weight.items() if w == max_w]
    if len(top) == 1:
        info["status"] = "locked_majority"
        info["mode"] = top[0]
        return top[0], info

    # tie: abstain by default; optionally break it directionally. Count, over the
    # judge's confident verdicts, how often each tied answer is the PREFERRED side
    # (CUT -> its LEFT "old" answer; KEEP -> its RIGHT "new" answer) and lock the
    # most-preferred. No confident preference -> stay abstain (do not guess).
    if tie_break == "directional":
        pref: dict = {}
        for frm, to in switches:
            v = cuts.get((frm, to))
            li, ri = frag_idx[frm], frag_idx[to]
            if v == "CUT":
                a = frags[li].get("ans")
            elif v == "KEEP":
                a = frags[ri].get("ans")
            else:
                continue
            if a is not None:
                pref[a] = pref.get(a, 0) + 1
        if pref:
            choice = max(top, key=lambda a: pref.get(a, 0))
            if pref.get(choice, 0) > 0:
                info["status"] = "locked_directional"
                info["mode"] = choice
                info["tie_among"] = top
                info["pref"] = pref
                return choice, info

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


def evaluate_one(agent: HuggingFaceAgent, rec: dict, strategy: dict, rubric_threshold: float = 8.0, sidecar: dict | None = None, blind: bool = False, error_vocab: str | None = None) -> dict:
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
    is_rubric = (agg in ("rubric_cut", "rubric_ce"))
    is_ce = (agg == "rubric_ce")
    is_v5 = (agg == "rubric_v5")
    allow_unsure = (agg in _CONSERVATIVE_AGGS) or is_rubric or is_v5
    switches = _switch_edges(rec)
    directed = _build_directed(rec, sidecar) if (is_rubric or is_v5) else {}
    cuts: dict[tuple[int, int], str] = {}
    per_switch: dict[tuple[int, int], dict] = {}
    raw = None
    attempts = 0
    undecided = list(switches)
    tok = [0, 0, 0]  # [prompt, completion, reasoning] accumulated across passes
    parse_fn = _parse_rubric_verdicts if is_rubric else _parse_verdicts
    cot_by_to = _reasoning_by_to(rec)
    ans_by_r = {r["r"]: r.get("ans") for r in rec.get("rounds", [])}

    def _absorb(content) -> None:
        nonlocal undecided
        if is_v5:
            got = _parse_rubric_v5_verdicts(content or "", cot_by_to)
        else:
            got = parse_fn(content or "")
        for e, v in got.items():
            if is_v5:
                per_switch[e] = v
                cuts[e] = _v5_to_verdict(v, ans_by_r.get(e[0]), ans_by_r.get(e[1]))
            elif is_rubric:
                per_switch[e] = v
                if is_ce:
                    # rubric_ce: same three-dim judge, but the CUT trigger scores only on
                    # contradiction+error (the two discriminative dims); the direction-agnostic
                    # disconnection is kept raw but excluded from the gate.
                    v["score"] = max(v.get("contradiction", 0.0), v.get("error", 0.0))
                cuts[e] = _score_to_verdict(v, rubric_threshold)
            else:
                cuts[e] = v
        undecided = [e for e in undecided if e not in got]

    # Pass 1: open KEEP/CUT(/UNSURE) prompt over all answer-switches.
    if undecided:
        attempts += 1
        if is_v5:
            p1 = build_rubric_v5_prompt(rec, undecided, directed, blind=blind)
        elif is_rubric:
            p1 = build_rubric_cut_prompt(rec, undecided, directed, blind=blind, error_vocab=error_vocab)
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
        if is_v5:
            forced = build_rubric_v5_prompt(rec, undecided, directed, blind=blind)
        elif is_rubric:
            forced = build_rubric_cut_prompt(rec, undecided, directed, blind=blind, error_vocab=error_vocab)
        else:
            forced = build_forced_cut_prompt(rec, undecided, allow_unsure)
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
        # rubric_cut also degrades to mode (a majority-vote "stable state"), not final:
        # an all-UNSURE trace carries no confident CUT/KEEP verdict, so the natural prior
        # is the answer the trace settled on most often.
        # rubric_cut / rubric_ce / rubric_v5 all degrade to mode on an all-UNSURE trace
        # (mode = the majority-vote "stable state"). 2026-10-26: rubric_v5 was flipped
        # from an honest-ABSTAIN fallback to mode -- no backlink-verified error + no
        # confident verdict is a weak signal, not a proof of absence, so the settled mode
        # beats refusing to answer (abstain scores 0 on accuracy).
        if agg.endswith("_mode") or agg in ("rubric_cut", "rubric_ce", "rubric_v5"):
            fallback = "mode"
        else:
            fallback = "final"
        if n_sw > 0 and n_unsure == n_sw:
            info = {"status": f"all_unsure_fallback_{fallback}",
                    "fragments": _ans_fragments(rec),
                    "n_switch": n_sw,
                    "survivors": None,
                    "n_unsure": n_unsure}
            if fallback == "mode":
                verdict = _mode_answer(rec)
            else:
                verdict = rec.get("final_ans")
        else:
            # rubric_cut breaks surviving-count ties by the judge's directional
            # preference (CUT/KEEP side); conservative_cut keeps abstain-on-tie.
            _tie = "directional" if agg in ("rubric_cut", "rubric_ce", "rubric_v5") else "abstain"
            verdict, info = _elimination_mode_lock(rec, cuts, allow_unsure=True, tie_break=_tie, vote_mode=_VOTE_MODE)
    else:
        verdict, info = _elimination_mode_lock(rec, cuts, allow_unsure=allow_unsure, vote_mode=_VOTE_MODE)

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
        "vote_mode": _VOTE_MODE,
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
    ap.add_argument("--critic-sidecar", type=Path, default=None,
                    help="optional strong-critic override JSON (task_id -> {round_str -> direction dict or list}) merged on top of the in-band transition critic_direction; both feed the per-switch directed_check")
    ap.add_argument("--blind", action="store_true",
                    help="rubric_cut blind mode: strip the self-report `reason` AND the critic directed_check, feeding the judge ONLY the hidden derivation steps (no polarity narration)")
    args = ap.parse_args()

    sidecar: dict | None = None
    if args.critic_sidecar:
        sidecar = json.loads(args.critic_sidecar.read_text(encoding="utf-8"))

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

    # 2026-10-22: rubric_cut now shows the evaluator the answer-free L3 wrong-execution
    # bank as an error-dim backlink. RSI_ERROR_VOCAB_CAP=0 (default) = full bank; a
    # positive value truncates head+tail. Empty bank (missing file) is a graceful no-op.
    error_vocab: str | None = None
    if args.strategy in ("rubric_cut", "rubric_ce"):
        cap = int(os.getenv("RSI_ERROR_VOCAB_CAP", "0"))
        error_vocab = _load_rubric_error_vocab(args.model, cap_chars=cap or None)

    recs = [json.loads(l) for l in open(args.transitions, encoding="utf-8")]
    # Stage-B target (new口径, 2026-10-19): MULTI-ANSWER tasks -- >=2 distinct committed
    # candidate answers -- trigger the RSI self-review, regardless of settle. The trigger
    # is the observable "multi-answer" fact (no gold needed). Single-answer tasks skip.
    recs = [r for r in recs if len(r.get("candidates", [])) >= 2]
    if args.limit:
        recs = recs[:args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # Atomic write: stage to a temp file then rename, so overlapping/concurrent runs
    # (or a killed background job) can never leave a half-written or interleaved
    # .verdict.jsonl that breaks line-based readers with stray bytes.
    tmp_out = args.out.with_suffix(args.out.suffix + f".tmp.{os.getpid()}")
    with open(tmp_out, "w", encoding="utf-8") as fout:
        # serial smoke-first; concurrency is a fast-follow, not needed for correctness
        for i, rec in enumerate(recs, 1):
            res = evaluate_one(agent, rec, strategy, rubric_threshold=args.rubric_threshold, sidecar=sidecar, blind=args.blind, error_vocab=error_vocab)
            fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            fout.flush()
            rows.append(res)
            behavior = "answer" if res["verdict"] is not None else "abstain"
            print(f"[{i}/{len(recs)}] {res['task_id']} gold={res['gold']} "
                  f"verdict={res['verdict']} ({behavior}) lock={res['lock_status']} "
                  f"correct={res['correct']} meta={res['meta_correct']}", flush=True)

    os.replace(tmp_out, args.out)
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