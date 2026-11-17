#!/usr/bin/env python3
"""Reach of the critique loop at the token budget of a placebo loop (docs/REVIEW_RESPONSE_PLAN.md, part A).
Post hoc, exploratory. Cost of a loop on a question = solver prompt + completion tokens of every round, plus
prompt + completion tokens of every critic call (MiniMax-M2.5: logged per round; deepseek, qwen: mean per call
from token_replay_summary.json). The first answer is always kept.
 per-question budget: the critique loop keeps the longest prefix of rounds whose cumulative cost does not
                      exceed the cost of the comparison loop on the same question;
 uniform cap:         the largest R such that rounds 0..R of the critique loop cost no more in total than the
                      comparison loop.
Also: the rate at which a correct answer first appears per feedback round, among questions not yet reached
(rounds 1-2, when nearly all loops are still running, and rounds 3-10, when only loops that have not stopped remain).
Reads frozen files only. Usage: python3 scripts/budget_matched_reach.py
(writes experiments/hle400/t3/budget_matched_reach.json)"""
import json,importlib.util,glob
from pathlib import Path
from math import comb
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
def pcm(f): m=json.load(open(f))['per_call_means']; return m['prompt_tokens']+m['completion_tokens']
CFG={'deepseek':('experiments/hle400/t3/is_correct_t3_sidecar_v3.json',{'A2':'experiments/hle400_A2/deepseek-v4-flash','A2P':'experiments/hle400_A2PRIME/deepseek-v4-flash-payg','C2':C2DS},pcm('experiments/hle400_C2/token_replay_summary.json')),
     'qwen':('experiments/hle400/t3/is_correct_t3_sidecar_rep.json',{a:f'experiments/rep200_{a}_qwen3.8-flash-payg/qwen3.8-flash-payg' for a in ('A2','A2P','C2')},pcm('experiments/rep200_C2_qwen3.8-flash-payg/token_replay_summary.json')),
     'minimax':('experiments/hle400/t3/is_correct_t3_sidecar_rep3.json',{a:f'experiments/rep3_{a}_minimax-m2.5/minimax-m2.5' for a in ('A2','A2P','C2')},None)}
def mcnemar(b,c):
    n=b+c
    return 1.0 if n==0 else min(1.0,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n)
OUT={}
for m,(sp,arms,critic_mean) in CFG.items():
    side=json.load(open(sp))['arms']; L={a:reco.load_jsonl(Path(d)/'loop_trajectories.jsonl') for a,d in arms.items()}
    tasks=sorted(L['C2'])
    def costs(a,t):
        out=[]
        for j,r in enumerate(L[a][t]['rounds']):
            c=(r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0)
            if a=='C2' and j>=1: c+= critic_mean if critic_mean is not None else (r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0)
            out.append(c)
        return out
    K={a:{t:reco.freeze_keys(L[a][t].get('gold_answer',''),L[a][t]) for t in tasks} for a in arms}
    def reach(a,t,n=None):
        # same rule as the main tables: a candidate is an answer identity; its last occurrence decides correctness
        keys=K[a][t]; s=side[a][t]; n=len(keys) if n is None else n
        return any(reco.last_key_correct(keys,s,k) for k in {k for k in keys[:n] if k is not None})
    cc={t:costs('C2',t) for t in tasks}; full_c2=sum(sum(v) for v in cc.values()); OUT[m]={'critique_full':{'reached':sum(reach('C2',t) for t in tasks),'tokens_M':round(full_c2/1e6,1),'rounds_per_q':round(sum(len(v) for v in cc.values())/400,2)}}
    print(f"{m}: critique loop, full: reached {OUT[m]['critique_full']['reached']}, {full_c2/1e6:.1f}M tokens, {OUT[m]['critique_full']['rounds_per_q']} rounds per question")
    for y in ('A2','A2P'):
        by={t:sum(costs(y,t)) for t in tasks}; tot_y=sum(by.values()); ry={t:reach(y,t) for t in tasks}
        keep={}
        for t in tasks:
            cum=0; n=1
            for j,c in enumerate(cc[t]):
                cum+=c
                if j==0 or cum<=by[t]: n=j+1
                else: break
            keep[t]=n
        used=sum(sum(cc[t][:keep[t]]) for t in tasks)
        rx={t:reach('C2',t,keep[t]) for t in tasks}; b=sum(rx[t] and not ry[t] for t in tasks); c=sum(ry[t] and not rx[t] for t in tasks)
        R=0
        while R+1<=10 and sum(sum(cc[t][:R+2]) for t in tasks)<=tot_y: R+=1
        ru={t:reach('C2',t,R+1) for t in tasks}; b2=sum(ru[t] and not ry[t] for t in tasks); c2=sum(ry[t] and not ru[t] for t in tasks); used2=sum(sum(cc[t][:R+1]) for t in tasks)
        fb=sum(reach('C2',t) and not ry[t] for t in tasks); fc=sum(ry[t] and not reach('C2',t) for t in tasks)
        OUT[m][y]={'comparison_reached':sum(ry.values()),'comparison_tokens_M':round(tot_y/1e6,1),'full':{'b':fb,'c':fc},
                   'per_question_budget':{'reached':sum(rx.values()),'b':b,'c':c,'p':round(mcnemar(b,c),4),'rounds_kept_per_q':round(sum(keep.values())/400,2),'tokens_M':round(used/1e6,1),'only_first_answer_kept':sum(v==1 for v in keep.values())},
                   'uniform_cap':{'feedback_rounds':R,'reached':sum(ru.values()),'b':b2,'c':c2,'p':round(mcnemar(b2,c2),4),'tokens_M':round(used2/1e6,1)}}
        o=OUT[m][y]; q=o['per_question_budget']; u=o['uniform_cap']
        print(f"  vs {y} (reached {o['comparison_reached']}, {o['comparison_tokens_M']}M; full critique {fb}/{fc})")
        print(f"     per-question budget: critique reached {q['reached']} with {q['tokens_M']}M, {q['rounds_kept_per_q']} rounds kept per question ({q['only_first_answer_kept']} questions keep only the first answer): {b}/{c} p={q['p']}")
        print(f"     uniform cap of {R} feedback round(s): critique reached {u['reached']} with {u['tokens_M']}M: {b2}/{c2} p={u['p']}")
    # rate at which a correct answer first appears, per feedback round, among questions not yet reached
    OUT[m]['first_reach_per_round']={}
    for a in ('A2','A2P','C2'):
        e=[0,0]; l=[0,0]
        for t in tasks:
            keys=K[a][t]; s=side[a][t]; ok={k:reco.last_key_correct(keys,s,k) for k in set(keys) if k is not None}; hit=False
            for j,k in enumerate(keys):
                good=k is not None and ok[k]
                if j>=1 and not hit:
                    bkt=e if j<=2 else l; bkt[0]+=1; bkt[1]+=good
                hit=hit or good
        OUT[m]['first_reach_per_round'][a]={'rounds_1_2':[e[1],e[0],round(e[1]/e[0],3)],'rounds_3_10':[l[1],l[0],round(l[1]/max(1,l[0]),3)]}
        print(f"  first reach per feedback round, {a}: rounds 1-2 {e[1]}/{e[0]}={e[1]/e[0]:.3f}; rounds 3-10 {l[1]}/{l[0]}={l[1]/max(1,l[0]):.3f}")
json.dump(OUT,open('experiments/hle400/t3/budget_matched_reach.json','w'),indent=1)
