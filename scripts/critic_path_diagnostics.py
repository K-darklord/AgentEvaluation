#!/usr/bin/env python3
"""Exploratory diagnostics of the critique loop on the 800 new questions, for questions whose first answer is wrong
(the first answer is shared by all loops): how often a correct answer is reached, when, what happens after it is first
reached, and what the plurality answer is when it is not the correct one. Also the critic's output by correctness of the
answer it criticizes. Usage: python3 scripts/critic_path_diagnostics.py (writes experiments/hle400/t3/critic_path_diagnostics.json)"""
import json,sys,statistics
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,J,T
OUT={}
for model,sf in (('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json'),('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json')):
    side=J(sf)['arms']; OUT[model]={}
    for arm in ('A2','C2'):
        c=Counter(); first_round=[]; after=[]; nd={True:[],False:[]}; ctok={True:[],False:[]}
        for l in open(f'experiments/conf_{arm}_{model}/{model}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); k=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[arm][d['task_id']]; n=len(k)
            if arm=='C2':
                for i in range(1,n):   # critique received before round i concerns the answer of round i-1
                    r=d['rounds'][i]; cd=r.get('critic_direction')
                    if isinstance(cd,list) and not r.get('critic_fallback') and k[i-1] is not None:
                        ok=bool(sl[i-1]['c']); nd[ok].append(len(cd)); ctok[ok].append((r.get('critic_completion_tokens') or 0))
            if sl[0]['c'] or d['rounds'][0].get('finish_reason')=='length': continue
            c['first wrong']+=1
            cnt=Counter(x for x in k if x is not None)
            if not cnt: continue
            top=max(cnt.values()); tied=[x for x in cnt if cnt[x]==top]; okk={x:reco.last_key_correct(k,sl,x) for x in cnt}; sel=sum(okk[x] for x in tied)/len(tied)
            cor=[i for i in range(n) if k[i] is not None and okk[k[i]]]; sl=[{'c':(k[i] is not None and okk[k[i]])} for i in range(n)]
            if not cor: continue
            c['reached']+=1; c['selected']+=sel; j=cor[0]; first_round.append(j); rest=[i for i in range(j+1,n) if k[i] is not None]; after.append(len(rest))
            c['reached in the last round']+= (j==n-1)
            if rest:
                c['has later rounds']+=1; c['next round still correct']+=bool(sl[rest[0]]['c']); c['later rounds correct']+=sum(bool(sl[i]['c']) for i in rest); c['later rounds']+=len(rest)
            c['last answer correct']+=bool(sl[n-1]['c']) and k[n-1] is not None
            if sel<1:
                c['reached, not selected']+=1; c['plurality is the first answer']+= (k[0] in tied); c['votes of plurality']+=top; c['votes of correct']+=max(cnt[x] for x in cnt if okk[x]); c['candidates']+=len(cnt)
        R=c['reached']; ns=max(1,c['reached, not selected'])
        o={'first answer wrong':c['first wrong'],'reached':R,'selected':round(c['selected'],1),'selected per reached':round(c['selected']/max(1,R),3),'median round of first correct answer':statistics.median(first_round) if first_round else None,
           'first reached only in the last round':c['reached in the last round'],'next round still correct':round(c['next round still correct']/max(1,c['has later rounds']),3),'share of later rounds correct':round(c['later rounds correct']/max(1,c['later rounds']),3),
           'mean rounds after first correct':round(statistics.mean(after),2) if after else None,'last answer correct':c['last answer correct'],
           'reached but not selected':c['reached, not selected'],'of these: plurality is the first answer':round(c['plurality is the first answer']/ns,3),'of these: mean votes plurality / correct / candidates':[round(c['votes of plurality']/ns,2),round(c['votes of correct']/ns,2),round(c['candidates']/ns,2)]}
        if arm=='C2': o['critic']={('criticized answer correct' if ok else 'criticized answer incorrect'):{'rounds':len(nd[ok]),'mean doubts':round(statistics.mean(nd[ok]),2),'share with three doubts':round(sum(x>=3 for x in nd[ok])/len(nd[ok]),3),'mean critic output tokens':round(statistics.mean(ctok[ok]))} for ok in (True,False)}
        OUT[model][arm]=o; print(model,arm,json.dumps(o,ensure_ascii=False))
json.dump(OUT,open(T+'critic_path_diagnostics.json','w'),indent=1)
