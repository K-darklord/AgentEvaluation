#!/usr/bin/env python3
"""Update docs/consistency_manifest.json for paper v17: drop text strings of v16 that the rewrite removed (their data
checks are kept) and add the numbers of the new parts, each tied to a frozen read-out and to a string in main.tex.
Usage: python3 scripts/build_manifest_v17.py && python3 scripts/check_manifest.py"""
import json
M=json.load(open('docs/consistency_manifest.json')); tex=open(M['paper']).read()
dropped=0
for f in M['numeric_facts']:
    keep=[s for s in f.get('tex',[]) if s in tex]; dropped+=len(f.get('tex',[]))-len(keep)
    if 'tex' in f: f['tex']=keep
T='experiments/hle400/t3/'
E2,BE,S1,DS,BB,MEM,CR,SE,AD=(T+x for x in ('equal_token_samples_readout.json','bbeh_equal_token_readout.json','selection_confirmation_readout.json','selection_confirmation_ds_readout.json','second_benchmark_readout.json','memory_manipulation_readout.json','critic_doubts_by_correctness.json','grading_key_sensitivity.json','selection_confirmation_addendum_readout.json'))
N=[]
def F(i,v,js,*tx): N.append({'id':i,'value':v,'paper':'v17','json':js,'tex':list(tx)})
ESC='E-SC selected: critique - equal-token samples'; EUSC='E-USC selected: critique - USC'; EC='E-C selected on questions reached by both: critique - equal-token samples'; ER='E-R reached: critique - equal-token samples'
for m,lab in (('qwen','qw'),('deepseek','ds')):
    c=json.load(open(E2))[m]
    F(f'e2_{lab}_crit_reached',c['conditions']['critique']['reached'],[E2,m,'conditions','critique','reached'])
    F(f'e2_{lab}_samp_reached',c['conditions']['equal-token samples']['reached'],[E2,m,'conditions','equal-token samples','reached'])
    F(f'e2_{lab}_samp_selected',c['conditions']['equal-token samples']['selected'],[E2,m,'conditions','equal-token samples','selected'])
    F(f'e2_{lab}_usc',c['conditions']['USC']['correct'],[E2,m,'conditions','USC','correct'])
    for k,t in (('esc',ESC),('eusc',EUSC),('ec',EC)):
        for q in ('diff','lo','hi'): F(f'e2_{lab}_{k}_{q}',c['tests'][t][q],[E2,m,'tests',t,q])
    for q in ('diff','lo90','hi90'): F(f'e2_{lab}_er_{q}',c[ER][q],[E2,m,ER,q])
    F(f'e2_{lab}_both',c['n_reached_by_both'],[E2,m,'n_reached_by_both'])
    F(f'e2_{lab}_ratio',c['alignment']['ratio'],[E2,m,'alignment','ratio'])
    F(f'e2_{lab}_spq',c['samples_per_question']['mean'],[E2,m,'samples_per_question','mean'])
    F(f'e2_{lab}_uscfail',c['usc_parse_failures'],[E2,m,'usc_parse_failures'])
    for k in ('exact only, E-SC','exact only, E-USC','equal-token samples - nine samples','USC - equal-token samples'):
        F(f'e2_{lab}_{k}',c['descriptive'][k]['diff'],[E2,m,'descriptive',k,'diff'])
    for g in ('exactMatch','multipleChoice'): F(f'e2_{lab}_{g}',c['by_answer_type'][g]['E-SC']['diff'],[E2,m,'by_answer_type',g,'E-SC','diff'])
    for k in ('reach_term','conversion_term'): F(f'e2_{lab}_{k}',c['decomposition']['critique - equal-token samples'][k],[E2,m,'decomposition','critique - equal-token samples',k])
q=json.load(open(E2))
F('e2_tex_qw_core','',None) if False else None
N+=[{'id':'e2_core_strings','value':None,'paper':'v17','tex':['348 / \\textbf{385} & 370 / \\textbf{397} & 591 / \\textbf{611}','\\textbf{205.3} / 180.0 & \\textbf{254.2} / 229.0 & \\textbf{390.5} / 356.5',
 '18.8; 1.18 & 17.2; 1.15 & 21.2; 1.13','$+25.3$ \\ci{4.4}{46.5}$^{*}$ & $+25.2$ \\ci{7.8}{41.8}$^{**}$ & $+34.0$ \\ci{13.8}{55.0}$^{**}$',
 '$+26.8$ \\ci{9.0}{44.9}$^{**}$ (290) & $+32.0$ \\ci{17.6}{46.4}$^{***}$ (323) & $+35.4$ \\ci{16.0}{54.0}$^{**}$ (540)','$+22.3$ \\ci{1.5}{43.1}$^{*}$ & $+19.2$ \\ci{2.0}{37.1}$^{*}$',
 '$-37$ \\ci{-58}{-18} & $-27$ \\ci{-45}{-8} & $-20$ \\ci{-39}{-1}','by 28.6 (\\ci{10.2}{47.5}) and 17.2 (\\ci{2.8}{31.6})','($+24.3$ and $+19.8$)','($+1.0$ and $+5.4$)',
 'reach 56, 36 and 64 more questions and select 1.9, 4.4 and 12.0 more']}]
