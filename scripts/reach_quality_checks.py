#!/usr/bin/env python3
"""Exploratory checks on reach: (a) by question format (multiple choice vs open); (b) quality of the second candidate:
when the first candidate is wrong and the method produces a second, how often is the second correct?
Reads frozen files only. Usage: python3 scripts/reach_quality_checks.py"""
import json,importlib.util,glob,re
from pathlib import Path
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','A3':'experiments/hle400_A3/deepseek-v4-flash','C2':C2DS}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','A3','C2')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','A3','C2')})}
def mcn(b,c):
    n=b+c; return 1.0 if n==0 else min(1,sum(comb(n,i) for i in range(0,min(b,c)+1))*2/2**n)
OUT={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; R={}; MC=None; Q2={}
    for a,d in arms.items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if a=='A3' else 0; tasks=sorted(loop)
        if MC is None: MC={t:bool(re.fullmatch(r'[A-Z]',str(loop[t].get('gold_answer','')).strip())) for t in tasks}
        reach={}; n2=c2=0
        for t in tasks:
            lp=loop[t]; keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[a][t][st:]
            cands=[]
            for k in keys:
                if k is not None and k not in cands: cands.append(k)
            cc=[bool(reco.last_key_correct(keys,sl,k)) for k in cands]; reach[t]=any(cc)
            if len(cc)>=2 and not cc[0]: n2+=1; c2+=cc[1]
        R[a]=reach; Q2[a]=(c2,n2)
    nmc=sum(MC.values()); print(m,'multiple choice',nmc,'open',400-nmc)
    for fmt,sel in (('MC',[t for t in MC if MC[t]]),('open',[t for t in MC if not MC[t]])):
        row={a:sum(R[a][t] for t in sel) for a in arms}
        def disc(x,y): B=sum(R[x][t] and not R[y][t] for t in sel); C=sum(R[y][t] and not R[x][t] for t in sel); return f"{B}/{C} p={mcn(B,C):.3g}"
        print('  ',fmt,row,'| FC vs RP',disc('C2','A2'),'| FC vs PP',disc('C2','A2P'),'| PP vs RP',disc('A2P','A2'),'| FC vs SC',disc('C2','A3'))
    print('   second candidate correct | first wrong:',{a:f"{c}/{n}={c/n:.2f}" for a,(c,n) in Q2.items()})
    OUT[m]={'second_candidate':Q2}
