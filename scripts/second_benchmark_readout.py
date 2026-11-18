#!/usr/bin/env python3
"""Read-out of the second benchmark, BBEH, qwen3.8-flash (docs/SECOND_BENCHMARK_SPEC.md section 3) and of the predictions
registered before the read-out (docs/REACH_SELECTION_DATA.md section 8, P1-P5; docs/CONTROLS_RESULTS.md, hypotheses of 18:50).
 BBEH-hard (800): token alignment; B-S1 selected(critique) - selected(token-yoked), B-S2 critique - reassuring,
   B-A3 critique - nine samples (sign-flip permutation, two-sided, Holm over the three); reach: 90% interval of
   reached(critique) - reached(token-yoked) against +-33; descriptive rows; by task.
 BBEH-easy (240): descriptive only.
 P1-P5: confidence = number of the nine samples that give the same answer as the T=0 first answer (strata 0-3, 4-6, 7-9).
Scoring is rule-based (the benchmark's evaluate.py); a candidate is identified by the key in the score file and takes the
verdict of its last occurrence. Reads frozen files only.
Usage: python3 scripts/second_benchmark_readout.py [--dry]   (--dry replaces every verdict by a coin flip, to test the code
without seeing results; writes nothing). Writes experiments/hle400/t3/second_benchmark_readout.json"""
import json,sys,random
from collections import Counter
from confirm_common import T,toks,ctoks,mcn,perm,holm
DRY='--dry' in sys.argv; Q='qwen3.8-flash-payg'
SIDE=json.load(open(T+'bbeh_sidecar.json'))['arms']
if DRY:
    r=random.Random(0)
    for a in SIDE:
        for t in SIDE[a]:
            for x in SIDE[a][t]: x['c']=r.random()<0.3
