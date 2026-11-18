#!/usr/bin/env python3
"""Read-out of stage 1 of the memory manipulation (docs/MEMORY_MANIPULATION_SPEC_v3_1.md, section 5), qwen3.8-flash,
BBEH-hard, generic-doubt loops at the critique loop's token budget (no critic call; feedback carries nothing about the answer).
 Conditions: A2PY (existing) = previous answer shown, permission to keep it; GKI = previous answer shown, the sentence
 permitting to keep it removed, 400 questions (000-039 of each task); GNM = previous answer not shown, 800 questions.
 5.1 manipulation check: share of questions whose round-1 answer equals the first answer, GNM against A2PY (exact
     McNemar p < .05 and an absolute difference of at least 5 percentage points, in either direction; the direction
     is reported), else NM-2 is 'not judged: manipulation not effective'. Questions whose first or round-1 answer has
     no key (empty or cut-off output) are excluded from this check.
 5.2 NM-2 (the only confirmatory test): selected(A2PY) - selected(GNM) > 0, 800 questions; sign-flip permutation,
     two-sided; total tokens of GNM within 95-120% of the budget and at most 40 questions at the cap.
 5.3 visibility (GKI - GNM) and permission (A2PY - GKI) on the 400 questions (index below 40 in every task, the same
     rule for every condition); descriptive rows.
 5.4 'concentration' wording allowed only if NM-2 is confirmed, GNM repeats the first answer less than A2PY at round 1,
     and GNM does not reach significantly fewer correct answers than A2PY (exact McNemar).
Reads frozen files only. Usage: python3 scripts/memory_manipulation_readout.py [--selftest]
(--selftest: the with-memory run stands in for the new conditions and every verdict is a coin flip; tests the code, writes
nothing). Writes experiments/hle400/t3/memory_manipulation_readout.json"""
import json,sys,re,random
from collections import Counter
from confirm_common import T,J,reco,toks,ctoks,mcn,perm,holm
ST='--selftest' in sys.argv; Q='qwen3.8-flash-payg'
def norm(s): return re.sub(r'\s+','',str(s).lower())
def leak_hit(prev,cd):
    """previous answer present in the critique text (rule of spec 3.2); None if the answer cannot be checked"""
    p=norm(prev); c=norm(json.dumps(cd,ensure_ascii=False))
    if not p or len(p)>60 or re.fullmatch(r'\(?[a-z]\)?',p): return None
    if re.fullmatch(r'[-+]?\d+(\.\d+)?',p): return re.search(r'(?<![\d.])'+re.escape(p)+r'(?![\d.])',c) is not None
    return (p in c) if len(p)>=3 else None
def run(path,keyfun,samples=False,budget=None):
    """per-question results; keyfun(d) -> (keys, verdicts) per round"""
    out={}
    for l in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); t=d['task_id']; keys,ver=keyfun(d); R=d['rounds']; lo,hi=(1,10) if samples else (0,len(keys)); ks=keys[lo:hi]
        def ok(k): return bool(ver[max(j for j,x in enumerate(keys) if x==k)])
        cnt=Counter(k for k in ks if k is not None); res=dict(reached=0,selected=0.0,cand=len(cnt))
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; res.update(reached=int(any(ok(k) for k in cnt)),selected=sum(ok(k) for k in tied)/len(tied))
        rep=[0,0,0,0]
        for i in range(len(ks)-1):
            if ks[i] is None: continue
            c=bool(ver[lo+i]); rep[0 if c else 2]+=1; rep[1 if c else 3]+= ks[i+1]==ks[i]
        lk=[leak_hit(R[i-1].get('final_answer'),R[i].get('critic_direction')) for i in range(1,len(R)) if isinstance(R[i].get('critic_direction'),list) and not R[i].get('critic_fallback')]
        cds=[json.dumps(R[i]['critic_direction'],ensure_ascii=False).lower() for i in range(1,len(R)) if isinstance(R[i].get('critic_direction'),list) and not R[i].get('critic_fallback')]
        ref=[len(cds),sum(bool(re.search(r'your answer|you said|your previous|your computation',x)) for x in cds),sum(bool(re.search(r'the (final |chosen |selected |computed |stated )?(answer|response|solution|reasoning|computation|calculation|value|option)|assumed|treated|chosen|selected|asserted|applied|computed|counted',x)) for x in cds)]
        fa=norm(R[0].get('final_answer'))
        res.update(r1_same=(None if (samples or len(keys)<2 or keys[0] is None or keys[1] is None) else int(keys[1]==keys[0])),rounds=hi-lo,tokens=sum(toks(r)+ctoks(r) for r in R[lo:hi]),solver=sum(toks(r) for r in R),
                   cap=int(bool(d.get('yoke_hit_cap'))),short=int(budget is not None and sum(toks(r) for r in R)<budget[t]),rep=rep,ref=ref,leak=[sum(1 for x in lk if x),sum(1 for x in lk if x is not None)],
                   short_first=bool(re.fullmatch(r'\(?[a-z]\)?',fa) or re.fullmatch(r'[-+]?\d{1,3}',fa)))
        out[t]=res
    return out
