#!/usr/bin/env python3
"""Pre-specified read-out for docs/COST_MATCHED_SC_AND_USC_SPEC.md (R1, R2) + two-model combined tests.
Reads frozen files only. Usage: python3 scripts/cost_matched_readout.py"""
import json,sys,importlib.util,random
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_v3.json'))['arms']
exa=json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_A3extra.json'))['arms']['A3extra']
T=json.load(open('experiments/hle400/t3/two_model_scores.json'))
A3=reco.load_jsonl(Path('experiments/hle400_A3/deepseek-v4-flash/loop_trajectories.jsonl'))
X=reco.load_jsonl(Path('experiments/hle400_A3_extra/deepseek-v4-flash/loop_trajectories.jsonl'))
tasks=sorted(A3)
def perm(x,y,sub=None,n=10000):
    idx=sub if sub is not None else range(len(x))
    d=[x[i]-y[i] for i in idx]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.4f} (n={len(d)})"
K={}; C={}
for t in tasks:
    K[t]=reco.freeze_keys(A3[t].get('gold_answer',''),A3[t])[1:]+reco.freeze_keys(X[t].get('gold_answer',''),X[t]); C[t]=side['A3'][t][1:]+exa[t]
def vote(t,n):
    keys=K[t][:n]; sl=C[t][:n]; cnt=Counter(k for k in keys if k is not None)
    if not cnt: return 0.0
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return sum(bool(reco.last_key_correct(keys,sl,k)) for k in tied)/len(tied)
V11=[vote(t,11) for t in tasks]; ds=T['deepseek']; q=T['qwen']
print('A3 vote N=11:',round(sum(V11),1))
print('R1  C2.mode vs A3-11 vote:',perm(ds['C2']['sel'],V11))
man=json.load(open('experiments/hle400/t3/api_failure_rerun_manifest.json'))['rerun_tasks']
rows=[json.loads(l) for l in open('experiments/hle400/t3/usc_result.jsonl')]
amap={'A3-9':'A3','A3-11':'A3','C2':'C2','C3':'C3','A2':'A2','A2P':'A2P'}
U={}; stale=Counter()
for x in rows:
    a=amap[x['arm']]; t=x['task_id']; sr=x['selected_round']
    if t in man.get(a,[]): stale[x['arm']]+=1; U.setdefault(x['arm'],{})[t]=None; continue
    if sr is None: c=0.0
    elif a=='A3': c=float(bool(C[t][int(sr)-1]['c']))
    else: c=float(bool(side[a][t][int(sr)]['c']))
    U.setdefault(x['arm'],{})[t]=c
print('USC rows excluded as stale (task rerun after USC call):',dict(stale))
W={k:[U[k][t] for t in tasks] for k in U}
ok=lambda *ks:[i for i in range(400) if all(W[k][i] is not None for k in ks)]
for k in W: print('  USC',k,sum(v for v in W[k] if v is not None),'of',sum(v is not None for v in W[k]))
s=ok('A3-11'); print('R2  C2.mode vs USC(A3-11):',perm(ds['C2']['sel'],W['A3-11'],s))
print('    C3.mode vs USC(A3-11):',perm(ds['C3']['sel'],W['A3-11'],s))
print('    USC(A3-11) vs vote(A3-11):',perm(W['A3-11'],V11,s))
s=ok('A3-11','C2'); print('    USC(C2) vs USC(A3-11):',perm(W['C2'],W['A3-11'],s))
print('\ncombined over both models (same 400 items; per-item sum of the two models):')
for a,b in (('C2','A2'),('C2','A2P'),('C2','A3'),('A2','A3'),('A2P','A2')):
    for key in ('sel','pool','fin','ceil'):
        x=[ds[a][key][i]+q[a][key][i] for i in range(400)]; y=[ds[b][key][i]+q[b][key][i] for i in range(400)]
        print(f'  {a} vs {b} [{key}]:',perm(x,y))
