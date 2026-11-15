#!/usr/bin/env python3
"""Appendix quantities for all three models, with the definitions of persistence_and_settle.py,
tie_and_adaptive_baselines.py and review_fixes_stats.py (which cover deepseek, or deepseek and qwen, only):
 (a) repeat probabilities: probability that the next answer repeats the current one, by correctness of the
     current answer (loops: consecutive rounds; independent samples: ordered pairs among samples 1-9), with
     their ratio, their difference (gap) and the odds ratio;
 (b) first revision: questions repaired / damaged by the first round of feedback;
 (c) does the critic hand over answers: share of critiques whose text contains the solver's next answer,
     among changes of a numeric or free-text answer that change correctness;
 (d) first answers cut off at the token limit; average single-sample accuracy.
Reads frozen files only. Usage: python3 scripts/three_model_appendix.py
(writes experiments/hle400/t3/three_model_appendix.json)"""
import json,importlib.util,re,glob
from pathlib import Path
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','C2':C2DS,'A3':'experiments/hle400_A3/deepseek-v4-flash'}),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','C2','A3')}),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','C2','A3')})}
def norm(s): return re.sub(r'\s+','',str(s).lower())
OUT={}
for m,(sp,arms) in CFG.items():
    side=json.load(open(sp))['arms']; OUT[m]={}
    for arm,d in arms.items():
        loop=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); st=1 if arm=='A3' else 0
        a=[0,0,0,0]; up=down=0; leak={'rep':[0,0],'dam':[0,0]}; trunc0=0; samp=0
        for t,lp in loop.items():
            keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[arm][t]
            trunc0+= lp['rounds'][0].get('finish_reason')=='length'
            k,s=keys[st:],sl[st:]
            if arm=='A3':
                k,s=k[:9],s[:9]; samp+=sum(bool(x['c']) for x in s)
                for i in range(len(k)):
                    for j in range(len(k)):
                        if i!=j and k[i] is not None:
                            c=bool(s[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= k[j]==k[i]
                continue
            for i in range(len(k)-1):
                if k[i] is None: continue
                c=bool(s[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= k[i+1]==k[i]
            if len(s)>1:
                c0,c1=bool(s[0]['c']),bool(s[1]['c']); up+= (not c0) and c1; down+= c0 and (not c1)
            if arm=='C2':
                for i in range(1,len(keys)):
                    if keys[i-1] is None or keys[i] is None or keys[i]==keys[i-1]: continue
                    p,q=bool(sl[i-1]['c']),bool(sl[i]['c'])
                    if p==q: continue
                    fam,val=keys[i]
                    if fam=='letter': continue
                    c=norm(json.dumps(lp['rounds'][i].get('critic_direction') or [],ensure_ascii=False))
                    hit=(re.search(r'(?<!\d)'+re.escape(str(val))+r'(?!\d)',c) is not None) if fam=='int' else (len(norm(val))>=3 and norm(val) in c)
                    kind='rep' if q else 'dam'; leak[kind][1]+=1; leak[kind][0]+=hit
        sc,sw=a[1]/a[0],a[3]/a[2]
        r={'repeat_correct':round(sc,4),'repeat_incorrect':round(sw,4),'ratio':round(sc/sw,3),'gap':round(sc-sw,4),'odds_ratio':round((sc/(1-sc))/(sw/(1-sw)),3),'counts':a}
        line=f"{m} {arm}: repeat|correct {sc:.2f} repeat|incorrect {sw:.2f} ratio {sc/sw:.1f} gap {sc-sw:.2f} odds ratio {(sc/(1-sc))/(sw/(1-sw)):.1f}"
        if arm=='A3':
            r['single_sample_correct']=round(samp/9,1); line+=f" | average single sample {samp/9:.1f} of 400"
        else:
            r.update(first_round_repaired=up,first_round_damaged=down,first_answer_truncated=trunc0)
            line+=f" | first revision repaired {up} damaged {down} | first answers cut off {trunc0}"
        if arm=='C2':
            r['critic_contains_next_answer']={'better':leak['rep'],'worse':leak['dam']}
            line+=f" | critic text contains next answer: better {leak['rep'][0]}/{leak['rep'][1]}, worse {leak['dam'][0]}/{leak['dam'][1]}"
        OUT[m][arm]=r; print(line)
json.dump(OUT,open('experiments/hle400/t3/three_model_appendix.json','w'),indent=1)
