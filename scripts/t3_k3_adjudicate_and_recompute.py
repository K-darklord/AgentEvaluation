#!/usr/bin/env python3
"""K=3 dispute adjudication (second-agent, 2026-11-02) + full recompute.

Inputs : experiments/hle400/t3/is_correct_t3_sidecar.json (K1 astra per-round verdicts)
         experiments/hle400_{A,A2,A3,C3}/deepseek-v4-flash/loop_trajectories.jsonl
Outputs: experiments/hle400/t3/k3_adjudication.json         (every override, with reason)
         experiments/hle400/t3/is_correct_t3_sidecar_v2.json (adjudicated per-round verdicts)
         experiments/hle400/t3/t3_final_scores_v2.json        (winner-level accuracy per arm.metric)
         experiments/hle400/t3/transition_metrics_v2.json     (per-arm / per-task transition data)
Rules  : (1) winning or any round with finish_reason=="length" -> wrong (no commit)
         (2) one verdict per *answer variant* (same substance => same verdict, all arms/rounds)
         (3) adjudications below override the K1 sidecar and the K3 payload
"""
import json, re, sys
from pathlib import Path
from collections import Counter
from math import comb
sys.path.insert(0, ".")
from src.score_hle_arms import load_index, read_traj, _settle_idx, _mode_idx, _key

T3 = Path("experiments/hle400/t3")
ARMS = {"A": ["init"], "A2": ["init", "final", "settle", "mode"], "A3": ["init", "vote"], "C3": ["init", "final", "settle", "mode"], "C2": ["init", "final", "settle", "mode"], "A2P": ["init", "final", "settle", "mode"]}
# Arms whose critic is an independent LLM call (bank-free C2 included). Template/placebo
# critic arms (A2, future A2P) make zero LLM critic calls and must NOT be hardcoded here.
LLM_CRITIC_ARMS = {"C3", "A3C3", "C2"}
idx = load_index(Path("data/raw/hle/hle_400_new.jsonl"))
def _traj_dir(a):
    # C2 and A2P ran on the payg endpoint (deepseek-v4-flash-payg); the other four arms on token-plan.
    return "deepseek-v4-flash-payg" if a in ("C2", "A2P") else "deepseek-v4-flash"
def _exp_dir(a):
    return "hle400_A2PRIME" if a == "A2P" else f"hle400_{a}"
traj = {a: read_traj(Path(f"experiments/{_exp_dir(a)}/{_traj_dir(a)}/loop_trajectories.jsonl")) for a in ARMS}
side = json.load(open(T3 / "is_correct_t3_sidecar.json"))["arms"]
side["C2"] = json.load(open(T3 / "is_correct_t3_sidecar_C2.json"))["arms"]["C2"]
side["A2P"] = json.load(open(T3 / "is_correct_t3_sidecar_A2P.json"))["arms"]["A2P"]

def ws(s): return " ".join(str(s).split())

# ---- adjudication: (task_id, predicate on normalized answer text) -> (verdict, reason, confidence, needs_user)
def has(*subs):
    return lambda a: all(s in a for s in subs)
def rx(p):
    r = re.compile(p, re.S); return lambda a: bool(r.search(a))

