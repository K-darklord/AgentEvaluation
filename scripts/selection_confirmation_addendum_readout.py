#!/usr/bin/env python3
"""Read-out of the addendum on the 800 new questions, qwen3.8-flash (docs/SELECTION_CONFIRMATION_ADDENDUM.md, section 3):
 T-A3 selected(critique) - selected(nine independent samples) > 0
 T-Q  selected(critique) - selected(question-only critique continued to equal tokens) > 0
 (sign-flip permutation, two-sided, Holm over the two); token alignment of the continued loop; descriptive rows.
Reads frozen files only. Usage: python3 scripts/selection_confirmation_addendum_readout.py
(writes experiments/hle400/t3/selection_confirmation_addendum_readout.json)"""
import json,gc
from confirm_common import *
Q='qwen3.8-flash-payg'; s1=J('is_correct_t3_sidecar_confirm.json')['arms']; s2=J('is_correct_t3_sidecar_confirm2.json')['arms']; B=J('yoke_budget_qwen_confirm.json')['budget']
R={'C2':arm(f'experiments/conf_C2_{Q}/{Q}',s1['C2'],critic=True),'A2':arm(f'experiments/conf_A2_{Q}/{Q}',s1['A2']),'A2PY':arm(f'experiments/conf_A2PY_{Q}/{Q}',s1['A2PY']),
   'A3':arm(f'experiments/conf_A3_{Q}/{Q}',s2['A3'],samples=True),'C2Q':arm(f'experiments/conf_C2Q_{Q}/{Q}',s2['C2Q'],critic=True),
   'C2QY':arm(f'experiments/yoke_C2QY_confirm_{Q}/{Q}',s2['C2QY'],critic=True,budget=B),'C2QYall':arm(f'experiments/yoke_C2QY_confirm_{Q}/{Q}',s2['C2QY'],critic=True)}
NAMES={'A2':'reassuring','A2PY':'token-yoked generic doubt','C2Q':'question-only critique, natural stop','C2QY':'question-only critique, equal tokens','C2QYall':'question-only critique, all rounds','C2':'critique','A3':'nine samples'}
TASKS=order(R['C2']); assert len(TASKS)==800 and all(order(R[a])==TASKS for a in R)
BT=sum(B.values()); al=sum(R['C2QY'][t]['tokens'] for t in TASKS); short=sum(R['C2QY'][t]['short'] for t in TASKS); aligned=(0.95<=al/BT<=1.20) and short<=40
OUT={'n':800,'token_alignment':{'budget_total_M':round(BT/1e6,2),'aligned_total_M':round(al/1e6,2),'ratio':round(al/BT,3),'questions_short_of_budget':short,'aligned':aligned}}
print(f"token alignment of the continued question-only loop: {al/1e6:.2f}M against {BT/1e6:.2f}M (ratio {al/BT:.3f}); short of budget {short}; aligned {aligned}\n")
OUT['conditions']={NAMES[a]:summary(R[a],TASKS) for a in NAMES}
print(f"{'method':40s} last selected reached conv | exact: reached selected | rounds cand change tokens | repeat cor/inc ratio")
for n,s in OUT['conditions'].items(): print(f"{n:40s} {s['last']:4d} {s['selected']:6.1f} {s['reached']:4d} {s['conversion']:.2f} | {s['reached_exact']:4d} {s['selected_exact']:6.1f} | {s['rounds_per_q']:5.2f} {s['candidates_per_q']:.2f} {s['answer_change_rate']:.2f} {s['tokens_M']:6.1f}M | {s['repeat_correct']:.2f}/{s['repeat_incorrect']:.2f} {s['repeat_ratio']}")
S=lambda a:vec(R[a],'selected',TASKS); Rc=lambda a:vec(R[a],'reached',TASKS); X=lambda a:vec(R[a],'selected_x',TASKS)
conf={'T-A3 selected: critique - nine samples':perm(S('C2'),S('A3')),'T-Q selected: critique - question-only critique at equal tokens':perm(S('C2'),S('C2QY'))}
holm(conf)
if not aligned: conf['T-Q selected: critique - question-only critique at equal tokens']['confirmed']=None
OUT['tests']=conf; print('\ntests fixed in advance (selected), Holm over two')
for k,v in conf.items(): print(f"  {k:66s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}]  p={v['p']:.4f}  Holm p={v['p_holm']:.4f}  confirmed: {v['confirmed']}")
rq=perm(Rc('C2'),Rc('C2QY')); rq['mcnemar']=mcn(Rc('C2'),Rc('C2QY')); rq['within_33']=bool(rq['lo90']>-33 and rq['hi90']<33)
sec={'reached':{'critique vs nine samples':mcn(Rc('C2'),Rc('A3')),'critique vs question-only at equal tokens':rq['mcnemar'],'critique vs question-only, natural stop':mcn(Rc('C2'),Rc('C2Q')),'question-only: equal tokens vs natural stop':mcn(Rc('C2QY'),Rc('C2Q')),'question-only at equal tokens vs token-yoked generic doubt':mcn(Rc('C2QY'),Rc('A2PY')),'nine samples vs token-yoked generic doubt':mcn(Rc('A3'),Rc('A2PY'))},
     'reached_difference_critique_minus_question_only_equal_tokens':rq,
     'selected':{'nine samples - reassuring':perm(S('A3'),S('A2')),'nine samples - token-yoked generic doubt':perm(S('A3'),S('A2PY')),'critique - question-only, natural stop':perm(S('C2'),S('C2Q')),'critique - question-only, all rounds':perm(S('C2'),S('C2QYall')),'question-only: equal tokens - natural stop':perm(S('C2QY'),S('C2Q')),'question-only at equal tokens - token-yoked generic doubt':perm(S('C2QY'),S('A2PY')),'question-only at equal tokens - reassuring':perm(S('C2QY'),S('A2'))},
     'exact_matches_only':{'T-A3':perm(X('C2'),X('A3')),'T-Q':perm(X('C2'),X('C2QY'))}}
