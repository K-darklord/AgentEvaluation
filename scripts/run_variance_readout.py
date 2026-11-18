#!/usr/bin/env python3
"""Read-out of the repeated runs (docs/RUN_VARIANCE_SPEC.md): critique loop and token-yoked generic-doubt loop run a second
time on the first 400 new questions (hle_401..hle_800), qwen3.8-flash, with the same inputs. Descriptive; no test.
Reports reached and selected of each run, the per-question difference in selected score between the two runs of a loop
(sum, standard deviation), the share of questions with the same plurality answer, and selected(critique) - selected(token-yoked)
for the four combinations of runs. Reads frozen files only.
Usage: python3 scripts/run_variance_readout.py (writes experiments/hle400/t3/run_variance_readout.json)"""
import json,importlib.util,statistics
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T='experiments/hle400/t3/'; Q='qwen3.8-flash-payg'
s1=json.load(open(T+'is_correct_t3_sidecar_confirm.json'))['arms']; s2=json.load(open(T+'is_correct_t3_sidecar_confirm_rerun.json'))['arms']
RUNS={'critique':((f'experiments/conf_C2_{Q}/{Q}',s1['C2']),(f'experiments/conf_C2r_{Q}/{Q}',s2['C2'])),'token-yoked generic doubt':((f'experiments/conf_A2PY_{Q}/{Q}',s1['A2PY']),(f'experiments/conf_A2PYr_{Q}/{Q}',s2['A2PY']))}
TASKS=[f'hle_{i}' for i in range(401,801)]
def score(d,side):
    L=reco.load_jsonl(Path(d)/'loop_trajectories.jsonl'); R=[];S=[];P=[]
    for t in TASKS:
        k=reco.freeze_keys(L[t].get('gold_answer',''),L[t]); sl=side[t]; cnt=Counter(x for x in k if x is not None)
        if not cnt: R.append(0); S.append(0.0); P.append(None); continue
        ok={x:reco.last_key_correct(k,sl,x) for x in cnt}; top=max(cnt.values()); tied=sorted([x for x in cnt if cnt[x]==top],key=str)
        R.append(int(any(ok.values()))); S.append(sum(ok[x] for x in tied)/len(tied)); P.append(json.dumps(tied,ensure_ascii=False))
    return R,S,P
OUT={}; V={}
for name,(a,b) in RUNS.items():
    Ra,Sa,Pa=score(*a); Rb,Sb,Pb=score(*b); V[name]=(Sa,Sb); d=[y-x for x,y in zip(Sa,Sb)]
    same0=sum(str(reco.load_jsonl(Path(a[0])/'loop_trajectories.jsonl')[t]['rounds'][0].get('final_answer'))==str(reco.load_jsonl(Path(b[0])/'loop_trajectories.jsonl')[t]['rounds'][0].get('final_answer')) for t in TASKS[:40])
    OUT[name]={'first_run':{'reached':sum(Ra),'selected':round(sum(Sa),1)},'second_run':{'reached':sum(Rb),'selected':round(sum(Sb),1)},
      'selected_second_minus_first':round(sum(d),1),'sd_of_per_question_difference':round(statistics.pstdev(d),3),'sd_of_the_sum_over_400':round(statistics.pstdev(d)*400**0.5,1),
      'questions_with_different_selected_score':sum(abs(x)>1e-9 for x in d),'same_plurality_answer':round(sum(x==y for x,y in zip(Pa,Pb))/400,3),
      'reached_only_first':sum(x and not y for x,y in zip(Ra,Rb)),'reached_only_second':sum(y and not x for x,y in zip(Ra,Rb)),'first_answers_identical_in_first_40':same0}
    print(name,OUT[name])
C=V['critique']; Y=V['token-yoked generic doubt']
OUT['selected critique - token-yoked']={f'critique run {i+1}, token-yoked run {j+1}':round(sum(C[i])-sum(Y[j]),1) for i in (0,1) for j in (0,1)}
print(OUT['selected critique - token-yoked'])
json.dump(OUT,open(T+'run_variance_readout.json','w'),indent=1)
