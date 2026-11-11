#!/usr/bin/env python3
"""S1 scoring: A3 extra rounds 10-11 -> is_correct_t3_sidecar_A3extra.json.

Frozen protocol, identical to the pipeline that built is_correct_t3_sidecar_v2.json:
  per round: finish_reason=="length" -> trunc (wrong)
             else existing variant -> reuse the frozen v2 verdict (same substance =>
             same verdict); else T1 exact-match -> t1; else astra (gpt-6-astra) K=1 ->
             astra_true/astra_false; then K3 dispute rules (copied verbatim from
             scripts/t3_k3_adjudicate_and_recompute.py) may override.

Output: experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json  (sidecar v2 format,
        arms["A3extra"][task_id] = two {c,s} entries for rounds 10 and 11).
"""
from __future__ import annotations

import json
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.score_hle_arms  # noqa: E402  (_load_dotenv + _force_no_proxy)
import src.hle_scorer as hs  # noqa: E402
from src import config  # noqa: E402
import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

from src.score_hle_arms import load_index, read_traj  # noqa: E402

INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
SIDECAR_V2 = AGENT_ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_v2.json"
A3EXTRA_TRAJ = AGENT_ROOT / "experiments/hle400_A3_extra/deepseek-v4-flash/loop_trajectories.jsonl"
ASTRA_CACHE = AGENT_ROOT / "experiments/hle400_A3_extra/t3/astra_verdicts.jsonl"
SIDECAR_OUT = AGENT_ROOT / "experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json"

# ---------------------------------------------------------------------------
# K3 dispute rules (frozen copy from scripts/t3_k3_adjudicate_and_recompute.py)
# ---------------------------------------------------------------------------
def ws(s):
    return " ".join(str(s).split())


def has(*subs):
    return lambda a: all(s in a for s in subs)


def rx(p):
    r = re.compile(p, re.S)
    return lambda a: bool(r.search(a))


RULES = [
 ("hle_280", lambda a: re.search(r"log\\?\!?\s*\\?\(?\s*\\?left\(?\s*2\s*\+", a) is not None and "sqrt" in a and not re.match(r"\\\[\s*B\s*\+", a), True,
  "Theta-equivalent to gold: max/sum are Theta-equal, log(2+L/B) ~ log(L/B) when L>>B and the sqrt term dominates when L<=B", "medium", True),
 ("hle_280", rx(r"log\s*\\?\(?\s*\\?left\(?\s*1\s*\+"), False, "log(1+L/B) gives Theta(B) when L<B, not Theta(sqrt(BL))", "medium", False),
 ("hle_021", lambda a: ("\\bot\\multimap" in a or "\\bot \\multimap" in a) and ("0}=1" in a or "(0)=1" in a or "{0}=1" in a) and "C" in a, True,
  "f(w)=bot^w -o 1 with C=f(b)^{(x)m}: verified derivable/non-derivable on {1,1}/2, {2}/1x2, {1,2}/1x3, {1,3}/2x2, {4}/2x2; question asks for ANY encoding", "medium", True),
 ("hle_021", has("\\bot\\otimes\\cdots\\otimes\\bot}_{w", "\\multimap 1"), True, "same encoding (ii), uncurried form", "medium", True),
 ("hle_021", has("f(w)=(A^{\\,w})\\multimap 1"), True, "same encoding (ii)", "medium", True),
 ("hle_021", has("\\underline{0}=\\bot"), False, "1 -o X == X in MLL, so f(w) collapses to bot: not an encoding", "high", False),
 ("hle_021", has("f(n+1)=1\\multimap f(n)"), False, "1 -o X == X, collapses", "high", False),
 ("hle_021", lambda a: "\\otimes \\bot" in a or "\\otimes\\bot" in a and "\\multimap" not in a, False, "f(w)=bot^{(x)w}: sequent derivable for every W with sum=mb, does not encode EP", "high", False),
 ("hle_030", rx(r"r\^\{\s*\\?,?\s*A\(1-\\cos\\theta\)\+B\\sin\\theta"), True,
  "answer exhibits the corrector r^{A(1-cos th)+B sin th} (alone or multiplying the known A=B=0 profile)", "medium", True),
 ("hle_030", rx(r"r\^\{-A\(1-\\cos\\theta\)-B"), False, "wrong sign", "high", False),
 ("hle_030", rx(r"e\^\{-?B\\theta\}|e\^\{-B\\frac"), False, "B-dependence wrong (exp instead of power of r)", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "+", True,
  "derived: with X2=U2+bZ1, |K_Y|=(P1+1)(P2+2b alpha+1)-(b+alpha)^2 is maximised at b=alpha P1; clipping to |b|<=sqrt(P2) is the power-feasible optimum", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "-", False, "-alpha P1 as the primary value is the wrong sign under X2=U2+bZ1 (restore rejected)", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "other", False, "b=alpha / b=0 / other: not alpha P1", "high", False),
 ("hle_153", lambda a: "\\int" in a and ("\\mathcal{D}" in a or "\\mathcal D" in a or "D[" in a) and "exp" in a.lower() and not a.startswith("with Grassmann"), True,
  "question asks for the imaginary-time path-integral form; gold is the operator trace. Judge follows the question", "medium", True),
 ("hle_386", lambda a: ("isomeriz" in a.lower() or "isomerise" in a.lower()) and not a.startswith("At sunrise and sunset") and "sunrise and sunset it must be flat" not in a and not a.startswith("It must continuously adjust"), True,
  "trans-cis photoisomerization IS rotation about the N=N bond; the vaguer 'flip over or change shape ... mimicking trans-cis photoisomerization' is the same claim", "medium", True),
 ("hle_170", lambda a: ws(a).replace(" ", "") == "DDSSDS", True, "exact", "high", False),
 ("hle_170", lambda a: ws(a).replace(" ", "") != "DDSSDS", False, "no committed six-foot D/S string (or wrong string)", "high", False),
 ("hle_036", lambda a: _num_close(a, 1.03, 0.005), True, "within 0.5% of 1.03", "high", False),
 ("hle_036", lambda a: (_first_num(a) is not None) and not _num_close(a, 1.03, 0.005), False, "numeric value outside 0.5% of 1.03 (1.0436 is 1.3% off)", "high", False),
 ("hle_121", lambda a: ("y" in a and "b" in a and "\\ge" in a.replace("≥", "\\ge")) and len(a) < 400, True,
  "verified case-by-case (b=0/1 with a=0/1): each variant forces y=min(0,x) for x<1 and is consistent with y=x-1 for x>=1 (needs l<=0, as the gold does)", "high", False),
 ("hle_374", lambda a: re.fullmatch(r"[UDLR]+", ws(a).replace(" ", "")) is not None and re.sub(r"(.)\1+", r"\1", ws(a).replace(" ", "")) == "ULDL", True, "compresses to ULDL per the question's own rule", "high", False),
 ("hle_201", lambda a: "2^{50}" in a and "2^{100}" not in a and "\\binom{50}{25}" in a and "25-3k" in a, True,
  "form pi/2^50 * (C(50,25)^2 + 2*sum_{k=1..8} (-1)^k C(50,25-k)C(50,25-3k)) — exact rational equality with gold", "high", False),
 ("hle_201", lambda a: (("(50!)^2" in a) or ("(50!)^{2}" in a)) and "4^{25}" in a and "m+25" in a, True,
  "form pi*(50!)^2/(4^25*25!) * sum 1/((50-2m)! m! (m+25)!) — exact rational equality with gold", "high", False),
]