NAMES={'A':'first answer','A2':'reassuring','A2P':'generic doubt','A2PY':'token-yoked generic doubt','C2':'critique','A3':'nine samples'}
HLE_EFFECT={('0-3',True):-0.064,('0-3',False):0.062,('4-6',True):-0.074,('4-6',False):0.090,('7-9',True):-0.040,('7-9',False):0.059}
def hk(k): return None if k is None else json.dumps(k,sort_keys=True,ensure_ascii=False)
def arm(split,a):
    out={}
    for l in open(f'experiments/b1_{a}_{split}_{Q}/{Q}/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); t=d['task_id']; sl=SIDE[a][t]; R=d['rounds']; assert len(sl)==len(R),(a,t); keys=[hk(x['k']) for x in sl]
        lo,hi=(1,10) if a=='A3' else (0,len(keys)); ks=keys[lo:hi]
        def ok(k): return bool(sl[max(j for j,x in enumerate(keys) if x==k)]['c'])
        cnt=Counter(k for k in ks if k is not None); res=dict(reached=0,selected=0.0,cand=len(cnt),kept_first=0.0)
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; res.update(reached=int(any(ok(k) for k in cnt)),selected=sum(ok(k) for k in tied)/len(tied),kept_first=(1/len(tied) if keys[0] in tied else 0.0))
        rep=[0,0,0,0]; ch=[0,0]
        for i in range(len(ks)-1):
            if ks[i] is None: continue
            c=bool(sl[lo+i]['c']); rep[0 if c else 2]+=1; rep[1 if c else 3]+= ks[i+1]==ks[i]
            if ks[i+1] is not None: ch[1]+=1; ch[0]+= ks[i+1]!=ks[i]
        first_ok=None if (keys[0] is None or R[0].get('finish_reason')=='length') else ok(keys[0])
        res.update(last=int(bool(sl[hi-1]['c'])),first=int(bool(sl[0]['c'])),first_ok=first_ok,rounds=hi-lo,tokens=sum(toks(r)+ctoks(r) for r in R[lo:hi]),cap=int(bool(d.get('yoke_hit_cap'))),rep=rep,ch=ch,
                   up=int(len(sl)>1 and not sl[0]['c'] and bool(sl[1]['c'])),down=int(len(sl)>1 and bool(sl[0]['c']) and not sl[1]['c']),
                   agree=(None if keys[0] is None else sum(x==keys[0] for x in keys[1:10])) if a=='A3' else None,task=t.rsplit('_',1)[0])
        out[t]=res
    return out
def summ(A,ts):
    S=lambda k:sum(A[t][k] for t in ts); rp=[sum(A[t]['rep'][i] for t in ts) for i in range(4)]; ch=[sum(A[t]['ch'][i] for t in ts) for i in range(2)]
    return {'reached':S('reached'),'selected':round(S('selected'),1),'last':S('last'),'conversion':round(S('selected')/max(1,S('reached')),3),'rounds_per_q':round(S('rounds')/len(ts),2),'candidates_per_q':round(S('cand')/len(ts),2),'answer_change_rate':round(ch[0]/max(1,ch[1]),3),'tokens_M':round(S('tokens')/1e6,1),
            'repeat_correct':round(rp[1]/max(1,rp[0]),3),'repeat_incorrect':round(rp[3]/max(1,rp[2]),3),'first_revision_repaired':S('up'),'first_revision_damaged':S('down')}
OUT={'dry_run':DRY}
for split,N in (('hard',800),('easy',240)):
    R={a:arm(split,a) for a in NAMES}; ts=sorted(R['C2']); assert len(ts)==N and all(sorted(R[a])==ts for a in R)
    V=lambda a,k:[R[a][t][k] for t in ts]; O={'n':N,'first_answer_correct':sum(V('A','first'))}
    yt=sum(V('A2PY','tokens')); ct=sum(V('C2','tokens')); cap=sum(V('A2PY','cap')); aligned=(0.95<=yt/ct<=1.20) and cap<=40
    O['token_alignment']={'critique_M':round(ct/1e6,2),'token_yoked_M':round(yt/1e6,2),'ratio':round(yt/ct,3),'at_cap':cap,'aligned':aligned}
    O['conditions']={NAMES[a]:summ(R[a],ts) for a in NAMES}
    print(f"\n===== BBEH-{split} ({N} questions; first answer correct {O['first_answer_correct']}) =====\ntoken alignment: {O['token_alignment']}")
    for n,s in O['conditions'].items(): print(f"  {n:28s} last {s['last']:4d} selected {s['selected']:6.1f} reached {s['reached']:4d} conv {s['conversion']:.2f} | rounds {s['rounds_per_q']:5.2f} cand {s['candidates_per_q']:.2f} change {s['answer_change_rate']:.2f} tokens {s['tokens_M']:6.1f}M | repeat {s['repeat_correct']:.2f}/{s['repeat_incorrect']:.2f} | first revision {s['first_revision_repaired']}/{s['first_revision_damaged']}")
    S=lambda a:V(a,'selected'); Rc=lambda a:V(a,'reached')
    tests={'S1 selected: critique - token-yoked generic doubt':perm(S('C2'),S('A2PY')),'S2 selected: critique - reassuring':perm(S('C2'),S('A2')),'A3 selected: critique - nine samples':perm(S('C2'),S('A3'))}
    if split=='hard':
        holm(tests)
        if not aligned: tests['S1 selected: critique - token-yoked generic doubt']['confirmed']=None
    O['selected_tests']=tests; print(' selected'+(' (confirmatory, Holm over three)' if split=='hard' else ' (descriptive)'))
    for k,v in tests.items(): print(f"   {k:52s} {v['diff']:+6.1f} [{v['lo']:+.1f},{v['hi']:+.1f}] p={v['p']:.4f}"+(f" Holm p={v['p_holm']:.4f} confirmed: {v['confirmed']}" if split=='hard' else ''))
    r1=perm(Rc('C2'),Rc('A2PY')); r1['mcnemar']=mcn(Rc('C2'),Rc('A2PY')); M=33 if split=='hard' else None
    if M: r1['verdict']=('not judged' if not aligned else 'equivalent' if (r1['lo90']>-M and r1['hi90']<M) else 'different' if (r1['lo90']>M or r1['hi90']<-M) else 'inconclusive'); r1['critique_reaches_no_more']=bool(r1['hi90']<M)
    O['reached_critique_minus_token_yoked']=r1; print(f" reached, critique - token-yoked: {r1['diff']:+.0f}, 90% interval [{r1['lo90']:+.0f},{r1['hi90']:+.0f}]"+(f" against +-{M} -> {r1['verdict']}; upper limit below +{M}: {r1['critique_reaches_no_more']}" if M else '')+f"; discordant {r1['mcnemar']['only_first']}/{r1['mcnemar']['only_second']} p={r1['mcnemar']['p']:.4f}")
    O['reached']={f'{NAMES[a]} vs {NAMES[b]}':mcn(Rc(a),Rc(b)) for a,b in (('C2','A2'),('C2','A2P'),('A2PY','A2P'),('C2','A3'),('A2P','A2'))}
    O['selected_other']={f'{NAMES[a]} - {NAMES[b]}':perm(S(a),S(b)) for a,b in (('C2','A2P'),('A2PY','A2P'),('A2PY','A2'),('A3','A2'),('C2','A'),('A2','A'))}
    print(' reached:',{k:(v['only_first'],v['only_second'],v['p']) for k,v in O['reached'].items()}); print(' selected, other:',{k:(v['diff'],v['lo'],v['hi']) for k,v in O['selected_other'].items()})
    bt={}
    for t in ts: bt.setdefault(R['C2'][t]['task'],[]).append(t)
    O['by_task']={k:{'n':len(v),'first_correct':sum(R['A'][t]['first'] for t in v),**{f'critique - {NAMES[b]}':round(sum(R['C2'][t]['selected']-R[b][t]['selected'] for t in v),1) for b in ('A2','A2PY','A3')}} for k,v in sorted(bt.items())}
    print(' by task (n, first correct, critique minus reassuring / token-yoked / samples):'); [print(f"   {k.replace('bbeh_b1_',''):24s} {v['n']:3d} {v['first_correct']:3d} {v['critique - reassuring']:+6.1f} {v['critique - token-yoked generic doubt']:+6.1f} {v['critique - nine samples']:+6.1f}") for k,v in O['by_task'].items()]
    # ---- registered predictions: confidence strata
    cell=Counter(); kept=Counter(); gain=Counter(); selA=Counter(); selC=Counter()
    for t in ts:
        ag=R['A3'][t]['agree']; fo=R['C2'][t]['first_ok']
        if ag is None or fo is None: continue
        st='0-3' if ag<=3 else ('4-6' if ag<=6 else '7-9'); c=(st,bool(fo)); cell[c]+=1; kept[c]+=R['C2'][t]['kept_first']; kept[c,'A2']+=R['A2'][t]['kept_first']; selA[c]+=R['A2'][t]['selected']; selC[c]+=R['C2'][t]['selected']; gain[c]+=R['C2'][t]['selected']-R['A2'][t]['selected']
    P={'cells':{f'{st} | first {"correct" if fc else "wrong"}':{'n':cell[st,fc],'critique_plurality_is_first_answer':round(kept[st,fc]/max(1,cell[st,fc]),3),'reassuring_plurality_is_first_answer':round(kept[(st,fc),'A2']/max(1,cell[st,fc]),3),'selected_reassuring':round(selA[st,fc],1),'selected_critique':round(selC[st,fc],1)} for st in ('0-3','4-6','7-9') for fc in (True,False)}}
    pooled={st:(kept[st,True]+kept[st,False])/max(1,cell[st,True]+cell[st,False]) for st in ('0-3','4-6','7-9')}; hi_c=kept['7-9',True]/max(1,cell['7-9',True]); hi_w=kept['7-9',False]/max(1,cell['7-9',False])
    P['P1']={'pooled_by_stratum':{k:round(v,3) for k,v in pooled.items()},'high_first_correct':round(hi_c,3),'high_first_wrong':round(hi_w,3),'monotone':bool(pooled['0-3']<pooled['4-6']<pooled['7-9']),'high_at_least_.85':bool(pooled['7-9']>=.85),'high_difference_at_most_.10':bool(abs(hi_c-hi_w)<=.10)}
    P['P1']['holds']=bool(P['P1']['monotone'] and P['P1']['high_at_least_.85'] and P['P1']['high_difference_at_most_.10'])
    tot=tests['S2 selected: critique - reassuring']['diff']; lw=gain['0-3',False]
    P['P2']={'gain_low_confidence_first_wrong':round(lw,1),'total_gain':tot,'share':round(lw/tot,3) if tot>0 else None,'holds':bool(tot>0 and lw/tot>=2/3)}
    P['P3']={'abs_difference':abs(tot),'holds':bool(abs(tot)<=12)} if split=='easy' else None
    P['P4_high_confidence_first_correct']={'correct':cell['7-9',True],'n':cell['7-9',True]+cell['7-9',False]}
    pred=sum(cell[c]*HLE_EFFECT[c] for c in HLE_EFFECT); s2=tests['S2 selected: critique - reassuring']
    P['P5']={'predicted_net':round(pred,1),'observed':s2['diff'],'observed_95':[s2['lo'],s2['hi']],'inside':bool(s2['lo']<=pred<=s2['hi'])}
    O['predictions']=P
    print(' confidence strata (n; critique: plurality still first answer; selected reassuring -> critique):'); [print(f"   {k:22s} n={v['n']:4d} kept {v['critique_plurality_is_first_answer']:.2f} (reassuring {v['reassuring_plurality_is_first_answer']:.2f}) selected {v['selected_reassuring']:6.1f} -> {v['selected_critique']:6.1f}") for k,v in P['cells'].items()]
    print(' P1',P['P1']); print(' P2',P['P2']); print(' P3',P['P3']); print(' P4',P['P4_high_confidence_first_correct']); print(' P5',P['P5'])
    OUT[split]=O
h=OUT['hard']['selected_tests']['S2 selected: critique - reassuring']; OUT['hypotheses_of_18_50']={'B-S2':h['diff'],'interval':[h['lo'],h['hi']],'half_of_HLE_estimate':18.4,'supports':('ability' if (h['lo']>0 and h['diff']>=18.4) else 'state' if (h['lo']<=0<=h['hi'] and h['diff']<18.4) else 'neither')}
print('\nhypotheses of 18:50:',OUT['hypotheses_of_18_50'])
a,b=OUT['easy']['predictions']['P4_high_confidence_first_correct'],OUT['hard']['predictions']['P4_high_confidence_first_correct']; print('P4: high-confidence first answers correct, easy %d/%d vs hard %d/%d'%(a['correct'],a['n'],b['correct'],b['n']))
if not DRY: json.dump(OUT,open(T+'second_benchmark_readout.json','w'),indent=1)
