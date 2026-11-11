#!/usr/bin/env python3
"""Unified evaluator audit for the three same-model judges (freeze-key identity, sidecar v2).

  Judge-R  : rubric_ce three-dimension scores -> CUT/KEEP/UNSURE   (experiments/hle400/t3/c3_rubric_ce.jsonl)
  Judge-R+ : Q-CUT (question-visible, cited, falsifier) -> CUT/NO_CUT (experiments/hle400/t3/qcut_result.jsonl)
  Judge-C  : critic over-feedback judge -> OVER/WARRANTED/UNSURE     (experiments/hle400/t3/judge_c_verdicts_dashscope.jsonl)

For each judge prints (markdown):
  (1) edge-level confusion on decisive edges (fix = W->R, break = R->W), dev/test/all, LR + 95% CI, E1
  (2) pre-registered +-logLR aggregation: dev-fit -> test (E3) and test-fit -> dev (E4), vs mode
  (3) conditional-on-counts test: judge vs counts-only vs accuracy when disagreeing
  (4) exhaustive aggregation grid (node/fragment/candidate x weights x gating), in-sample max and cross-half
Usage: python3 scripts/judge_conditional_test.py
"""
import json,sys,importlib.util,math
from pathlib import Path
from collections import Counter
from math import comb
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('reco',ROOT/'scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T3=ROOT/'experiments/hle400/t3'
side=json.load(open(T3/'is_correct_t3_sidecar_v2.json'))['arms']['C3']
loop=reco.load_jsonl(ROOT/'experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl')
ev=reco.load_jsonl(T3/'c3_rubric_ce.jsonl')
QV={}
for r in map(json.loads,open(T3/'qcut_result.jsonl')): QV.setdefault((r['task_id'],int(r['from_r']),int(r['to_r'])),[]).append(r['verdict'])
JC={(r['task_id'],r['from_r'],r['to_r']):r['final'] for r in map(json.loads,open(T3/'judge_c_verdicts_dashscope.jsonl'))}
PAIRWISE={}
for r in map(json.loads,open(T3/'qcut_pairwise_result.jsonl')): PAIRWISE[(r['task_id'],int(r['from_r']),int(r['to_r']))]=r['bucket']
dev=lambda t:int(t.split('_')[1])%2==0
# verdict getters: return raw verdict string or None (absent)
def gR(t,a,b):
    ps=(ev.get(t) or {}).get('per_switch',{}); k=f"{a}->{b}"
    return reco._score_to_verdict(ps[k],reco.CUT_BAR) if k in ps else 'UNSURE'
def gRp(t,a,b):
    vs=QV.get((t,a,b)); 
    if not vs: return None
    return 'CUT' if all(x=='CUT' for x in vs) else 'NO_CUT' if all(x=='NO_CUT' for x in vs) else 'UNSURE'
def gC(t,a,b): return JC.get((t,a,b))
def gP(t,a,b):
    v=PAIRWISE.get((t,a,b))
    return 'CUT' if v=='cut' else ('KEEP' if v=='keep' else None)
JUDGES={'Judge-R':(gR,{'CUT':'break','KEEP':'fix','UNSURE':None}),
        'Judge-R+':(gRp,{'CUT':'break','NO_CUT':'fix','UNSURE':None}),
        'Judge-C':(gC,{'OVER':'break','WARRANTED':'fix','UNSURE':None}),
        'Judge-P':(gP,{'CUT':'break','KEEP':'fix'})}
TASKS={}
for t,lp in loop.items():
    keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[t]
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: continue
    runs=[];rid=-1
    for i,k in enumerate(keys):
        if k is None: runs.append(None); continue
        if i==0 or keys[i-1]!=k: rid+=1
        runs.append(rid)
    m=sorted(cnt.values(),reverse=True); last={}
    for i,k in enumerate(keys):
        if k is not None: last[k]=i
    sw=[]
    for a,b in reco.freeze_switches(keys):
        oc,nc=bool(sl[a]['c']),bool(sl[b]['c'])
        sw.append((a,b,'fix' if (not oc and nc) else 'break' if (oc and not nc) else 'other'))
    TASKS[t]=dict(keys=keys,cnt=cnt,sw=sw,runs=runs,last=last,margin=(m[0]-m[1]) if len(m)>1 else 99,
                  mode=reco.freeze_mode_key(keys),corr={k:reco.last_key_correct(keys,sl,k) for k in cnt})
ALL=list(TASKS); D=[t for t in ALL if dev(t)]; T=[t for t in ALL if not dev(t)]
modeacc=lambda ts:sum(TASKS[t]['corr'][TASKS[t]['mode']] for t in ts)
def mcnemar(b,c):
    n=b+c; return None if n==0 else round(min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n),3)
