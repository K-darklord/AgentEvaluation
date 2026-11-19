#!/usr/bin/env python3
"""Add the supplementary read-outs of scripts/equal_token_supplement.py (draft v17b) to docs/consistency_manifest.json.
Usage: python3 scripts/build_manifest_v17b.py && python3 scripts/check_manifest.py"""
import json
M=json.load(open('docs/consistency_manifest.json')); M['numeric_facts']=[f for f in M['numeric_facts'] if not f['id'].startswith('supp_')]
T='experiments/hle400/t3/'; N=[]
for c in ('qwen','deepseek','bbeh'):
    f=T+f'equal_token_supplement_{c}.json'; o=json.load(open(f))
    for sec,key in (('a_last_answer','last - samples plurality'),('b_loop_without_first_answer','difference'),('c_samples_within_budget','selected difference'),('c_samples_within_budget','reached difference'),('d_vote_splitting_bound','difference')):
        for q in ('diff','lo','hi'): N.append({'id':f'supp_{c}_{sec[:1]}_{key[:8]}_{q}','value':o[sec][key][q],'paper':'v17b','json':[f,sec,key,q]})
    N.append({'id':f'supp_{c}_last','value':o['a_last_answer']['critique_last'],'paper':'v17b','json':[f,'a_last_answer','critique_last']})
    N.append({'id':f'supp_{c}_depth','value':o['f_sequential_depth']['critique_feedback_rounds_per_q'],'paper':'v17b','json':[f,'f_sequential_depth','critique_feedback_rounds_per_q']})
    N.append({'id':f'supp_{c}_within_n','value':o['c_samples_within_budget']['samples_per_q'],'paper':'v17b','json':[f,'c_samples_within_budget','samples_per_q']})
N.append({'id':'supp_strings','value':None,'paper':'v17b','tex':['\\quad within the budget & $+28.5$ & $+26.4$ & $+52.5$','\\quad no first answer & $+29.1$ & $+26.5$ & $+39.7$','\\quad last answer & $+27.0$ & $+25.0$ & $+0.5$','\\quad merged & $+9.3$ & $+19.2$ & $+27.3$',
 '\\quad within the budget & $-17$ & $-8$ & $+3$','($-17$, $-8$ and $+3$, no difference significant)','grows to 28.5, 26.4 and 52.5','(29.1, 26.5 and 39.7)','(the last answer is ahead of the samples by 27.0 and 25.0)','correct on 357 questions against 390.5',
 '19.2 (\\ci{2.8}{36.5}) on \\ds{} and 27.3 (\\ci{7.2}{49.4}) on BBEH, and 9.3 (\\ci{-13.3}{31.5}) on \\qw{} with HLE','selects 256.2 questions against 254.2','(16.7, 15.1 and 19.4 per question)','6.3, 6.0 and 6.9 rounds of feedback']})
M['numeric_facts']+=N; M['paper_version']='v17b draft'
json.dump(M,open('docs/consistency_manifest.json','w'),indent=1,ensure_ascii=False); print('added',len(N))
