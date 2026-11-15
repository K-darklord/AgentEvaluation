#!/usr/bin/env python3
"""Check docs/consistency_manifest.json against (a) the JSON outputs of the analysis scripts and
(b) the text of paper/acl/main.tex. Reads files only; run the analysis scripts first if their outputs are stale.
Each fact has: "value"; optionally "json" = [file, key, key, ...] (a list leaf is summed and rounded to one
decimal); optionally "tex" = strings that must occur in main.tex.
Usage: python3 scripts/check_manifest.py"""
import json,sys
M=json.load(open('docs/consistency_manifest.json')); tex=open(M['paper']).read(); cache={}; bad=0; nj=nt=0
def leaf(spec):
    f=spec[0]; o=cache.setdefault(f,json.load(open(f)))
    for k in spec[1:]: o=o[k]
    if isinstance(o,list) and o and all(isinstance(x,(int,float,bool)) for x in o) and len(o)>3: o=round(sum(o),1)
    return o
def same(a,b):
    if isinstance(a,bool) or isinstance(b,bool): return a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return abs(round(a,2)-b)<0.0051 or abs(round(a,1)-b)<1e-9
    if isinstance(a,list) and isinstance(b,list): return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
for f in M['numeric_facts']:
    if 'json' in f:
        nj+=1; got=leaf(f['json'])
        if not same(got,f['value']): bad+=1; print('MISMATCH data ',f['id'],'manifest',f['value'],'file',got)
    for s in f.get('tex',[]):
        nt+=1
        if s not in tex: bad+=1; print('MISSING in tex',f['id'],repr(s))
print(f"{len(M['numeric_facts'])} facts; {nj} checked against script outputs, {nt} strings checked in {M['paper']}; {bad} problems")
sys.exit(1 if bad else 0)
