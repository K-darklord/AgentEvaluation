#!/usr/bin/env python3
"""Read-out of (1) the controls continued to the critique loop's token budget on qwen3.8-flash
(docs/EQUAL_TOKEN_CONTROLS_SPEC.md v4, section 5) and (2) the token-yoked generic-doubt control on MiniMax-M2.5
(docs/TOKEN_YOKED_MINIMAX_ADDENDUM.md; criteria of docs/TOKEN_YOKED_CONTROL_SPEC.md v2.1, section 5).
Equal-token trajectory of a question = its rounds up to and including the first round at which cumulative tokens
reach the question's budget (what a run that stops at the budget would contain). Three views are reported:
natural stop (the earlier runs), equal tokens per question (primary), all rounds actually run.
 qwen:    E1 critique vs question-only, E2 critique vs mismatched, E3 critique vs reassuring, each at equal tokens
          (reached, exact McNemar, two-sided, Holm over the three); companions; selected (descriptive).
 MiniMax: token alignment; Y1 critique vs token-yoked generic doubt; Y2 token-yoked vs generic doubt.
Reads frozen files only. Usage: python3 scripts/equal_token_readout.py  (writes experiments/hle400/t3/equal_token_readout.json)"""
import json,importlib.util,random
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T='experiments/hle400/t3/'
def J(f): return json.load(open(T+f))
def toks(r,critic=False): return (r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0)+(((r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0)) if critic else 0)
def mcn(x,y):
    b=sum(p and not q for p,q in zip(x,y)); c=sum(q and not p for p,q in zip(x,y)); n=b+c
    return {'only_first':b,'only_second':c,'p':round(1.0 if n==0 else min(1.0,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n),5)}
def perm(x,y):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]
    ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(10000)); bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return {'diff':round(obs,1),'lo':round(bs[50],1),'hi':round(bs[1949],1),'p':round((ge+1)/10001,4)}
def rdiff(x,y):
    """difference in reached questions, first minus second, with 90% and 95% bootstrap intervals over questions"""
    d=[float(a)-float(b) for a,b in zip(x,y)]; r=random.Random(1); bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return {'diff':round(sum(d)),'lo90':round(bs[100]),'hi90':round(bs[1899]),'lo95':round(bs[50]),'hi95':round(bs[1949])}
def holm(tests,keys):
    run=0.0
    for i,k in enumerate(sorted(keys,key=lambda k:tests[k]['p'])):
        run=max(run,min(1.0,(len(keys)-i)*tests[k]['p'])); tests[k]['p_holm']=round(run,5)
class Arm:
    def __init__(s,path,side,critic=False):
        s.L=reco.load_jsonl(Path(path)/'loop_trajectories.jsonl'); s.side=side; s.critic=critic; s.tasks=sorted(s.L)
        s.K={t:reco.freeze_keys(s.L[t].get('gold_answer',''),s.L[t]) for t in s.tasks}
    def n_aligned(s,t,budget):
        cum=0
        for j,r in enumerate(s.L[t]['rounds']):
            cum+=toks(r,s.critic)
            if cum>=budget: return j+1
        return len(s.L[t]['rounds'])
    def tokens(s,t,n=None): return sum(toks(r,s.critic) for r in s.L[t]['rounds'][:n])
    def score(s,t,n=None,exact=False):
        keys=s.K[t]; sl=s.side[t]
        def ok(k):
            i=max(j for j,x in enumerate(keys) if x==k); return bool(sl[i]['c']) and (not exact or sl[i].get('s')=='t1')
        cnt=Counter(k for k in keys[:n] if k is not None)
        if not cnt: return False,0.0,0
        top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
        return any(ok(k) for k in cnt), sum(ok(k) for k in tied)/len(tied), len(cnt)
    def vec(s,ns=None,exact=False):
        v=[s.score(t,None if ns is None else ns[t],exact) for t in s.tasks]; return [x[0] for x in v],[x[1] for x in v],[x[2] for x in v]
    def change_rate(s,ns=None):
        c=n=0
        for t in s.tasks:
            k=s.K[t][:None if ns is None else ns[t]]
            for i in range(1,len(k)):
                if k[i-1] is not None and k[i] is not None: n+=1; c+= k[i]!=k[i-1]
        return round(c/max(1,n),3)