OUT['secondary']=sec
print('\nreached (only first / only second):'); [print(f"  {k:60s} {v['only_first']:3d}/{v['only_second']:<3d} p={v['p']:.4f}") for k,v in sec['reached'].items()]
print(f"  reached, critique - question-only at equal tokens: {rq['diff']:+.0f}, 90% interval [{rq['lo90']:+.0f},{rq['hi90']:+.0f}]; within +-33: {rq['within_33']}")
print('selected:'); [print(f"  {k:60s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}") for k,v in sec['selected'].items()]
for k,v in sec['exact_matches_only'].items(): print(f"  exact matches only {k:6s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
OUT['by_batch']={}
for lab,I in (('first 400 new questions',range(0,400)),('second 400 new questions',range(400,800))):
    g=lambda v:[v[i] for i in I]; OUT['by_batch'][lab]={'T-A3':perm(g(S('C2')),g(S('A3'))),'T-Q':perm(g(S('C2')),g(S('C2QY')))}
    b=OUT['by_batch'][lab]; print(f"{lab}: T-A3 {b['T-A3']['diff']:+.1f} [{b['T-A3']['lo']:+.1f},{b['T-A3']['hi']:+.1f}]  T-Q {b['T-Q']['diff']:+.1f} [{b['T-Q']['lo']:+.1f},{b['T-Q']['hi']:+.1f}]")
for key,lab in (('category','subject'),('answer_type','answer type')):
    st=strata(['hle_confirm_s1.jsonl','hle_confirm_s2.jsonl'],key); out={}; ag={c:[0,0] for c in ('A3','C2QY')}
    print(f"\nby {lab}: critique vs nine samples | vs question-only at equal tokens : reached only-critique/only-other, selected difference")
    for g,I in sorted(st.items(),key=lambda kv:-len(kv[1])):
        row={'n':len(I)}; cells=[]
        for c in ('A3','C2QY'):
            b=sum(Rc('C2')[i] and not Rc(c)[i] for i in I); k=sum(Rc(c)[i] and not Rc('C2')[i] for i in I); d=sum(S('C2')[i]-S(c)[i] for i in I)
            row[NAMES[c]]={'reached_only_critique':b,'reached_only_other':k,'selected_diff':round(d,1)}; cells.append(f"{b:3d}/{k:<3d} {d:+6.1f}"); ag[c][0]+=b>k; ag[c][1]+=d>0
        out[g]=row; print(f"  {str(g):28s} n={len(I):4d}  "+' | '.join(cells))
    out['_strata_in_which_critique_is_ahead (reached, selected)']={NAMES[c]:ag[c] for c in ag}; print('  strata in which critique is ahead (reached, selected):',out['_strata_in_which_critique_is_ahead (reached, selected)']); OUT[f'by_{key}']=out
json.dump({'selected':{a:S(a) for a in R},'reached':{a:Rc(a) for a in R},'selected_exact':{a:X(a) for a in R}},open(T+'vectors_confirm_addendum.json','w'))
json.dump(OUT,open(T+'selection_confirmation_addendum_readout.json','w'),indent=1)
