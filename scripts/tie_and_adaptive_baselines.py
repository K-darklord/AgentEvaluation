#!/usr/bin/env python3
"""Tie-break sensitivity, randomized-tie paired tests, cost-matched adaptive self-consistency (simulated on
A3 samples with random permutations), per-round curves, final-init reconciliation and endpoint alignment.
Source of the §3.1 / §5.1 / §5.3 / §5.4 / §8 numbers in docs/PAPER_DRAFT.md (v5). Reads frozen files only.
Usage: python3 scripts/tie_and_adaptive_baselines.py"""
import json,sys,importlib.util,math,random
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(__import__('os').environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
ARM={}
for arm,d in (('A2','deepseek-v4-flash'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg'),('A2P','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    T={}
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]
        toks=[(r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0) for r in lp['rounds']]
        T[t]=dict(keys=keys,sl=sl,toks=toks)
    ARM[arm]=T
tasks=sorted(ARM['C3'])
def pick(keys,sl,rule,rng=None,start=0):
    ks=keys[start:]; ss=sl[start:]
    cnt=Counter(k for k in ks if k is not None)
    if not cnt: return False
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    last={};first={}
    for i,k in enumerate(ks):
        if k is None: continue
        last[k]=i; first.setdefault(k,i)
    if rule=='latest': k=max(tied,key=lambda k:last[k])
    elif rule=='earliest': k=min(tied,key=lambda k:first[k])
    else: k=rng.choice(tied)
    return reco.last_key_correct(ks,ss,k)
print("=== M2: tie-break sensitivity (mode over all rounds for loop arms; vote over samples r1..9 for A3) ===")
res={}
for arm in ('A2','C3','C2','A3'):
    st=1 if arm=='A3' else 0
    row={}
    for rule in ('latest','earliest'):
        row[rule]=[pick(ARM[arm][t]['keys'],ARM[arm][t]['sl'],rule,start=st) for t in tasks]
    rng=random.Random(0); acc=[0.0]*len(tasks)
    for _ in range(200):
        for i,t in enumerate(tasks): acc[i]+=pick(ARM[arm][t]['keys'],ARM[arm][t]['sl'],'random',rng,start=st)
    row['random']=[a/200 for a in acc]
    ties=sum(1 for t in tasks if (lambda c: len(c)>1 and sorted(c.values())[-1]==sorted(c.values())[-2])(Counter(k for k in ARM[arm][t]['keys'][st:] if k)))
    res[arm]=row
    print(f"{arm}: latest {sum(row['latest'])}  earliest {sum(row['earliest'])}  random(E) {sum(row['random']):.1f}   tie-decided items {ties}")
print("paired McNemar, same tie rule both arms:")
for rule in ('latest','earliest'):
    for a,b in (('C3','A3'),('C2','A3'),('A2','A3'),('C3','A2'),('C2','A2')):
        x=res[a][rule]; y=res[b][rule]; B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i])
        print(f"  [{rule}] {a} vs {b}: {sum(x)} vs {sum(y)}  {B}/{C}  p={mcn(B,C):.3f}")
print("\n=== M3/M5: adaptive-stopping self-consistency on A3's samples in order (stop when some answer has 3 votes; else all 9) ===")
tot=0; toks=0; ties_lat=0; acc_lat=0; acc_first=0
for t in tasks:
    d=ARM['A3'][t]; ks=d['keys'][1:]; ss=d['sl'][1:]; tk=d['toks'][1:]
    cnt=Counter(); stop=len(ks)
    for i,k in enumerate(ks):
        if k is not None: cnt[k]+=1
        if cnt and max(cnt.values())>=3: stop=i+1; break
    toks+=sum(tk[:stop])
    acc_lat+=pick(ks[:stop],ss[:stop],'latest'); acc_first+=pick(ks[:stop],ss[:stop],'earliest')