RULES = [
 # hle_280 : Theta-equivalence. '2+' regularised log, sum or max form -> correct. '1+' / 'sqrt(BL)+L' / other -> wrong.
 ("hle_280", lambda a: re.search(r"log\\?\!?\s*\\?\(?\s*\\?left\(?\s*2\s*\+", a) is not None and "sqrt" in a and not re.match(r"\\\[\s*B\s*\+", a), True,
  "Theta-equivalent to gold: max/sum are Theta-equal, log(2+L/B) ~ log(L/B) when L>>B and the sqrt term dominates when L<=B", "medium", True),
 ("hle_280", rx(r"log\s*\\?\(?\s*\\?left\(?\s*1\s*\+"), False, "log(1+L/B) gives Theta(B) when L<B, not Theta(sqrt(BL))", "medium", False),
 # hle_021 : encoding (ii) f(w)=bot^w -o 1 (0=1, n+1 = bot -o n) -> correct (small-case derivability checks pass; question accepts any valid encoding)
 ("hle_021", lambda a: ("\\bot\\multimap" in a or "\\bot \\multimap" in a) and ("0}=1" in a or "(0)=1" in a or "{0}=1" in a) and "C" in a, True,
  "f(w)=bot^w -o 1 with C=f(b)^{(x)m}: verified derivable/non-derivable on {1,1}/2, {2}/1x2, {1,2}/1x3, {1,3}/2x2, {4}/2x2; question asks for ANY encoding", "medium", True),
 ("hle_021", has("\\bot\\otimes\\cdots\\otimes\\bot}_{w", "\\multimap 1"), True, "same encoding (ii), uncurried form", "medium", True),
 ("hle_021", has("f(w)=(A^{\\,w})\\multimap 1"), True, "same encoding (ii)", "medium", True),
 ("hle_021", has("\\underline{0}=\\bot"), False, "1 -o X == X in MLL, so f(w) collapses to bot: not an encoding", "high", False),
 ("hle_021", has("f(n+1)=1\\multimap f(n)"), False, "1 -o X == X, collapses", "high", False),
 ("hle_021", lambda a: "\\otimes \\bot" in a or "\\otimes\\bot" in a and "\\multimap" not in a, False, "f(w)=bot^{(x)w}: sequent derivable for every W with sum=mb, does not encode EP", "high", False),
 # hle_030 : any answer containing the corrector factor r^{A(1-cos)+B sin} with correct sign -> correct
 ("hle_030", rx(r"r\^\{\s*\\?,?\s*A\(1-\\cos\\theta\)\+B\\sin\\theta"), True,
  "answer exhibits the corrector r^{A(1-cos th)+B sin th} (alone or multiplying the known A=B=0 profile)", "medium", True),
 ("hle_030", rx(r"r\^\{-A\(1-\\cos\\theta\)-B"), False, "wrong sign", "high", False),
 ("hle_030", rx(r"e\^\{-?B\\theta\}|e\^\{-B\\frac"), False, "B-dependence wrong (exp instead of power of r)", "high", False),
 # hle_129 : sign of the FIRST stated b value decides. +alpha P_1 (clipped or not) -> correct ; -alpha P_1 / b=alpha / b=0 -> wrong
 ("hle_129", lambda a: _b_sign(a) == "+", True,
  "derived: with X2=U2+bZ1, |K_Y|=(P1+1)(P2+2b alpha+1)-(b+alpha)^2 is maximised at b=alpha P1; clipping to |b|<=sqrt(P2) is the power-feasible optimum", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "-", False, "-alpha P1 as the primary value is the wrong sign under X2=U2+bZ1 (restore rejected)", "high", False),
 ("hle_129", lambda a: _b_sign(a) == "other", False, "b=alpha / b=0 / other: not alpha P1", "high", False),
 # hle_153 : path-integral Z (grand-canonical variant included) -> correct (question asks for the path-integral form)
 ("hle_153", lambda a: "\\int" in a and ("\\mathcal{D}" in a or "\\mathcal D" in a or "D[" in a) and "exp" in a.lower() and not a.startswith("with Grassmann"), True,
  "question asks for the imaginary-time path-integral form; gold is the operator trace. Judge follows the question", "medium", True),
 # hle_386 : trans-cis (photo)isomerization at sunrise/sunset -> correct ; 'flat at sunrise and sunset' -> wrong
 ("hle_386", lambda a: ("isomeriz" in a.lower() or "isomerise" in a.lower()) and not a.startswith("At sunrise and sunset") and "sunrise and sunset it must be flat" not in a and not a.startswith("It must continuously adjust"), True,
  "trans-cis photoisomerization IS rotation about the N=N bond; the vaguer 'flip over or change shape ... mimicking trans-cis photoisomerization' is the same claim", "medium", True),
 # hle_170 : only a 6-letter D/S string counts
 ("hle_170", lambda a: ws(a).replace(" ", "") == "DDSSDS", True, "exact", "high", False),
 ("hle_170", lambda a: ws(a).replace(" ", "") != "DDSSDS", False, "no committed six-foot D/S string (or wrong string)", "high", False),
 # hle_036 : numeric tolerance 0.5 % of gold 1.03
 ("hle_036", lambda a: _num_close(a, 1.03, 0.005), True, "within 0.5% of 1.03", "high", False),
 ("hle_036", lambda a: (_first_num(a) is not None) and not _num_close(a, 1.03, 0.005), False, "numeric value outside 0.5% of 1.03 (1.0436 is 1.3% off)", "high", False),
 # hle_121 : every big-M / relabelled-b variant verified to be an exact MILP encoding of f (b<->1-b, M in {1,u,u-l})
 ("hle_121", lambda a: ("y" in a and "b" in a and "\\ge" in a.replace("≥", "\\ge")) and len(a) < 400, True,
  "verified case-by-case (b=0/1 with a=0/1): each variant forces y=min(0,x) for x<1 and is consistent with y=x-1 for x>=1 (needs l<=0, as the gold does)", "high", False),
 # hle_374 : compressed path rule
 ("hle_374", lambda a: re.fullmatch(r"[UDLR]+", ws(a).replace(" ", "")) is not None and re.sub(r"(.)\1+", r"\1", ws(a).replace(" ", "")) == "ULDL", True, "compresses to ULDL per the question's own rule", "high", False),
 # hle_201 : two algebraic forms exactly equal to gold 289026722411805831750717*pi/2^41
 # (verified with exact rational arithmetic; 2^41 = 2199023255552).
 ("hle_201", lambda a: "2^{50}" in a and "2^{100}" not in a and "\\binom{50}{25}" in a and "25-3k" in a, True,
  "form pi/2^50 * (C(50,25)^2 + 2*sum_{k=1..8} (-1)^k C(50,25-k)C(50,25-3k)) — exact rational equality with gold", "high", False),
 ("hle_201", lambda a: (("(50!)^2" in a) or ("(50!)^{2}" in a)) and "4^{25}" in a and "m+25" in a, True,
  "form pi*(50!)^2/(4^25*25!) * sum 1/((50-2m)! m! (m+25)!) — exact rational equality with gold", "high", False),
]

