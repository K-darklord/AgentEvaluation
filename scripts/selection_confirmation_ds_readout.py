#!/usr/bin/env python3
"""Read-out of the confirmation on the 800 new questions for the second model, deepseek-v4-flash
(docs/SELECTION_CONFIRMATION_DEEPSEEK_SPEC.md, section 2; criteria as for qwen).
 token alignment; D-S1 selected(critique) - selected(token-yoked); D-S2 critique - reassuring; D-A3 critique - nine samples
 (sign-flip permutation, two-sided, Holm over the three); D-R1 equivalence of reached within +-27 (90% bootstrap interval);
 descriptive rows; mean of the two models on the same 800 questions (descriptive).
Reads frozen files only. Usage: python3 scripts/selection_confirmation_ds_readout.py
(writes experiments/hle400/t3/selection_confirmation_ds_readout.json)"""
import json,gc
from confirm_common import *
D='deepseek-v4-flash-payg'; side=J('is_correct_t3_sidecar_confirm_ds.json')['arms']; B=J('yoke_budget_deepseek_confirm.json')['budget']
NAMES={'A':'first answer','A2':'reassuring','A2P':'generic doubt','A2PY':'token-yoked generic doubt','C2':'critique','A3':'nine samples'}
R={}
for a in NAMES: R[a]=arm(f'experiments/conf_{a}_{D}/{D}',side[a],critic=(a=='C2'),samples=(a=='A3')); gc.collect()
R['A2PYw']=arm(f'experiments/conf_A2PY_{D}/{D}',side['A2PY'],budget=B,within=True); gc.collect()
TASKS=order(R['C2']); assert len(TASKS)==800 and all(order(R[a])==TASKS for a in R)
OUT={'n':800,'model':D}
yt=sum(R['A2PY'][t]['all_tokens'] for t in TASKS); BT=sum(B.values()); cap=sum(R['A2PY'][t]['cap'] for t in TASKS); aligned=(0.95<=yt/BT<=1.20) and cap<=40
OUT['token_alignment']={'critique_total_M':round(BT/1e6,2),'token_yoked_total_M':round(yt/1e6,2),'ratio':round(yt/BT,3),'questions_at_cap':cap,'aligned':aligned}
print(f"token alignment: token-yoked {yt/1e6:.2f}M against critique {BT/1e6:.2f}M (ratio {yt/BT:.3f}); at the cap {cap}; aligned {aligned}\n")
OUT['conditions']={NAMES[a]:summary(R[a],TASKS) for a in NAMES}
print(f"{'method':28s} last selected reached conv | exact: reached selected | rounds cand change tokens | repeat cor/inc ratio | first revision +/-")
for n,s in OUT['conditions'].items(): print(f"{n:28s} {s['last']:4d} {s['selected']:6.1f} {s['reached']:4d} {s['conversion']:.2f} | {s['reached_exact']:4d} {s['selected_exact']:6.1f} | {s['rounds_per_q']:5.2f} {s['candidates_per_q']:.2f} {s['answer_change_rate']:.2f} {s['tokens_M']:6.1f}M | {s['repeat_correct']:.2f}/{s['repeat_incorrect']:.2f} {s['repeat_ratio']} | {s['first_revision_repaired']}/{s['first_revision_damaged']}")
S=lambda a:vec(R[a],'selected',TASKS); Rc=lambda a:vec(R[a],'reached',TASKS); X=lambda a:vec(R[a],'selected_x',TASKS)
conf={'D-S1 selected: critique - token-yoked generic doubt':perm(S('C2'),S('A2PY')),'D-S2 selected: critique - reassuring':perm(S('C2'),S('A2')),'D-A3 selected: critique - nine samples':perm(S('C2'),S('A3'))}
holm(conf)
if not aligned: conf['D-S1 selected: critique - token-yoked generic doubt']['confirmed']=None
OUT['confirmatory']=conf; print('\nconfirmatory tests (selected), Holm over three')
for k,v in conf.items(): print(f"  {k:52s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}]  p={v['p']:.4f}  Holm p={v['p_holm']:.4f}  confirmed: {v['confirmed']}")
r1=perm(Rc('C2'),Rc('A2PY')); r1['mcnemar']=mcn(Rc('C2'),Rc('A2PY')); M=27
r1['verdict']=('not judged (tokens not aligned)' if not aligned else 'equivalent' if (r1['lo90']>-M and r1['hi90']<M) else 'different' if (r1['lo90']>M or r1['hi90']<-M) else 'inconclusive')
OUT['D-R1 reached: critique - token-yoked generic doubt']=r1
print(f"\nD-R1 reached, critique - token-yoked: {r1['diff']:+.0f}, 90% interval [{r1['lo90']:+.0f},{r1['hi90']:+.0f}] against +-{M} -> {r1['verdict']}; discordant {r1['mcnemar']['only_first']}/{r1['mcnemar']['only_second']} p={r1['mcnemar']['p']:.4f}")
sec={'reached':{f'{NAMES[a]} vs {NAMES[b]}':mcn(Rc(a),Rc(b)) for a,b in (('C2','A2'),('C2','A2P'),('A2PY','A2P'),('A2PY','A2'),('A2P','A2'),('C2','A3'))},
     'selected':{f'{NAMES[a]} - {NAMES[b]}':perm(S(a),S(b)) for a,b in (('C2','A2P'),('A2PY','A2P'),('A2PY','A2'),('A2P','A2'),('A3','A2'),('A3','A2PY'),('C2','A'),('A2','A'))},
     'exact_matches_only':{'D-S1':perm(X('C2'),X('A2PY')),'D-S2':perm(X('C2'),X('A2')),'D-A3':perm(X('C2'),X('A3'))},
     'within_budget':{'D-S1':perm(S('C2'),vec(R['A2PYw'],'selected',TASKS)),'D-R1':{**perm(Rc('C2'),vec(R['A2PYw'],'reached',TASKS)),'mcnemar':mcn(Rc('C2'),vec(R['A2PYw'],'reached',TASKS))}},
     'last_minus_selected':{NAMES[a]:perm(vec(R[a],'last',TASKS),S(a)) for a in ('A2','A2P','A2PY','C2')},
     'exact_share_of_selected':{NAMES[a]:round(sum(X(a))/max(1e-9,sum(S(a))),3) for a in NAMES}}
