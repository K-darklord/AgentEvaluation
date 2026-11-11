#!/usr/bin/env python3
"""Generate is_correct_t3_sidecar_v3.json + rerun manifest (api_failure repair).

For the hle400 main experiment, the api_failure repair (rule 1 + rule 3) rewrote a
small set of task trajectories. This script re-scores ONLY the rerun tasks under the
exact frozen protocol, and merges the new per-round verdicts into the v2 sidecar to
produce v3. v2 is preserved verbatim.

Frozen per-round protocol (identical to t3_k3_adjudicate_and_recompute.py):
    finish_reason == "length"        -> {"c": false, "s": "trunc"}
    else T1 deterministic match      -> {"c": true,  "s": "t1"}
    else astra (gpt-6-astra) K=1     -> {"c": bool,  "s": "astra_true"/"astra_false"}
    then K3 RULES adjudication       -> {"c": bool,  "s": "adjudicated", "adj": true}

astra K=1 verdicts are reused from the frozen K1 sidecars via a memo keyed on
(task_id, final_answer); only genuinely-new T1-missed answers trigger a live astra
call (resumable cache astra_verdicts_v3.jsonl).

Also emits a manifest: per arm / rerun task -> rounds before/after, old (v2) vs new
(v3) winner-level correctness for the arm's canonical metric.

Run:  python3 scripts/gen_t3_sidecar_v3.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re as _re
import sys
import threading
from collections import Counter
from pathlib import Path

AGENT_ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
sys.path.insert(0, str(AGENT_ROOT))

import src.score_hle_arms  # noqa: E402,F401  (_load_dotenv + _force_no_proxy)
import src.hle_scorer as hs  # noqa: E402
from src import config  # noqa: E402
from src.score_hle_arms import load_index, read_traj, _settle_idx, _mode_idx, _key  # noqa: E402

import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

T3 = AGENT_ROOT / "experiments/hle400/t3"
INDEX = AGENT_ROOT / "data/raw/hle/hle_400_new.jsonl"
V2_PATH = T3 / "is_correct_t3_sidecar_v2.json"
V3_PATH = T3 / "is_correct_t3_sidecar_v3.json"
ASTRA_CACHE = T3 / "astra_verdicts_v3.jsonl"
MANIFEST_PATH = T3 / "api_failure_rerun_manifest.json"

# arm -> (exp_dir, traj_dir, original_backup, K1 sidecar file)
ARMS = {
    "A":   ("hle400_A",       "deepseek-v4-flash",      None, "is_correct_t3_sidecar.json"),
    "A2":  ("hle400_A2",      "deepseek-v4-flash",      "loop_trajectories.jsonl.bak_apifail_20261110_232641", "is_correct_t3_sidecar.json"),
    "A3":  ("hle400_A3",      "deepseek-v4-flash",      "loop_trajectories.jsonl.bak_apifail_20261110_232700", "is_correct_t3_sidecar.json"),
    "C3":  ("hle400_C3",      "deepseek-v4-flash",      "loop_trajectories.jsonl.bak_apifail_20261110_232648", "is_correct_t3_sidecar.json"),
    "C2":  ("hle400_C2",      "deepseek-v4-flash-payg", "loop_trajectories.jsonl.bak_apifail_20261110_225209", "is_correct_t3_sidecar_C2.json"),
    "A2P": ("hle400_A2PRIME", "deepseek-v4-flash-payg", "loop_trajectories.jsonl.bak_apifail_20261110_232652", "is_correct_t3_sidecar_A2P.json"),
}
CANONICAL = {"A": "init", "A2": "mode", "A3": "vote", "C3": "mode", "C2": "mode", "A2P": "mode"}


# ---- K3 RULES (verbatim copy from t3_k3_adjudicate_and_recompute.py) ----
def ws(s): return " ".join(str(s).split())
def has(*subs):
    return lambda a: all(s in a for s in subs)
def rx(p):
    return lambda a: bool(_re.search(p, a))

RULES = [
 ("hle_280", lambda a: _re.search(r"log\\?\!?\s*\\?\(?\s*\\?left\(?\s*2\s*\+", a) is not None and "sqrt" in a and not _re.match(r"\\\[\s*B\s*\+", a), True,
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
 ("hle_036", lambda a: (_first_num(a) is not None) and not _num_close(a, 1.03, 0.005), False, "numeric value outside 0.5% of 1.03", "high", False),
 ("hle_121", lambda a: ("y" in a and "b" in a and "\\ge" in a.replace("≥", "\\ge")) and len(a) < 400, True,
  "verified case-by-case: each variant forces y=min(0,x) for x<1 and is consistent with y=x-1 for x>=1", "high", False),
 ("hle_374", lambda a: _re.fullmatch(r"[UDLR]+", ws(a).replace(" ", "")) is not None and _re.sub(r"(.)\1+", r"\1", ws(a).replace(" ", "")) == "ULDL", True,
  "compresses to ULDL per the question's own rule", "high", False),
 ("hle_201", lambda a: "2^{50}" in a and "2^{100}" not in a and "\\binom{50}{25}" in a and "25-3k" in a, True,
  "form pi/2^50 * (C(50,25)^2 + 2*sum ...) — exact rational equality with gold", "high", False),
 ("hle_201", lambda a: (("(50!)^2" in a) or ("(50!)^{2}" in a)) and "4^{25}" in a and "m+25" in a, True,
  "form pi*(50!)^2/(4^25*25!) * sum ... — exact rational equality with gold", "high", False),
]

def _b_sign(a):
    m = _re.search(r"b(?:_\{?\\?(?:text\{)?opt\}?\}?|\^?\*?|\^\{?\*\}?)?\s*=\s*(.{0,160})", a, _re.S)
    if not m: return None
    rhs = " ".join(m.group(1).split())
    for _ in range(10):
        rhs = _re.sub(r"^(\s|\\\(|\\\[|\(|\[|\{|\\boxed\{|\\begin\{cases\}|\\operatorname\{clip\}\(|\\left\(|\\,|\\;|\\!|\\ |\\quad|%)+", "", rhs)
    rhs = _re.sub(r"^\\operatorname\{sgn\}\(\\alpha\)\s*\\min\s*\\left\(\s*\|\\alpha\|\s*", "\\alpha ", rhs)
    if _re.match(r"-\s*\\alpha\s*P_?\{?1", rhs): return "-"
    if _re.match(r"\\alpha\s*P_?\{?1|P_?\{?1\}?\s*\\alpha", rhs): return "+"
    return "other"

def _first_num(a):
    m = _re.search(r"-?\d+\.\d+|-?\d+", a.replace(",", ""))
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


# ---- astra K1 (verbatim methodology from c2_k1_sidecar.py) ----
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


def load_k1_sidecars():
    out = {}
    for arm, (_, _, _, k1_file) in ARMS.items():
        p = T3 / k1_file
        if not p.exists():
            continue
        data = json.load(open(p))
        arms = data.get("arms", {})
        if arm in arms:
            out[arm] = arms[arm]
    return out


def build_astra_memo(k1_side):
    """memo[(task_id, final_answer)] = bool from the frozen K1 sidecars (original answers)."""
    memo = {}
    for arm, (exp_dir, traj_dir, bak_name, _) in ARMS.items():
        if bak_name is None:
            continue
        bak_path = AGENT_ROOT / "experiments" / exp_dir / traj_dir / bak_name
        if not bak_path.exists():
            continue
        bak = read_traj(bak_path)
        arms_k1 = k1_side.get(arm, {})
        for tid, rec in bak.items():
            if tid not in arms_k1:
                continue
            rounds = rec.get("rounds", [])
            for i, r in enumerate(rounds):
                if i >= len(arms_k1[tid]):
                    break
                v = arms_k1[tid][i]
                if isinstance(v, dict) and str(v.get("s", "")).startswith("astra_"):
                    fa = r.get("final_answer", "")
                    if fa:
                        memo[(tid, fa)] = bool(v.get("c"))
    return memo


def load_astra_cache():
    cache = {}
    if ASTRA_CACHE.exists():
        for line in ASTRA_CACHE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cache[(d["task_id"], d["final_answer"])] = d["c"]
    return cache


def score_round(meta, tid, r, memo, astra_cache, dry_run):
    fa = r.get("final_answer", "")
    if r.get("finish_reason") == "length":
        return {"c": False, "s": "trunc"}
    if hs.score_t1(meta["gold"], meta["answer_type"], meta["shape"], fa):
        return {"c": True, "s": "t1"}
    key = (tid, fa)
    if key in astra_cache:
        return {"c": bool(astra_cache[key]), "s": "astra_true" if astra_cache[key] else "astra_false"}
    if key in memo:
        return {"c": bool(memo[key]), "s": "astra_true" if memo[key] else "astra_false"}
    if dry_run:
        return {"c": None, "s": "astra_needed"}
    verdict, _ = astra_judge(meta["question"], meta["gold"], fa)
    if verdict is None:
        print(f"  [warn] astra returned None for {tid}; fallback False", flush=True)
        verdict = False
    with open(ASTRA_CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"task_id": tid, "final_answer": fa, "c": verdict}, ensure_ascii=False) + "\n")
    astra_cache[key] = verdict
    return {"c": bool(verdict), "s": "astra_true" if verdict else "astra_false"}


def winner_idx(arm, met, meta, task):
    rs = task["rounds"]
    if met == "init": return 0
    if met == "final": return len(rs) - 1
    if met == "settle": return _settle_idx(meta, task)
    if met == "mode": return _mode_idx(meta, task)
    if met == "vote":
        s = rs[1:]; v = Counter()
        for j, r in enumerate(s):
            k = _key(meta, r)
            if k is not None: v[k] += 1
        if not v: return 1 if s else None
        wk = v.most_common(1)[0][0]
        return 1 + next(j for j, r in enumerate(s) if _key(meta, r) == wk)
    raise ValueError(met)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no live astra calls")
    args = ap.parse_args()

    idx = load_index(INDEX)
    v2 = json.load(open(V2_PATH))
    v2_arms = v2["arms"]

    k1_side = load_k1_sidecars()
    memo = build_astra_memo(k1_side)
    astra_cache = load_astra_cache()

    cur = {}
    bak = {}
    for arm, (exp_dir, traj_dir, bak_name, _) in ARMS.items():
        cur[arm] = read_traj(AGENT_ROOT / "experiments" / exp_dir / traj_dir / "loop_trajectories.jsonl")
        bak[arm] = {}
        if bak_name:
            bp = AGENT_ROOT / "experiments" / exp_dir / traj_dir / bak_name
            if bp.exists():
                bak[arm] = read_traj(bp)

    rerun = {}
    for arm in ARMS:
        changed = []
        for tid in cur[arm]:
            if tid in bak[arm] and json.dumps(cur[arm][tid], sort_keys=True) != json.dumps(bak[arm][tid], sort_keys=True):
                changed.append(tid)
        rerun[arm] = sorted(changed)

    v3_arms = {a: {tid: [dict(x) for x in rows] for tid, rows in v2_arms[a].items()} for a in v2_arms}
    manifest = []
    for arm in ARMS:
        for tid in rerun[arm]:
            meta = idx[tid]
            task = cur[arm][tid]
            old_task = bak[arm].get(tid, {"rounds": []})
            new_rows = []
            for r in task["rounds"]:
                s = score_round(meta, tid, r, memo, astra_cache, args.dry_run)
                if s.get("c") is None:
                    new_rows.append(s)
                    continue
                adj = adjudicate(tid, r.get("final_answer", ""))
                if adj is not None:
                    v, reason, conf, ask = adj
                    s = {"c": v, "s": "adjudicated", "adj": True}
                new_rows.append(s)
            v3_arms[arm][tid] = new_rows
            met = CANONICAL[arm]
            old_correct = None
            if tid in v2_arms[arm]:
                wi = winner_idx(arm, met, meta, old_task)
                if wi is not None and 0 <= wi < len(v2_arms[arm][tid]):
                    old_correct = bool(v2_arms[arm][tid][wi].get("c"))
            new_correct = None
            wi = winner_idx(arm, met, meta, task)
            if wi is not None and 0 <= wi < len(new_rows):
                new_correct = new_rows[wi].get("c")
            manifest.append({
                "arm": arm, "task_id": tid, "metric": met,
                "rounds_before": len(old_task.get("rounds", [])),
                "rounds_after": len(task["rounds"]),
                "old_correct": old_correct, "new_correct": new_correct,
                "endpoint": task.get("endpoint", ""),
            })

    if not args.dry_run:
        json.dump({"note": "K1 astra sidecar + truncation rule + K3 adjudication; api_failure rerun tasks re-scored (v3)", "arms": v3_arms},
                  open(V3_PATH, "w"), ensure_ascii=False)
        print(f"[v3] wrote {V3_PATH}")

    json.dump({"rerun_tasks": rerun, "manifest": manifest},
              open(MANIFEST_PATH, "w"), indent=1, ensure_ascii=False)
    print(f"[manifest] wrote {MANIFEST_PATH}")
    print("\n== rerun task counts ==")
    for arm in ARMS:
        if rerun[arm]:
            print(f"  {arm}: {len(rerun[arm])} -> {rerun[arm]}")
    print("\n== manifest ==")
    for m in manifest:
        print(f"  {m['arm']:4s} {m['task_id']:8s} {m['metric']:6s} rounds {m['rounds_before']}->{m['rounds_after']} "
              f"old={m['old_correct']!r} new={m['new_correct']!r}")


if __name__ == "__main__":
    main()