OUT={}
# ============================ qwen: continued controls ============================
Q='qwen3.8-flash-payg'; BUD=J('yoke_budget_qwen.json')['budget']; TOT=sum(BUD.values())
rep=J('is_correct_t3_sidecar_rep.json')['arms']; ctrl=J('is_correct_t3_sidecar_ctrl.json')['arms']; c2=J('is_correct_t3_sidecar_ctrl2.json')['arms']; yk=J('is_correct_t3_sidecar_yoke.json')['arms']
C=Arm(f'experiments/rep200_C2_{Q}/{Q}',rep['C2']); TASKS=C.tasks
NAT={'reassuring':Arm(f'experiments/rep200_A2_{Q}/{Q}',rep['A2']),'mismatched critique':Arm(f'experiments/ctrl_C2X_{Q}/{Q}',ctrl['C2X']),'generic doubt':Arm(f'experiments/rep200_A2P_{Q}/{Q}',rep['A2P']),'question-only critique':Arm(f'experiments/ctrl_C2Q_{Q}/{Q}',ctrl['C2Q'],True)}
EQ={'reassuring':Arm(f'experiments/yoke_A2Y_{Q}/{Q}',c2['A2Y']),'mismatched critique':Arm(f'experiments/yoke_C2XY_{Q}/{Q}',c2['C2XY']),'generic doubt':Arm(f'experiments/yoke_A2PY_{Q}/{Q}',yk['A2PY']),'question-only critique':Arm(f'experiments/yoke_C2QY_{Q}/{Q}',c2['C2QY'],True)}
Rc,Sc,_=C.vec(); Rcx,Scx,_=C.vec(exact=True)
OUT['qwen']={'critique':{'reached':sum(Rc),'selected':round(sum(Sc),1),'tokens_M':round(TOT/1e6,2),'selected_exact':round(sum(Scx),1)},'feedback':{}}
V={}
print(f"qwen. critique loop: reached {sum(Rc)}, selected {sum(Sc):.1f}, {TOT/1e6:.2f}M tokens\n")
print(f"{'feedback':24s} | natural stop: reach sel tokens | equal tokens: reach sel tokens(ratio) rounds cand change cap | all rounds: reach sel tokens(ratio)")
for name in ('reassuring','mismatched critique','generic doubt','question-only critique'):
    a=EQ[name]; nat=NAT[name]; ns={t:a.n_aligned(t,BUD[t]) for t in TASKS}
    Rn,Sn,_=nat.vec(); Re,Se,Ce=a.vec(ns); Ra,Sa,_=a.vec(); Rex,Sex,_=a.vec(ns,exact=True)
    tn=sum(nat.tokens(t) for t in TASKS); te=sum(a.tokens(t,ns[t]) for t in TASKS); ta=sum(a.tokens(t) for t in TASKS)
    cap=sum(bool(a.L[t].get('yoke_hit_cap')) for t in TASKS); short=sum(a.tokens(t,ns[t])<BUD[t] for t in TASKS)
    aligned=(0.95<=te/TOT<=1.20) and short<=20
    d={'natural':{'reached':sum(Rn),'selected':round(sum(Sn),1),'tokens_M':round(tn/1e6,1)},
       'equal_tokens':{'reached':sum(Re),'selected':round(sum(Se),1),'selected_exact':round(sum(Sex),1),'tokens_M':round(te/1e6,2),'ratio':round(te/TOT,3),'feedback_rounds_per_q':round(sum(ns[t]-1 for t in TASKS)/400,2),'candidates_per_q':round(sum(Ce)/400,2),'answer_change_rate':a.change_rate(ns),'questions_short_of_budget':short,'aligned':aligned},
       'all_rounds':{'reached':sum(Ra),'selected':round(sum(Sa),1),'tokens_M':round(ta/1e6,2),'ratio':round(ta/TOT,3),'at_cap':cap}}
    OUT['qwen']['feedback'][name]=d; V[name]={'nat':(Rn,Sn),'eq':(Re,Se),'all':(Ra,Sa),'eqx':(Rex,Sex)}
    e=d['equal_tokens']
    print(f"{name:24s} | {sum(Rn):3d} {sum(Sn):5.1f} {tn/1e6:5.1f}M | {e['reached']:3d} {e['selected']:5.1f} {e['tokens_M']:5.2f}M ({e['ratio']:.3f}) {e['feedback_rounds_per_q']:5.2f} {e['candidates_per_q']:.2f} {e['answer_change_rate']:.2f} short {short} aligned {aligned} | {sum(Ra):3d} {sum(Sa):5.1f} {ta/1e6:5.2f}M ({ta/TOT:.3f}) cap {cap}")
