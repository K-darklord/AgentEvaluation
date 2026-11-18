#!/usr/bin/env python3
"""Deepseek read-out of the confirmation run on 800 new questions (docs/SELECTION_CONFIRMATION_DEEPSEEK_SPEC.md section 2).
Same criteria as the qwen read-out (scripts/selection_confirmation_readout.py), with a third confirmatory arm (A3) and the
reach-equivalence bound widened to +-27 per the deepseek spec.
  token alignment of the token-yoked generic-doubt loop (95-120% of critique; at most 40 questions at the cap)
  D-S1 selected(critique) - selected(token-yoked) > 0 ; D-S2 selected(critique) - selected(reassuring) > 0 ;
  D-A3 selected(critique) - selected(nine-sample self-consistency) > 0
     (sign-flip permutation, 10,000, two-sided, direction must agree; 95% bootstrap; Holm over the three)
  D-R1 equivalence: 90% bootstrap interval of reached(critique) - reached(token-yoked) inside +-27
  descriptive rows: conditions, exact matching, within-budget view, by subject and answer type, two-model means
Reads frozen files only. Usage: python3 scripts/selection_confirmation_readout_ds.py
(writes experiments/hle400/t3/selection_confirmation_readout_ds.json)"""
import json, importlib.util, random
from pathlib import Path
from collections import Counter
from math import comb
spec = importlib.util.spec_from_file_location('reco', 'scripts/recompute_evaluator_offline.py')
reco = importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T = 'experiments/hle400/t3/'; Q = 'deepseek-v4-flash-payg'
def J(f): return json.load(open(T + f))
def toks(r): return (r.get('prompt_tokens') or 0) + (r.get('completion_tokens') or 0)
def ctoks(r): return (r.get('critic_prompt_tokens') or 0) + (r.get('critic_completion_tokens') or 0)
def mcn(x, y):
    b = sum(p and not q for p, q in zip(x, y)); c = sum(q and not p for p, q in zip(x, y)); n = b + c
    return {'only_first': b, 'only_second': c, 'p': round(1.0 if n == 0 else min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n), 5)}
def perm(x, y, ci90=False):
    d = [a - b for a, b in zip(x, y)]; obs = sum(d); r = random.Random(1); nz = [v for v in d if v]
    ge = sum(abs(sum(v if r.random() < .5 else -v for v in nz)) >= abs(obs) - 1e-9 for _ in range(10000))
    bs = sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    o = {'diff': round(obs, 1), 'lo': round(bs[50], 1), 'hi': round(bs[1949], 1), 'p': round((ge + 1) / 10001, 5)}
    if ci90: o['lo90'] = round(bs[100], 1); o['hi90'] = round(bs[1899], 1)
    return o
class Arm:
    def __init__(s, path, side):
        s.L = reco.load_jsonl(Path(path) / 'loop_trajectories.jsonl'); s.side = side
        s.tasks = sorted(s.L, key=lambda t: int(t.split('_')[1]))
        s.K = {t: reco.freeze_keys(s.L[t].get('gold_answer', ''), s.L[t]) for t in s.tasks}
    def score(s, t, n=None, exact=False):
        keys = s.K[t]; sl = s.side[t]
        def ok(k):
            i = max(j for j, x in enumerate(keys) if x == k); return bool(sl[i]['c']) and (not exact or sl[i].get('s') == 't1')
        cnt = Counter(k for k in keys[:n] if k is not None)
        if not cnt: return False, 0.0, 0
        top = max(cnt.values()); tied = [k for k in cnt if cnt[k] == top]
        return any(ok(k) for k in cnt), sum(ok(k) for k in tied) / len(tied), len(cnt)
    def vec(s, ns=None, exact=False):
        v = [s.score(t, None if ns is None else ns[t], exact) for t in s.tasks]
        return [x[0] for x in v], [x[1] for x in v], [x[2] for x in v]
    def stats(s):
        c = n = 0
        for t in s.tasks:
            k = s.K[t]
            for i in range(1, len(k)):
                if k[i - 1] is not None and k[i] is not None: n += 1; c += k[i] != k[i - 1]
        N = len(s.tasks)
        return {'feedback_rounds_per_q': round(sum(len(s.L[t]['rounds']) - 1 for t in s.tasks) / N, 2),
                'answer_change_rate': round(c / max(1, n), 3),
                'solver_tokens_M': round(sum(toks(r) for t in s.tasks for r in s.L[t]['rounds']) / 1e6, 2)}
