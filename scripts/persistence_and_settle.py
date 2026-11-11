#!/usr/bin/env python3
"""Stay probabilities by correctness (loops: consecutive rounds; A3: all ordered pairs of samples), with item
bootstrap CIs; recency-rule mode; share of correct rounds off the item's main correct key; suspicions per round.
Reads frozen files only (sidecar v3 by default). Usage: python3 scripts/persistence_and_settle.py"""
import json,sys,importlib.util,random,os
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(os.environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
rng=random.Random(0)
for arm,d in (('A2','deepseek-v4-flash'),('A2P','deepseek-v4-flash-payg'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    st=1 if arm=='A3' else 0
    per=[]; latest=0; off=tot=0; sus=Counter(); nr=0
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]; nr+=len(keys)
        a=[0,0,0,0]
        if arm=='A3':
            for i in range(len(keys)):
                for j in range(len(keys)):
                    if i!=j and keys[i] is not None:
                        c=bool(sl[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= keys[j]==keys[i]
        else:
            for i in range(len(keys)-1):
                if keys[i] is None: continue
                c=bool(sl[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= keys[i+1]==keys[i]
        per.append(a)
        cnt=Counter(k for k in keys if k is not None)
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; last={k:i for i,k in enumerate(keys) if k is not None}
            latest+=bool(reco.last_key_correct(keys,sl,max(tied,key=lambda k:last[k])))
        ck=Counter(k for k,s in zip(keys,sl) if k is not None and s['c'])
        if ck: tot+=sum(ck.values()); off+=sum(ck.values())-max(ck.values())
        if arm in('C2','C3'):
            for r in lp['rounds'][1:]: sus[len(r.get('critic_direction') or [])]+=1
    def ratio(P):
        A=[sum(x[i] for x in P) for i in range(4)]; sc=A[1]/A[0]; sw=A[3]/A[2]; return sc,sw,sc/sw
    sc,sw,rt=ratio(per); bs=[ratio([per[rng.randrange(400)] for _ in range(400)]) for _ in range(1000)]
    def ci(i): v=sorted(b[i] for b in bs); return f"[{v[25]:.2f},{v[974]:.2f}]"
    print(f"{arm}: mode(recency) {latest} mean rounds {nr/400:.2f} | stay|correct {sc:.2f} {ci(0)} stay|wrong {sw:.2f} {ci(1)} ratio {rt:.2f} {ci(2)} | off-main correct {off}/{tot}={off/tot:.2f}"+(f" | suspicions/round {dict(sus)}" if sus else ""))