tests={}
for lab,name in (('E1 critique vs question-only','question-only critique'),('E2 critique vs mismatched','mismatched critique'),('E3 critique vs reassuring','reassuring'),('(earlier Y1) critique vs generic doubt','generic doubt')):
    tests[lab]={'equal_tokens':mcn(Rc,V[name]['eq'][0]),'natural':mcn(Rc,V[name]['nat'][0]),'all_rounds':mcn(Rc,V[name]['all'][0]),'gain_from_tokens':mcn(V[name]['eq'][0],V[name]['nat'][0]),
               'selected_equal_tokens':perm(Sc,V[name]['eq'][1]),'selected_natural':perm(Sc,V[name]['nat'][1]),'selected_all_rounds':perm(Sc,V[name]['all'][1]),'selected_exact_equal_tokens':perm(Scx,V[name]['eqx'][1])}
prim=['E1 critique vs question-only','E2 critique vs mismatched','E3 critique vs reassuring']
P={k:tests[k]['equal_tokens'] for k in prim}; holm(P,prim)
OUT['qwen']['reached_difference_equal_tokens']={k:rdiff(Rc,V[n]['eq'][0]) for k,n in (('critique - question-only','question-only critique'),('critique - mismatched','mismatched critique'),('critique - reassuring','reassuring'),('critique - generic doubt','generic doubt'))}
print('\nreached, critique minus control at equal tokens, with 90% interval:',OUT['qwen']['reached_difference_equal_tokens'])
OUT['qwen']['tests']=tests
print('\nreached: critique only / control only (exact McNemar)')
for k,v in tests.items():
    e=v['equal_tokens']; print(f"  {k:40s} equal tokens {e['only_first']:3d}/{e['only_second']:<3d} p={e['p']:.4f}"+(f" Holm p={e['p_holm']:.4f}" if 'p_holm' in e else ' '*14)+f" | natural {v['natural']['only_first']}/{v['natural']['only_second']} | all rounds {v['all_rounds']['only_first']}/{v['all_rounds']['only_second']} p={v['all_rounds']['p']:.4f} | equal tokens vs natural stop of the same feedback {v['gain_from_tokens']['only_first']}/{v['gain_from_tokens']['only_second']} p={v['gain_from_tokens']['p']:.4f}")
print('\nselected: critique minus control (descriptive)')
for k,v in tests.items():
    s=v['selected_equal_tokens']; x=v['selected_exact_equal_tokens']; print(f"  {k:40s} equal tokens {s['diff']:+5.1f} [{s['lo']:+.1f},{s['hi']:+.1f}] p={s['p']:.3f} | exact matches only {x['diff']:+5.1f} [{x['lo']:+.1f},{x['hi']:+.1f}] p={x['p']:.3f} | natural {v['selected_natural']['diff']:+.1f} | all rounds {v['selected_all_rounds']['diff']:+.1f}")
names=['reassuring','mismatched critique','generic doubt','question-only critique']
OUT['qwen']['between_controls_equal_tokens']={f'{a} vs {b}':mcn(V[a]['eq'][0],V[b]['eq'][0]) for i,a in enumerate(names) for b in names[i+1:]}
print('\nequal tokens, controls against each other (reached only-first / only-second):')
for k,v in OUT['qwen']['between_controls_equal_tokens'].items(): print(f"  {k:48s} {v['only_first']}/{v['only_second']} p={v['p']:.4f}")
a=EQ['question-only critique']; nat=NAT['question-only critique']; over=[i for i,t in enumerate(TASKS) if nat.tokens(t)>=BUD[t]]; under=[i for i in range(400) if i not in set(over)]
Re=V['question-only critique']['eq'][0]
OUT['qwen']['question_only_strata']={lab:{'n':len(I),'critique_reached':sum(Rc[i] for i in I),'control_reached':sum(Re[i] for i in I),'only_critique':sum(Rc[i] and not Re[i] for i in I),'only_control':sum(Re[i] and not Rc[i] for i in I)} for lab,I in (('already_over_budget',over),('continued',under))}
print('\nquestion-only critique by stratum:',OUT['qwen']['question_only_strata'])
OUT['qwen']['exact_share_of_selected']={n:round(sum(V[n]['eqx'][1])/max(1e-9,sum(V[n]['eq'][1])),3) for n in names}; OUT['qwen']['exact_share_of_selected']['critique']=round(sum(Scx)/sum(Sc),3)
print('share of selected questions that are exact matches (equal tokens):',OUT['qwen']['exact_share_of_selected'])
# ============================ MiniMax: token-yoked generic doubt ============================
MB=J('yoke_budget_minimax.json')['budget']; MT=sum(MB.values()); r3=J('is_correct_t3_sidecar_rep3.json')['arms']; ymm=J('is_correct_t3_sidecar_yoke_minimax.json')['arms']
mC=Arm('experiments/rep3_C2_minimax-m2.5/minimax-m2.5',r3['C2']); mG=Arm('experiments/rep3_A2P_minimax-m2.5/minimax-m2.5',r3['A2P']); mR=Arm('experiments/rep3_A2_minimax-m2.5/minimax-m2.5',r3['A2']); mY=Arm('experiments/yoke_A2PY_minimax-m2.5/minimax-m2.5',ymm['A2PY'])
MTASKS=mC.tasks; ns={t:mY.n_aligned(t,MB[t]) for t in MTASKS}
# within budget: rounds whose cumulative cost does not exceed the budget (round 0 always kept)
nw={}
for t in MTASKS:
    cum=0; n=1
    for j,r in enumerate(mY.L[t]['rounds']):
        cum+=toks(r)
        if j==0 or cum<=MB[t]: n=j+1
        else: break
    nw[t]=n
