#!/usr/bin/env python3
"""Read-only audit: impact of the 300 s streaming wall-clock timeout on existing runs.

Reads only timing/token/answer-text fields from loop_trajectories.jsonl and usc_result.jsonl.
Never reads is_correct, sidecars, or any correctness file. Writes only
experiments/hle400/t3/wall_timeout_flags.json (unless --no-write).

Usage: python3 wall_timeout_audit.py [--repo ~/PycharmProjects/AgentEvaluation] [--no-write]
"""
import argparse, json, os, re, glob, statistics as st
from collections import Counter

CAP = 16384          # thinking budget used by every arm
WALL = 300.0         # seconds; config default LLM_STREAM_WALL_TIMEOUT
READ = 60.0          # seconds; config default LLM_STREAM_READ_TIMEOUT

HLE = {
 'qwen': {'A':'conf_A_qwen3.8-flash-payg','C2':'conf_C2_qwen3.8-flash-payg',
          'A2':'conf_A2_qwen3.8-flash-payg','A2PY':'conf_A2PY_qwen3.8-flash-payg',
          'A3':'conf_A3_qwen3.8-flash-payg','A3Y':'conf_A3Y_qwen3.8-flash-payg','USC':None},
 'deepseek': {'A':'conf_A_deepseek-v4-flash-payg','C2':'conf_C2_deepseek-v4-flash-payg',
              'A2':'conf_A2_deepseek-v4-flash-payg','A2PY':'conf_A2PY_deepseek-v4-flash-payg',
              'A3':'conf_A3_deepseek-v4-flash-payg','A3Y':'conf_A3Y_deepseek-v4-flash-payg','USC':None},
}
BBEH = {'qwen': {c: f'b1_{c}_hard_qwen3.8-flash-payg' for c in
                 ('A','C2','A2','A2P','A2PY','A3','A3Y','GNM','GKI','GT7')}}

def load(repo, d):
    p = glob.glob(os.path.join(repo, 'experiments', d, '*', 'loop_trajectories.jsonl'))
    if not p: return None
    return [json.loads(l) for l in open(p[0], encoding='utf-8') if l.strip()]

def calls(items):
    out=[]
    for it in items:
        for r in it['rounds']:
            out.append(dict(task=it['task_id'], round=r.get('round'), latency=r.get('latency_ms'),
                            completion=r.get('completion_tokens') or 0, reasoning=r.get('reasoning_tokens') or 0,
                            finish=r.get('finish_reason'), api=bool(r.get('api_failure')),
                            answer=str(r.get('committed_answer') or ''),
                            critic_reasoning=r.get('critic_reasoning_tokens') or 0,
                            critic_completion=r.get('critic_completion_tokens') or 0))
    return out

def speed(cs):
    sp=[c['completion']/(c['latency']/1000.0) for c in cs
        if c['latency'] and 0<c['latency']<=250000 and c['completion']>2000]
    if len(sp)<10: return None,len(sp)
    sp.sort(); return sp[int(0.05*(len(sp)-1))],len(sp)

def imp(c,s):
    if not s or not c['latency'] or c['completion']<=0: return None
    return (c['latency']/1000.0) > (c['completion']/s + 30.0)