print(f"A3-adaptive(k=3): acc latest-tie {acc_lat}  earliest-tie {acc_first}  solver tokens {toks/1e6:.2f} M  (full A3 vote 136, 51.32 M; C3.mode 154, 37.05 M)")
x=[pick(ARM['A3'][t]['keys'][1:],ARM['A3'][t]['sl'][1:],'earliest') for t in tasks]
print("\n=== M4: per-round accuracy curves (fraction correct among items still running at round r; and cumulative ceiling) ===")
for arm in ('A2','C3','C2'):
    T=ARM[arm]; line=[]; ceil=[]
    for r in range(0,11):
        alive=[t for t in tasks if r<len(T[t]['keys'])]
        if not alive: break
        corr=sum(T[t]['sl'][r]['c'] for t in alive)
        reach=sum(any(x['c'] for x in T[t]['sl'][:r+1]) for t in tasks)
        line.append(f"r{r}:{corr}/{len(alive)}"); ceil.append(reach)
    print(f"{arm} alive-correct: "+" ".join(line)); print(f"{arm} any-correct-by-round: {ceil}  mean rounds {sum(len(T[t]['keys']) for t in tasks)/400:.2f}")
print("\n=== M4: reconcile final-init with per-round correctness changes (C3) ===")
for arm in ('A2','C3','C2'):
    T=ARM[arm]; up=dn=0; up_from_none=dn_to_none=0; cc_diff=0; c_tr=0
    for t in tasks:
        keys=T[t]['keys']; sl=T[t]['sl']
        for i in range(1,len(keys)):
            a,b=bool(sl[i-1]['c']),bool(sl[i]['c'])
            if not a and b: up+=1; up_from_none+= keys[i-1] is None
            if a and not b: dn+=1; dn_to_none+= keys[i] is None
            if a and b: c_tr+=1; cc_diff+= keys[i]!=keys[i-1]
    init=sum(T[t]['sl'][0]['c'] for t in tasks); fin=sum(T[t]['sl'][-1]['c'] for t in tasks)
    print(f"{arm}: all round-level up {up} (from no-commit {up_from_none}) down {dn} (into no-commit {dn_to_none}) net {up-dn} = final-init {fin-init}; correct->correct transitions {c_tr}, of which key changed {cc_diff} ({cc_diff/max(1,c_tr):.2f})")
print("\n=== minor 1: exact p for ceiling 47/8 and 50/7 ===")
print("47/8 p=%.2e  50/7 p=%.2e"%(mcn(47,8),mcn(50,7)))
print("\n=== minor 10: headroom-37 decomposition by margin (C3) ===")
C=Counter()
for t in tasks:
    keys=ARM['C3'][t]['keys']; sl=ARM['C3'][t]['sl']; cnt=Counter(k for k in keys if k)
    if not cnt: continue
    mk=reco.freeze_mode_key(keys)
    if reco.last_key_correct(keys,sl,mk) or not any(reco.last_key_correct(keys,sl,k) for k in cnt): continue
    c=sorted(cnt.values(),reverse=True); m=c[0]-(c[1] if len(c)>1 else 0)
    C['tie' if m==0 else 'margin1' if m==1 else 'margin>=2']+=1
print(dict(C))

print("\n=== cost-matched: critic arms vs A3-adaptive (same tie rule) ===")
def adaptive(rule):
    out=[]
    for t in tasks:
        d=ARM['A3'][t]; ks=d['keys'][1:]; ss=d['sl'][1:]
        cnt=Counter(); stop=len(ks)
        for i,k in enumerate(ks):
            if k is not None: cnt[k]+=1
            if cnt and max(cnt.values())>=3: stop=i+1; break
        out.append(pick(ks[:stop],ss[:stop],rule))
    return out
for rule in ('latest','earliest'):
    y=adaptive(rule)
    for a in ('A2','C3','C2'):
        x=res[a][rule]; B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i])
        print(f"  [{rule}] {a} {sum(x)} vs A3-adaptive {sum(y)}: {B}/{C} p={mcn(B,C):.3f}")