def _b_sign(a):
    """Sign of the first committed b value. '+' for alpha P_1 (also clip(alpha P_1)/piecewise with alpha P_1 first),
    '-' for -alpha P_1, 'other' for b=alpha, b=0, -alpha/(P1+1) etc., None if no b= statement."""
    m = re.search(r"b(?:_\{?\\?(?:text\{)?opt\}?\}?|\^?\*?|\^\{?\*\}?)?\s*=\s*(.{0,160})", a, re.S)
    if not m: return None
    rhs = " ".join(m.group(1).split())
    for _ in range(10):
        rhs = re.sub(r"^(\s|\\\(|\\\[|\(|\[|\{|\\boxed\{|\\begin\{cases\}|\\operatorname\{clip\}\(|\\left\(|\\,|\\;|\\!|\\ |\\quad|%)+", "", rhs)
    rhs = re.sub(r"^\\operatorname\{sgn\}\(\\alpha\)\s*\\min\s*\\left\(\s*\|\\alpha\|\s*", "\\alpha ", rhs)
    if re.match(r"-\s*\\alpha\s*P_?\{?1", rhs): return "-"
    if re.match(r"\\alpha\s*P_?\{?1|P_?\{?1\}?\s*\\alpha", rhs): return "+"
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

# ---- apply overrides to the sidecar
overrides = []
side2 = {a: {} for a in ARMS}
for arm in ARMS:
    for tid, task in traj[arm].items():
        rows = []
        for i, r in enumerate(task["rounds"]):
            s = dict(side[arm][tid][i])
            fa = r.get("final_answer", "")
            if r.get("finish_reason") == "length":
                if s["c"]:
                    overrides.append({"task_id": tid, "arm": arm, "round": i, "from": True, "to": False, "src": "trunc", "reason": "finish_reason=length -> no commit", "confidence": "high", "needs_user": False})
                s = {"c": False, "s": "trunc"}
            else:
                adj = adjudicate(tid, fa)
                if adj is not None:
                    v, reason, conf, ask = adj
                    if s["c"] != v:
                        overrides.append({"task_id": tid, "arm": arm, "round": i, "from": s["c"], "to": v, "src": "adjudicated", "reason": reason, "confidence": conf, "needs_user": ask, "answer": fa[:200]})
                    s = {"c": v, "s": "adjudicated" if s["c"] != v else s["s"], "adj": True}
            rows.append(s)
        side2[arm][tid] = rows

# ---- winners
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

correct = {}
scores = {}
for arm, mets in ARMS.items():
    for met in mets:
        c = set()
        for tid, task in traj[arm].items():
            wi = winner_idx(arm, met, idx[tid], task)
            if wi is None or wi < 0: continue
            if side2[arm][tid][wi]["c"]: c.add(tid)
        correct[f"{arm}.{met}"] = c
        scores[f"{arm}.{met}"] = {"correct": len(c), "n": 400, "acc": round(len(c) / 400, 4)}