def agg(x):
    if not x: return None
    return dict(n=len(x), mean_completion=round(st.mean(c['completion'] for c in x),1),
                mean_answer_chars=round(st.mean(len(c['answer']) for c in x),1),
                finish=dict(Counter(c['finish'] for c in x)))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',default=os.path.expanduser('~/PycharmProjects/AgentEvaluation'))
    ap.add_argument('--no-write',action='store_true'); a=ap.parse_args()

    pat=re.compile(r'(LLM_STREAM_WALL_TIMEOUT|LLM_STREAM_READ_TIMEOUT|AGENTEVALUATION_SOLVE_TIMEOUT)')
    env_hits={}
    for p in glob.glob(os.path.join(a.repo,'scripts','*.sh'))+glob.glob(os.path.join(a.repo,'*.sh'))+glob.glob(os.path.join(a.repo,'scripts','*.log')):
        try: t=open(p,encoding='utf-8',errors='ignore').read()
        except Exception: continue
        if pat.search(t): env_hits[os.path.relpath(p,a.repo)]=sorted(set(pat.findall(t)))
    for p in glob.glob(os.path.join(a.repo,'docs','*.md')):
        try: t=open(p,encoding='utf-8',errors='ignore').read()
        except Exception: continue
        if pat.search(t): env_hits[os.path.relpath(p,a.repo)]=sorted(set(pat.findall(t)))
    hist=[]
    for h in ('~/.zsh_history','~/.bash_history'):
        p=os.path.expanduser(h)
        if os.path.exists(p):
            for line in open(p,encoding='utf-8',errors='ignore'):
                if pat.search(line): hist.append(line.strip()[:200])

    rows={}; flags={}; content={}
    for scope,spec in (('HLE-800',HLE),('BBEH-800',BBEH)):
        for model,conds in spec.items():
            for cond,d in conds.items():
                if d is None: continue
                items=load(a.repo,d)
                if items is None:
                    rows[f'{scope} {model} {cond}']={'missing':True}; continue
                cs=calls(items); s,ncal=speed(cs)
                _sp=[c['completion']/(c['latency']/1000.0) for c in cs if c['latency'] and 0<c['latency']<=250000 and c['completion']>2000]
                med=st.median(_sp) if _sp else None
                capped=[c for c in cs if c['reasoning']>=CAP]
                r=dict(items=len(items),calls=len(cs),capped=len(capped),
                       over300=sum(1 for c in cs if c['latency'] and c['latency']>WALL*1000),
                       impossible=sum(1 for c in capped if imp(c,s)),
                       api_fail=sum(1 for c in cs if c['api']),
                       critic_calls=sum(1 for c in cs if c['critic_completion']>0),
                       critic_capped=sum(1 for c in cs if c['critic_reasoning']>=CAP),
                       impossible_med=sum(1 for c in capped if med and imp(c,med)),
                       speed=round(s,1) if s else None, speed_med=round(med,1) if med else None, calib=ncal)
                rows[f'{scope} {model} {cond}']=r
                content[f'{scope} {model} {cond}']={'retry_suspected':agg([c for c in capped if imp(c,s) is True]),
                                                    'no_retry_sign':agg([c for c in capped if imp(c,s) is False])}
                f={}
                for c in cs:
                    x=f.setdefault(c['task'],dict(impossible=False,impossible_med=False,rounds=[],api_fail=False))
                    if imp(c,s) is True: x['impossible']=True; x['rounds'].append(c['round'])
                    if med and imp(c,med): x['impossible_med']=True
                    if c['api']: x['api_fail']=True
                flags[f'{scope}|{model}|{cond}']=f

    # C: whole-question reruns, only evidence on disk
    backups=[os.path.relpath(p,a.repo) for p in glob.glob(os.path.join(a.repo,'experiments','**','*bak_apifail*'),recursive=True)]
    scope_dirs=set()
    for spec in (HLE,BBEH):
        for conds in spec.values():
            scope_dirs |= {d for d in conds.values() if d}
    in_scope=[b for b in backups if any(d in b for d in scope_dirs)]
    rerun_scripts=sorted(os.path.relpath(p,a.repo) for p in glob.glob(os.path.join(a.repo,'scripts','*rerun*')))

    # USC
    usc=None
    p=os.path.join(a.repo,'experiments','hle400','t3','usc_result.jsonl')
    if os.path.exists(p):
        rs=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
        usc=dict(rows=len(rs),latency_recorded=False,
                 capped=sum(1 for r in rs if (r.get('reasoning_tokens') or 0)>=CAP),
                 fields=sorted({k for r in rs for k in r}))

    out=dict(config=dict(wall=WALL,read=READ,cap=CAP),
             A=dict(env_hits=env_hits,shell_history=hist[:20],rerun_scripts=rerun_scripts),
             B=rows,C=dict(backups_total=len(backups),in_scope=in_scope,api_fail_by_condition={k:v['api_fail'] for k,v in rows.items() if 'api_fail' in v}),
             D=content,USC=usc)
    if not a.no_write:
        dst=os.path.join(a.repo,'experiments','hle400','t3','wall_timeout_flags.json')
        flags['_definitions']={'impossible':'latency > completion/speed_5th_percentile + 30 (spec)',
                               'impossible_med':'same with median speed (sensitivity)',
                               'rounds':'round indices flagged by the spec definition',
                               'api_fail':'rounds recorded as api_failure'}
        json.dump(flags,open(dst,'w'),ensure_ascii=False); print('wrote',dst)
    print(json.dumps(out,ensure_ascii=False,indent=1))

if __name__=='__main__':
    main()
