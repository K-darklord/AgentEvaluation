#!/usr/bin/env python3
"""qwen replication frozen scoring -> is_correct_t3_sidecar_rep.json.

Frozen per-round protocol, identical to the main experiment
(scripts/gen_t3_sidecar_v3.py / scripts/s1_a3extra_k1_sidecar.py):
    finish_reason == "length"  -> {"c": false, "s": "trunc"}
    else T1 deterministic match -> {"c": true,  "s": "t1"}
    else astra (gpt-6-astra) K=1 -> {"c": bool, "s": "astra_true"/"astra_false"}
    then K3 RULES adjudication  -> {"c": bool, "s": "adjudicated", "adj": true}

Arms: A, A2, A2P, A3, C2 (no C3). Sidecar is per-round verdicts only; winner-level
metrics are computed downstream in REPLICATION_RESULTS generation.

astra K=1 verdicts are cached in astra_verdicts_rep.jsonl keyed on
(task_id, final_answer); resumable.

Run:  python3 scripts/gen_t3_sidecar_rep.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.score_hle_arms  # noqa: E402,F401  (_load_dotenv + _force_no_proxy)
import src.hle_scorer as hs  # noqa: E402
from src import config  # noqa: E402
from src.score_hle_arms import load_index, read_traj  # noqa: E402

import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
M = "qwen3.8-flash-payg"
ARMS = ["A", "A2", "A2P", "A3", "C2"]
T3 = AGENT_ROOT / "experiments/hle400/t3"
ASTRA_CACHE = T3 / "astra_verdicts_rep.jsonl"
SIDECAR_OUT = T3 / "is_correct_t3_sidecar_rep.json"


def exp_dir(arm):
    return f"rep200_{arm}_qwen3.8-flash-payg"


def traj_path(arm):
    return AGENT_ROOT / "experiments" / exp_dir(arm) / M / "loop_trajectories.jsonl"


# ---------------------------------------------------------------------------
# K3 dispute rules (frozen copy from scripts/t3_k3_adjudicate_and_recompute.py)
# ---------------------------------------------------------------------------
def ws(s):
    return " ".join(str(s).split())


def has(*subs):
    return lambda a: all(s in a for s in subs)


def rx(p):
    return lambda a: bool(re.search(p, a))


RULES = [
 ("hle_280", lambda a: re.search(r"log\\?\!?\s*\\?\(?\s*\\?left\(?\s*2\s*\+", a) is not None and "sqrt" in a and not re.match(r"\\\[\s*B\s*\+", a), True,
  "Theta-equivalent to gold: max/sum are Theta-equal, log(2+L/B) ~ log(L/B) when L>>B and the sqrt term dominates when L<=B", "medium", True),
 ("hle_280", rx(r"log\s*\\?\(?\s*\\?left\(?\s*1\s*\+"), False, "log(1+L/B) gives Theta(B) when L<B, not Theta(sqrt(BL))", "medium", False),
 ("hle_021", lambda a: ("\\bot\\multimap" in a or "\\bot \\multimap" in a) and ("0}=1" in a or "(0)=1" in a or "{0}=1" in a) and "C" in a, True,
  "f(w)=bot^w -o 1 with C=f(b)^{(x)m}: verified derivable/non-derivable; question asks for ANY encoding", "medium", True),
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
  "derived: b=alpha P1 maximises |K_Y|; clipping to |b|<=sqrt(P2) is power-feasible optimum", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "-", False, "-alpha P1 as primary is wrong sign under X2=U2+bZ1", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "other", False, "b=alpha / b=0 / other: not alpha P1", "high", False),
 ("hle_153", lambda a: "\\int" in a and ("\\mathcal{D}" in a or "\\mathcal D" in a or "D[" in a) and "exp" in a.lower() and not a.startswith("with Grassmann"), True,
  "question asks for the imaginary-time path-integral form; gold is the operator trace", "medium", True),
 ("hle_386", lambda a: ("isomeriz" in a.lower() or "isomerise" in a.lower()) and not a.startswith("At sunrise and sunset") and "sunrise and sunset it must be flat" not in a and not a.startswith("It must continuously adjust"), True,
  "trans-cis photoisomerization IS rotation about the N=N bond", "medium", True),
 ("hle_170", lambda a: ws(a).replace(" ", "") == "DDSSDS", True, "exact", "high", False),
 ("hle_170", lambda a: ws(a).replace(" ", "") != "DDSSDS", False, "no committed six-foot D/S string (or wrong string)", "high", False),
 ("hle_036", lambda a: _num_close(a, 1.03, 0.005), True, "within 0.5% of 1.03", "high", False),
 ("hle_036", lambda a: (_first_num(a) is not None) and not _num_close(a, 1.03, 0.005), False, "numeric value outside 0.5% of 1.03 (1.0436 is 1.3% off)", "high", False),
 ("hle_121", lambda a: ("y" in a and "b" in a and "\\ge" in a.replace("≥", "\\ge")) and len(a) < 400, True,
  "verified case-by-case: each variant forces y=min(0,x) for x<1 and is consistent with y=x-1 for x>=1", "high", False),
 ("hle_374", lambda a: re.fullmatch(r"[UDLR]+", ws(a).replace(" ", "")) is not None and re.sub(r"(.)\1+", r"\1", ws(a).replace(" ", "")) == "ULDL", True,
  "compresses to ULDL per the question's own rule", "high", False),
 ("hle_201", lambda a: "2^{50}" in a and "2^{100}" not in a and "\\binom{50}{25}" in a and "25-3k" in a, True,
  "form pi/2^50 * (C(50,25)^2 + 2*sum ...) — exact rational equality with gold", "high", False),
 ("hle_201", lambda a: (("(50!)^2" in a) or ("(50!)^{2}" in a)) and "4^{25}" in a and "m+25" in a, True,
  "form pi*(50!)^2/(4^25*25!) * sum ... — exact rational equality with gold", "high", False),
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


def astra_judge(question, gold, response):
    last_served = None
    for _ in range(3):
        try:
            r = get_client().chat.completions.create(
                model=config.ASTRA_MODEL,
                messages=[{"role": "user", "content": hs.JUDGE_PROMPT.format(question=question, response=response[:4000], gold=gold)}],
                max_tokens=200, temperature=0,
            )
            txt = (r.choices[0].message.content or "").strip().upper()
            served = getattr(r, "model", None)
            if txt.startswith("CORRECT"):
                return True, served
            if txt.startswith("INCORRECT"):
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
            cache[(d["task_id"], d["final_answer"])] = d.get("c")
    return cache


def score_round(meta, tid, r, astra_cache, dry_run):
    fa = (r.get("final_answer") or "").strip()
    if r.get("finish_reason") == "length":
        return {"c": False, "s": "trunc"}
    if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
        return {"c": True, "s": "t1"}
    key = (tid, fa)
    if key in astra_cache:
        v = astra_cache[key]
        return {"c": bool(v), "s": "astra_true" if v else "astra_false"}
    if dry_run:
        return {"c": None, "s": "astra_needed"}
    verdict, _ = astra_judge(meta["question"], meta["gold"], fa)
    if verdict is None:
        verdict = False
    with open(ASTRA_CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"task_id": tid, "final_answer": fa, "c": verdict}, ensure_ascii=False) + "\n")
    astra_cache[key] = verdict
    return {"c": bool(verdict), "s": "astra_true" if verdict else "astra_false"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no live astra calls")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    idx = load_index(INDEX)
    astra_cache = load_astra_cache()

    # collect (arm, tid, round) needing a fresh astra call (non-trunc, T1-missed, uncached)
    todo = []  # list of (arm, tid, round_index, key)
    for arm in ARMS:
        traj = read_traj(traj_path(arm))
        if not traj:
            print(f"ERROR: no trajectory for {arm}", file=sys.stderr)
            return 1
        for tid in sorted(traj):
            meta = idx[tid]
            for i, r in enumerate(traj[tid]["rounds"]):
                fa = (r.get("final_answer") or "").strip()
                if r.get("finish_reason") == "length":
                    continue
                if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
                    continue
                key = (tid, fa)
                if key in astra_cache:
                    continue
                todo.append((arm, tid, i, key))

    # dedup keys across arms (same (tid, fa) judged once)
    seen = set()
    unique_todo = []
    for arm, tid, i, key in todo:
        if key in seen:
            continue
        seen.add(key)
        unique_todo.append((arm, tid, i, key))

    print(f"astra: cached={sum(1 for v in astra_cache.values() if v is not None)} "
          f"todo={len(unique_todo)} dry_run={args.dry_run}", flush=True)

    if not args.dry_run and unique_todo:
        ASTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        fh = ASTRA_CACHE.open("a", encoding="utf-8")

        def process(item):
            arm, tid, i, key = item
            m = idx[tid]
            verdict, served = astra_judge(m["question"], m["gold"], key[1])
            if verdict is None:
                verdict = False
            return {"task_id": tid, "final_answer": key[1], "c": verdict, "served_model": served}

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(process, it): it for it in unique_todo}
            for n, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                astra_cache[(rec["task_id"], rec["final_answer"])] = rec["c"]
                if n % 50 == 0 or n == len(unique_todo):
                    print(f"  astra {n}/{len(unique_todo)}", flush=True)
        fh.close()

    # final scoring pass
    arms_out = {}
    stats = Counter()
    for arm in ARMS:
        traj = read_traj(traj_path(arm))
        arm_rows = {}
        for tid in sorted(traj):
            meta = idx[tid]
            rows = []
            for r in traj[tid]["rounds"]:
                s = score_round(meta, tid, r, astra_cache, dry_run=args.dry_run)
                if s.get("c") is None:
                    rows.append(s)
                    continue
                adj = adjudicate(tid, (r.get("final_answer") or "").strip())
                if adj is not None:
                    v, reason, conf, ask = adj
                    s = {"c": v, "s": "adjudicated", "adj": True}
                rows.append(s)
                stats[s["s"]] += 1
            arm_rows[tid] = rows
        arms_out[arm] = arm_rows

    out = {
        "note": "qwen replication sidecar; frozen protocol (trunc > T1 > astra K1 > K3 rules). "
                "K3 rules reused verbatim from main experiment.",
        "stats": dict(stats),
        "arms": arms_out,
    }
    if not args.dry_run:
        SIDECAR_OUT.parent.mkdir(parents=True, exist_ok=True)
        SIDECAR_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"\n== rep sidecar stats ==\n  {dict(stats)}", flush=True)
        print(f"-> {SIDECAR_OUT}", flush=True)
    else:
        print(f"\n== dry-run: stats ==\n  {dict(stats)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