print("\n=== round-1 one-step check: up/down from r0->r1 per arm ===")
for arm in ('A2','C3','C2'):
    T=ARM[arm]; up=sum(1 for t in tasks if not T[t]['sl'][0]['c'] and T[t]['sl'][1]['c']); dn=sum(1 for t in tasks if T[t]['sl'][0]['c'] and not T[t]['sl'][1]['c'])
    print(f"{arm}: r0->r1 up {up} down {dn}  ECR1={up/287:.3f} EIR1={dn/113:.3f} ratio {up/287/(dn/113):.2f} (threshold 0.39)")

print("\n=== randomized A3 tie-break: distribution of McNemar p for critic arms (latest, as specified) vs A3.vote(random) ===")
import statistics
def a3_random(rng, start=1):
    return [pick(ARM['A3'][t]['keys'],ARM['A3'][t]['sl'],'random',rng,start=start) for t in tasks]
for a in ('C3','C2','A2'):
    x=res[a]['latest']; ps=[]; accs=[]
    rng=random.Random(1)
    for _ in range(300):
        y=a3_random(rng); accs.append(sum(y))
        B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); ps.append(mcn(B,C))
    ps.sort()
    print(f"  {a}.mode(latest)={sum(x)} vs A3.vote(random): A3 acc mean {statistics.mean(accs):.1f} [{min(accs)},{max(accs)}]  p median {ps[150]:.3f}  IQR [{ps[75]:.3f},{ps[225]:.3f}]  P(p<0.05)={sum(p<0.05 for p in ps)/300:.2f}")
print("\n=== how much of the loop arms' mode comes from the recency tie rule (latest vs random expectation) ===")
for a in ('A2','C3','C2'):
    print(f"  {a}: latest {sum(res[a]['latest'])}  random E {sum(res[a]['random']):.1f}  earliest {sum(res[a]['earliest'])}  -> recency contributes {sum(res[a]['latest'])-sum(res[a]['random']):.1f} items")
print("\n=== same against cost-matched adaptive A3 with random ties ===")
def adaptive_random(rng):
    out=[]
    for t in tasks:
        d=ARM['A3'][t]; ks=d['keys'][1:]; ss=d['sl'][1:]
        cnt=Counter(); stop=len(ks)
        for i,k in enumerate(ks):
            if k is not None: cnt[k]+=1
            if cnt and max(cnt.values())>=3: stop=i+1; break
        out.append(pick(ks[:stop],ss[:stop],'random',rng))
    return out
for a in ('C3','C2'):
    x=res[a]['latest']; ps=[]; accs=[]; rng=random.Random(2)
    for _ in range(300):
        y=adaptive_random(rng); accs.append(sum(y))
        B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); ps.append(mcn(B,C))
    ps.sort(); print(f"  {a}.mode(latest)={sum(x)} vs A3-adaptive(random): acc mean {statistics.mean(accs):.1f}  p median {ps[150]:.3f} IQR [{ps[75]:.3f},{ps[225]:.3f}]  P(p<0.05)={sum(p<0.05 for p in ps)/300:.2f}")

print("\n=== M1: fully randomized ties on BOTH sides (300 paired draws) ===")
def rand_pick_all(arm,rng,start=0):
    return [pick(ARM[arm][t]['keys'],ARM[arm][t]['sl'],'random',rng,start=start) for t in tasks]
for a in ('C3','C2','A2','A2P'):
    ps=[];da=[];db=[]; rng=random.Random(11)
    for _ in range(300):
        x=rand_pick_all(a,rng); y=rand_pick_all('A3',rng,start=1)
        B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); ps.append(mcn(B,C)); da.append(sum(x)); db.append(sum(y))
    ps.sort(); print(f"  {a}(random ties) mean {statistics.mean(da):.1f} vs A3(random) mean {statistics.mean(db):.1f}: p median {ps[150]:.3f} IQR [{ps[75]:.3f},{ps[225]:.3f}] P(p<0.05)={sum(p<0.05 for p in ps)/300:.2f}")
