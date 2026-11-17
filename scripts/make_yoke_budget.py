#!/usr/bin/env python3
"""Token budget per question for a token-yoked generic-doubt control (docs/TOKEN_YOKED_CONTROL_SPEC.md and the
specifications that reuse it). Budget of a question = what the critique loop spent on it: prompt + completion tokens
of every solver round, plus the critic call of every feedback round. Critic tokens are taken from the trajectory when
they were logged per round (critic_prompt_tokens + critic_completion_tokens); otherwise each call is costed at the
mean of the replayed calls given with --critic-mean-from (a token_replay_summary.json).
Reads trajectories of the critique loop only; contains no correctness information.
Usage: python3 scripts/make_yoke_budget.py                      (qwen, original 400 questions; default paths)
       python3 scripts/make_yoke_budget.py --c2 <dir with loop_trajectories.jsonl> --out <json> [--critic-mean-from <json>] [--model <name>]"""
import json,argparse
ap=argparse.ArgumentParser()
ap.add_argument('--c2',default='experiments/rep200_C2_qwen3.8-flash-payg/qwen3.8-flash-payg')
ap.add_argument('--out',default='experiments/hle400/t3/yoke_budget_qwen.json')
ap.add_argument('--critic-mean-from',default='experiments/rep200_C2_qwen3.8-flash-payg/token_replay_summary.json')
ap.add_argument('--model',default='qwen3.8-flash-payg')
a=ap.parse_args()
mean=None
if a.critic_mean_from:
    m=json.load(open(a.critic_mean_from))['per_call_means']; mean=m['prompt_tokens']+m['completion_tokens']
B={}; R={}; logged=fallback=0
for l in open(a.c2.rstrip('/')+'/loop_trajectories.jsonl'):
    if not l.strip(): continue
    d=json.loads(l); rs=d['rounds']; tot=sum((r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0) for r in rs)
    for r in rs[1:]:
        c=(r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0)
        if 'critic_prompt_tokens' in r: tot+=c; logged+=1
        else:
            assert mean is not None,'critic tokens not logged and no --critic-mean-from given'
            tot+=mean; fallback+=1
    B[d['task_id']]=round(tot); R[d['task_id']]=len(rs)-1
json.dump({'model':a.model,'source':a.c2,'critic_tokens_per_call':round(mean,2) if mean else None,'critic_calls_logged':logged,'critic_calls_costed_at_mean':fallback,'unit':'prompt + completion tokens','budget':B,'critique_feedback_rounds':R},open(a.out,'w'),indent=0)
v=sorted(B.values()); print(f"{len(B)} questions; total {sum(v)/1e6:.1f}M; per question min {v[0]} median {v[len(v)//2]} max {v[-1]}; critic calls logged {logged}, costed at the mean {fallback}")
