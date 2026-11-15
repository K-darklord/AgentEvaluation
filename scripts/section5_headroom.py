"""Section 5 descriptives on the frozen v3 bank-critic (C3) trajectories: reach, recency-rule mode, headroom split,
switch counts, coverage of each judge, and the base rate used in the text. Same definitions as judge_conditional_test.py.
Usage: python3 scripts/section5_headroom.py"""
import json, importlib.util
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reco',ROOT/'scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
T3=ROOT/'experiments/hle400/t3'
side=json.load(open(T3/'is_correct_t3_sidecar_v3.json'))['arms']['C3']
loop=reco.load_jsonl(ROOT/'experiments/hle400_C3/deepseek-v4-flash/loop_trajectories.jsonl')
ev=reco.load_jsonl(T3/'c3_rubric_ce.jsonl')
QV=set((r['task_id'],int(r['from_r']),int(r['to_r'])) for r in map(json.loads,open(T3/'qcut_result.jsonl')))
JC=set((r['task_id'],r['from_r'],r['to_r']) for r in map(json.loads,open(T3/'judge_c_verdicts_dashscope.jsonl')))
reach=mode=0; split=Counter(); sw=Counter(); nsw=0; cov=Counter(); multi=0; multi_help=0; ties=0; tie_has=0; tie_rec=0
for t,lp in loop.items():
    keys=reco.freeze_keys(lp.get('gold_answer',''),lp); sl=side[t]
    cnt=Counter(k for k in keys if k is not None)
    if not cnt: continue
    corr={k:reco.last_key_correct(keys,sl,k) for k in cnt}; mk=reco.freeze_mode_key(keys)
    r=any(corr.values()); m=bool(corr[mk]); reach+=r; mode+=m
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    if len(tied)>1:
        ties+=1
        if any(corr[k] for k in tied): tie_has+=1; tie_rec+=m
    if len(cnt)>1:
        multi+=1; multi_help+=(r and not m)
    if r and not m:
        best=max(cnt[k] for k in cnt if corr[k]); gap=top-best
        split['tie' if gap==0 else 'one vote' if gap==1 else 'more']+=1
    for a,b in reco.freeze_switches(keys):
        nsw+=1; oc,nc=bool(sl[a]['c']),bool(sl[b]['c']); sw[('R' if oc else 'W')+'->'+('R' if nc else 'W')]+=1
        cov['R']+=(f"{a}->{b}" in ((ev.get(t) or {}).get('per_switch',{}))); cov['R+']+=((t,a,b) in QV); cov['C']+=((t,a,b) in JC)
out=dict(reach=reach,mode=mode,headroom=reach-mode,split=dict(split),switches=nsw,switch_types=dict(sw),judged=dict(cov),
         questions_with_more_than_one_candidate=multi,of_which_overturning_helps=multi_help,tied_questions=ties,tied_with_correct=tie_has,recency_recovers=tie_rec)
print(json.dumps(out,indent=1)); json.dump(out,open(T3/'section5_headroom.json','w'),indent=1)
