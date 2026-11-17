#!/usr/bin/env python3
"""Read-out of the token-yoked and content controls on qwen3.8-flash, exactly as fixed in
docs/TOKEN_YOKED_CONTROL_SPEC.md (v2.1, section 5) and docs/CONTENT_CONTROLS_SPEC.md (v2.2, section 5).
Conditions: A2P generic-doubt loop, A2PY token-yoked generic-doubt control, C2X mismatched-critique loop,
C2Q question-only critique loop, C2 critique loop (A2 reassuring loop for reference).
 5.1  token alignment of A2PY (total within 95%-120% of the critique loop's cost, at most 20 questions at the cap)
 tests on reached (exact McNemar, two-sided): Y1 C2 vs A2PY (all rounds; and rounds within budget), Y2 A2PY vs A2P,
       X1 C2 vs C2X, X2 C2X vs A2P, Q1 C2 vs C2Q, Q2 C2Q vs A2P; Holm over the three primary tests Y1, X1, Q1
 selected (expected score, random ties): differences with sign-flip permutation (10,000) and bootstrap 95% interval
 manipulation checks: overlap of feedback with the question, feedback length, doubts per round, changes of answer,
       candidates, rounds, tokens; flags for C2Q against C2 (length below 70%, share of three doubts off by >15 points)
Reads frozen files only. Usage: python3 scripts/controls_readout.py  (writes experiments/hle400/t3/controls_readout.json)"""
import json,importlib.util,random,re
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T='experiments/hle400/t3/'; Q='qwen3.8-flash-payg'
SIDE=json.load(open(T+'is_correct_t3_sidecar_rep.json'))['arms']; SIDE.update(json.load(open(T+'is_correct_t3_sidecar_yoke.json'))['arms']); SIDE.update(json.load(open(T+'is_correct_t3_sidecar_ctrl.json'))['arms'])
DIR={'A2':f'experiments/rep200_A2_{Q}/{Q}','A2P':f'experiments/rep200_A2P_{Q}/{Q}','A2PY':f'experiments/yoke_A2PY_{Q}/{Q}','C2X':f'experiments/ctrl_C2X_{Q}/{Q}','C2Q':f'experiments/ctrl_C2Q_{Q}/{Q}','C2':f'experiments/rep200_C2_{Q}/{Q}'}
NAME={'A2':'reassuring','A2P':'generic doubt','A2PY':'token-yoked generic doubt','C2X':'mismatched critique','C2Q':'question-only critique','C2':'critique'}
L={a:reco.load_jsonl(Path(p)/'loop_trajectories.jsonl') for a,p in DIR.items()}
TASKS=sorted(L['C2']); assert len(TASKS)==400 and all(sorted(L[a])==TASKS for a in L)
BUD=json.load(open(T+'yoke_budget_qwen.json')); CRITIC=BUD['critic_tokens_per_call']
K={a:{t:reco.freeze_keys(L[a][t].get('gold_answer',''),L[a][t]) for t in TASKS} for a in L}
def toks(r): return (r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0)
def reach_sel(a,t,n=None):
    keys=K[a][t]; s=SIDE[a][t]; ok={k:reco.last_key_correct(keys,s,k) for k in set(keys) if k is not None}
    ks=[k for k in (keys if n is None else keys[:n]) if k is not None]; cnt=Counter(ks)
    if not cnt: return False,0.0
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return any(ok[k] for k in cnt), sum(ok[k] for k in tied)/len(tied)
R={a:[reach_sel(a,t)[0] for t in TASKS] for a in L}; S={a:[reach_sel(a,t)[1] for t in TASKS] for a in L}
# A2PY within budget: rounds whose cumulative solver tokens do not exceed the budget (round 0 always kept)
keep=[]
for t in TASKS:
    cum=0; n=1
    for j,r in enumerate(L['A2PY'][t]['rounds']):
        cum+=toks(r)
        if j==0 or cum<=BUD['budget'][t]: n=j+1
        else: break
    keep.append(n)
R['A2PY_within']=[reach_sel('A2PY',t,n)[0] for t,n in zip(TASKS,keep)]; S['A2PY_within']=[reach_sel('A2PY',t,n)[1] for t,n in zip(TASKS,keep)]
def mcn(x,y):
    b=sum(p and not q for p,q in zip(R[x],R[y])); c=sum(q and not p for p,q in zip(R[x],R[y])); n=b+c
    p=1.0 if n==0 else min(1.0,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n)
    return {'only_first':b,'only_second':c,'p':round(p,5)}