def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
pairs = [("C3.final", "A3.vote"), ("C3.mode", "A3.vote"), ("C3.final", "A2.final"), ("C3.mode", "A2.mode"), ("A2.final", "A3.vote"), ("A2.mode", "A3.vote"), ("C3.final", "A.init"), ("A3.vote", "A.init"), ("A2.final", "A.init"), ("C3.final", "C2.final"), ("C3.mode", "C2.mode"), ("C2.final", "A3.vote"), ("C2.mode", "A3.vote"), ("C2.final", "A2.final"), ("C2.mode", "A2.mode"), ("C2.final", "A.init"), ("C2.mode", "A.init"), ("A2P.final", "C2.final"), ("A2P.mode", "C2.mode"), ("A2P.final", "A3.vote"), ("A2P.mode", "A3.vote"), ("A2P.final", "A2.final"), ("A2P.mode", "A2.mode"), ("A2P.final", "A.init"), ("A2P.mode", "A.init")]
paired = {}
for x, y in pairs:
    b, c = len(correct[x] - correct[y]), len(correct[y] - correct[x])
    paired[f"{x} vs {y}"] = {"only_left": b, "only_right": c, "both": len(correct[x] & correct[y]), "mcnemar_p": round(mcnemar(b, c), 4)}

# ---- transitions
trans = {}
for arm in ARMS:
    per_task = {}
    eir_n = eir_d = ecr_n = ecr_d = 0
    for tid, task in traj[arm].items():
        meta = idx[tid]; rs = task["rounds"]; sv = side2[arm][tid]
        cor = [s["c"] for s in sv]
        keys = [_key(meta, r) for r in rs]
        switches = []
        for i in range(1, len(rs)):
            if keys[i] != keys[i - 1]:
                switches.append({"round": i, "from_correct": cor[i - 1], "to_correct": cor[i], "from_key": str(keys[i - 1]), "to_key": str(keys[i]), "critic_direction": bool(rs[i - 1].get("critic_direction"))})
            if cor[i - 1]:
                eir_d += 1; eir_n += (not cor[i])
            else:
                ecr_d += 1; ecr_n += cor[i]
        si = _settle_idx(meta, task); mi = _mode_idx(meta, task)
        per_task[tid] = {"n_rounds": len(rs), "init_correct": cor[0], "final_correct": cor[-1],
                         "settle_correct": (cor[si] if si is not None else None), "mode_correct": (cor[mi] if mi >= 0 else None),
                         "p_act": any(cor), "p_flip": any(cor) and not cor[-1], "n_switches": len(switches),
                         "wrong_to_correct": sum(1 for s in switches if (not s["from_correct"]) and s["to_correct"]),
                         "correct_to_wrong": sum(1 for s in switches if s["from_correct"] and not s["to_correct"]),
                         "per_round_correct": cor, "switches": switches}
    n = len(per_task)
    trans[arm] = {"summary": {"P_act": round(sum(t["p_act"] for t in per_task.values()) / n, 4),
                              "P_flip": round(sum(t["p_flip"] for t in per_task.values()) / n, 4),
                              "EIR": round(eir_n / eir_d, 4) if eir_d else None, "EIR_num_den": [eir_n, eir_d],
                              "ECR": round(ecr_n / ecr_d, 4) if ecr_d else None, "ECR_num_den": [ecr_n, ecr_d],
                              "init_acc": round(sum(t["init_correct"] for t in per_task.values()) / n, 4),
                              "final_acc": round(sum(t["final_correct"] for t in per_task.values()) / n, 4),
                              "mean_rounds": round(sum(t["n_rounds"] for t in per_task.values()) / n, 2),
                              "tasks_with_switch": sum(1 for t in per_task.values() if t["n_switches"]),
                              "wrong_to_correct_switches": sum(t["wrong_to_correct"] for t in per_task.values()),
                              "correct_to_wrong_switches": sum(t["correct_to_wrong"] for t in per_task.values())},
                  "tasks": per_task}

init_set = correct["A.init"]
lost_gained = {k: {"kept_init_correct": len(init_set & v), "lost": sorted(init_set - v), "gained": len(v - init_set)} for k, v in correct.items()}

USER_APPROVED = True  # 2026-11-02 18:07: user accepted all adjudications incl. hle_021/030/153/280
for o in overrides:
    if o.get("needs_user"):
        o["needs_user"] = False; o["user_approved"] = True
