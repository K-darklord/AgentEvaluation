#!/usr/bin/env python3
"""Budget per question for a control that is continued from an existing run and matched to the critique loop
in TOTAL tokens (docs/EQUAL_TOKEN_CONTROLS_SPEC.md v3, question-only critique). Some questions of the existing
run already spent more than the critique loop did on them; those are left as they are. Every other question is
topped up by the same fraction f of its shortfall, with f chosen so that the total equals the critique loop's
total: budget_q = spent_q + f * (critique_q - spent_q).
Spent = solver prompt + completion tokens of every round, plus logged critic prompt + completion tokens.
Reads token counts only; no correctness information.
Usage: python3 scripts/make_resume_budget_total.py   (writes experiments/hle400/t3/yoke_budget_qwen_c2qy.json)"""
import json
Q='qwen3.8-flash-payg'
B=json.load(open('experiments/hle400/t3/yoke_budget_qwen.json'))['budget']
spent={}
for l in open(f'experiments/ctrl_C2Q_{Q}/{Q}/loop_trajectories.jsonl'):
    d=json.loads(l); spent[d['task_id']]=sum((r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0) for r in d['rounds'])+sum((r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0) for r in d['rounds'][1:])
assert set(spent)==set(B)
short={t:B[t]-spent[t] for t in B if spent[t]<B[t]}
f=(sum(B.values())-sum(spent.values()))/sum(short.values())
assert 0<f<1
out={t:(round(spent[t]+f*short[t]) if t in short else spent[t]) for t in B}
json.dump({'model':Q,'rule':'total matched to the critique loop; under-budget questions topped up by the fraction f of their shortfall','f':round(f,4),'critique_total':sum(B.values()),'spent_total':sum(spent.values()),'questions_topped_up':len(short),'unit':'prompt + completion tokens, solver and critic','budget':out},open('experiments/hle400/t3/yoke_budget_qwen_c2qy.json','w'),indent=0)
print(f"f = {f:.3f}; {len(short)} questions topped up, {len(B)-len(short)} left as they are; already spent {sum(spent.values())/1e6:.2f}M, to add {sum(out.values())/1e6-sum(spent.values())/1e6:.2f}M, total {sum(out.values())/1e6:.2f}M against {sum(B.values())/1e6:.2f}M for the critique loop")
