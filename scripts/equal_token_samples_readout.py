#!/usr/bin/env python3
"""Read-out of E2 (docs/EQUAL_TOKEN_SAMPLES_SPEC.md section 3, with docs/E2_DECOMPOSITION_REGISTRATION.md sections 2 and 4),
qwen3.8-flash and deepseek-v4-flash, 800 new HLE questions. Each model is one family:
 precondition: A3Y sample tokens (rounds 1..last, the T=0 first answer excluded) within 95-120% of the budget total and at
   most 40 questions at the 100-sample cap; otherwise the tests of that model are not judged.
 E-SC  selected(critique) - selected(A3Y plurality) > 0
 E-USC selected(critique) - correct(USC choice) > 0          (USC parse failures keep the fallback choice of s2_usc.py)
 E-C   on questions reached by both critique and A3Y: selected(critique) - selected(A3Y) > 0
       sign-flip permutation 10,000, two-sided, direction must be positive; Holm over these three, alpha .05.
 E-R   reached(critique) - reached(A3Y): equivalent if the 90% bootstrap interval lies within +-m (qwen 33, deepseek 27).
 Descriptive: A3Y - nine samples; USC - A3Y; A3Y against reassuring and token-yoked; exact matches only; samples per
 question; USC parse failures; reach/conversion decomposition; by answer type.
Reads frozen files only; first checks that every grader-scored round has a real verdict. Usage:
python3 scripts/equal_token_samples_readout.py [--selftest]  (writes experiments/hle400/t3/equal_token_samples_readout.json;
--selftest replaces every verdict by a coin flip, tests the code and writes nothing)"""
import json,gc,sys
from collections import Counter
from confirm_common import *
import random as _r
ST='--selftest' in sys.argv; _rnd=_r.Random(0)
def rz(a):
    if not ST: return a
    for arm_ in a.values():
        for x in arm_.values():
            for y in (x if isinstance(x,list) else [x]): y['c']=_rnd.random()<.3
    return a
cache={}
for l in open(T+'astra_verdicts_confirm.jsonl'):
    d=json.loads(l); cache[(d['task_id'],d['final_answer'])]=str(d.get('served_model'))
def samples_all(path,sl_all,budget):
    """independent samples 1..last (round 0 excluded); same definitions as confirm_common.arm"""
    out={}; bad=0
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=sl_all[t]; R=d['rounds']; assert len(keys)==len(sl)==len(R),(path,t)
        for i,r in enumerate(R):
            if sl[i].get('s') in ('astra_true','astra_false'):
                v=cache.get((t,r.get('final_answer'))); bad+= v is None or v.startswith('ERR')
        def ok(k,exact=False):
            i=max(j for j,x in enumerate(keys) if x==k); return bool(sl[i]['c']) and (not exact or sl[i].get('s')=='t1')
        ks=keys[1:]; cnt=Counter(k for k in ks if k is not None); res=dict(reached=0,selected=0.0,reached_x=0,selected_x=0.0,cand=len(cnt))
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
            res.update(reached=int(any(ok(k) for k in cnt)),selected=sum(ok(k) for k in tied)/len(tied),reached_x=int(any(ok(k,True) for k in cnt)),selected_x=sum(ok(k,True) for k in tied)/len(tied))
        res.update(n=len(ks),solver=sum(toks(r) for r in R[1:]),cap=int(len(R)-1>=100 or bool(d.get('yoke_hit_cap'))))
        out[t]=res
    assert bad==0,f'{bad} grader-scored rounds without a real verdict in {path}'
    return out
def dec(S1,R1,S0,R0):
    c1,c0=S1/max(1,R1),S0/max(1,R0); return {'total':round(S1-S0,1),'reach_term':round((R1-R0)*(c1+c0)/2,1),'conversion_term':round((c1-c0)*(R1+R0)/2,1)}
