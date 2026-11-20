#!/usr/bin/env python3
"""Manifest for draft v18 (rewording only, no new numbers): drop text strings that the rewrite removed (the data checks of
those facts are kept) and add the strings of the reworded main text. Usage: python3 scripts/build_manifest_v18.py"""
import json
M=json.load(open('docs/consistency_manifest.json')); tex=open(M['paper']).read(); n=0
for f in M['numeric_facts']:
    if 'tex' in f:
        k=[s for s in f['tex'] if s in tex]; n+=len(f['tex'])-len(k); f['tex']=k
M['numeric_facts']=[f for f in M['numeric_facts'] if f['id']!='v18_strings']
M['numeric_facts'].append({'id':'v18_strings','value':None,'paper':'v18','tex':[
 '348 / \\textbf{385} & 370 / \\textbf{397} & 591 / \\textbf{611}','\\textbf{205.3} / 180.0 & \\textbf{254.2} / 229.0 & \\textbf{390.5} / 356.5','Samples per question & 18.8 & 17.2 & 21.2',
 '$+25.3$ \\ci{4.4}{46.5}$^{*}$ & $+25.2$ \\ci{7.8}{41.8}$^{**}$ & $+34.0$ \\ci{13.8}{55.0}$^{**}$','$+26.8$ \\ci{9.0}{44.9}$^{**}$ & $+32.0$ \\ci{17.6}{46.4}$^{***}$ & $+35.4$ \\ci{16.0}{54.0}$^{**}$',
 '$+22.3$ \\ci{1.5}{43.1}$^{*}$ & $+19.2$ \\ci{2.0}{37.1}$^{*}$','Both methods reach 290, 323 and 540 questions.','reaches 56, 36 and 64 more questions and selects only 1.9, 4.4 and 12.0 more',
 'independent sampling selects 47, 58 and 58. The critique loop selects 59, 69 and 66.','are $-15$ questions on \\qw{} and $-1$ on \\ds','17 and 8 more on HLE-800 and 3 fewer on BBEH-800',
 'Token-matched & $\\mathbf{+23.8}$ & $-7.2$ & $+18.6$','Reassuring loop & $\\mathbf{+36.8}$ & $-1.9$ & $+10.6$','selects 256.2 questions against 254.2','It selects 27.1 more than independent sampling (\\ci{8.6}{45.0})',
 '(368.0 against 371.9 at temperature 0)','($+11.6$, \\ci{-9.6}{31.6})','2.96 against 2.96 per round on \\qw, 2.81 against 2.86 on \\ds{} and 2.94 against 2.95 on BBEH-800',
 'Critique loop & .43 & \\textbf{.29} & & .44 & \\textbf{.29} & & .45 & \\textbf{.16}','by 12.4 questions, but the difference was not significant (\\ci{-6.0}{30.9}',
 'the differences are 29.1, 26.5 and 39.7, and with the samples held within the budget they are 28.5, 26.4 and 52.5','($+27.0$ and $+25.0$) and disappears on BBEH-800 ($+0.5$)',
 '($+19.2$, \\ci{2.8}{36.5}) and on BBEH-800 ($+27.3$, \\ci{7.2}{49.4}) but not on \\qw{} with HLE-800 ($+9.3$, \\ci{-13.3}{31.5})','($+1.5$, \\ci{-13.5}{16.5})','which is 14\\%, 11\\% and 10\\% more']})
M['paper_version']='v18 draft'; json.dump(M,open('docs/consistency_manifest.json','w'),indent=1,ensure_ascii=False); print('dropped strings',n)
