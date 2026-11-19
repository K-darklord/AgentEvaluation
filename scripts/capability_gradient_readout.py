#!/usr/bin/env python3
"""Read-out of the capability-gradient study (docs/CAPABILITY_GRADIENT_SPEC.md, section 5): qwen4-max on the 800 new HLE
questions, same design, definitions and criteria as for qwen3.8-flash and deepseek-v4-flash.
 preconditions: tokens of the token-yoked loop and of the equal-token samples each within 95-120% of the budget total,
   at most 40 questions at the cap; a test that uses a condition failing this is not judged.
 family 1 (Holm over three): G-SC selected(critique) - selected(equal-token samples) > 0;
   G-USC selected(critique) - correct(USC) > 0; G-C the same as G-SC on questions reached by both.
 family 2 (Holm over two): G-S1 selected(critique) - selected(token-yoked) > 0; G-S2 selected(critique) - selected(reassuring) > 0.
 equivalence (90% bootstrap interval within +-33): G-R1 reached critique - token-yoked; G-R reached critique - samples.
 Descriptive: reassuring and token-yoked against equal-token samples; exact matches only; last answer; samples within
 the budget; merged correct candidates; decomposition; keep probabilities; by answer type; and the same differences for
 qwen3.8-flash on the same questions with the difference between the two models (question-level bootstrap).
First checks that every grader-scored round has a real verdict. Usage: python3 scripts/capability_gradient_readout.py
[--selftest]  (--selftest: qwen3.8-flash stands in for qwen4-max, verdicts are coin flips; tests the code, writes nothing).
Writes experiments/hle400/t3/capability_gradient_readout.json"""
import json,gc,sys,random
from collections import Counter
from confirm_common import *
ST='--selftest' in sys.argv; rnd=random.Random(0); F='qwen3.8-flash-payg'; G=F if ST else 'qwen4-max-payg'
def rz(a):
    if ST:
        for arm_ in a.values():
            for x in arm_.values():
                for y in (x if isinstance(x,list) else [x]): y['c']=rnd.random()<.3
    return a
cache={}
for l in open(T+'astra_verdicts_confirm.jsonl'):
    d=json.loads(l); cache[(d['task_id'],d['final_answer'])]=str(d.get('served_model'))
def check(path,side):
    bad=0
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); sl=side[d['task_id']]; assert len(sl)==len(d['rounds']),(path,d['task_id'])
        for i,r in enumerate(d['rounds']):
            if sl[i].get('s') in ('astra_true','astra_false'):
                v=cache.get((d['task_id'],r.get('final_answer'))); bad+= v is None or v.startswith('ERR')
    assert bad==0,f'{bad} grader-scored rounds without a real verdict in {path}'
def samples_all(path,side,B):
    out={}
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[t]; R=d['rounds']
        ok=lambda k,ex=False:(lambda i:bool(sl[i]['c']) and (not ex or sl[i].get('s')=='t1'))(max(j for j,x in enumerate(keys) if x==k))
        def vote(idx,merge=False,ex=False):
            cnt=Counter(keys[i] for i in idx if keys[i] is not None)
            if not cnt: return 0.0,0
            good={k:ok(k,ex) for k in cnt}
            if merge:
                c=sum(n for k,n in cnt.items() if good[k]); cnt=Counter({k:n for k,n in cnt.items() if not good[k]})
                if c: cnt['__c__']=c; good['__c__']=True
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; return sum(good[k] for k in tied)/len(tied),int(any(good.values()))
        full=list(range(1,len(keys))); cum=0; keep=[]
        for i in full:
            cum+=toks(R[i])
            if cum<=B[t] or not keep: keep.append(i)
            else: break
        s,r=vote(full); sx,_=vote(full,ex=True); sm,_=vote(full,merge=True); sw,rw=vote(keep)
        out[t]=dict(selected=s,reached=r,selected_x=sx,selected_merged=sm,selected_within=sw,reached_within=rw,n=len(full),solver=sum(toks(x) for x in R[1:]),cap=int(len(R)-1>=100 or bool(d.get('yoke_hit_cap'))),cand=len({k for k in keys[1:] if k is not None}))
    return out