RC,SC,_=mC.vec(); RG,SG,_=mG.vec(); RR,SR,_=mR.vec(); RY,SY,CY=mY.vec(); RW,SW,_=mY.vec(nw); RCx,SCx,_=mC.vec(exact=True); RYx,SYx,_=mY.vec(exact=True)
ty=sum(mY.tokens(t) for t in MTASKS); cap=sum(bool(mY.L[t].get('yoke_hit_cap')) for t in MTASKS); al=(0.95<=ty/MT<=1.20) and cap<=20
OUT['minimax']={'token_alignment':{'critique_total_M':round(MT/1e6,2),'yoked_total_M':round(ty/1e6,2),'ratio':round(ty/MT,3),'questions_at_cap':cap,'aligned':al},
 'conditions':{'reassuring':{'reached':sum(RR),'selected':round(sum(SR),1)},'generic doubt':{'reached':sum(RG),'selected':round(sum(SG),1),'answer_change_rate':mG.change_rate()},
               'token-yoked generic doubt':{'reached':sum(RY),'selected':round(sum(SY),1),'reached_within_budget':sum(RW),'selected_within_budget':round(sum(SW),1),'feedback_rounds_per_q':round(sum(len(mY.L[t]['rounds'])-1 for t in MTASKS)/400,2),'candidates_per_q':round(sum(CY)/400,2),'answer_change_rate':mY.change_rate(),'selected_exact':round(sum(SYx),1)},
               'critique':{'reached':sum(RC),'selected':round(sum(SC),1),'answer_change_rate':mC.change_rate(),'selected_exact':round(sum(SCx),1)}},
 'tests':{'Y1 critique vs token-yoked (all rounds)':mcn(RC,RY),'Y1 critique vs token-yoked (within budget)':mcn(RC,RW),'Y2 token-yoked vs generic doubt':mcn(RY,RG),'reference: token-yoked vs reassuring':mcn(RY,RR),'reference: critique vs generic doubt':mcn(RC,RG)},
 'selected':{'critique - token-yoked':perm(SC,SY),'critique - token-yoked (exact matches only)':perm(SCx,SYx),'token-yoked - generic doubt':perm(SY,SG),'critique - generic doubt':perm(SC,SG),'critique - reassuring':perm(SC,SR)}}
OUT['minimax']['reached_difference']={'critique - token-yoked':rdiff(RC,RY)}
m=OUT['minimax']; c=m['conditions']; print('MiniMax reached, critique minus token-yoked:',m['reached_difference'])
print(f"\nMiniMax. token alignment: token-yoked {ty/1e6:.2f}M against {MT/1e6:.2f}M (ratio {ty/MT:.3f}); at the cap {cap}; aligned {al}")
for k,v in c.items(): print(f"  {k:26s} "+' '.join(f"{a}={b}" for a,b in v.items()))
for k,v in m['tests'].items(): print(f"  {k:46s} {v['only_first']:3d}/{v['only_second']:<3d} p={v['p']:.4f}")
for k,v in m['selected'].items(): print(f"  selected {k:44s} {v['diff']:+5.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.3f}")
json.dump(OUT,open(T+'equal_token_readout.json','w'),indent=1)