def _b_sign(a):
    m = re.search(r"b(?:_\{?\\?(?:text\{)?opt\}?\}?|\^?\*?|\^\{?\*\}?)?\s*=\s*(.{0,160})", a, re.S)
    if not m:
        return None
    rhs = " ".join(m.group(1).split())
    for _ in range(10):
        rhs = re.sub(r"^(\s|\\\(|\\\[|\(|\[|\{|\\boxed\{|\\begin\{cases\}|\\operatorname\{clip\}\(|\\left\(|\\,|\\;|\\!|\\ |\\quad|%)+", "", rhs)
    rhs = re.sub(r"^\\operatorname\{sgn\}\(\\alpha\)\s*\\min\s*\\left\(\s*\|\\alpha\|\s*", "\\alpha ", rhs)
    if re.match(r"-\s*\\alpha\s*P_?\{?1", rhs):
        return "-"
    if re.match(r"\\alpha\s*P_?\{?1|P_?\{?1\}?\s*\\alpha", rhs):
        return "+"
    return "other"


def _first_num(a):
    m = re.search(r"-?\d+\.\d+|-?\d+", a.replace(",", ""))
    return float(m.group()) if m else None


def _num_close(a, g, tol):
    v = _first_num(a)
    return v is not None and abs(v - g) <= tol * abs(g)


def adjudicate(task, ans):
    a = ans.strip()
    for t, pred, verdict, reason, conf, ask in RULES:
        if t == task:
            try:
                if pred(a):
                    return verdict, reason, conf, ask
            except Exception:
                pass
    return None


# ---------------------------------------------------------------------------
# astra K1 judge (mirror scripts/c2_k1_sidecar.py)
# ---------------------------------------------------------------------------
_client = None
_client_lock = threading.Lock()


def get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(
                    base_url=config.ASTRA_BASE_URL,
                    api_key=config.ASTRA_API_KEY,
                    timeout=httpx.Timeout(150.0, connect=15.0),
                )
    return _client


def astra_once(question, gold, response):
    client = get_client()
    prompt = hs.JUDGE_PROMPT.format(question=question, response=response[:4000], gold=gold)
    r = client.chat.completions.create(
        model=config.ASTRA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )
    txt = r.choices[0].message.content or ""
    return txt, getattr(r, "model", None)


def astra_judge(question, gold, response):
    last_served = None
    for _ in range(3):
        try:
            txt, served = astra_once(question, gold, response)
            up = txt.strip().upper()
            if up.startswith("CORRECT"):
                return True, served
            if up.startswith("INCORRECT"):
                return False, served
            last_served = served
        except Exception as e:  # noqa: BLE001
            last_served = f"ERR:{type(e).__name__}"
    return None, last_served