def wilson(k,n,z=1.96):
    if n==0: return None
    p=k/n; z2=z*z; d=1+z2/n
    ctr=(p+z2/(2*n))/d; hw=z*math.sqrt(p*(1-p)/n+z2/(4*n*n))/d
    return ctr-hw, ctr+hw
def confusion(name,tasks):
    g,_=JUDGES[name]; C=Counter()
    for t in tasks:
        for a,b,typ in TASKS[t]['sw']:
            v=g(t,a,b)
            if v is None: continue
            C[(v,typ)]+=1
    return C
def lr_table(name,tasks):
    g,mp=JUDGES[name]; C=confusion(name,tasks); vs=[v for v in mp]; 
    Nf=sum(C[(v,'fix')] for v in vs); Nb=sum(C[(v,'break')] for v in vs); LR={}; rows=[]
    for v in vs:
        nf,nb=C[(v,'fix')],C[(v,'break')]; lr=((nf+1)/(Nf+3))/((nb+1)/(Nb+3)); se=math.sqrt(1/(nf+1)+1/(nb+1))
        LR[v]=lr; rows.append(f"| {v} | {nf} | {nb} | {C[(v,'other')]} | {lr:.2f} | [{math.exp(math.log(lr)-1.96*se):.2f}, {math.exp(math.log(lr)+1.96*se):.2f}] |")
    good=sum(C[(v,'break')] for v in vs if mp[v]=='break')+sum(C[(v,'fix')] for v in vs if mp[v]=='fix')
    tot=sum(C[(v,'fix')]+C[(v,'break')] for v in vs if mp[v])
    return LR,rows,(good,tot,Nf+Nb)
def apply_lr(name,tasks,LR):
    g,_=JUDGES[name]; tot=0; ch=Counter()
    for t in tasks:
        d=TASKS[t]; keys=d['keys']; s={k:math.log(c) for k,c in d['cnt'].items()}
        for a,b,_ in d['sw']:
            v=g(t,a,b)
            if v is None or v not in LR: continue
            l=math.log(LR[v]); s[keys[b]]+=l; s[keys[a]]-=l
        pick=max(s,key=lambda k:(round(s[k],9),d['last'][k]))
        ok=d['corr'][pick]; tot+=ok
        if ok!=d['corr'][d['mode']]: ch['+' if ok else '-']+=1
    return tot,ch['+'],ch['-']
def conditional(name):
    g,mp=JUDGES[name]; C=Counter()
    for t,d in TASKS.items():
        for a,b,typ in d['sw']:
            if typ=='other': continue
            v=g(t,a,b); j=mp.get(v) if v else None
            if j is None: continue
            cp='fix' if d['cnt'][d['keys'][b]]>=d['cnt'][d['keys'][a]] else 'break'
            C['n']+=1; C['j']+=(j==typ); C['c']+=(cp==typ); C['ag']+=(j==cp)
            if j!=cp: C['dn']+=1; C['dj']+=(j==typ)
    return C