def dec(S1,R1,S0,R0):
    c1,c0=S1/max(1,R1),S0/max(1,R0); return {'total':round(S1-S0,1),'reach_term':round((R1-R0)*(c1+c0)/2,1),'conversion_term':round((c1-c0)*(R1+R0)/2,1)}
def model(M,loops,a3,new,bud):
    L=rz(J(loops)['arms']); S3=rz(J(a3)['arms']); N=rz(J(new)['arms']); B=J(bud)['budget']
    P=lambda a:f'experiments/conf_{a}_{M}/{M}'
    for a,s in (('A2',L['A2']),('C2',L['C2']),('A2PY',L['A2PY']),('A3Y',N['A3Y'])): check(P(a),s)
    R={'C2':arm(P('C2'),L['C2'],critic=True),'A2':arm(P('A2'),L['A2']),'A2PY':arm(P('A2PY'),L['A2PY']),'A3':arm(P('A3'),S3['A3'],samples=True)}; gc.collect()
    Y=samples_all(P('A3Y'),N['A3Y'],B); U=N['USC']; ts=order(R['C2']); assert len(ts)==800 and all(order(R[a])==ts for a in R) and order(Y)==ts and order(U)==ts
    return R,Y,U,B,ts
R,Y,U,B,ts=model(G,*(('is_correct_t3_sidecar_confirm.json','is_correct_t3_sidecar_confirm2.json','is_correct_t3_sidecar_confirm3.json','yoke_budget_qwen_confirm.json') if ST else ('is_correct_t3_sidecar_q4max.json','is_correct_t3_sidecar_q4max.json','is_correct_t3_sidecar_q4max_e2.json','yoke_budget_q4max_confirm.json')))
v=lambda A,k:[A[t][k] for t in ts]; S=lambda a:v(R[a],'selected'); Rc=lambda a:v(R[a],'reached'); sY,rY=v(Y,'selected'),v(Y,'reached'); u=[float(bool(U[t]['c'])) for t in ts]
bt=sum(B[t] for t in ts); ysum=sum(v(Y,'solver')); pysum=sum(v(R['A2PY'],'all_tokens'))
al={'samples':{'ratio':round(ysum/bt,3),'at_cap':sum(v(Y,'cap'))},'token_yoked':{'ratio':round(pysum/bt,3),'at_cap':sum(v(R['A2PY'],'cap'))}}
for k in al: al[k]['aligned']=bool(.95<=al[k]['ratio']<=1.20 and al[k]['at_cap']<=40)
O={'selftest':ST,'model':G,'first_answer_correct':sum(v(R['C2'],'first')),'alignment':al,'samples_per_question':round(sum(v(Y,'n'))/800,2),'usc_parse_failures':sum(not U[t]['parse_ok'] for t in ts),
   'conditions':{'critique':summary(R['C2'],ts),'reassuring':summary(R['A2'],ts),'token-yoked generic doubt':summary(R['A2PY'],ts),'nine samples':summary(R['A3'],ts),
                 'equal-token samples':{'reached':sum(rY),'selected':round(sum(sY),1),'conversion':round(sum(sY)/max(1,sum(rY)),3),'candidates_per_q':round(sum(v(Y,'cand'))/800,2)},'USC':{'correct':sum(u)}}}
both=[i for i,t in enumerate(ts) if R['C2'][t]['reached'] and Y[t]['reached']]
f1={'G-SC selected: critique - equal-token samples':perm(S('C2'),sY),'G-USC selected: critique - USC':perm(S('C2'),u),'G-C selected on questions reached by both':perm([S('C2')[i] for i in both],[sY[i] for i in both])}; holm(f1)
f2={'G-S1 selected: critique - token-yoked generic doubt':perm(S('C2'),S('A2PY')),'G-S2 selected: critique - reassuring':perm(S('C2'),S('A2'))}; holm(f2)
for x in f1.values():
    if not al['samples']['aligned']: x['confirmed']=None
if not al['token_yoked']['aligned']: f2['G-S1 selected: critique - token-yoked generic doubt']['confirmed']=None
def eq(x,y,okk):
    r=perm(x,y); r['mcnemar']=mcn(x,y); r['verdict']=('not judged (tokens not aligned)' if not okk else 'equivalent' if (r['lo90']>-33 and r['hi90']<33) else 'different' if (r['lo90']>33 or r['hi90']<-33) else 'inconclusive'); return r
