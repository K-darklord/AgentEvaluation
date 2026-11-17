#!/usr/bin/env python3
"""Mechanism quantities on the 800 new questions (qwen3.8-flash), with the definitions of three_model_appendix.py:
 (a) repeat probabilities: probability that the next answer repeats the current one, by correctness of the current answer;
 (b) plurality answer against last answer (the verdict of the last round, as in two_model_tables.py), with a
     sign-flip permutation test and bootstrap interval of last minus plurality; first revision repaired / damaged.
Descriptive; no test. For comparison the same rows on the original 400 questions.
Reads frozen files only. Usage: python3 scripts/confirmation_mechanism.py (writes experiments/hle400/t3/confirmation_mechanism.json)"""
import json,importlib.util,random
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T='experiments/hle400/t3/'; Q='qwen3.8-flash-payg'; J=lambda f: json.load(open(T+f))['arms']
conf=J('is_correct_t3_sidecar_confirm.json'); rep=J('is_correct_t3_sidecar_rep.json'); yk=J('is_correct_t3_sidecar_yoke.json')
SETS={'new 800':{'reassuring':(f'experiments/conf_A2_{Q}/{Q}',conf['A2']),'generic doubt':(f'experiments/conf_A2P_{Q}/{Q}',conf['A2P']),'token-yoked generic doubt':(f'experiments/conf_A2PY_{Q}/{Q}',conf['A2PY']),'critique':(f'experiments/conf_C2_{Q}/{Q}',conf['C2'])},
      'original 400':{'reassuring':(f'experiments/rep200_A2_{Q}/{Q}',rep['A2']),'generic doubt':(f'experiments/rep200_A2P_{Q}/{Q}',rep['A2P']),'token-yoked generic doubt':(f'experiments/yoke_A2PY_{Q}/{Q}',yk['A2PY']),'critique':(f'experiments/rep200_C2_{Q}/{Q}',rep['C2'])}}
def perm(d):
    obs=sum(d); r=random.Random(1); nz=[v for v in d if v]
    ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(10000)); bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000))
    return {'diff':round(obs,1),'lo':round(bs[50],1),'hi':round(bs[1949],1),'p':round((ge+1)/10001,4)}
OUT={}
for s,arms in SETS.items():
    OUT[s]={}; print(f"\n{s}\n{'loop':28s} repeat|correct repeat|incorrect ratio gap odds | selected (plurality) last answer | first revision repaired/damaged")
    for name,(d,side) in arms.items():
        L=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); a=[0,0,0,0]; sel=last=0.0; up=down=0; D=[]
        for t,lp in L.items():
            k=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[t]
            for i in range(len(k)-1):
                if k[i] is None: continue
                c=bool(sl[i]['c']); a[0 if c else 2]+=1; a[1 if c else 3]+= k[i+1]==k[i]
            if len(sl)>1:
                c0,c1=bool(sl[0]['c']),bool(sl[1]['c']); up+=(not c0) and c1; down+= c0 and not c1
            cnt=Counter(x for x in k if x is not None)
            sq=0.0
            if cnt:
                ok={x:reco.last_key_correct(k,sl,x) for x in cnt}; top=max(cnt.values()); tied=[x for x in cnt if cnt[x]==top]; sq=sum(ok[x] for x in tied)/len(tied)
            lq=float(bool(sl[-1]['c'])); sel+=sq; last+=lq; D.append(lq-sq)
        sc,sw=a[1]/a[0],a[3]/a[2]
        OUT[s][name]={'repeat_correct':round(sc,3),'repeat_incorrect':round(sw,3),'ratio':round(sc/sw,2),'gap':round(sc-sw,3),'odds_ratio':round((sc/(1-sc))/(sw/(1-sw)),2),'selected':round(sel,1),'last':round(last,1),'first_revision_repaired':up,'first_revision_damaged':down,'counts':a,'last_minus_selected':perm(D)}
        print(f"{name:28s} {sc:.2f} {sw:.2f} {sc/sw:.2f} {sc-sw:+.2f} {(sc/(1-sc))/(sw/(1-sw)):.2f} | {sel:6.1f} {last:6.1f} | {up}/{down} | last - selected {OUT[s][name]['last_minus_selected']}")
json.dump(OUT,open(T+'confirmation_mechanism.json','w'),indent=1)