def perm(x,y):
    d=[a-b for a,b in zip(S[x],S[y])]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]
    ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(10000))
    bs=sorted(sum(d[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    return {'diff':round(obs,1),'lo':round(bs[50],1),'hi':round(bs[1949],1),'p':round((ge+1)/10001,4)}
OUT={'conditions':{}}
# ---- 5.1 token alignment ----
c2_total=sum(BUD['budget'][t] for t in TASKS); y_total=sum(sum(toks(r) for r in L['A2PY'][t]['rounds']) for t in TASKS)
cap=sum(bool(L['A2PY'][t].get('yoke_hit_cap')) for t in TASKS)
aligned=(0.95<=y_total/c2_total<=1.20) and cap<=20
OUT['token_alignment']={'critique_total_M':round(c2_total/1e6,2),'yoked_total_M':round(y_total/1e6,2),'ratio':round(y_total/c2_total,3),'questions_at_cap':cap,'aligned':aligned,
                        'within_budget_total_M':round(sum(sum(toks(r) for r in L['A2PY'][t]['rounds'][:n]) for t,n in zip(TASKS,keep))/1e6,2)}
print(f"5.1 token alignment: token-yoked spent {y_total/1e6:.2f}M against {c2_total/1e6:.2f}M for the critique loop (ratio {y_total/c2_total:.3f}); questions at the 100-round cap: {cap}; aligned: {aligned}")
# ---- descriptives and manipulation checks ----
STOP=set("a an the of to in on at for by with from and or not is are was were be been being this that these those it its as if then than so such which who whom what when where how why can could may might must shall should will would do does did have has had you your we our they their he she his her i me my no yes one two three any all each some more most other into over under between about also only both same very".split())
def words(s): return {w for w in re.findall(r"[a-z][a-z\-]{2,}",str(s).lower()) if w not in STOP}
def fb_text(r): return ' '.join(' '.join(str(d.get(k) or '') for k in ('archetype_name','suspicion','check')) for d in (r.get('critic_direction') or []))
for a in ('A2','A2P','A2PY','C2X','C2Q','C2'):
    fbr=[];chg=tot=0;cand=[];ov=[];ln=[];nd=Counter();solver=0;critic=0;fallback=0
    for t in TASKS:
        rs=L[a][t]['rounds']; fbr.append(len(rs)-1); keys=K[a][t]; cand.append(len({k for k in keys if k is not None})); solver+=sum(toks(r) for r in rs)
        qw=words(L[a][t].get('prompt',''))
        for i in range(1,len(rs)):
            if keys[i-1] is not None and keys[i] is not None: tot+=1; chg+= keys[i]!=keys[i-1]
            cd=rs[i].get('critic_direction') or []; fallback+=bool(rs[i].get('critic_fallback'))
            if a!='A2':
                nd[len(cd)]+=1
                if cd:
                    tx=fb_text(rs[i]); ln.append(len(tx)); fw=words(tx); ov.append(len(fw&qw)/max(1,len(fw|qw)))
            if a=='C2': critic+=CRITIC
            if a=='C2Q': critic+=(rs[i].get('critic_prompt_tokens') or 0)+(rs[i].get('critic_completion_tokens') or 0)
            if a=='C2X': critic+=CRITIC  # cost at which the reused critiques were originally produced (not spent again)
    d={'name':NAME[a],'reached':sum(R[a]),'selected':round(sum(S[a]),1),'feedback_rounds_per_q':round(sum(fbr)/400,2),'candidates_per_q':round(sum(cand)/400,2),
       'answer_change_rate':round(chg/tot,3),'solver_tokens_M':round(solver/1e6,1),'critic_tokens_M':round(critic/1e6,1),'total_tokens_M':round((solver+critic)/1e6,1)}
    if ln: d.update(feedback_chars_mean=round(sum(ln)/len(ln)),overlap_with_question=round(sum(ov)/len(ov),3),share_three_doubts=round(nd[3]/sum(nd.values()),3),doubts_per_round=dict(sorted(nd.items())),critic_fallback_rounds=fallback)
    OUT['conditions'][a]=d
    print(f"{NAME[a]:26s} reached {d['reached']:3d} selected {d['selected']:5.1f} | rounds/q {d['feedback_rounds_per_q']:5.2f} cand/q {d['candidates_per_q']:.2f} change rate {d['answer_change_rate']:.2f} | tokens {d['solver_tokens_M']}+{d['critic_tokens_M']}M"+(f" | feedback {d['feedback_chars_mean']} chars, overlap with question {d['overlap_with_question']:.3f}, three doubts {d['share_three_doubts']:.2f}, fallback rounds {fallback}" if ln else ''))
OUT['conditions']['A2PY_within']={'name':'token-yoked, rounds within budget','reached':sum(R['A2PY_within']),'selected':round(sum(S['A2PY_within']),1)}
print(f"{'token-yoked, within budget':26s} reached {sum(R['A2PY_within']):3d} selected {sum(S['A2PY_within']):5.1f}")
c2,cq=OUT['conditions']['C2'],OUT['conditions']['C2Q']
flag=(cq['feedback_chars_mean']<0.70*c2['feedback_chars_mean']) or abs(cq['share_three_doubts']-c2['share_three_doubts'])>0.15
OUT['c2q_length_confound_flag']={'length_ratio':round(cq['feedback_chars_mean']/c2['feedback_chars_mean'],2),'three_doubts_difference':round(cq['share_three_doubts']-c2['share_three_doubts'],3),'flagged':flag}
print(f"question-only critique vs critique: feedback length ratio {cq['feedback_chars_mean']/c2['feedback_chars_mean']:.2f}, share of three doubts {cq['share_three_doubts']:.2f} vs {c2['share_three_doubts']:.2f}; flagged as confounded with length: {flag}")
# does the question-only critic's text contain the solver's next answer? (same string check as the main appendix)
def norm(s): return re.sub(r'\s+','',str(s).lower())
hit=n=0
for t in TASKS:
    keys=K['C2Q'][t]; rs=L['C2Q'][t]['rounds']
    for i in range(1,len(keys)):
        if keys[i] is None or keys[i]==keys[i-1]: continue
        fam,val=keys[i]
        if fam=='letter': continue
        c=norm(json.dumps(rs[i].get('critic_direction') or [],ensure_ascii=False)); n+=1
        hit+=(re.search(r'(?<!\d)'+re.escape(str(val))+r'(?!\d)',c) is not None) if fam=='int' else (len(norm(val))>=3 and norm(val) in c)
OUT['c2q_critic_contains_next_answer']=[hit,n]; print(f"question-only critic text contains the solver's next (changed, non-letter) answer: {hit}/{n}")
# ---- tests ----
tests={'Y1 critique vs token-yoked (all rounds)':('C2','A2PY'),'Y1 critique vs token-yoked (within budget)':('C2','A2PY_within'),'Y2 token-yoked vs generic doubt':('A2PY','A2P'),
       'X1 critique vs mismatched':('C2','C2X'),'X2 mismatched vs generic doubt':('C2X','A2P'),'Q1 critique vs question-only':('C2','C2Q'),'Q2 question-only vs generic doubt':('C2Q','A2P'),
       'reference: critique vs generic doubt':('C2','A2P'),'reference: mismatched vs reassuring':('C2X','A2'),'reference: question-only vs reassuring':('C2Q','A2'),'reference: token-yoked vs reassuring':('A2PY','A2'),'reference: question-only vs mismatched':('C2Q','C2X')}
OUT['reached_tests']={k:mcn(*v) for k,v in tests.items()}; OUT['selected_tests']={k:perm(*v) for k,v in tests.items()}
prim=['Y1 critique vs token-yoked (all rounds)','X1 critique vs mismatched','Q1 critique vs question-only']
order=sorted(prim,key=lambda k:OUT['reached_tests'][k]['p']); run=0.0
for i,k in enumerate(order):
    run=max(run,min(1.0,(3-i)*OUT['reached_tests'][k]['p'])); OUT['reached_tests'][k]['p_holm']=round(run,5)
print('\nreached (only first / only second, exact McNemar):')
for k in tests:
    r=OUT['reached_tests'][k]; s=OUT['selected_tests'][k]
    print(f"  {k:46s} {r['only_first']:3d}/{r['only_second']:<3d} p={r['p']:.4f}"+(f" Holm p={r['p_holm']:.4f}" if 'p_holm' in r else ' '*14)+f" | selected {s['diff']:+5.1f} [{s['lo']:+.1f},{s['hi']:+.1f}] p={s['p']:.3f}")
# ---- sensitivity: only exact matches count as correct (grader and adjudication ignored); added after a simulated review ----
def reach_sel_exact(a,t):
    keys=K[a][t]; s=SIDE[a][t]; cnt=Counter(k for k in keys if k is not None)
    if not cnt: return False,0.0
    def ok(k):
        i=max(j for j,x in enumerate(keys) if x==k); return bool(s[i]['c']) and s[i].get('s')=='t1'
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return any(ok(k) for k in cnt), sum(ok(k) for k in tied)/len(tied)
ARMS6=('A2','C2X','A2P','C2Q','A2PY','C2'); RX={a:[reach_sel_exact(a,t)[0] for t in TASKS] for a in ARMS6}; SX={a:[reach_sel_exact(a,t)[1] for t in TASKS] for a in ARMS6}
R_,S_=R,S; R,S=RX,SX
OUT['exact_match_only']={'selected':{a:round(sum(SX[a]),1) for a in ARMS6},'reached':{a:sum(RX[a]) for a in ARMS6},'critique_minus':{y:{'selected':perm('C2',y),'reached':mcn('C2',y)} for y in ('A2PY','C2X','C2Q','A2P','A2')}}
R,S=R_,S_
print('\nexact matches only: selected',OUT['exact_match_only']['selected'],'reached',OUT['exact_match_only']['reached'])
for y,v in OUT['exact_match_only']['critique_minus'].items(): print(f"  critique - {NAME[y]:26s} selected {v['selected']['diff']:+5.1f} [{v['selected']['lo']:+.1f},{v['selected']['hi']:+.1f}] p={v['selected']['p']:.3f} | reached {v['reached']['only_first']}/{v['reached']['only_second']} p={v['reached']['p']:.3f}")
json.dump(OUT,open(T+'controls_readout.json','w'),indent=1)