O.update({'n_reached_by_both':len(both),'family_1':f1,'family_2':f2,'G-R1 reached: critique - token-yoked':eq(Rc('C2'),Rc('A2PY'),al['token_yoked']['aligned']),'G-R reached: critique - equal-token samples':eq(Rc('C2'),rY,al['samples']['aligned'])})
O['descriptive']={'reassuring - equal-token samples':perm(S('A2'),sY),'token-yoked - equal-token samples':perm(S('A2PY'),sY),'USC - equal-token samples':perm(u,sY),'equal-token samples - nine samples':perm(sY,S('A3')),
  'exact only: critique - equal-token samples':perm(v(R['C2'],'selected_x'),v(Y,'selected_x')),'last answer of critique - equal-token samples':perm(v(R['C2'],'last'),sY),
  'critique - samples within the budget':perm(S('C2'),v(Y,'selected_within')),'reached: critique - samples within the budget':perm(Rc('C2'),v(Y,'reached_within')),
  'merged correct candidates, samples only: critique - samples':perm(S('C2'),v(Y,'selected_merged')),
  'decomposition critique - equal-token samples':dec(sum(S('C2')),sum(Rc('C2')),sum(sY),sum(rY))}
st=strata(['hle_confirm_s1.jsonl','hle_confirm_s2.jsonl'],'answer_type'); O['by_answer_type']={g:{'n':len(I),'G-SC':perm([S('C2')[i] for i in I],[sY[i] for i in I])} for g,I in st.items()}
if not ST:
    R0,Y0,U0,B0,ts0=model(F,'is_correct_t3_sidecar_confirm.json','is_correct_t3_sidecar_confirm2.json','is_correct_t3_sidecar_confirm3.json','yoke_budget_qwen_confirm.json'); assert ts0==ts
    d=lambda a,b:[x-y for x,y in zip(a,b)]; z=[0.0]*800; g=lambda A,k:[A[t][k] for t in ts]
    O['gradient: qwen4-max minus qwen3.8-flash (descriptive)']={
      'critique - equal-token samples':perm(d(S('C2'),sY),d(g(R0['C2'],'selected'),g(Y0,'selected'))),'critique - token-yoked':perm(d(S('C2'),S('A2PY')),d(g(R0['C2'],'selected'),g(R0['A2PY'],'selected'))),
      'critique - reassuring':perm(d(S('C2'),S('A2')),d(g(R0['C2'],'selected'),g(R0['A2'],'selected'))),'first_answer_correct':[sum(g(R0['C2'],'first')),O['first_answer_correct']]}
print('model',G,'first answer correct',O['first_answer_correct'],'alignment',al,'samples per question',O['samples_per_question'],'USC parse failures',O['usc_parse_failures'])
for n,s in O['conditions'].items(): print(f"  {n:26s}",{k:s[k] for k in s if k in ('reached','selected','conversion','last','correct','tokens_M','repeat_correct','repeat_incorrect')})
for fam in ('family_1','family_2'):
    for k,x in O[fam].items(): print(f"  {k:58s} {x['diff']:+6.1f} [{x['lo']:+.1f},{x['hi']:+.1f}] p={x['p']:.4f} Holm={x['p_holm']:.4f} confirmed={x['confirmed']}")
for k in ('G-R1 reached: critique - token-yoked','G-R reached: critique - equal-token samples'): x=O[k]; print(f"  {k}: {x['diff']:+.0f}, 90% [{x['lo90']:+.0f},{x['hi90']:+.0f}] vs +-33 -> {x['verdict']}")
for k,x in O['descriptive'].items(): print('   ',k,{q:x[q] for q in x if q in ('diff','lo','hi','p','total','reach_term','conversion_term')})
for k in O:
    if k.startswith('gradient'): print(k,{a:({q:b[q] for q in ('diff','lo','hi','p')} if isinstance(b,dict) else b) for a,b in O[k].items()})
print('selftest:',ST)
if not ST: json.dump(O,open(T+'capability_gradient_readout.json','w'),indent=1)