def summ(A,ts):
    S=lambda k:sum(A[t][k] for t in ts); rp=[sum(A[t]['rep'][i] for t in ts) for i in range(4)]; r1=[A[t]['r1_same'] for t in ts if A[t]['r1_same'] is not None]
    return {'n':len(ts),'reached':S('reached'),'selected':round(S('selected'),1),'conversion':round(S('selected')/max(1,S('reached')),3),'candidates_per_q':round(S('cand')/len(ts),2),'rounds_per_q':round(S('rounds')/len(ts),2),'tokens_M':round(S('tokens')/1e6,1),
            'repeat_correct':round(rp[1]/max(1,rp[0]),3),'repeat_incorrect':round(rp[3]/max(1,rp[2]),3),'round1_same_as_first':round(sum(r1)/max(1,len(r1)),3) if r1 else None}
def manip(NM,WM,ts):
    ps=[(NM[t]['r1_same'],WM[t]['r1_same']) for t in ts if NM[t]['r1_same'] is not None and WM[t]['r1_same'] is not None]; m=mcn([a for a,b in ps],[b for a,b in ps]); a=sum(x for x,_ in ps)/len(ps); b=sum(y for _,y in ps)/len(ps)
    return {'n':len(ps),'without_memory':round(a,3),'with_memory':round(b,3),'difference':round(b-a,3),'mcnemar':m,'direction':('less repetition without memory' if a<b else 'more repetition without memory'),'passed':bool(m['p']<.05 and abs(b-a)>=0.05)}
def leak_share(A,ts):
    h=sum(A[t]['leak'][0] for t in ts); n=sum(A[t]['leak'][1] for t in ts); r=[sum(A[t]['ref'][i] for t in ts) for i in range(3)]
    return {'checked':n,'contain_previous_answer':h,'share':round(h/max(1,n),3),'above_0.30':bool(n and h/n>.30),'critiques':r[0],'share_with_your_answer_phrases':round(r[1]/max(1,r[0]),3),'share_referring_to_what_the_attempt_did':round(r[2]/max(1,r[0]),3)}
OUT={'selftest':ST}; rnd=random.Random(0)
bs=json.load(open(T+'bbeh_sidecar.json'))['arms']; bn=bs if ST else json.load(open(T+'bbeh_sidecar_nm.json'))['arms']
def bkey(side):
    def f(d):
        sl=side[d['task_id']]; assert len(sl)==len(d['rounds']),d['task_id']
        return [None if x['k'] is None else json.dumps(x['k'],sort_keys=True,ensure_ascii=False) for x in sl],[(rnd.random()<.3) if ST else bool(x['c']) for x in sl]
    return f