OUT['secondary']=sec
print('\nreached (only first / only second):'); [print(f"  {k:44s} {v['only_first']:3d}/{v['only_second']:<3d} p={v['p']:.4f}") for k,v in sec['reached'].items()]
print('selected:'); [print(f"  {k:44s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}") for k,v in sec['selected'].items()]
for g in ('exact_matches_only','within_budget','last_minus_selected'):
    for k,v in sec[g].items(): print(f"  {g:20s} {k:28s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
print('  exact-match share of selected:',sec['exact_share_of_selected'])
OUT['by_batch']={}
for lab,I in (('first 400 new questions',range(0,400)),('second 400 new questions',range(400,800))):
    g=lambda v:[v[i] for i in I]; OUT['by_batch'][lab]={'D-S1':perm(g(S('C2')),g(S('A2PY'))),'D-S2':perm(g(S('C2')),g(S('A2'))),'D-A3':perm(g(S('C2')),g(S('A3'))),'reached':mcn(g(Rc('C2')),g(Rc('A2PY')))}
    b=OUT['by_batch'][lab]; print(f"\n{lab}: D-S1 {b['D-S1']['diff']:+.1f} [{b['D-S1']['lo']:+.1f},{b['D-S1']['hi']:+.1f}]  D-S2 {b['D-S2']['diff']:+.1f} [{b['D-S2']['lo']:+.1f},{b['D-S2']['hi']:+.1f}]  D-A3 {b['D-A3']['diff']:+.1f} [{b['D-A3']['lo']:+.1f},{b['D-A3']['hi']:+.1f}]  reach discordant {b['reached']['only_first']}/{b['reached']['only_second']}")
for key,lab in (('category','subject'),('answer_type','answer type')):
    st=strata(['hle_confirm_s1.jsonl','hle_confirm_s2.jsonl'],key); out={}; ag={c:[0,0] for c in ('A2','A2PY','A3')}
    print(f"\nby {lab}: critique vs reassuring | vs token-yoked | vs nine samples : reached only-critique/only-other, selected difference")
    for g,I in sorted(st.items(),key=lambda kv:-len(kv[1])):
        row={'n':len(I)}; cells=[]
        for c in ('A2','A2PY','A3'):
            b=sum(Rc('C2')[i] and not Rc(c)[i] for i in I); k=sum(Rc(c)[i] and not Rc('C2')[i] for i in I); d=sum(S('C2')[i]-S(c)[i] for i in I)
            row[NAMES[c]]={'reached_only_critique':b,'reached_only_other':k,'selected_diff':round(d,1)}; cells.append(f"{b:3d}/{k:<3d} {d:+6.1f}"); ag[c][0]+=b>k; ag[c][1]+=d>0
        out[g]=row; print(f"  {str(g):28s} n={len(I):4d}  "+' | '.join(cells))
    out['_strata_in_which_critique_is_ahead (reached, selected)']={NAMES[c]:ag[c] for c in ag}; print('  strata in which critique is ahead (reached, selected):',out['_strata_in_which_critique_is_ahead (reached, selected)']); OUT[f'by_{key}']=out
json.dump({'selected':{a:S(a) for a in NAMES},'reached':{a:Rc(a) for a in NAMES},'selected_exact':{a:X(a) for a in NAMES}},open(T+'vectors_confirm_ds.json','w'))
json.dump(OUT,open(T+'selection_confirmation_ds_readout.json','w'),indent=1)
