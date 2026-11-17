#!/usr/bin/env python3
"""Pairing of questions for the mismatched-critique control (docs/CONTENT_CONTROLS_SPEC.md).
Each question q is paired with another question q' of the same answer type (multiple choice / open form)
and a different subject area, whose critiques in the frozen critique loop are of similar length (same tertile
of mean length), by a fixed seed; the control shows the solver the critiques that the frozen
critique loop (qwen) received on q'. No question is paired with itself. Contains task ids only.
Usage: python3 scripts/make_mismatch_map.py   (writes experiments/hle400/t3/mismatch_map_qwen.json)"""
import json,random
rows=[json.loads(l) for l in open('data/raw/hle/hle_400_new.jsonl')]
ids=[f'hle_{i+1:03d}' for i in range(400)]
def clen(dirs):  # characters of one critique as the solver sees it (labels, suspicions, checks)
    return sum(len(str(d.get('archetype_name') or ''))+len(str(d.get('suspicion') or ''))+len(str(d.get('check') or '')) for d in dirs)
T={}; LEN={}; NDIR={}
for l in open('experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg/loop_trajectories.jsonl'):
    d=json.loads(l); cr=[r['critic_direction'] for r in d['rounds'][1:] if r.get('critic_direction')]
    T[d['task_id']]=len(cr); LEN[d['task_id']]=sum(clen(c) for c in cr)/max(1,len(cr)); NDIR[d['task_id']]=sum(len(c) for c in cr)/max(1,len(cr))
assert set(T)==set(ids)
cut=sorted(LEN.values()); c1,c2=cut[133],cut[266]
tert=lambda t: 0 if LEN[t]<=c1 else (1 if LEN[t]<=c2 else 2)
rng=random.Random(20261115); M={}
for i,t in enumerate(ids):
    pool=[ids[j] for j in range(400) if j!=i and rows[j]['answer_type']==rows[i]['answer_type'] and rows[j]['category']!=rows[i]['category'] and T[ids[j]]>=1 and tert(ids[j])==tert(t)]
    M[t]=rng.choice(pool)
assert all(k!=v for k,v in M.items())
json.dump({'seed':20261115,'rule':'same answer type, different subject area, same tertile of mean critique length in the frozen critique loop, donor has at least one critique','source':'experiments/rep200_C2_qwen3.8-flash-payg/','length_tertile_cuts_chars':[round(c1),round(c2)],'donor':M,'donor_critique_rounds':{t:T[M[t]] for t in ids}},open('experiments/hle400/t3/mismatch_map_qwen.json','w'),indent=0)
own=sum(LEN.values())/400; don=sum(LEN[M[t]] for t in ids)/400
print('400 pairs; distinct donors',len(set(M.values())),'; donor critique rounds: min',min(T[v] for v in M.values()))
print(f"mean critique length (chars): own {own:.0f}, donor {don:.0f}; mean doubts per critique: own {sum(NDIR.values())/400:.2f}, donor {sum(NDIR[M[t]] for t in ids)/400:.2f}; tertile cuts {c1:.0f}, {c2:.0f}")
