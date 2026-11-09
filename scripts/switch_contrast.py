#!/usr/bin/env python3
"""Contrast R->W vs W->R switches (freeze-key, sidecar v2) on gold-free features.
Input: experiments/hle400/t3/r2w_w2r_switches_freezekey.jsonl. Prints per-feature
R->W rate / W->R rate / AUC, on all edges and on dev(even)/test(odd) halves."""
import json,re,sys,math
from collections import Counter
P='experiments/hle400/t3/r2w_w2r_switches_freezekey.jsonl'
R=[json.loads(l) for l in open(P)]
def norm(s): return ' '.join((s or '').split())
HEDGE=re.compile(r"\b(maybe|perhaps|likely|probably|i think|not sure|uncertain|guess|hmm|might be|could be|i recall|i believe)\b",re.I)
VER=re.compile(r"\b(check|verif|sanity|plug|substitut|confirm|consistent|matches|let'?s test|small case|for n ?=|n ?= ?\d)",re.I)
FB=re.compile(r"\b(feedback|reviewer|critic)\b",re.I)
STOPW=set("the a an of to in and or is are be for that this with as on by it its from at not no if then than which what".split())
def toks(s): return {w for w in re.findall(r"[a-z][a-z\-]{3,}",(s or '').lower()) if w not in STOPW}
def feats(r):
    oc,nc=norm(r['old_cot']),norm(r['new_cot'])
    old_ans,new_ans=norm(r['old_answer']),norm(r['new_answer'])
    kb=[None if k is None else tuple(k) for k in r['keys_before']]
    newk=tuple(r['new_key']); oldk=tuple(r['old_key'])
    run_old=0
    for k in reversed(kb):
        if k==oldk: run_old+=1
        else: break
    crit=r['critic']; sus=' '.join((c.get('suspicion') or '')+' '+(c.get('check') or '') for c in crit)
    ctoks=toks(sus); ntail=nc[-6000:]
    ov=len(ctoks & toks(ntail))/max(1,len(ctoks))
    f=dict(
      pos=r['to_r'],
      old_run_len=run_old,
      new_is_revert=newk in kb,
      new_is_novel=newk not in kb,
      n_cands_before=len({k for k in kb if k is not None}),
      old_trunc=r['from_status']=='trunc', new_trunc=r['to_status']=='trunc',
      new_len=len(nc), old_len=len(oc), len_ratio=len(nc)/max(1,len(oc)),
      new_hedge=len(HEDGE.findall(ntail))/max(1,len(ntail)/1000),
      old_hedge=len(HEDGE.findall(oc[-6000:]))/max(1,len(oc[-6000:])/1000),
      new_verify=len(VER.findall(ntail))/max(1,len(ntail)/1000),
      new_cites_feedback=bool(FB.search(nc[-2000:])),
      new_mentions_old_answer=(len(old_ans)>=2 and old_ans[:40].lower() in nc.lower()),
      old_mentions_new_answer=(len(new_ans)>=2 and new_ans[:40].lower() in oc.lower()),
      critic_overlap=ov,
      n_suspicions=len(crit),
      arch_retrieval=any('retrieval' in (c.get('archetype_name') or '') for c in crit),
      arch_procedure=any('procedure' in (c.get('archetype_name') or '') for c in crit),
      arch_constraint=any('constraint' in (c.get('archetype_name') or '') for c in crit),
      arch_label=any('label' in (c.get('archetype_name') or '') for c in crit),
      fam_letter=r['family']=='letter', fam_int=r['family']=='int', fam_raw=r['family']=='raw',
      new_final_marker=bool(re.search(r"final answer|answer:|boxed",nc[-400:],re.I)),
    )
    return f
def auc(pos,neg):
    if not pos or not neg: return float('nan')
    w=0
    for p in pos:
        for q in neg: w+=1 if p>q else 0.5 if p==q else 0
    return w/(len(pos)*len(neg))
rows=[(r,feats(r)) for r in R]
names=list(rows[0][1].keys())
def table(sub,label):
    pos=[f for r,f in sub if r['type']=='R->W']; neg=[f for r,f in sub if r['type']=='W->R']
    print(f"\n[{label}] R->W n={len(pos)}  W->R n={len(neg)}   (AUC = P(R->W ranked above W->R); <0.5 means feature favours W->R)")
    print(f"{'feature':24s} {'mean R->W':>10s} {'mean W->R':>10s} {'AUC':>6s}")
    res=[]
    for n in names:
        a=[float(f[n]) for f in pos]; b=[float(f[n]) for f in neg]
        res.append((n,sum(a)/len(a),sum(b)/len(b),auc(a,b)))
    for n,ma,mb,u in sorted(res,key=lambda x:-abs(x[3]-0.5)):
        print(f"{n:24s} {ma:10.3f} {mb:10.3f} {u:6.3f}")
    return {n:u for n,_,_,u in res}
clean=[(r,f) for r,f in rows if not f['old_trunc'] and not f['new_trunc']]
A=table(rows,'ALL edges'); 
D=table([(r,f) for r,f in clean if int(r['task_id'].split('_')[1])%2==0],'clean, dev(even)')
T=table([(r,f) for r,f in clean if int(r['task_id'].split('_')[1])%2==1],'clean, test(odd)')
print("\nstable features (same side of 0.5 on dev and test, |AUC-0.5|>=0.08 on both):")
for n in names:
    if (D[n]-0.5)*(T[n]-0.5)>0 and abs(D[n]-0.5)>=0.08 and abs(T[n]-0.5)>=0.08: print(f"  {n:24s} dev {D[n]:.3f}  test {T[n]:.3f}")
