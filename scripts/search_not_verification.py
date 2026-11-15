#!/usr/bin/env python3
"""Exploratory (not pre-registered): is the selection gain of one condition over another explained by reach alone?
For each pair (X,Y) and model: conversion = selected/reach; decomposition of selected(X)-selected(Y) into questions
reached by both, by X only, by Y only; own last answer vs own vote. Reads frozen per-question scores only.
Usage: python3 scripts/search_not_verification.py  (writes experiments/hle400/t3/search_not_verification.json)"""
import json,importlib.util,io,contextlib,random
two=json.load(open('experiments/hle400/t3/two_model_scores.json'))
spec=importlib.util.spec_from_file_location('tm','scripts/third_model_readout.py'); tm=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(tm)
MS={'deepseek':two['deepseek'],'qwen':two['qwen'],'minimax':tm.S}; N=range(400); OUT={}
def boot(f,n=2000,seed=0):
    r=random.Random(seed); v=sorted(f([r.randrange(400) for _ in N]) for _ in range(n)); return round(v[50],3),round(v[1949],3)
def perm(d,n=10000):
    obs=sum(d); r=random.Random(1); nz=[v for v in d if v]; ge=sum(abs(sum(v if r.random()<.5 else -v for v in nz))>=abs(obs)-1e-9 for _ in range(n))
    bs=sorted(sum(d[r.randrange(len(d))] for _ in range(len(d))) for _ in range(2000)) if d else [0]*2000
    return dict(n=len(d),diff=round(obs,1),lo=round(bs[50],1),hi=round(bs[1949],1),p=round((ge+1)/(n+1),4))
print('== conversion = selected / reach')
for m,S in MS.items():
    OUT[m]={'conversion':{}}
    for a in ('A2','A2P','C2','A3'):
        f=lambda idx,a=a: sum(S[a]['sel'][i] for i in idx)/max(1,sum(S[a]['ceil'][i] for i in idx)); OUT[m]['conversion'][a]=[round(f(N),4),*boot(f)]
    f=lambda idx: sum(S['C2']['sel'][i] for i in idx)/max(1,sum(S['C2']['ceil'][i] for i in idx))-sum(S['A2']['sel'][i] for i in idx)/max(1,sum(S['A2']['ceil'][i] for i in idx))
    OUT[m]['conversion']['C2-A2']=[round(f(N),4),*boot(f)]
    print(m,OUT[m]['conversion'])
print('\n== decomposition by reach status')
for x,y in (('C2','A2'),('C2','A2P'),('C2','A3'),('A2P','A2')):
    pool=[]
    for m,S in MS.items():
        both=[i for i in N if S[x]['ceil'][i] and S[y]['ceil'][i]]; xo=[i for i in N if S[x]['ceil'][i] and not S[y]['ceil'][i]]; yo=[i for i in N if S[y]['ceil'][i] and not S[x]['ceil'][i]]
        sx=lambda I,a: round(sum(S[a]['sel'][i] for i in I),1); d=[S[x]['sel'][i]-S[y]['sel'][i] for i in both]; pool+=d
        r=dict(both_n=len(both),both_x=sx(both,x),both_y=sx(both,y),both_test=perm(d),x_only_n=len(xo),x_only_selected=sx(xo,x),y_only_n=len(yo),y_only_selected=sx(yo,y),total=round(sx(N,x)-sx(N,y),1))
        OUT[m][f'{x}-{y}']=r; print(f"{x}-{y} {m}: both n={r['both_n']} {x} {r['both_x']} vs {y} {r['both_y']} diff {r['both_test']['diff']:+} [{r['both_test']['lo']},{r['both_test']['hi']}] p={r['both_test']['p']} | {x}-only n={len(xo)} sel {r['x_only_selected']} | {y}-only n={len(yo)} sel {r['y_only_selected']} | total {r['total']:+}")
    OUT[f'pooled {x}-{y} both-reached']=perm(pool); print('   pooled both-reached:',OUT[f'pooled {x}-{y} both-reached'])
print('\n== own last answer vs own vote (final, selected)')
for m,S in MS.items():
    OUT[m]['final_vs_selected']={a:[sum(S[a]['fin']),round(sum(S[a]['sel']),1),perm([S[a]['fin'][i]-S[a]['sel'][i] for i in N])] for a in ('A2','A2P','C2')}
    print(m,{a:(v[0],v[1],v[2]['diff'],v[2]['p']) for a,v in OUT[m]['final_vs_selected'].items()})
OUT['pooled final-selected C2']=perm([sum(S['C2']['fin'][i]-S['C2']['sel'][i] for S in MS.values()) for i in N]); print('pooled FC final - selected',OUT['pooled final-selected C2'])
json.dump(OUT,open('experiments/hle400/t3/search_not_verification.json','w'),indent=1)