OUT={}
for key,M,m,sides in (('qwen','qwen3.8-flash-payg',33,{'loops':'is_correct_t3_sidecar_confirm.json','A3':'is_correct_t3_sidecar_confirm2.json','new':'is_correct_t3_sidecar_confirm3.json','budget':'yoke_budget_qwen_confirm.json'}),
                      ('deepseek','deepseek-v4-flash-payg',27,{'loops':'is_correct_t3_sidecar_confirm_ds.json','A3':'is_correct_t3_sidecar_confirm_ds.json','new':'is_correct_t3_sidecar_confirm_ds2.json','budget':'yoke_budget_deepseek_confirm.json'})):
    L=rz(J(sides['loops'])['arms']); S3=rz(J(sides['A3'])['arms']); N=rz(J(sides['new'])['arms']); B=J(sides['budget'])['budget']
    R={'C2':arm(f'experiments/conf_C2_{M}/{M}',L['C2'],critic=True),'A2':arm(f'experiments/conf_A2_{M}/{M}',L['A2']),'A2PY':arm(f'experiments/conf_A2PY_{M}/{M}',L['A2PY']),
       'A3':arm(f'experiments/conf_A3_{M}/{M}',S3['A3'],samples=True)}; gc.collect()
    Y=samples_all(f'experiments/conf_A3Y_{M}/{M}',N['A3Y'],B); U=N['USC']
    ts=order(R['C2']); assert len(ts)==800 and all(order(R[a])==ts for a in R) and order(Y)==ts and order(U)==ts
    v=lambda A,k,q=ts:[A[t][k] for t in q]; S=lambda a:v(R[a],'selected'); Rc=lambda a:v(R[a],'reached')
    sY,rY=v(Y,'selected'),v(Y,'reached'); u=[float(bool(U[t]['c'])) for t in ts]; ux=[float(bool(U[t]['c']) and U[t].get('s')=='t1') for t in ts]
    yt=sum(v(Y,'solver')); bt=sum(B[t] for t in ts); cap=sum(v(Y,'cap')); aligned=bool(.95<=yt/bt<=1.20 and cap<=40)
    o={'alignment':{'A3Y_tokens_M':round(yt/1e6,2),'budget_M':round(bt/1e6,2),'ratio':round(yt/bt,3),'at_cap':cap,'aligned':aligned}}
    sp=sorted(v(Y,'n')); o['samples_per_question']={'median':sp[400],'mean':round(sum(sp)/800,2),'max':sp[-1]}
    o['usc_parse_failures']=sum(not U[t]['parse_ok'] for t in ts)
    o['conditions']={'critique':summary(R['C2'],ts),'reassuring':summary(R['A2'],ts),'token-yoked generic doubt':summary(R['A2PY'],ts),'nine samples':summary(R['A3'],ts),
        'equal-token samples':{'reached':sum(rY),'selected':round(sum(sY),1),'conversion':round(sum(sY)/max(1,sum(rY)),3),'reached_exact':sum(v(Y,'reached_x')),'selected_exact':round(sum(v(Y,'selected_x')),1),'candidates_per_q':round(sum(v(Y,'cand'))/800,2)},
        'USC':{'correct':sum(u),'correct_exact':sum(ux)}}
    both=[i for i,t in enumerate(ts) if R['C2'][t]['reached'] and Y[t]['reached']]
    tests={'E-SC selected: critique - equal-token samples':perm(S('C2'),sY),'E-USC selected: critique - USC':perm(S('C2'),u),
           'E-C selected on questions reached by both: critique - equal-token samples':perm([S('C2')[i] for i in both],[sY[i] for i in both])}
    holm(tests)
    for x in tests.values():
        x['judged']=aligned
        if not aligned: x['confirmed']=None
    o['n_reached_by_both']=len(both); o['tests']=tests
    er=perm(Rc('C2'),rY); er['mcnemar']=mcn(Rc('C2'),rY)
    er['verdict']=('not judged (tokens not aligned)' if not aligned else 'equivalent' if (er['lo90']>-m and er['hi90']<m) else 'different' if (er['lo90']>m or er['hi90']<-m) else 'inconclusive'); er['margin']=m
    o['E-R reached: critique - equal-token samples']=er
    o['decomposition']={'critique - equal-token samples':dec(sum(S('C2')),sum(Rc('C2')),sum(sY),sum(rY)),'critique - nine samples':dec(sum(S('C2')),sum(Rc('C2')),sum(S('A3')),sum(Rc('A3'))),
                        'token-yoked - equal-token samples':dec(sum(S('A2PY')),sum(Rc('A2PY')),sum(sY),sum(rY))}
    o['descriptive']={'equal-token samples - nine samples':perm(sY,S('A3')),'USC - equal-token samples':perm(u,sY),'equal-token samples - reassuring':perm(sY,S('A2')),
        'equal-token samples - token-yoked':perm(sY,S('A2PY')),'reached equal-token vs nine samples':mcn(rY,Rc('A3')),
        'exact only, E-SC':perm(v(R['C2'],'selected_x'),v(Y,'selected_x')),'exact only, E-USC':perm(v(R['C2'],'selected_x'),ux)}
    st=strata(['hle_confirm_s1.jsonl','hle_confirm_s2.jsonl'],'answer_type'); o['by_answer_type']={}
    for g,I in st.items():
        o['by_answer_type'][g]={'n':len(I),'E-SC':perm([S('C2')[i] for i in I],[sY[i] for i in I]),'E-USC':perm([S('C2')[i] for i in I],[u[i] for i in I])}
    OUT[key]=o
    print(f"\n=== {M} ===\nalignment {o['alignment']}; samples per question {o['samples_per_question']}; USC parse failures {o['usc_parse_failures']}")
    for n,s in o['conditions'].items(): print(f"  {n:26s} {s}")
    for k,x in tests.items(): print(f"  {k:72s} {x['diff']:+6.1f} [{x['lo']:+.1f},{x['hi']:+.1f}] p={x['p']:.4f} Holm={x['p_holm']:.4f} confirmed={x['confirmed']}")
    print(f"  E-R reached: critique - equal-token samples {er['diff']:+.0f}, 90% [{er['lo90']:+.0f},{er['hi90']:+.0f}] vs +-{m} -> {er['verdict']}; discordant {er['mcnemar']['only_first']}/{er['mcnemar']['only_second']} (questions reached by both: {len(both)})")
    for k,x in o['decomposition'].items(): print('  decomposition',k,x)
    for k,x in o['descriptive'].items(): print('  ',k,x)
    for g,x in o['by_answer_type'].items(): print(f"  {g}: n={x['n']} E-SC {x['E-SC']['diff']:+.1f} [{x['E-SC']['lo']:+.1f},{x['E-SC']['hi']:+.1f}]  E-USC {x['E-USC']['diff']:+.1f} [{x['E-USC']['lo']:+.1f},{x['E-USC']['hi']:+.1f}]")
    del R,Y,L,S3,N; gc.collect()
print('selftest:',ST)
if not ST: json.dump(OUT,open(T+'equal_token_samples_readout.json','w'),indent=1)