B=json.load(open(T+'yoke_budget_bbeh_hard.json'))['budget']; bp=lambda a:f'experiments/b1_{a}_hard_{Q}/{Q}'; alias={'GNM':'A2PY','GKI':'A2PY'}
R={'A2PY':run(bp('A2PY'),bkey(bs['A2PY']),budget=B),'A3':run(bp('A3'),bkey(bs['A3']),samples=True)}
for a in ('GNM','GKI'): R[a]=run(bp(alias[a] if ST else a),bkey(bn[alias[a] if ST else a]),budget=B)
ts=sorted(R['A2PY']); assert len(ts)==800 and sorted(R['GNM'])==ts
sub=[t for t in ts if int(t.rsplit('_',1)[1])<40]; assert len(sub)==400 and all(t in R['GKI'] for t in sub)
if not ST: assert sorted(R['GKI'])==sub
V=lambda a,k,q=ts:[R[a][t][k] for t in q]; QS={'A2PY':ts,'A3':ts,'GNM':ts,'GKI':sub}
OUT['conditions']={a:summ(R[a],QS[a]) for a in R}; OUT['conditions_on_the_400']={a:summ(R[a],sub) for a in R}
gt=sum(V('GNM','solver')); bt=sum(B[t] for t in ts); cap=sum(V('GNM','cap')); OUT['GNM_token_alignment']={'ratio':round(gt/bt,3),'at_cap':cap,'aligned':bool(0.95<=gt/bt<=1.20 and cap<=40)}
OUT['manipulation_check']={'GNM vs A2PY (800)':manip(R['GNM'],R['A2PY'],ts),'GKI vs A2PY (400; descriptive)':manip(R['GKI'],R['A2PY'],sub)}
nm2=perm(V('A2PY','selected'),V('GNM','selected')); why=[x for x,c in (('manipulation not effective',not OUT['manipulation_check']['GNM vs A2PY (800)']['passed']),('tokens not aligned',not OUT['GNM_token_alignment']['aligned'])) if c]
nm2['judged']=not why; nm2['not_judged_because']=why; nm2['confirmed']=bool(not why and nm2['diff']>0 and nm2['p']<.05); OUT['stage_2_to_be_run']=nm2['confirmed']; OUT['NM-2 selected: token-yoked generic doubt - the same without memory (800; confirmatory)']=nm2
rm=mcn(V('A2PY','reached'),V('GNM','reached')); OUT['reached: token-yoked vs the same without memory (800)']=rm
reach_lower=bool(sum(V('GNM','reached'))<sum(V('A2PY','reached')) and rm['p']<.05)
OUT['concentration_wording_allowed']=bool(nm2['confirmed'] and OUT['manipulation_check']['GNM vs A2PY (800)']['direction']=='less repetition without memory' and not reach_lower)
P=lambda a,b:perm(V(a,'selected',sub),V(b,'selected',sub))
OUT['visibility_and_permission_400']={'permission (A2PY - GKI)':P('A2PY','GKI'),'visibility (GKI - GNM)':P('GKI','GNM'),'both (A2PY - GNM)':P('A2PY','GNM')}
OUT['visibility_claim_allowed']=bool(OUT['visibility_and_permission_400']['visibility (GKI - GNM)']['lo']>0)
OUT['minus_nine_samples']={a:perm(V(a,'selected',QS[a]),V('A3','selected',QS[a])) for a in ('GNM','A2PY','GKI')}
for lab,C in (('each condition on its own questions',OUT['conditions']),('all conditions on the 400 questions',OUT['conditions_on_the_400'])):
    print(lab)
    for a,s in C.items(): print(f"  {a:5s} n={s['n']} selected {s['selected']:6.1f} reached {s['reached']:4d} conv {s['conversion']:.2f} cand {s['candidates_per_q']:.2f} rounds {s['rounds_per_q']:5.2f} tokens {s['tokens_M']:6.1f}M repeat {s['repeat_correct']:.2f}/{s['repeat_incorrect']:.2f} round-1 same as first {s['round1_same_as_first']}")
print('GNM token alignment:',OUT['GNM_token_alignment']); print('manipulation check:',OUT['manipulation_check'])
print(f"NM-2 (confirmatory): {nm2['diff']:+.1f} [{nm2['lo']:+.1f},{nm2['hi']:+.1f}] p={nm2['p']:.4f} judged: {nm2['judged']} {why} confirmed: {nm2['confirmed']}")
print('reached, token-yoked vs without memory:',OUT['reached: token-yoked vs the same without memory (800)'])
for k,v in OUT['visibility_and_permission_400'].items(): print(f"  {k:26s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}")
print('visibility claim allowed (lower limit above 0):',OUT['visibility_claim_allowed']); print('concentration wording allowed:',OUT['concentration_wording_allowed'])
for a,v in OUT['minus_nine_samples'].items(): print(f"  {a:5s} minus nine samples {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}]")
print('stage 2 (question-only critique line on HLE) to be run:',OUT['stage_2_to_be_run'])
if not ST: json.dump(OUT,open(T+'memory_manipulation_readout.json','w'),indent=1)