b=json.load(open(BE))
for a in ('C2','A3Y','GT7','A2PY','A3'):
    for k in ('reached','selected'): F(f'bet_{a}_{k}',b['conditions'][a][k],[BE,'conditions',a,k])
for t in b['tests']:
    for k in ('diff','lo','hi'): F(f'bet_{t[:4]}_{k}',b['tests'][t][k],[BE,'tests',t,k])
for k in ('diff','lo90','hi90'): F(f'bet_er_{k}',b['B-ER reached: critique - equal-token samples'][k],[BE,'B-ER reached: critique - equal-token samples',k])
for k in ('GT7 - A2PY (temperature within the loop)','critique - GT7','A3Y - nine samples','A2PY - equal-token samples'):
    for q in ('diff','lo','hi'): F(f'bet_{k[:12]}_{q}',b['descriptive'][k][q],[BE,'descriptive',k,q])
F('bet_crit_keep',[b['conditions']['C2']['repeat_after_correct'],b['conditions']['C2']['repeat_after_incorrect']],None,'Critique & .43 & \\textbf{.29} & & .44 & \\textbf{.29} & & .45 & \\textbf{.16}')
N[-1]['json']=None; N[-1].pop('json')
N+=[{'id':'v17_strings','value':None,'paper':'v17','tex':['It selects 368.0 questions, against 371.9 at temperature 0 ($-3.9$, \\ci{-22.5}{15.9}) and 356.5 for the samples.','($+11.6$, \\ci{-9.6}{31.6})',
 '2.96 against 2.96 per round on \\qw, 2.81 against 2.86 on \\ds{} and 2.94 against 2.95 on BBEH','(0.41 against 0.50 in the first round; $p<0.001$) and lowered the selected count by 12.4 (\\ci{-6.0}{30.9})',
 'token-yoked & $\\mathbf{+23.8}$ & $-7.2$ & $+18.6$','reassuring & $\\mathbf{+36.8}$ & $-1.9$ & $+10.6$',' & $+1.5$ & $+32.4$ & $+15.4$','Reassuring & .64 & .60 & & .75 & .63 & & .72 & .38',
 'Token-yoked & .58 & .54 & & .73 & .61 & & .70 & .49','Samples & .35 & .31 & & .50 & .34 & & .58 & .32','$+27.3$, $+27.8$ and $+27.8$ on \\qw{} and $+25.7$, $+24.7$ and $+23.7$ on \\ds']}]
cr=json.load(open(CR))
for k in cr:
    for c in cr[k]: F(f'crit_{k[:8]}_{c[-9:]}',cr[k][c]['mean_doubts'],[CR,k,c,'mean_doubts'])
se=json.load(open(SE))
for m in se:
    for r in se[m]['E-SC']: F(f'sens_{m[:4]}_{r}',se[m]['E-SC'][r]['diff'],[SE,m,'E-SC',r,'diff'])
mm=json.load(open(MEM)); nm='NM-2 selected: token-yoked generic doubt - the same without memory (800; confirmatory)'
for q in ('diff','lo','hi'): F(f'mem_nm2_{q}',mm[nm][q],[MEM,nm,q])
F('mem_check_without',mm['manipulation_check']['GNM vs A2PY (800)']['without_memory'],[MEM,'manipulation_check','GNM vs A2PY (800)','without_memory'])
F('mem_check_with',mm['manipulation_check']['GNM vs A2PY (800)']['with_memory'],[MEM,'manipulation_check','GNM vs A2PY (800)','with_memory'])
for k in ('visibility (GKI - GNM)','permission (A2PY - GKI)'): F(f'mem_{k[:5]}',mm['visibility_and_permission_400'][k]['diff'],[MEM,'visibility_and_permission_400',k,'diff'])
s1=json.load(open(S1)); r1='R1 reached: critique - token-yoked generic doubt'
for q in ('diff','lo90','hi90'): F(f's1_r1_{q}',s1[r1][q],[S1,r1,q])
ds=json.load(open(DS)); dr='D-R1 reached: critique - token-yoked generic doubt'
for q in ('diff','lo90','hi90'): F(f'ds_r1_{q}',ds[dr][q],[DS,dr,q])
for t in ds['confirmatory']:
    for q in ('diff','lo','hi'): F(f'ds_{t[:4]}_{q}',ds['confirmatory'][t][q],[DS,'confirmatory',t,q])
bb=json.load(open(BB))['hard']
for t in bb['selected_tests']:
    for q in ('diff','lo','hi'): F(f'bb_{t[:2]}_{q}',bb['selected_tests'][t][q],[BB,'hard','selected_tests',t,q])
for q in ('diff','lo90','hi90'): F(f'bb_r_{q}',bb['reached_critique_minus_token_yoked'][q],[BB,'hard','reached_critique_minus_token_yoked',q])
ad=json.load(open(AD))
for t in ad['tests']:
    for q in ('diff','lo','hi'): F(f'add_{t[:4]}_{q}',ad['tests'][t][q],[AD,'tests',t,q])
N=[n for n in N if n]
M['numeric_facts']+=N; M['paper_version']='v17 draft'; M['date']='2026-11-20'
json.dump(M,open('docs/consistency_manifest.json','w'),indent=1,ensure_ascii=False)
print('dropped tex strings',dropped,'added facts',len(N))
