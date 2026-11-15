"""Path P2 of the human audit (docs/HUMAN_AUDIT_PLAN.md): computer-algebra verification that a model answer
and the reference answer are the same mathematical object. Reads nothing from key.json.
Each entry: audit id, transcription of the reference, transcription of the model answer, and the check.
A check passes only if (a) sympy simplifies the difference to 0 or the two sides are equal as exact integers,
and/or (b) the two sides agree to 1e-25 relative error at 50 digits for 20 random parameter draws.
Transcriptions are by hand from audit/human_audit_20261111/items.csv and must be confirmed by an annotator.
Usage: python3 scripts/human_audit_cas_checks.py   (writes audit/human_audit_20261111/cas_results.json)"""
import json, random
import sympy as sp
from sympy import log, pi, sqrt, asinh, acos, asin, acosh, atanh, exp, erfi, Rational, factorial, binomial, Symbol, Integral
import mpmath as mp
mp.mp.dps=50
rng=random.Random(20261111)
_u=rng.uniform
class _R:  # exact rational draws, so that 50-digit evaluation is not limited by float inputs
    @staticmethod
    def uniform(a,b): return sp.Rational(round(_u(a,b)*10**6),10**6)
rng=_R
def numeq(f,g,draw,n=20):
    worst=0
    for _ in range(n):
        v=draw(); a=sp.N(f.subs(v),50); b=sp.N(g.subs(v),50)
        worst=max(worst,abs((a-b)/b))
    return float(worst)
C=[]
def add(i,ref,ans,f,g,draw=None,note=''):
    r=dict(id=i,reference=ref,model_answer=ans,note=note)
    try: r['symbolic_zero']=bool(sp.simplify(f-g)==0)
    except Exception as e: r['symbolic_zero']=None
    r['max_rel_err']=numeq(f,g,draw or (lambda:{}),20 if draw else 1)
    r['equivalent']=bool(r['symbolic_zero'] or r['max_rel_err']<1e-25); C.append(r)
P=lambda *names:[Symbol(n,positive=True) for n in names]
add('H004','ln5/(ln14-ln3)','log5/log(14/3)',log(5)/(log(14)-log(3)),log(5)/log(Rational(14,3)))
add('H014','10^793+2*10^398+1000','1000(10^395+1)^2',sp.Integer(10)**793+2*sp.Integer(10)**398+1000,1000*(sp.Integer(10)**395+1)**2)
v0,c,g,h=P('v0','c','g','h'); gam=1/sqrt(1-v0**2/c**2); al=c*gam/g
add('H042','v0*alpha*arctanh(sqrt(2 h alpha c+h^2)/(alpha c+h)), alpha=c*gamma0/g','v0 c/(g sqrt(1-v0^2/c^2)) * arccosh(1+(g h/c^2) sqrt(1-v0^2/c^2))',
    v0*al*atanh(sqrt(2*h*al*c+h**2)/(al*c+h)), v0*c/(g*sqrt(1-v0**2/c**2))*acosh(1+g*h/c**2*sqrt(1-v0**2/c**2)),
    lambda:(lambda cc:{c:cc,v0:cc*rng.uniform(.05,.95),g:rng.uniform(.5,20),h:rng.uniform(.1,50)})(rng.uniform(1,10)),
    note='gamma0 read as the Lorentz factor 1/sqrt(1-v0^2/c^2); confirm against the question')
for i in ('H051','H089'): add(i,'pi*arcsinh(1)','pi*ln(1+sqrt2)',pi*asinh(1),pi*log(1+sqrt(2)))
daw=lambda x: exp(-x**2)*sqrt(pi)/2*erfi(x)
refD=-2+1/((1-daw(1))/sp.E**3+daw(2))
add('H063','-2+1/((1-DawsonF[1])/E^3+DawsonF[2])','-2+e^4/(e+(sqrt(pi)/2)(erfi(2)-erfi(1)))',refD,-2+sp.E**4/(sp.E+sqrt(pi)/2*(erfi(2)-erfi(1))))
s=Symbol('s'); add('H090','-2+1/((1-DawsonF[1])/E^3+DawsonF[2])','-2+e^4/(e+int_1^2 e^{s^2} ds)',refD,-2+sp.E**4/(sp.E+Integral(exp(s**2),(s,1,2)).doit()))
add('H068','pi/ln(4)','pi/(2 ln 2)',pi/log(4),pi/(2*log(2)))
add('H070','9!^2','131681894400',factorial(9)**2,sp.Integer(131681894400))
n,m=Symbol('n',integer=True,positive=True),Symbol('m',integer=True,positive=True)
r=dict(id='H078',reference='2*sum_{k=0}^{(d-1)/2} C(n,k)',model_answer='2+2*sum_{i=1}^{(d-1)/2} C(n,i)',note='checked exactly for all odd d<=41, n<=60')
r['symbolic_zero']=None; r['max_rel_err']=0.0
r['equivalent']=all(2*sum(sp.binomial(N,k) for k in range((d-1)//2+1))==2+2*sum(sp.binomial(N,k) for k in range(1,(d-1)//2+1)) for d in range(1,42,2) for N in range(1,61)); C.append(r)
e,B,hh,V1=P('e','B','h','V1'); hbar=hh/(2*pi)
add('H088','2e^2 B/h(V_1)','e^2 B/(pi hbar V_1)',2*e**2*B/(hh*V1),e**2*B/(pi*hbar*V1),lambda:{e:rng.uniform(.1,5),B:rng.uniform(.1,5),hh:rng.uniform(.1,5),V1:rng.uniform(.1,5)},
    note='reference read as 2 e^2 B/(h V_1); hbar=h/(2 pi)')
add('H094','arccos(2 sqrt(6)/5)','arcsin(1/5)',acos(2*sqrt(6)/5),asin(Rational(1,5)))
json.dump(C,open('audit/human_audit_20261111/cas_results.json','w'),indent=1)
for r in C: print(r['id'],'equivalent' if r['equivalent'] else 'NOT equivalent','symbolic',r['symbolic_zero'],'relerr %.1e'%r['max_rel_err'],r['note'])