NAMES = {'A': 'first answer', 'A2': 'reassuring', 'A2P': 'generic doubt', 'A2PY': 'token-yoked generic doubt', 'C2': 'critique', 'A3': 'nine-sample self-consistency'}
conf = J('is_correct_t3_sidecar_confirm_ds.json')['arms']
N = {a: Arm(f'experiments/conf_{a}_{Q}/{Q}', conf[a]) for a in NAMES}
TASKS = N['C2'].tasks; assert len(TASKS) == 800 and all(N[a].tasks == TASKS for a in N)
OUT = {'n': 800, 'model': Q}
# ---- token alignment (same criterion as qwen)
B = J('yoke_budget_deepseek_confirm.json')['budget']; BT = sum(B.values()); Y = N['A2PY']
yt = sum(toks(r) for t in TASKS for r in Y.L[t]['rounds']); cap = sum(bool(Y.L[t].get('yoke_hit_cap')) for t in TASKS); aligned = (0.95 <= yt / BT <= 1.20) and cap <= 40
OUT['token_alignment'] = {'critique_total_M': round(BT / 1e6, 2), 'token_yoked_total_M': round(yt / 1e6, 2), 'ratio': round(yt / BT, 3), 'questions_at_cap': cap, 'aligned': aligned}
print(f"token alignment: token-yoked {yt / 1e6:.2f}M against critique {BT / 1e6:.2f}M (ratio {yt / BT:.3f}); at the cap {cap}; aligned {aligned}\n")
nw = {}
for t in TASKS:
    cum = 0; n = 1
    for j, r in enumerate(Y.L[t]['rounds']):
        cum += toks(r)
        if j == 0 or cum <= B[t]: n = j + 1
        else: break
    nw[t] = n
V = {a: N[a].vec() for a in N}; X = {a: N[a].vec(exact=True) for a in N}; W = Y.vec(nw); WX = Y.vec(nw, exact=True)
OUT['conditions'] = {}
print(f"{'loop':28s} reached selected conversion | exact matches only: reached selected | rounds/q candidates/q change tokens")
for a in ('A', 'A2', 'A2P', 'A2PY', 'C2', 'A3'):
    R, S, Cn = V[a]; st = N[a].stats(); tk = st['solver_tokens_M'] + (round(sum(ctoks(r) for t in TASKS for r in N[a].L[t]['rounds']) / 1e6, 2) if a == 'C2' else 0)
    OUT['conditions'][NAMES[a]] = {'reached': sum(R), 'selected': round(sum(S), 1), 'conversion': round(sum(S) / sum(R), 3), 'reached_exact': sum(X[a][0]), 'selected_exact': round(sum(X[a][1]), 1), 'candidates_per_q': round(sum(Cn) / 800, 2), 'tokens_M': round(tk, 1), **st}
    print(f"{NAMES[a]:28s} {sum(R):4d} {sum(S):7.1f} {sum(S) / sum(R):.3f} | {sum(X[a][0]):4d} {sum(X[a][1]):6.1f} | {st['feedback_rounds_per_q']:5.2f} {sum(Cn) / 800:.2f} {st['answer_change_rate']:.2f} {tk:.1f}M")
OUT['conditions']['token-yoked generic doubt']['within_budget'] = {'reached': sum(W[0]), 'selected': round(sum(W[1]), 1)}
print(f"{'  token-yoked, within budget':28s} {sum(W[0]):4d} {sum(W[1]):7.1f}")
# ---- confirmatory (three, Holm over three)
S1 = perm(V['C2'][1], V['A2PY'][1]); S2 = perm(V['C2'][1], V['A2'][1]); A3 = perm(V['C2'][1], V['A3'][1])
order = sorted([('S1', S1), ('S2', S2), ('A3', A3)], key=lambda kv: kv[1]['p']); run = 0.0
for i, (k, v) in enumerate(order):
    run = max(run, min(1.0, (3 - i) * v['p'])); v['p_holm'] = round(run, 5)
    v['confirmed'] = bool(aligned if k == 'S1' else True) and v['diff'] > 0 and v['p_holm'] < .05
