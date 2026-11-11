#!/usr/bin/env python3
"""Additional statistics requested in review (2026-11-11): bank critic vs placebos, pooled bound at 11 samples,
model x condition interactions, single-sample accuracy, truncation rates, answer-leak check on free-critic
trajectories, suspicions per round. Reads frozen files only. Usage: python3 scripts/review_fixes_stats.py"""
import json,sys,importlib.util,random,re
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T=json.load(open('experiments/hle400/t3/two_model_scores.json')); ds,q=T['deepseek'],T['qwen']
def perm(x,y,n=10000):
    d=[a-b for a,b in zip(x,y)]; obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=0
    for _ in range(n):
        if abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9: ge+=1
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return f"{obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/(n+1):.4f}"
print("BC vs RP selected:",perm(ds['C3']['sel'],ds['A2']['sel'])); print("BC vs PP selected:",perm(ds['C3']['sel'],ds['A2P']['sel']))
print("BC vs RP pooled:",perm(ds['C3']['pool'],ds['A2']['pool'])); print("BC vs RP final:",perm(ds['C3']['fin'],ds['A2']['fin']))
# interactions (qwen diff minus deepseek diff), same items
for a,b,key in (('C2','A2','fin'),('C2','A2','sel'),('C2','A2P','sel'),('C2','A3','sel')):
    x=[q[a][key][i]-q[b][key][i] for i in range(400)]; y=[ds[a][key][i]-ds[b][key][i] for i in range(400)]
    print(f"interaction qwen-deepseek, {a}-{b} [{key}]:",perm(x,y))
SIDE={'ds':json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_v3.json'))['arms'],'qw':json.load(open('experiments/hle400/t3/is_correct_t3_sidecar_rep.json'))['arms']}
P={'ds':{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C3':'experiments/hle400_C3/deepseek-v4-flash','C2':'experiments/hle400_C2/deepseek-v4-flash-payg'},
   'qw':{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')}}
def norm(s): return re.sub(r'\s+','',str(s).lower())
for m in ('ds','qw'):
    for arm,d in P[m].items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); side=SIDE[m][arm]
        tr=0; n=0; r0tr=0
        for t,lp in loop.items():
            rs=lp['rounds'][(1 if arm=='A3' else 0):]
            tr+=sum(r.get('finish_reason')=='length' for r in rs); n+=len(rs); r0tr+= lp['rounds'][0].get('finish_reason')=='length'
        line=f"{m} {arm}: truncated rounds {tr}/{n}={tr/n:.3f}; truncated greedy first answers {r0tr}"
        if arm=='A3':
            c=sum(bool(x['c']) for t in side for x in side[t][1:]); line+=f"; single-sample accuracy {c/(9*400):.3f} = {c/9:.1f} of 400"
        if arm=='C2':
            sus=Counter(); rep=dam=0; leak={'rep':[0,0],'dam':[0,0]}
            for t,lp in loop.items():
                keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[t]
                for r in lp['rounds'][1:]: sus[len(r.get('critic_direction') or [])]+=1
                for i in range(1,len(keys)):
                    if keys[i-1] is None or keys[i] is None or keys[i]==keys[i-1]: continue
                    a,b=bool(sl[i-1]['c']),bool(sl[i]['c'])
                    if a==b: continue
                    kind='rep' if b else 'dam'; rep+=b; dam+=a
                    fam,val=keys[i]
                    if fam=='letter': continue
                    c=norm(json.dumps(lp['rounds'][i].get('critic_direction') or [],ensure_ascii=False))
                    hit = (re.search(r'(?<!\d)'+re.escape(str(val))+r'(?!\d)',c) is not None) if fam=='int' else (len(norm(val))>=3 and norm(val) in c)
                    leak[kind][1]+=1; leak[kind][0]+=hit
            tot=sum(sus.values()); line+=f"; suspicions/round {dict(sorted(sus.items()))} three={sus[3]/tot:.2f}; decisive switches repair {rep} damage {dam}; new answer string inside critic text: repair {leak['rep'][0]}/{leak['rep'][1]}, damage {leak['dam'][0]}/{leak['dam'][1]}"
        print(line)
