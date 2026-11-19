#!/usr/bin/env python3
"""Supplementary read-outs for the comparison at equal tokens (critique loop against token-matched independent samples),
added after an external-style review of draft v17. All descriptive; the confirmatory results stand as read out.
For each cell (qwen HLE, deepseek HLE, qwen BBEH-hard):
 a. last answer of the critique loop against the plurality of the samples;
 b. critique loop without its first answer (rounds 1..last), since the samples exclude the T=0 first answer;
 c. samples counted only while their cumulative tokens stay within the budget (at least one sample);
 d. bound on vote splitting: all candidates scored correct are merged into one before the vote, in both methods;
 e. share of answers cut off at the token limit, per method;
 f. sequential depth: feedback rounds per question of the loop (samples can be drawn in parallel);
 g. BBEH: the difference by task.
Usage: python3 scripts/equal_token_supplement.py <qwen|deepseek|bbeh>  (writes experiments/hle400/t3/equal_token_supplement_<cell>.json)"""
import json,sys
from collections import Counter
sys.path.insert(0,'scripts')
from confirm_common import reco,T,J,toks,perm,mcn,order
cell=sys.argv[1]; Q='qwen3.8-flash-payg'; D='deepseek-v4-flash-payg'
if cell=='bbeh':
    bs=J('bbeh_sidecar.json')['arms']; be=J('bbeh_sidecar_et.json')['arms']; B=J('yoke_budget_bbeh_hard.json')['budget']
    P={'C2':f'experiments/b1_C2_hard_{Q}/{Q}','A3Y':f'experiments/b1_A3Y_hard_{Q}/{Q}','A2PY':f'experiments/b1_A2PY_hard_{Q}/{Q}'}; S={'C2':bs['C2'],'A3Y':be['A3Y'],'A2PY':bs['A2PY']}
    keyf=lambda d,sl:[None if x['k'] is None else json.dumps(x['k'],sort_keys=True) for x in sl]
else:
    M=Q if cell=='qwen' else D; a,b,bud=(('is_correct_t3_sidecar_confirm.json','is_correct_t3_sidecar_confirm3.json','yoke_budget_qwen_confirm.json') if cell=='qwen' else ('is_correct_t3_sidecar_confirm_ds.json','is_correct_t3_sidecar_confirm_ds2.json','yoke_budget_deepseek_confirm.json'))
    L=J(a)['arms']; N=J(b)['arms']; B=J(bud)['budget']
    P={k:f'experiments/conf_{k}_{M}/{M}' for k in ('C2','A3Y','A2PY')}; S={'C2':L['C2'],'A3Y':N['A3Y'],'A2PY':L['A2PY']}
    keyf=lambda d,sl:reco.freeze_keys(d.get('gold_answer',''),d)
def vote(keys,ver,idx,merge=False):
    """expected score of the plurality over the answers at positions idx; candidate correct by its last occurrence overall"""
    ks=[keys[i] for i in idx if keys[i] is not None]
    if not ks: return 0.0,0
    ok={k:bool(ver[max(j for j,x in enumerate(keys) if x==k)]) for k in set(ks)}; cnt=Counter(ks)
    if merge:
        c=sum(n for k,n in cnt.items() if ok[k]); cnt=Counter({k:n for k,n in cnt.items() if not ok[k]})
        if c: cnt['__correct__']=c; ok['__correct__']=True
    top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
    return sum(ok[k] for k in tied)/len(tied), int(any(ok.values()))
R={}
for arm,samples in (('C2',False),('A2PY',False),('A3Y',True)):
    out={}
    for l in open(P[arm]+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not l.strip(): continue
        d=json.loads(l); t=d['task_id']; sl=S[arm][t]; keys=keyf(d,sl); ver=[bool(x['c']) for x in sl]; rr=d['rounds']; n=len(keys); assert n==len(rr)
        full=list(range(1,n)) if samples else list(range(n)); r={}
        r['sel'],r['rea']=vote(keys,ver,full); r['sel_merged'],_=vote(keys,ver,full,merge=True)
        r['trunc']=sum(x.get('finish_reason')=='length' for x in rr[1:]); r['answers']=n-1; r['rounds']=n-1
        if samples:
            cum=0; keep=[]
            for i in range(1,n):
                cum+=toks(rr[i])
                if cum<=B[t] or not keep: keep.append(i)
                else: break
            r['sel_within'],r['rea_within']=vote(keys,ver,keep); r['n_within']=len(keep)
        else:
            r['last']=float(ver[-1]); r['sel_nofirst'],r['rea_nofirst']=vote(keys,ver,list(range(1,n)) if n>1 else [0])
        out[t]=r
    R[arm]=out
ts=sorted(R['C2']) if cell=='bbeh' else order(R['C2']); assert len(ts)==800 and sorted(R['A3Y'])==sorted(ts)
V=lambda a,k:[R[a][t][k] for t in ts]; s=lambda a,k:round(sum(V(a,k)),1)
O={'cell':cell,'as_read_out':{'critique_selected':s('C2','sel'),'samples_selected':s('A3Y','sel'),'difference':perm(V('C2','sel'),V('A3Y','sel'))},
 'a_last_answer':{'critique_last':s('C2','last'),'last - samples plurality':perm(V('C2','last'),V('A3Y','sel')),'last - own plurality':perm(V('C2','last'),V('C2','sel')),'token_yoked_last':s('A2PY','last')},
 'b_loop_without_first_answer':{'critique_selected':s('C2','sel_nofirst'),'critique_reached':s('C2','rea_nofirst'),'difference':perm(V('C2','sel_nofirst'),V('A3Y','sel'))},
 'c_samples_within_budget':{'samples_per_q':round(sum(V('A3Y','n_within'))/800,2),'samples_selected':s('A3Y','sel_within'),'samples_reached':s('A3Y','rea_within'),'critique_reached':s('C2','rea'),
    'selected difference':perm(V('C2','sel'),V('A3Y','sel_within')),'reached difference':perm(V('C2','rea'),V('A3Y','rea_within')),'reached mcnemar':mcn(V('C2','rea'),V('A3Y','rea_within'))},
 'd_vote_splitting_bound':{'critique_selected':s('C2','sel_merged'),'samples_selected':s('A3Y','sel_merged'),'difference':perm(V('C2','sel_merged'),V('A3Y','sel_merged')),'token_yoked_selected':s('A2PY','sel_merged')},
 'e_cut_off_share':{a:round(sum(V(a,'trunc'))/max(1,sum(V(a,'answers'))),4) for a in R},
 'f_sequential_depth':{'critique_feedback_rounds_per_q':round(sum(V('C2','rounds'))/800,2),'token_yoked_rounds_per_q':round(sum(V('A2PY','rounds'))/800,2),'samples_per_q':round(sum(V('A3Y','answers'))/800,2)}}
if cell=='bbeh':
    O['g_by_task']={}
    for task in sorted({t.rsplit('_',1)[0] for t in ts}):
        I=[t for t in ts if t.rsplit('_',1)[0]==task]; O['g_by_task'][task.replace('bbeh_b1_','')]={'n':len(I),'critique':round(sum(R['C2'][t]['sel'] for t in I),1),'samples':round(sum(R['A3Y'][t]['sel'] for t in I),1),'diff':round(sum(R['C2'][t]['sel']-R['A3Y'][t]['sel'] for t in I),1)}
    O['g_tasks_with_critique_ahead']=sum(v['diff']>0 for v in O['g_by_task'].values())
json.dump(O,open(T+f'equal_token_supplement_{cell}.json','w'),indent=1)
for k,v in O.items(): print(k,json.dumps(v)[:700])