def load_astra_cache():
    cache = {}
    if ASTRA_CACHE.exists():
        for line in ASTRA_CACHE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cache[(d["task_id"], d["final_answer"])] = d.get("verdict")
    return cache


def build_variant_map():
    """Map (task_id, final_answer text) -> frozen v2 final verdict for every non-trunc
    round across all arms. Trunc rounds are skipped (trunc is per-round, not per-variant)."""
    v2 = json.loads(SIDECAR_V2.read_text(encoding="utf-8"))["arms"]
    traj_dirs = {a: ("deepseek-v4-flash-payg" if a in ("C2", "A2P") else "deepseek-v4-flash")
                 for a in ("A", "A2", "A3", "C3", "C2", "A2P")}
    exp_dirs = {a: ("hle400_A2PRIME" if a == "A2P" else f"hle400_{a}")
                for a in ("A", "A2", "A3", "C3", "C2", "A2P")}
    vm = {}
    for arm in ("A", "A2", "A3", "C3", "C2", "A2P"):
        traj = read_traj(AGENT_ROOT / "experiments" / exp_dirs[arm] / traj_dirs[arm]
                         / "loop_trajectories.jsonl")
        side = v2[arm]
        for tid, task in traj.items():
            rounds = task["rounds"]
            verdicts = side.get(tid, [])
            for i, r in enumerate(rounds):
                if r.get("finish_reason") == "length":
                    continue
                fa = (r.get("final_answer") or "").strip()
                if not fa:
                    continue
                if i < len(verdicts):
                    vm[(tid, fa)] = verdicts[i]
    return vm


def verdict_for(tid, meta, r, variant_map, astra_cache):
    """Final frozen verdict for one A3extra round: trunc > reuse-variant > T1 > astra K1,
    then K3 rules may override a fresh (non-reused) verdict."""
    fa = r.get("final_answer", "")
    if r.get("finish_reason") == "length":
        return {"c": False, "s": "trunc"}
    key = (tid, fa.strip())
    if key in variant_map:
        return dict(variant_map[key])  # reuse frozen v2 final verdict verbatim
    # fresh variant: K1 (T1 or astra), then K3 rules
    if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
        base = {"c": True, "s": "t1"}
    else:
        v = astra_cache.get(key)
        base = {"c": bool(v), "s": "astra_true" if v else "astra_false"}
    adj = adjudicate(tid, fa)
    if adj is not None:
        vv, _reason, _conf, _ask = adj
        changed = base["c"] != vv
        return {"c": vv, "s": "adjudicated" if changed else base["s"], "adj": True}
    return base


def main():
    idx = load_index(INDEX)
    traj = read_traj(A3EXTRA_TRAJ)
    if not traj:
        print(f"ERROR: no trajectory at {A3EXTRA_TRAJ}", file=sys.stderr)
        return 1
    variant_map = build_variant_map()
    astra_cache = load_astra_cache()

    # collect fresh variants needing astra (not trunc, not reused, T1 missed)
    todo = []
    for tid in sorted(traj):
        meta = idx[tid]
        for r in traj[tid]["rounds"]:
            fa = r.get("final_answer", "")
            if r.get("finish_reason") == "length":
                continue
            key = (tid, fa.strip())
            if key in variant_map:
                continue
            if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
                continue
            todo.append(key)

    to_judge = [k for k in todo if astra_cache.get(k) is None]
    print(f"astra: cached={sum(1 for v in astra_cache.values() if v is not None)} "
          f"todo={len(todo)} to_judge={len(to_judge)}", flush=True)
    if to_judge:
        ASTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        fh = ASTRA_CACHE.open("a", encoding="utf-8")

        def process(key):
            tid, fa = key
            m = idx[tid]
            verdict, served = astra_judge(m["question"], m["gold"], fa)
            return {"task_id": tid, "final_answer": fa,
                    "verdict": verdict, "served_model": served}

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(process, k): k for k in to_judge}
            for i, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                astra_cache[(rec["task_id"], rec["final_answer"])] = rec["verdict"]
                if i % 50 == 0 or i == len(to_judge):
                    print(f"  astra {i}/{len(to_judge)}", flush=True)
        fh.close()

    arms = {}
    stats = Counter()
    for tid in sorted(traj):
        meta = idx[tid]
        out_rows = [verdict_for(tid, meta, r, variant_map, astra_cache)
                    for r in traj[tid]["rounds"]]
        for v in out_rows:
            stats[v["s"]] += 1
        arms[tid] = out_rows

    out = {
        "arm": "A3extra",
        "note": "S1 A3 extra rounds 10-11 sidecar; frozen protocol (trunc > reuse-variant "
                "> T1 > astra K1 > K3 rules). Variants already adjudicated in "
                "is_correct_t3_sidecar_v2.json are reused verbatim.",
        "stats": dict(stats),
        "arms": {"A3extra": arms},
    }
    SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIDECAR_OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n== A3extra sidecar stats ==\n  {dict(stats)}", flush=True)
    print(f"-> {SIDECAR_OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
