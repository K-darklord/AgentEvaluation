"""Path P3 support (docs/HUMAN_AUDIT_PLAN.md): brute-force check of the MILP-encoding items (H006, H053, H065 and the reference).
Question: base constraints  y<=(u-1)a, y>=l, y<=x-a, y>=x-1, a in {0,1};  add two inequalities with b in {0,1}
so that the feasible set of y is exactly {f(x)} for l<=x<=u, where f(x)=x-1 if x>=1 else min(0,x).
For each (l,u) and x on a grid, the feasible y-set is the union over (a,b) of [max lower bounds, min upper bounds].
An encoding is exact iff that union is the single point f(x) for every x. Reads no audit key. Exact rational arithmetic."""
from fractions import Fraction as F
import itertools, json
f=lambda x: x-1 if x>=1 else min(F(0),x)
ENC={
 'reference: y>=b*l, y>=x+b-1':        lambda x,a,b,l,u:[b*l, x+b-1],
 'H006: y>=x-u+ub-ua, y>=-u+ub-ua':    lambda x,a,b,l,u:[x-u+u*b-u*a, -u+u*b-u*a],
 'H053: y>=x-u+l+ub-lb, y>=-ub+lb':    lambda x,a,b,l,u:[x-u+l+u*b-l*b, -u*b+l*b],
 'H065: y>=x-M+Mb, y>=-Mb, M=u-l+max(0,-u)': lambda x,a,b,l,u:(lambda M:[x-M+M*b, -M*b])(u-l+max(F(0),-u)),
}
def exact(enc,l,u,n=240):
    bad=[]
    for k in range(n+1):
        x=l+(u-l)*F(k,n); ivs=[]
        for a,b in itertools.product((0,1),(0,1)):
            lo=max([l,x-1]+enc(x,a,b,l,u)); hi=min((u-1)*a, x-a)
            if lo<=hi: ivs.append((lo,hi))
        if not ivs or any(lo!=f(x) or hi!=f(x) for lo,hi in ivs): bad.append((str(x),[(str(p),str(q)) for p,q in ivs],str(f(x))))
    return bad
out={}
for name,enc in ENC.items():
    res={}
    for l,u in [(F(-3),F(4)),(F(-1),F(2)),(F(-5,2),F(7,2)),(F(-10),F(10)),(F(-1,2),F(3,2))]:
        bad=exact(enc,l,u); res[f'l={l},u={u}']={'exact':not bad,'n_bad':len(bad),'first_bad':bad[:1]}
    out[name]=res; print(name,'->',{k:v['exact'] for k,v in res.items()}, '' if all(v['exact'] for v in res.values()) else next(v['first_bad'] for v in res.values() if not v['exact']))
json.dump(out,open('audit/human_audit_20261111/milp_check.json','w'),indent=1)