json.dump({"rules_applied": len(overrides), "user_approved_all": USER_APPROVED, "overrides": overrides,
           "needs_user_decision": sorted({(o["task_id"]) for o in overrides if o.get("needs_user")}),
           "decision_summary": {
             "hle_280": "all '2+' variants CORRECT (demotes rejected); '1+' variants wrong",
             "hle_021": "encoding f(w)=bot^w -o 1 CORRECT (3 demotes rejected, unstable kept); collapsing/tensor-only encodings wrong",
             "hle_030": "any answer exhibiting the corrector factor CORRECT (demote rejected; inconsistent K1 rounds fixed)",
             "hle_129": "+alpha P1 primary CORRECT (demote rejected); -alpha P1 primary WRONG (restore rejected)",
             "hle_153": "path-integral forms CORRECT (unstable kept; A3 r1 fixed)",
             "hle_386": "trans-cis isomerization answers CORRECT (demote rejected); 'flat at sunrise/sunset' wrong",
             "hle_170": "only DDSSDS correct; C3 r8 / A3 r8 fragments WRONG (unstable keep rejected)",
             "hle_036": "0.5% tolerance: 1.0436 WRONG (demote accepted)",
             "hle_121": "all variants are exact encodings -> CORRECT (unstable kept; K1 wrongs fixed)",
             "hle_374": "compressed path CORRECT (unstable kept)",
             "hle_201": "two algebraic forms CORRECT (exact rational equality with gold 289026722411805831750717*pi/2^41)",}},
          open(T3 / "k3_adjudication.json", "w"), indent=1, ensure_ascii=False)
json.dump({"note": "K1 astra sidecar + truncation rule + K3 adjudication (scripts/t3_k3_adjudicate_and_recompute.py)", "arms": side2}, open(T3 / "is_correct_t3_sidecar_v2.json", "w"))
# ---- cost (solver tokens only: critic/evaluator calls are NOT logged per round) and answer-form split
cost = {}
for arm in ARMS:
    tot = sum(r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) for t in traj[arm].values() for r in t["rounds"])
    rounds = sum(len(t["rounds"]) for t in traj[arm].values())
    critic_calls = (sum(1 for t in traj[arm].values() for r in t["rounds"][1:]
                        if r.get("critic_direction") or r.get("critic_fallback"))
                    if arm in LLM_CRITIC_ARMS else 0)
    cost[arm] = {"solver_tokens_total": tot, "solver_rounds": rounds,
                 "critic_calls_llm": critic_calls, "critic_calls_unlogged": critic_calls,  # legacy alias
                 "solver_tokens_per_correct": {m: round(tot / scores[f"{arm}.{m}"]["correct"]) for m in ARMS[arm]}}
form = {}
mc = {t for t, m in idx.items() if m["answer_type"] == "multipleChoice"}
for k, c in correct.items():
    form[k] = {"mcq_correct": len(c & mc), "mcq_n": len(mc), "mcq_acc": round(len(c & mc) / len(mc), 4),
               "open_correct": len(c - mc), "open_n": 400 - len(mc), "open_acc": round(len(c - mc) / (400 - len(mc)), 4)}
json.dump({"scores": scores, "paired": paired, "vs_shared_init": lost_gained, "cost_solver_only": cost, "by_answer_form": form}, open(T3 / "t3_final_scores_v2.json", "w"), indent=1)
print("\n== cost (solver tokens only)"); [print(" ", a, v) for a, v in cost.items()]
print("\n== by answer form (MCQ n=%d / open n=%d)" % (len(mc), 400 - len(mc)))
for k, v in form.items(): print(f"  {k:10s} MCQ {v['mcq_correct']:3d} ({v['mcq_acc']:.3f})  open {v['open_correct']:3d} ({v['open_acc']:.3f})")
json.dump(trans, open(T3 / "transition_metrics_v2.json", "w"))

print("overrides:", len(overrides), " needs_user tasks:", sorted({o["task_id"] for o in overrides if o.get("needs_user")}))
print(Counter((o["task_id"], o["to"]) for o in overrides))
print("\n== winner-level accuracy (v2)")
for k, v in scores.items(): print(f"  {k:10s} {v['correct']:4d}  {v['acc']:.4f}")
print("\n== paired")
for k, v in paired.items(): print(f"  {k:24s} L{v['only_left']:3d} R{v['only_right']:3d} both{v['both']:4d} p={v['mcnemar_p']}")
print("\n== vs shared init (112→?)")
for k, v in lost_gained.items(): print(f"  {k:10s} kept {v['kept_init_correct']:3d} lost {len(v['lost']):3d} gained {v['gained']:3d}")
print("\n== transitions")
for a, t in trans.items(): print(" ", a, t["summary"])
