"""Read-out of docs/BBEH_EQUAL_TOKEN_TEMPERATURE_SPEC.md section 5 (qwen3.8-flash, BBEH-hard, 800 questions).
Conditions: C2 critique loop (existing, T=0); A3Y independent samples continued to the critique budget (T=0.7);
GT7 token-yoked generic-doubt loop at T=0.7; A2PY token-yoked generic-doubt loop at T=0 (existing); A3 nine samples.
Candidates: loops use rounds 0..last; samples use samples 1..last (round 0 = the shared T=0 first answer is excluded).
A candidate is correct by the verdict of its last occurrence; selected = plurality, expected value under ties.
 Alignment (precondition for every test that uses the condition): solver tokens of A3Y and of GT7 within 95-120% of
   the budget total; at most 40 questions at the 100-round / 100-sample cap.
 Tests (Holm over B-SC, B-EC, T-1; alpha .05; sign-flip permutation 10,000, two-sided, direction must be positive):
   B-SC  selected(C2) - selected(A3Y) > 0
   B-EC  on questions reached by both C2 and A3Y: selected(C2) - selected(A3Y) > 0
   T-1   selected(GT7) - selected(A3Y) > 0   (same temperature, same tokens: loop vs independent samples)
   B-ER  reached(C2) - reached(A3Y): equivalent if the 90% bootstrap interval lies within +-33 (not in Holm)
 Descriptive: reach/conversion decomposition of each comparison; GT7 - A2PY (temperature within the loop); GT7 - C2;
   A3Y - A3; repeat rates after correct / incorrect answers; per-sample accuracy.
Usage: python3 scripts/bbeh_equal_token_readout.py [--selftest]   (selftest: A3 stands in for A3Y, A2PY for GT7,
verdicts are coin flips; tests the code, writes nothing). Writes experiments/hle400/t3/bbeh_equal_token_readout.json"""
import json,sys,random
from collections import Counter
from confirm_common import T,toks,ctoks,mcn,perm,holm
ST='--selftest' in sys.argv; Q='qwen3.8-flash-payg'; rnd=random.Random(0)
bs=json.load(open(T+'bbeh_sidecar.json'))['arms']; bn=bs if ST else json.load(open(T+'bbeh_sidecar_et.json'))['arms']
B=json.load(open(T+'yoke_budget_bbeh_hard.json'))['budget']
alias={'A3Y':'A3','GT7':'A2PY'}
def run(a,samples):
    src=alias[a] if (ST and a in alias) else a; side=(bn if a in alias else bs)[src]; out={}
    for l in open(f'experiments/b1_{src}_hard_{Q}/{Q}/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); t=d['task_id']; R=d['rounds']; sl=side[t]; assert len(sl)==len(R),(a,t)
        keys=[None if x['k'] is None else json.dumps(x['k'],sort_keys=True,ensure_ascii=False) for x in sl]
        ver=[(rnd.random()<.3) if ST else bool(x['c']) for x in sl]
        lo=1 if samples else 0; ks=keys[lo:]
        def ok(k): return bool(ver[max(j for j,x in enumerate(keys) if x==k)])
        cnt=Counter(k for k in ks if k is not None); res=dict(reached=0,selected=0.0,cand=len(cnt))
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
            res.update(reached=int(any(ok(k) for k in cnt)),selected=sum(ok(k) for k in tied)/len(tied))
        rep=[0,0,0,0]
        for i in range(len(ks)-1):
            if ks[i] is None: continue
            c=ver[lo+i]; rep[0 if c else 2]+=1; rep[1 if c else 3]+=ks[i+1]==ks[i]
        sol=sum(toks(r) for r in (R[1:] if samples else R))
        res.update(n=len(ks),acc=sum(ver[lo:]),solver=sol,tokens=sum(toks(r)+ctoks(r) for r in R[lo:]),rep=rep,
                   cap=int(len(R)-1>=100 or bool(d.get('yoke_hit_cap'))))
        out[t]=res
    return out
R={a:run(a,a in ('A3','A3Y')) for a in ('C2','A2PY','A3','A3Y','GT7')}
ts=sorted(R['C2']); assert len(ts)==800 and all(sorted(R[a])==ts for a in R)
V=lambda a,k,q=ts:[R[a][t][k] for t in q]; S=lambda a,k,q=ts:sum(V(a,k,q))
OUT={'selftest':ST}
def summ(a):
    rp=[sum(R[a][t]['rep'][i] for t in ts) for i in range(4)]
    return {'reached':S(a,'reached'),'selected':round(S(a,'selected'),1),'conversion':round(S(a,'selected')/max(1,S(a,'reached')),3),
            'candidates_per_q':round(S(a,'cand')/800,2),'answers_per_q':round(S(a,'n')/800,2),'accuracy_per_answer':round(S(a,'acc')/max(1,S(a,'n')),3),
            'tokens_M':round(S(a,'tokens')/1e6,1),'repeat_after_correct':round(rp[1]/max(1,rp[0]),3),'repeat_after_incorrect':round(rp[3]/max(1,rp[2]),3)}
OUT['conditions']={a:summ(a) for a in R}
bt=sum(B[t] for t in ts)
OUT['alignment']={a:{'ratio':round(S(a,'solver')/bt,3),'at_cap':S(a,'cap'),'aligned':bool(.95<=S(a,'solver')/bt<=1.20 and S(a,'cap')<=40)} for a in ('A3Y','GT7')}
def dec(x,y):
    r1,s1,r0,s0=S(x,'reached'),S(x,'selected'),S(y,'reached'),S(y,'selected'); c1,c0=s1/max(1,r1),s0/max(1,r0)
    return {'total':round(s1-s0,1),'reach_term':round((r1-r0)*(c1+c0)/2,1),'conversion_term':round((c1-c0)*(r1+r0)/2,1)}
both=[t for t in ts if R['C2'][t]['reached'] and R['A3Y'][t]['reached']]
tests={'B-SC selected: critique - equal-token samples':perm(V('C2','selected'),V('A3Y','selected')),
       'B-EC selected on questions reached by both: critique - equal-token samples':perm(V('C2','selected',both),V('A3Y','selected',both)),
       'T-1 selected: generic-doubt loop at T=0.7 - equal-token samples':perm(V('GT7','selected'),V('A3Y','selected'))}
need={'B-SC':['A3Y'],'B-EC':['A3Y'],'T-1':['A3Y','GT7']}
holm(tests)
for k,v in tests.items():
    v['holm_p']=v['p_holm']; why=[a+' tokens not aligned' for a in need[k.split()[0]] if not OUT['alignment'][a]['aligned']]
    v['judged']=not why; v['not_judged_because']=why; v['confirmed']=bool(not why and v['diff']>0 and v['p_holm']<.05)
OUT['n_reached_by_both']=len(both); OUT['tests']=tests
er=perm(V('C2','reached'),V('A3Y','reached')); er['equivalent_within_33']=bool(OUT['alignment']['A3Y']['aligned'] and -33<er['lo90'] and er['hi90']<33)
OUT['B-ER reached: critique - equal-token samples']=er; OUT['B-ER mcnemar']=mcn(V('C2','reached'),V('A3Y','reached'))
OUT['decomposition']={k:dec(x,y) for k,(x,y) in {'critique - equal-token samples':('C2','A3Y'),'GT7 - equal-token samples':('GT7','A3Y'),
    'critique - nine samples':('C2','A3'),'A2PY - equal-token samples':('A2PY','A3Y'),'GT7 - A2PY':('GT7','A2PY'),'critique - GT7':('C2','GT7')}.items()}
OUT['descriptive']={'GT7 - A2PY (temperature within the loop)':perm(V('GT7','selected'),V('A2PY','selected')),
    'critique - GT7':perm(V('C2','selected'),V('GT7','selected')),'A3Y - nine samples':perm(V('A3Y','selected'),V('A3','selected')),
    'A2PY - equal-token samples':perm(V('A2PY','selected'),V('A3Y','selected')),'reached GT7 vs A3Y':mcn(V('GT7','reached'),V('A3Y','reached'))}
for a,s in OUT['conditions'].items(): print(f"{a:5s}",s)
print('alignment:',OUT['alignment']); print('reached by both C2 and A3Y:',len(both))
for k,v in tests.items(): print(f"{k}: {v['diff']:+.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f} Holm={v['holm_p']:.4f} judged={v['judged']} {v['not_judged_because']} confirmed={v['confirmed']}")
print(f"B-ER: {er['diff']:+.1f} 90% [{er['lo90']:+.1f},{er['hi90']:+.1f}] equivalent within 33: {er['equivalent_within_33']}")
for k,v in OUT['decomposition'].items(): print('  decomposition',k,v)
for k,v in OUT['descriptive'].items(): print('  ',k,v)
if not ST: json.dump(OUT,open(T+'bbeh_equal_token_readout.json','w'),indent=1)
