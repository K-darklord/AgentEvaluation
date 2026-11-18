#!/usr/bin/env python3
"""Exploratory split of selected questions by the state of the first answer (correct, wrong, cut off), for the reassuring and critique loops on the 800 new questions; and the average single sample. Usage: python3 scripts/repair_loss_split.py ds|qw"""
import json,sys,importlib.util
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,J
def dec(model,sidefile,a3side=None):
    side=J(sidefile)['arms']; out={}
    for arm in ('A2','C2'):
        g=Counter()
        for l in open(f'experiments/conf_{arm}_{model}/{model}/loop_trajectories.jsonl'):
            if not l.strip(): continue
            d=json.loads(l); t=d['task_id']; keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[arm][t]
            cnt=Counter(k for k in keys if k is not None); sel=0.0
            if cnt:
                top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]; sel=sum(reco.last_key_correct(keys,sl,k) for k in tied)/len(tied)
            grp='first answer cut off' if d['rounds'][0].get('finish_reason')=='length' else ('first answer correct' if sl[0]['c'] else 'first answer wrong')
            g[grp,'n']+=1; g[grp,'sel']+=sel; g[grp,'first']+=bool(sl[0]['c']); g[grp,'rounds']+=len(keys); g[grp,'trunc_rounds']+=sum(r.get('finish_reason')=='length' for r in d['rounds'])
        out[arm]={k:{'n':g[k,'n'],'selected':round(g[k,'sel'],1),'gain over first answer':round(g[k,'sel']-g[k,'first'],1),'rounds per q':round(g[k,'rounds']/max(1,g[k,'n']),1)} for k in ('first answer correct','first answer wrong','first answer cut off')}
    s=a3side or side; tot=0; n=0; byT=Counter()
    for l in open(f'experiments/conf_A3_{model}/{model}/loop_trajectories.jsonl'):
        if not l.strip(): continue
        d=json.loads(l); sl=s['A3'][d['task_id']]
        for i in range(1,10): tot+=bool(sl[i]['c']); n+=1; byT[d['rounds'][i].get('finish_reason')=='length']+=1
    out['average single sample (T=0.7) correct, of 800']=round(tot/9,1); out['samples cut off']=round(byT[True]/n,3)
    return out
m=sys.argv[1]
if m=='ds': print(json.dumps(dec('deepseek-v4-flash-payg','is_correct_t3_sidecar_confirm_ds.json'),indent=1))
else:
    print(json.dumps(dec('qwen3.8-flash-payg','is_correct_t3_sidecar_confirm.json',J('is_correct_t3_sidecar_confirm2.json')['arms']),indent=1))