grid=[0,0.5,1.0]
def run_cfg(name,tasks,scheme,wB,wF,gate):
    g,mp=JUDGES[name]; tot=0; ch=Counter()
    for t in tasks:
        d=TASKS[t]; keys=d['keys']
        if d['margin']>gate: pick=d['mode']
        else:
            w=[1.0 if k is not None else 0.0 for k in keys]
            for a,b,_ in d['sw']:
                v=g(t,a,b); j=mp.get(v) if v else None
                if j is None: continue
                tgt,wt=(b,wB) if j=='break' else (a,wF)
                idx=[tgt] if scheme=='node' else [i for i in range(len(keys)) if (d['runs'][i]==d['runs'][tgt] if scheme=='fragment' else keys[i]==keys[tgt])]
                for i in idx: w[i]*=(1-wt)
            s={}
            for i,k in enumerate(keys):
                if k is not None: s[k]=s.get(k,0)+w[i]
            pick=max(s,key=lambda k:(round(s[k],9),d['last'][k]))
        ok=d['corr'][pick]; tot+=ok
        if ok!=d['corr'][d['mode']]: ch['+' if ok else '-']+=1
    return tot,ch['+'],ch['-']
cfgs=[(s,wB,wF,g) for s in ('node','fragment','candidate') for wB in grid for wF in grid for g in (99,1,0)]
print(f"# Same-model judge audit (freeze-key, sidecar v2)\n\nmode: all {modeacc(ALL)} | dev {modeacc(D)} | test {modeacc(T)}\n")
for name in JUDGES:
    print(f"## {name}\n")
    for lbl,ts in (('dev (even)',D),('test (odd)',T),('all 400',ALL)):
        LR,rows,(good,tot,ndec)=lr_table(name,ts)
        print(f"**{lbl}** — E1 edge accuracy (non-UNSURE decisive) = {good}/{tot} = {good/max(1,tot):.3f}; decisive edges with verdict {tot}/{ndec}\n")
        print("| verdict | fix | break | other | LR=P(v|fix)/P(v|break) | 95% CI |\n|---|---|---|---|---|---|"); print("\n".join(rows)); print()
    LRd,_,_=lr_table(name,D); LRt,_,_=lr_table(name,T)
    e3=apply_lr(name,T,LRd); e4=apply_lr(name,D,LRt)
    print(f"**E3** dev-fit ±logLR -> test: {e3[0]} vs mode {modeacc(T)} (+{e3[1]} −{e3[2]}, McNemar p={mcnemar(e3[1],e3[2])})  ")
    print(f"**E4** test-fit -> dev: {e4[0]} vs mode {modeacc(D)} (+{e4[1]} −{e4[2]}); LR dev/test: "+", ".join(f"{v} {LRd[v]:.2f}/{LRt[v]:.2f}" for v in LRd)+"\n")
    C=conditional(name); n=C['n']; wl,wu=wilson(C['dj'],C['dn'])
    wstr=f" [{wl:.3f}, {wu:.3f}]" if wl is not None else ""
    print(f"**Conditional on counts** (decisive edges with non-UNSURE verdict, n={n}): judge {C['j']/n:.3f} | counts-only {C['c']/n:.3f} | agree {C['ag']/n:.3f} | **judge when disagreeing {C['dj']}/{C['dn']} = {C['dj']/max(1,C['dn']):.3f}{wstr} (Wilson CI)**\n")
    if name != 'Judge-P':  # E5 pairwise: no exhaustive aggregation (spec N4)
        res=sorted(((run_cfg(name,ALL,*c),c) for c in cfgs),key=lambda r:-r[0][0]); b=res[0]
        bd=max(cfgs,key=lambda c:run_cfg(name,D,*c)[0]); bt=max(cfgs,key=lambda c:run_cfg(name,T,*c)[0])
        print(f"**Aggregation grid** ({len(cfgs)} configs, in-sample all 400): max {b[0][0]} (+{b[0][1]} −{b[0][2]}) at {b[1]}; configs ≥155: {sum(1 for r in res if r[0][0]>=155)}; best-on-dev→test {run_cfg(name,T,*bd)} (mode {modeacc(T)}); best-on-test→dev {run_cfg(name,D,*bt)} (mode {modeacc(D)})\n")
