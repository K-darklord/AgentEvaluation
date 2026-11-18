#!/usr/bin/env python3
"""qwen and deepseek on the same 800 new questions (descriptive; not among the tests fixed in advance):
difference between the two models in each selected-question contrast, and the mean of the two models.
Reads the per-question vectors written by the three read-out scripts.
Usage: python3 scripts/two_model_confirmation.py (writes experiments/hle400/t3/two_model_confirmation.json)"""
import json
from confirm_common import *
q=J('vectors_confirm.json')['selected']; qa=J('vectors_confirm_addendum.json')['selected']; d=J('vectors_confirm_ds.json')['selected']; q['A3']=qa['A3']
OUT={}
for name,b in (('critique - token-yoked generic doubt','A2PY'),('critique - reassuring','A2'),('critique - nine samples','A3'),('critique - generic doubt','A2P')):
    dq=[x-y for x,y in zip(q['C2'],q[b])]; dd=[x-y for x,y in zip(d['C2'],d[b])]; z=[0.0]*800
    OUT[name]={'qwen':round(sum(dq),1),'deepseek':round(sum(dd),1),'qwen_minus_deepseek':perm(dq,dd),'mean_of_two_models':perm([(x+y)/2 for x,y in zip(dq,dd)],z)}
    o=OUT[name]; print(f"{name:40s} qwen {o['qwen']:+6.1f} deepseek {o['deepseek']:+6.1f} | difference {o['qwen_minus_deepseek']['diff']:+6.1f} [{o['qwen_minus_deepseek']['lo']:+.1f},{o['qwen_minus_deepseek']['hi']:+.1f}] p={o['qwen_minus_deepseek']['p']:.4f} | mean {o['mean_of_two_models']['diff']:+6.1f} [{o['mean_of_two_models']['lo']:+.1f},{o['mean_of_two_models']['hi']:+.1f}] p={o['mean_of_two_models']['p']:.4f}")
json.dump(OUT,open(T+'two_model_confirmation.json','w'),indent=1)
