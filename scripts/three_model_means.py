#!/usr/bin/env python3
"""Mean over the three models of the difference in selected questions (Table "Paired comparisons", last column;
forest figure, "mean of three"). Exploratory summary, not a pre-specified test.
For each question the three per-model differences are summed; the sum is tested with a sign-flip permutation
(10,000 draws) and a question-level bootstrap (2,000 draws); totals are divided by three.
Same vote, tie rule and frozen files as two_model_tables.py / third_model_readout.py.
Also: differences between models in the critique - reassuring difference, and the split of that difference into
(reached_c - reached_p) x conversion_p and reached_c x (conversion_c - conversion_p).
Usage: python3 scripts/three_model_means.py   (writes experiments/hle400/t3/three_model_means.json)"""
import json,importlib.util,random,glob
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','A3','C2')})}
def selected(side,arm,d):
    """Expected score per question under uniformly random ties; independent samples use samples 1-9."""
    loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if arm=='A3' else 0; v=[]
    for t in sorted(loop):
        lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        if arm=='A3': keys,sl=keys[:9],sl[:9]
        cnt=Counter(k for k in keys if k is not None)
        if not cnt: v.append(0.0); continue
        ok=lambda k: bool(sl[max(j for j,x in enumerate(keys) if x==k)]['c'])
        top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; v.append(sum(ok(k) for k in tied)/len(tied))
    return v
S={m:{a:selected(json.load(open(sp))['arms'],a,d) for a,d in arms.items()} for m,(sp,arms) in CFG.items()}
OUT={'per_model_selected':{m:{a:round(sum(S[m][a]),1) for a in S[m]} for m in S},'mean_of_three':{}}
for m in S: print(m,OUT['per_model_selected'][m])
for x,y in (('C2','A2'),('C2','A2P'),('A2P','A2'),('C2','A3')):
    v=[sum(S[m][x][i]-S[m][y][i] for m in S) for i in range(400)]
    r=random.Random(1); nz=[q for q in v if q]; obs=sum(v)
    ge=sum(abs(sum(q if r.random()<.5 else -q for q in nz))>=abs(obs)-1e-9 for _ in range(10000))
    bs=sorted(sum(v[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    res={'diff':round(obs/3,1),'lo':round(bs[50]/3,1),'hi':round(bs[1949]/3,1),'p':round((ge+1)/10001,4)}
    OUT['mean_of_three'][f'{x}-{y}']=res
    print('mean of three',x,'-',y,'%+.1f [%+.1f,%+.1f] p=%.4f'%(res['diff'],res['lo'],res['hi'],res['p']))
# differences between models in the critique - reassuring difference (same questions), and the arithmetic
# split of each model's difference into a reach part and a conversion part (descriptive, exploratory)
OUT['between_models']={}
for m1,m2 in (('qwen','deepseek'),('qwen','minimax'),('deepseek','minimax')):
    v=[(S[m1]['C2'][i]-S[m1]['A2'][i])-(S[m2]['C2'][i]-S[m2]['A2'][i]) for i in range(400)]
    r=random.Random(1); nz=[q for q in v if q]; obs=sum(v)
    ge=sum(abs(sum(q if r.random()<.5 else -q for q in nz))>=abs(obs)-1e-9 for _ in range(10000))
    bs=sorted(sum(v[r.randrange(400)] for _ in range(400)) for _ in range(2000))
    OUT['between_models'][f'{m1}-{m2}']={'diff':round(obs,1),'lo':round(bs[50],1),'hi':round(bs[1949],1),'p':round((ge+1)/10001,4)}
    print(f"critique - reassuring, {m1} minus {m2}: {obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}] p={(ge+1)/10001:.4f}")
REACH={'deepseek':{'A2':153,'C2':198},'qwen':{'A2':123,'C2':182},'minimax':{'A2':125,'C2':152}}  # Table 3; checked by check_manifest.py
OUT['split']={}
for m in S:
    Sp,Sc=sum(S[m]['A2']),sum(S[m]['C2']); Rp,Rc=REACH[m]['A2'],REACH[m]['C2']; Cp,Cc=Sp/Rp,Sc/Rc
    reach_part=(Rc-Rp)*Cp; conv_part=Rc*(Cc-Cp)
    OUT['split'][m]={'reach_part':round(reach_part,1),'conversion_part':round(conv_part,1),'net':round(Sc-Sp,1),'share_lost':round(-conv_part/reach_part,2)}
    print(f"{m}: reach part {reach_part:+.1f}, conversion part {conv_part:+.1f}, net {Sc-Sp:+.1f}, share of the reach part lost {-conv_part/reach_part:.2f}")
json.dump(OUT,open('experiments/hle400/t3/three_model_means.json','w'),indent=1)