if not aligned: S1['confirmed'] = None
OUT['confirmatory'] = {'S1 selected: critique - token-yoked generic doubt': S1, 'S2 selected: critique - reassuring': S2, 'A3 selected: critique - nine-sample self-consistency': A3}
print('\nconfirmatory tests (selected)')
for k, v in OUT['confirmatory'].items(): print(f"  {k:56s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}]  p={v['p']:.4f}  Holm p={v['p_holm']:.4f}  confirmed: {v['confirmed']}")
# ---- D-R1 equivalence on reach (+-27)
R1 = perm([float(x) for x in V['C2'][0]], [float(x) for x in V['A2PY'][0]], ci90=True); R1['mcnemar'] = mcn(V['C2'][0], V['A2PY'][0])
R1['verdict'] = ('not judged (tokens not aligned)' if not aligned else 'equivalent' if (R1['lo90'] > -27 and R1['hi90'] < 27) else 'different' if (R1['lo90'] > 27 or R1['hi90'] < -27) else 'inconclusive')
OUT['R1 reached: critique - token-yoked generic doubt'] = R1
print(f"\nD-R1 reached, critique - token-yoked: {R1['diff']:+.0f}, 90% interval [{R1['lo90']:+.0f},{R1['hi90']:+.0f}] against +-27 -> {R1['verdict']}; discordant {R1['mcnemar']['only_first']}/{R1['mcnemar']['only_second']} p={R1['mcnemar']['p']:.4f}")
# ---- descriptive: reached disagreement pairs and selected pairwise differences
sec = {'reached': {'critique vs reassuring': mcn(V['C2'][0], V['A2'][0]), 'critique vs generic doubt': mcn(V['C2'][0], V['A2P'][0]), 'critique vs nine-sample self-consistency': mcn(V['C2'][0], V['A3'][0]), 'token-yoked vs generic doubt': mcn(V['A2PY'][0], V['A2P'][0]), 'token-yoked vs reassuring': mcn(V['A2PY'][0], V['A2'][0]), 'generic doubt vs reassuring': mcn(V['A2P'][0], V['A2'][0])},
       'selected': {'critique - generic doubt': perm(V['C2'][1], V['A2P'][1]), 'critique - nine-sample self-consistency': perm(V['C2'][1], V['A3'][1]), 'token-yoked - generic doubt': perm(V['A2PY'][1], V['A2P'][1]), 'token-yoked - reassuring': perm(V['A2PY'][1], V['A2'][1]), 'generic doubt - reassuring': perm(V['A2P'][1], V['A2'][1]), 'critique - first answer': perm(V['C2'][1], V['A'][1]), 'reassuring - first answer': perm(V['A2'][1], V['A'][1])},
       'exact_matches_only': {'S1': perm(X['C2'][1], X['A2PY'][1]), 'S2': perm(X['C2'][1], X['A2'][1]), 'A3': perm(X['C2'][1], X['A3'][1]), 'R1': {**perm([float(x) for x in X['C2'][0]], [float(x) for x in X['A2PY'][0]], ci90=True), 'mcnemar': mcn(X['C2'][0], X['A2PY'][0])}},
       'within_budget': {'S1': perm(V['C2'][1], W[1]), 'R1': {**perm([float(x) for x in V['C2'][0]], [float(x) for x in W[0]], ci90=True), 'mcnemar': mcn(V['C2'][0], W[0])}},
       'exact_share_of_selected': {NAMES[a]: round(sum(X[a][1]) / sum(V[a][1]), 3) for a in N}}
