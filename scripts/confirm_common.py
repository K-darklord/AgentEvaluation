#!/usr/bin/env python3
"""Shared code for the read-outs on the 800 new questions (streams trajectory files; definitions as in the paper).
A question is reached if any candidate answer is correct, selected if the most frequent candidate is correct (expected
score under random ties); a candidate's correctness is the verdict of its last occurrence (reco.last_key_correct)."""
import json,importlib.util,random,os
from collections import Counter
from math import comb
_here=os.path.dirname(os.path.abspath(__file__)); os.chdir(os.path.dirname(_here))
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T='experiments/hle400/t3/'
def J(f): return json.load(open(T+f))
def toks(r): return (r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0)
def ctoks(r): return (r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0)
def order(ts): return sorted(ts,key=lambda t:int(t.split('_')[1]))
def arm(path,side,critic=False,samples=False,budget=None,within=False):
    """per-question results for one condition. samples=True: independent samples (rounds 1-9, the T=0 first answer left out).
    budget: read each question up to and including the first round at which cumulative tokens reach its budget
    (within=True: only rounds whose cumulative tokens stay within the budget; round 0 always kept)."""
    out={}
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[t]; rounds=d['rounds']; assert len(keys)==len(sl)==len(rounds),(path,t)
        cost=[toks(r)+(ctoks(r) if critic else 0) for r in rounds]; n=len(keys)
        if budget is not None:
            cum=0
            for j,c in enumerate(cost):
                cum+=c
                if within:
                    if j==0 or cum<=budget[t]: n=j+1
                    else: break
                elif cum>=budget[t]: n=j+1; break
        lo=1 if samples else 0; hi=10 if samples else n; ks=keys[lo:hi]
        def ok(k,exact=False):
            i=max(j for j,x in enumerate(keys) if x==k); return bool(sl[i]['c']) and (not exact or sl[i].get('s')=='t1')
        cnt=Counter(k for k in ks if k is not None); res=dict(reached=0,selected=0.0,reached_x=0,selected_x=0.0,cand=len(cnt))
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
            res.update(reached=int(any(ok(k) for k in cnt)),selected=sum(ok(k) for k in tied)/len(tied),reached_x=int(any(ok(k,True) for k in cnt)),selected_x=sum(ok(k,True) for k in tied)/len(tied))
        rep=[0,0,0,0]; ch=[0,0]
        for i in range(len(ks)-1):
            if ks[i] is None: continue
            c=bool(sl[lo+i]['c']); rep[0 if c else 2]+=1; rep[1 if c else 3]+= ks[i+1]==ks[i]
            if ks[i+1] is not None: ch[1]+=1; ch[0]+= ks[i+1]!=ks[i]
        res.update(last=int(bool(sl[min(hi,len(sl))-1]['c'])),first=int(bool(sl[0]['c'])),rounds=min(hi,len(sl))-lo,tokens=sum(cost[lo:hi]),all_tokens=sum(cost),short=int(budget is not None and sum(cost[:n])<budget[t]),cap=int(bool(d.get('yoke_hit_cap'))),rep=rep,ch=ch,
                   up=int(len(sl)>1 and (not sl[0]['c']) and bool(sl[1]['c'])),down=int(len(sl)>1 and bool(sl[0]['c']) and not sl[1]['c']))
        out[t]=res; del d
    return out
def vec(A,key,tasks): return [A[t][key] for t in tasks]
def mcn(x,y):
    b=sum(bool(p) and not q for p,q in zip(x,y)); c=sum(bool(q) and not p for p,q in zip(x,y)); n=b+c
    return {'only_first':b,'only_second':c,'p':round(1.0 if n==0 else min(1.0,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n),5)}
def perm(x,y):
    d=[float(a)-float(b) for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]
    ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(10000)); bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return {'diff':round(obs,1),'lo':round(bs[50],1),'hi':round(bs[1949],1),'lo90':round(bs[100],1),'hi90':round(bs[1899],1),'p':round((ge+1)/10001,5)}
def holm(tests):
    """tests: dict name -> perm result; adds p_holm and confirmed (positive difference and p_holm < .05)"""
    run=0.0; ks=sorted(tests,key=lambda k:tests[k]['p'])
    for i,k in enumerate(ks): run=max(run,min(1.0,(len(ks)-i)*tests[k]['p'])); tests[k]['p_holm']=round(run,5); tests[k]['confirmed']=bool(tests[k]['diff']>0 and run<.05)
def summary(A,tasks):
    R=vec(A,'reached',tasks); S=vec(A,'selected',tasks); rp=[sum(A[t]['rep'][i] for t in tasks) for i in range(4)]; ch=[sum(A[t]['ch'][i] for t in tasks) for i in range(2)]
    sc=rp[1]/max(1,rp[0]); sw=rp[3]/max(1,rp[2])
    return {'reached':sum(R),'selected':round(sum(S),1),'conversion':round(sum(S)/max(1,sum(R)),3),'last':sum(vec(A,'last',tasks)),'reached_exact':sum(vec(A,'reached_x',tasks)),'selected_exact':round(sum(vec(A,'selected_x',tasks)),1),
            'rounds_per_q':round(sum(vec(A,'rounds',tasks))/len(tasks),2),'candidates_per_q':round(sum(vec(A,'cand',tasks))/len(tasks),2),'answer_change_rate':round(ch[0]/max(1,ch[1]),3),'tokens_M':round(sum(vec(A,'tokens',tasks))/1e6,1),
            'repeat_correct':round(sc,3),'repeat_incorrect':round(sw,3),'repeat_ratio':round(sc/sw,2) if sw else None,'first_revision_repaired':sum(vec(A,'up',tasks)),'first_revision_damaged':sum(vec(A,'down',tasks))}
def strata(file_list,key):
    rows=[json.loads(l) for f in file_list for l in open('data/raw/hle/'+f)]; d={}
    for i,r in enumerate(rows): d.setdefault(r[key],[]).append(i)
    return d