print("\n=== A2P symmetric-tie pairwise (both sides randomized, 300 paired draws) ===")
for si,b in enumerate(('C2','A2','A3')):
    ps=[]; da=[]; db=[]; rng=random.Random(21+si)
    for _ in range(300):
        x=rand_pick_all('A2P',rng); y=rand_pick_all(b,rng,start=(1 if b=='A3' else 0))
        B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); ps.append(mcn(B,C)); da.append(sum(x)); db.append(sum(y))
    ps.sort(); print(f"  A2P(random) mean {statistics.mean(da):.1f} vs {b}(random) mean {statistics.mean(db):.1f}: p median {ps[150]:.3f} IQR [{ps[75]:.3f},{ps[225]:.3f}] P(p<0.05)={sum(p<0.05 for p in ps)/300:.2f}")
print("\n=== M2: adaptive A3 under random sample orderings (300 permutations; samples drawn without replacement from the 9) ===")
accs=[];toks=[];ps_c2=[];ps_c3=[]; rng=random.Random(5)
xC2=res['C2']['latest']; xC3=res['C3']['latest']
for _ in range(300):
    y=[]; tk=0
    for t in tasks:
        d=ARM['A3'][t]; idx=list(range(1,len(d['keys']))); rng.shuffle(idx)
        ks=[d['keys'][i] for i in idx]; ss=[d['sl'][i] for i in idx]; tt=[d['toks'][i] for i in idx]
        cnt=Counter(); stop=len(ks)
        for i,k in enumerate(ks):
            if k is not None: cnt[k]+=1
            if cnt and max(cnt.values())>=3: stop=i+1; break
        tk+=sum(tt[:stop]); y.append(pick(ks[:stop],ss[:stop],'random',rng))
    accs.append(sum(y)); toks.append(tk)
    for x,ps in ((xC2,ps_c2),(xC3,ps_c3)):
        B=sum(1 for i in range(400) if x[i] and not y[i]); C=sum(1 for i in range(400) if y[i] and not x[i]); ps.append(mcn(B,C))
ps_c2.sort(); ps_c3.sort()
print(f"  A3-adaptive acc mean {statistics.mean(accs):.1f} [{min(accs)},{max(accs)}]  tokens mean {statistics.mean(toks)/1e6:.2f} M [{min(toks)/1e6:.2f},{max(toks)/1e6:.2f}]")
print(f"  C2.mode(latest) 159 vs adaptive: p median {ps_c2[150]:.3f} IQR [{ps_c2[75]:.3f},{ps_c2[225]:.3f}] P(p<0.05)={sum(p<0.05 for p in ps_c2)/300:.2f}")
print(f"  C3.mode(latest) 154 vs adaptive: p median {ps_c3[150]:.3f} IQR [{ps_c3[75]:.3f},{ps_c3[225]:.3f}] P(p<0.05)={sum(p<0.05 for p in ps_c3)/300:.2f}")
print("\n=== M3: endpoint alignment C2(payg) vs C3(token-plan) vs A2 — per-round statistics, rounds>=1 ===")
for arm,d in (('A2','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    loop=reco.load_jsonl(Path(f'experiments/hle400_{arm}/{d}/loop_trajectories.jsonl'))
    L=[];trunc=0;n=0;commit=0;rt=[]
    for t,lp in loop.items():
        for r in lp['rounds'][1:]:
            n+=1; L.append(len(r.get('reasoning_content') or '')); trunc+= r.get('finish_reason')=='length'
            commit+= bool((r.get('final_answer') or '').strip()); rt.append(r.get('reasoning_tokens') or 0)
    L.sort(); 
    print(f"  {arm}: rounds {n}  reasoning chars median {L[len(L)//2]:,} IQR [{L[len(L)//4]:,},{L[3*len(L)//4]:,}]  reasoning tokens mean {statistics.mean(rt):.0f}  truncation rate {trunc/n:.3f}  commit rate {commit/n:.3f}")