OUT['secondary'] = sec
print('\ndescriptive. reached (only first / only second):')
for k, v in sec['reached'].items(): print(f"  {k:40s} {v['only_first']:3d}/{v['only_second']:<3d} p={v['p']:.4f}")
print('selected:')
for k, v in sec['selected'].items(): print(f"  {k:40s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
for grp in ('exact_matches_only', 'within_budget'):
    for k, v in sec[grp].items(): print(f"  {grp:20s} {k}: {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}" + (f"  90% [{v['lo90']:+.0f},{v['hi90']:+.0f}] discordant {v['mcnemar']['only_first']}/{v['mcnemar']['only_second']}" if 'lo90' in v else ''))
print('  exact-match share of selected:', sec['exact_share_of_selected'])
# ---- by batch (the two draws of 400)
OUT['by_batch'] = {}
for lab, I in (('first 400 new questions', range(0, 400)), ('second 400 new questions', range(400, 800))):
    I = list(I); g = lambda a, j: [V[a][j][i] for i in I]
    OUT['by_batch'][lab] = {'reached': {NAMES[a]: sum(g(a, 0)) for a in N}, 'selected': {NAMES[a]: round(sum(g(a, 1)), 1) for a in N}, 'S1': perm(g('C2', 1), g('A2PY', 1)), 'S2': perm(g('C2', 1), g('A2', 1)), 'A3': perm(g('C2', 1), g('A3', 1)), 'R1': mcn(g('C2', 0), g('A2PY', 0))}
    b = OUT['by_batch'][lab]
    print(f"\n{lab}: reached {b['reached']}\n   selected {b['selected']}\n   S1 {b['S1']['diff']:+.1f} [{b['S1']['lo']:+.1f},{b['S1']['hi']:+.1f}]  S2 {b['S2']['diff']:+.1f} [{b['S2']['lo']:+.1f},{b['S2']['hi']:+.1f}]  A3 {b['A3']['diff']:+.1f} [{b['A3']['lo']:+.1f},{b['A3']['hi']:+.1f}]  R1 discordant {b['R1']['only_first']}/{b['R1']['only_second']}")
# ---- two-model mean (qwen + deepseek on the same 800) — descriptive only
qw = J('vectors_confirm.json')
OUT['two_model_mean'] = {}
print('\ntwo-model mean (per-question average of qwen and deepseek selected), descriptive:')
for lab, carm, parm in (('S1', 'C2', 'A2PY'), ('S2', 'C2', 'A2'), ('A3', 'C2', 'A3')):
    if carm in qw['selected'] and parm in qw['selected']:
        mc = [(a + b) / 2.0 for a, b in zip(qw['selected'][carm], V[carm][1])]
        mp = [(a + b) / 2.0 for a, b in zip(qw['selected'][parm], V[parm][1])]
        v = perm(mc, mp); OUT['two_model_mean'][lab] = v
        print(f"  {lab}: {v['diff']:+.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
    else:
        OUT['two_model_mean'][lab] = None
        print(f"  {lab}: skipped (qwen arm '{parm}' not scored)")
# ---- by subject and answer type (descriptive)
new = [json.loads(l) for f in ('hle_confirm_s1.jsonl', 'hle_confirm_s2.jsonl') for l in open('data/raw/hle/' + f)]
assert len(new) == 800
def strata(rows, key):
    d = {}
    for i, r in enumerate(rows): d.setdefault(r[key], []).append(i)
    return d
def table(vecs, rows, key, label):
    out = {}; print(f"\n{label}: by {key}.  critique vs reassuring | vs generic doubt | vs token-yoked :  reached only-critique/only-control, selected difference")
    agree = {c: [0, 0] for c in ('A2', 'A2P', 'A2PY')}
    for g, I in sorted(strata(rows, key).items(), key=lambda kv: -len(kv[1])):
        row = {'n': len(I)}; cells = []
        for c in ('A2', 'A2P', 'A2PY'):
            b = sum(vecs['C2'][0][i] and not vecs[c][0][i] for i in I); k = sum(vecs[c][0][i] and not vecs['C2'][0][i] for i in I); d = sum(vecs['C2'][1][i] - vecs[c][1][i] for i in I)
            row[NAMES[c]] = {'reached_only_critique': b, 'reached_only_control': k, 'selected_diff': round(d, 1)}; cells.append(f"{b:3d}/{k:<3d} {d:+6.1f}"); agree[c][0] += b > k; agree[c][1] += d > 0
        out[g] = row; print(f"  {str(g):28s} n={len(I):4d}  " + ' | '.join(cells))
    out['_strata_in_which_critique_is_ahead (reached, selected)'] = {NAMES[c]: agree[c] for c in agree}
    print('  strata in which critique is ahead (reached, selected):', out['_strata_in_which_critique_is_ahead (reached, selected)'])
    return out
OUT['by_subject_new_800'] = table(V, new, 'category', 'new 800')
OUT['by_answer_type_new_800'] = table(V, new, 'answer_type', 'new 800')
json.dump(OUT, open(T + 'selection_confirmation_readout_ds.json', 'w'), indent=1)
json.dump({'selected': {a: V[a][1] for a in V}, 'reached': {a: [int(x) for x in V[a][0]] for a in V}, 'selected_exact': {a: X[a][1] for a in X}}, open(T + 'vectors_confirm_ds.json', 'w'))
