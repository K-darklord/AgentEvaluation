#!/usr/bin/env python3
"""Independent re-computation of the main tests with a standard statistics library (SciPy), from the per-question
vectors written by selection_confirmation_readout.py and equal_token_readout.py.
 reached:  exact McNemar test = two-sided exact binomial test on the discordant pairs (scipy.stats.binomtest)
 selected: paired sign-flip permutation test (scipy.stats.permutation_test, permutation_type='samples', 10,000
           resamples, SciPy's own random generator) and percentile bootstrap over questions (scipy.stats.bootstrap)
Compares with the values in the read-out files and prints the largest deviations. The permutation p-values and the
bootstrap limits use different random numbers from the repository's scripts, so they agree up to Monte Carlo error.
Usage: python3 scripts/crosscheck_stats.py [directory with the json files]  (writes stats_crosscheck.json there)"""
import json,sys
import numpy as np
from scipy import stats
D=(sys.argv[1] if len(sys.argv)>1 else 'experiments/hle400/t3').rstrip('/')+'/'
J=lambda f: json.load(open(D+f))
vc=J('vectors_confirm.json'); ve=J('vectors_equal_token.json'); rc=J('selection_confirmation_readout.json'); re_=J('equal_token_readout.json')
rng=np.random.default_rng(20261117); OUT=[]
def mcn(x,y):
    x=np.array(x,bool); y=np.array(y,bool); b=int((x&~y).sum()); c=int((y&~x).sum())
    return b,c,(1.0 if b+c==0 else float(stats.binomtest(b,b+c,0.5).pvalue))
def sel(x,y):
    d=np.array(x,float)-np.array(y,float)
    p=stats.permutation_test((np.array(x,float),np.array(y,float)),lambda a,b,axis: np.sum(a-b,axis=axis),permutation_type='samples',n_resamples=10000,vectorized=True,alternative='two-sided',random_state=rng).pvalue
    ci=stats.bootstrap((d,),np.sum,n_resamples=10000,confidence_level=0.95,method='percentile',random_state=rng).confidence_interval
    return float(d.sum()),float(ci.low),float(ci.high),float(p)
def row(name,kind,ours,got): OUT.append({'test':name,'kind':kind,'repository':ours,'scipy':got})
# confirmation on 800 new questions
S=vc['selected']; R=vc['reached']; X=vc['selected_exact']
for name,a,b,key in (('S1 selected: critique - token-yoked','C2','A2PY','S1 selected: critique - token-yoked generic doubt'),('S2 selected: critique - reassuring','C2','A2','S2 selected: critique - reassuring')):
    o=rc['confirmatory'][key]; row(name,'selected',[o['diff'],o['lo'],o['hi'],o['p']],[round(v,4) for v in sel(S[a],S[b])])
for name,a,b,key in (('S1, exact matches only','C2','A2PY','S1'),('S2, exact matches only','C2','A2','S2')):
    o=rc['secondary']['exact_matches_only'][key]; row(name,'selected',[o['diff'],o['lo'],o['hi'],o['p']],[round(v,4) for v in sel(X[a],X[b])])
o=rc['R1 reached: critique - token-yoked generic doubt']; d=np.array(R['C2'],float)-np.array(R['A2PY'],float)
ci=stats.bootstrap((d,),np.sum,n_resamples=10000,confidence_level=0.90,method='percentile',random_state=rng).confidence_interval
row('R1 reached: critique - token-yoked (90% interval)','equivalence',[o['diff'],o['lo90'],o['hi90']],[float(d.sum()),float(ci.low),float(ci.high)])
for name,a,b,key in (('R1 discordant pairs','C2','A2PY',None),('reached: critique vs reassuring','C2','A2','critique vs reassuring'),('reached: critique vs generic doubt','C2','A2P','critique vs generic doubt'),('reached: token-yoked vs generic doubt','A2PY','A2P','token-yoked vs generic doubt')):
    o=rc['R1 reached: critique - token-yoked generic doubt']['mcnemar'] if key is None else rc['secondary']['reached'][key]
    row(name,'reached',[o['only_first'],o['only_second'],o['p']],[*mcn(R[a],R[b])[:2],round(mcn(R[a],R[b])[2],5)])
# first 400 questions at equal tokens (qwen) and MiniMax
q=ve['qwen']
for name,ctrl,key in (('E1 reached: critique vs question-only','question-only critique','E1 critique vs question-only'),('E2 reached: critique vs mismatched','mismatched critique','E2 critique vs mismatched'),('E3 reached: critique vs reassuring','reassuring','E3 critique vs reassuring'),('reached: critique vs token-yoked (qwen, 400)','generic doubt','(earlier Y1) critique vs generic doubt')):
    o=re_['qwen']['tests'][key]['equal_tokens']; g=mcn(q['critique']['reached'],q[ctrl]['reached']); row(name,'reached',[o['only_first'],o['only_second'],o['p']],[g[0],g[1],round(g[2],5)])
    o=re_['qwen']['tests'][key]['selected_equal_tokens']; row(name.replace('reached','selected'),'selected',[o['diff'],o['lo'],o['hi'],o['p']],[round(v,4) for v in sel(q['critique']['selected'],q[ctrl]['selected'])])
m=ve['minimax']
for name,a,b,key in (('MiniMax reached: critique vs token-yoked','critique','token-yoked generic doubt','Y1 critique vs token-yoked (all rounds)'),('MiniMax reached: token-yoked vs generic doubt','token-yoked generic doubt','generic doubt','Y2 token-yoked vs generic doubt')):
    o=re_['minimax']['tests'][key]; g=mcn(m[a]['reached'],m[b]['reached']); row(name,'reached',[o['only_first'],o['only_second'],o['p']],[g[0],g[1],round(g[2],5)])
o=re_['minimax']['selected']['critique - token-yoked']; row('MiniMax selected: critique - token-yoked','selected',[o['diff'],o['lo'],o['hi'],o['p']],[round(v,4) for v in sel(m['critique']['selected'],m['token-yoked generic doubt']['selected'])])
exact_ok=True; maxci=0.0; maxp=0.0
for r in OUT:
    a,b=r['repository'],r['scipy']
    if r['kind']=='reached': ok=(a[0]==b[0] and a[1]==b[1] and abs(a[2]-b[2])<1e-4); exact_ok&=ok; r['agree']=ok
    else:
        r['agree']=abs(a[0]-b[0])<0.051; exact_ok&=r['agree']; maxci=max(maxci,abs(a[1]-b[1]),abs(a[2]-b[2]))
        if len(a)>3: maxp=max(maxp,abs(a[3]-b[3]))
    print(f"{r['test']:52s} repository {a}  scipy {[round(v,4) if isinstance(v,float) else v for v in b]}  {'ok' if r['agree'] else 'DIFFERENT'}")
print(f"\npoint estimates, discordant counts and exact McNemar p-values identical: {exact_ok}")
print(f"largest difference in an interval limit (questions): {maxci:.1f}; largest difference in a permutation p-value: {maxp:.4f} (different random numbers)")
json.dump({'scipy_version':__import__('scipy').__version__,'identical_exact_quantities':bool(exact_ok),'max_interval_limit_difference':round(maxci,2),'max_permutation_p_difference':round(maxp,4),'rows':OUT},open(D+'stats_crosscheck.json','w'),indent=1)
