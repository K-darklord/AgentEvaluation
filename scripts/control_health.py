#!/usr/bin/env python3
"""Run-health summary for the token-yoked and content controls (docs/TOKEN_YOKED_CONTROL_SPEC.md,
docs/CONTENT_CONTROLS_SPEC.md). Reads trajectories but NO correctness field: completion, failures, truncation,
rounds, tokens against budget, cap hits, feedback length, number of doubts, repeated labels, donor checks.
Usage: python3 scripts/control_health.py <dir> [<dir> ...]   (dir = experiments/<run>/<model>)"""
import json,sys,statistics as st
from collections import Counter
SAFE=('round','arm','finish_reason','api_failure','prompt_tokens','completion_tokens','reasoning_tokens','critic_direction','critic_prompt_tokens','critic_completion_tokens','donor_task_id','donor_round','feedback_chars','committed_answer','latency_ms')
def med(v): return round(st.median(v),1) if v else None
MAP=None
for d in sys.argv[1:]:
    rows=[]
    try:
        for l in open(d.rstrip('/')+'/loop_trajectories.jsonl'):
            if l.strip(): rows.append(json.loads(l))
    except FileNotFoundError:
        print(d,': no trajectory file yet'); continue
    T=[{'task_id':x['task_id'],'arm':x.get('arm'),'rounds':[{k:r.get(k) for k in SAFE} for r in x['rounds']],**{k:x.get(k) for k in ('yoke_budget','yoke_cum_tokens','yoke_hit_cap')}} for x in rows]
    n=len(T); print(f"\n== {d}: {n} questions written, arm {Counter(t['arm'] for t in T).most_common()}")
    if not n: continue
    fb=[len(t['rounds'])-1 for t in T]; allr=[r for t in T for r in t['rounds']]
    fail=sum(any(r.get('api_failure') for r in t['rounds']) for t in T)
    trunc=sum(r.get('finish_reason')=='length' for r in allr); nocommit=sum(r.get('committed_answer') in (None,'') for r in allr)
    tok=[sum((r.get('prompt_tokens') or 0)+(r.get('completion_tokens') or 0) for r in t['rounds']) for t in T]
    print(f"   questions with a failed interface call: {fail} | truncated rounds {trunc}/{len(allr)} | rounds without a committed answer {nocommit}/{len(allr)}")
    print(f"   feedback rounds per question: min {min(fb)} median {med(fb)} max {max(fb)} | solver tokens per question: median {med(tok)} total {sum(tok)/1e6:.2f}M | slowest round {max((r.get('latency_ms') or 0) for r in allr)/1000:.0f}s")
    if any(t.get('yoke_budget') for t in T):
        ratio=[t['yoke_cum_tokens']/t['yoke_budget'] for t in T if t.get('yoke_budget')]
        print(f"   token-yoked: spent/budget min {min(ratio):.2f} median {med(ratio)} max {max(ratio):.2f}; total spent/total budget {sum(t['yoke_cum_tokens'] for t in T)/sum(t['yoke_budget'] for t in T):.3f}; questions at the 30-round cap {sum(bool(t.get('yoke_hit_cap')) for t in T)}; under budget without cap {sum((t['yoke_cum_tokens']<t['yoke_budget']) and not t.get('yoke_hit_cap') for t in T)}")
    fr=[r for t in T for r in t['rounds'][1:]]
    ch=[r['feedback_chars'] for r in fr if r.get('feedback_chars')]; nd=Counter(len(r.get('critic_direction') or []) for r in fr)
    if ch: print(f"   feedback length (chars): median {med(ch)} mean {sum(ch)/len(ch):.0f} | doubts per round {dict(sorted(nd.items()))}")
    if any(r.get('donor_task_id') for r in fr):
        if MAP is None: MAP=json.load(open('experiments/hle400/t3/mismatch_map_qwen.json'))['donor']
        bad=sum(any(r.get('donor_task_id')!=MAP.get(t['task_id']) for r in t['rounds'][1:]) for t in T)
        print(f"   mismatched critique: questions whose donor differs from the map: {bad}; self-donor: {sum(any(r.get('donor_task_id')==t['task_id'] for r in t['rounds'][1:]) for t in T)}")
    if any(t['arm']=='C2Q' for t in T):
        rep=tot=same=pairs=0
        for t in T:
            seen=set(); prev=None
            for r in t['rounds'][1:]:
                names=[str(x.get('archetype_name') or '').strip().lower() for x in (r.get('critic_direction') or [])]
                for x in names: tot+=1; rep+= x in seen
                seen.update(names)
                txt=json.dumps(r.get('critic_direction'),sort_keys=True)
                if prev is not None: pairs+=1; same+= txt==prev
                prev=txt
        ct=[(r.get('critic_prompt_tokens') or 0)+(r.get('critic_completion_tokens') or 0) for r in fr]
        print(f"   question-only critic: labels repeating an earlier round {rep}/{tot}; consecutive rounds with identical critique {same}/{pairs}; critic tokens per call median {med([c for c in ct if c])} (logged on {sum(1 for c in ct if c)}/{len(ct)} calls)")
