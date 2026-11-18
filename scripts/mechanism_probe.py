#!/usr/bin/env python3
"""Mechanism probe: four-source decomposition of the selection difference, the subdivision by the
state of the shared first answer, and the vote counts that decide a plurality.
Reads frozen trajectories + T3 sidecars only. Usage: python3 scripts/mechanism_probe.py"""
import json,glob,sys,statistics as st
from collections import Counter
from pathlib import Path
sys.path.insert(0,'scripts')
from confirm_common import reco,J

D='deepseek-v4-flash-payg';Q='qwen3.8-flash-payg';M='minimax-m2.5'
cf=J('is_correct_t3_sidecar_confirm.json')['arms'];cf2=J('is_correct_t3_sidecar_confirm2.json')['arms']
cds=J('is_correct_t3_sidecar_confirm_ds.json')['arms'];rep=J('is_correct_t3_sidecar_rep.json')['arms']
rep3=J('is_correct_t3_sidecar_rep3.json')['arms'];v3=J('is_correct_t3_sidecar_v3.json')['arms']
yk=J('is_correct_t3_sidecar_yoke.json')['arms'];ykm=J('is_correct_t3_sidecar_yoke_minimax.json')['arms']
C2DS=[d for d in glob.glob('experiments/hle400_C2/*') if Path(d,'loop_trajectories.jsonl').exists()][0]
CELLS={
 'ds400':{'A2':('experiments/hle400_A2/deepseek-v4-flash',v3['A2']),'C2':(C2DS,v3['C2'])},
 'q400':{'A2':(f'experiments/rep200_A2_{Q}/{Q}',rep['A2']),'C2':(f'experiments/rep200_C2_{Q}/{Q}',rep['C2']),'A2PY':(f'experiments/yoke_A2PY_{Q}/{Q}',yk['A2PY'])},
 'mm400':{'A2':(f'experiments/rep3_A2_{M}/{M}',rep3['A2']),'C2':(f'experiments/rep3_C2_{M}/{M}',rep3['C2']),'A2PY':(f'experiments/yoke_A2PY_{M}/{M}',ykm['A2PY'])},
 'q800':{'A2':(f'experiments/conf_A2_{Q}/{Q}',cf['A2']),'C2':(f'experiments/conf_C2_{Q}/{Q}',cf['C2']),'A2P':(f'experiments/conf_A2P_{Q}/{Q}',cf['A2P']),'A2PY':(f'experiments/conf_A2PY_{Q}/{Q}',cf['A2PY']),'QO':(f'experiments/conf_C2Q_{Q}/{Q}',cf2['C2Q'])},
 'ds800':{'A2':(f'experiments/conf_A2_{D}/{D}',cds['A2']),'C2':(f'experiments/conf_C2_{D}/{D}',cds['C2']),'A2P':(f'experiments/conf_A2P_{D}/{D}',cds['A2P']),'A2PY':(f'experiments/conf_A2PY_{D}/{D}',cds['A2PY'])}}

def load(path,side):
    out={}
    for line in open(path+'/loop_trajectories.jsonl',encoding='utf-8'):
        if not line.strip(): continue
        d=json.loads(line); t=d['task_id']
        keys=reco.freeze_keys(d.get('gold_answer',''),d); sl=side[t]
        cnt=Counter(k for k in keys if k is not None)
        ok={k:bool(reco.last_key_correct(keys,sl,k)) for k in cnt}
        fcr=None;nco=0
        for j,k in enumerate(keys):
            if k is not None and ok[k]:
                nco+=1
                if fcr is None: fcr=j
        top=max(cnt.values()) if cnt else 0; tied=[k for k in cnt if cnt[k]==top]
        sel=(sum(ok[k] for k in tied)/len(tied)) if tied else 0.0
        out[t]=dict(first=bool(sl[0]['c']),reached=int(any(ok.values())) if cnt else 0,sel=sel,nco=nco,fcr=fcr,
                    nd=len(cnt),nr=len(keys),
                    maxC=max((cnt[k] for k in cnt if ok[k]),default=0),
                    maxW=max((cnt[k] for k in cnt if not ok[k]),default=0))
    return out

P={c:{a:load(p,s) for a,(p,s) in arms.items()} for c,arms in CELLS.items()}

def dec(cell,other,crit='C2'):
    Pc,Pp=P[cell][crit],P[cell][other]
    base=[t for t in Pc if not Pc[t]['first']];fc=[t for t in Pc if Pc[t]['first']]
    both=[t for t in base if Pc[t]['reached'] and Pp[t]['reached']]
    oc=[t for t in base if Pc[t]['reached'] and not Pp[t]['reached']]
    op=[t for t in base if Pp[t]['reached'] and not Pc[t]['reached']]
    S=lambda X,X_=Pc: round(sum(X_[t]['sel'] for t in X),1)
    return dict(net=round(sum(Pc[t]['sel']-Pp[t]['sel'] for t in Pc),1),
                both=(len(both),round(S(both,Pp)/max(1,len(both)),2),round(S(both,Pc)/max(1,len(both)),2)),
                onlyc=(len(oc),round(S(oc)/max(1,len(oc)),2),S(oc)),
                onlyp=(len(op),round(S(op,Pp)/max(1,len(op)),2),-S(op,Pp)),
                fc=(len(fc),round(S(fc)-S(fc,Pp),1)))

if __name__=='__main__':
    print('=== four-source decomposition (selected; critique minus comparison) ===')
    for cell in P:
        for o in [a for a in ('A2','A2PY','A2P','QO') if a in P[cell]]:
            d=dec(cell,o)
            print(f"{cell:6}{o:5} net={d['net']:+6.1f} both={d['both']} onlyC={d['onlyc']} onlyP={d['onlyp']} first={d['fc']}")
    print('\n=== critique minus reassuring, by state of the first answer ===')
    for cell in P:
        Pc,Pp=P[cell]['C2'],P[cell]['A2']
        w=[t for t in Pc if not Pc[t]['first']];f=[t for t in Pc if Pc[t]['first']]
        print(f"{cell:6} wrong-first n={len(w):4d} net={sum(Pc[t]['sel']-Pp[t]['sel'] for t in w):+6.1f} | first-correct n={len(f):4d} net={sum(Pc[t]['sel']-Pp[t]['sel'] for t in f):+6.1f}")
    print('\n=== only-critique-reached: votes of the correct answer vs the strongest wrong answer ===')
    for cell in ('ds400','q400','q800','ds800'):
        Pc,Pp=P[cell]['C2'],P[cell]['A2']
        g=[t for t in Pc if not Pc[t]['first'] and Pc[t]['reached'] and not Pp[t]['reached']]
        fcr=[Pc[t]['fcr'] for t in g if Pc[t]['fcr'] is not None]
        print(f"{cell:6} n={len(g):4d} conv={sum(Pc[t]['sel'] for t in g)/len(g):.2f} "
              f"maxC={st.mean(Pc[t]['maxC'] for t in g):.2f} maxW={st.mean(Pc[t]['maxW'] for t in g):.2f} "
              f"gap={st.mean(Pc[t]['maxC']-Pc[t]['maxW'] for t in g):+.2f} first-correct-round median={st.median(fcr)}")
    print('\n=== rounds and selected per condition ===')
    for cell in P:
        for a,v in P[cell].items():
            print(f"{cell:6}{a:5} rounds/q={st.mean(x['nr'] for x in v.values()):5.2f} "
                  f"selected={sum(x['sel'] for x in v.values()):6.1f} distinct/q={st.mean(x['nd'] for x in v.values()):4.2f}")
