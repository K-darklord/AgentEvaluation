"""Path P2 of the second human audit (docs/HUMAN_AUDIT2_PLAN.md, revision 2026-11-19): computer-algebra verification
that a model answer and the reference answer are the same mathematical object. Reads nothing from key.json.
Same rule as scripts/human_audit_cas_checks.py: a check passes if sympy simplifies the difference to 0, or the two
sides agree to 1e-25 relative error at 50 digits for 20 random parameter draws; Boolean formulas by full truth table;
matrix factorizations by D^-1 N = H and left coprimeness (the 2x2 minors of [D N] have no common root).
Transcriptions are by hand from audit/selection_audit_20261117/items.csv and must be confirmed by an annotator.
Usage: python3 scripts/human_audit2_cas_checks.py   (writes audit/selection_audit_20261117/cas_results.json)"""
import json, random, itertools
import sympy as sp
from sympy import log, pi, sqrt, tan, cos, Rational, factorial, Symbol, Matrix, gcd
rng0=random.Random(20261119)
def R(a,b): return sp.Rational(round(rng0.uniform(a,b)*10**6),10**6)
def numeq(f,g,draw,n=20):
    worst=0
    for _ in range(n):
        v=draw(); a=sp.N(f.subs(v),50); b=sp.N(g.subs(v),50)
        worst=max(worst,abs((a-b)/b) if b!=0 else abs(a-b))
    return float(worst)
C=[]
def add(i,ref,ans,f,g,draw=None,note=''):
    r=dict(id=i,reference=ref,model_answer=ans,note=note)
    try: r['symbolic_zero']=bool(sp.simplify(f-g)==0)
    except Exception: r['symbolic_zero']=None
    r['max_rel_err']=numeq(f,g,draw or (lambda:{}),20 if draw else 1)
    r['equivalent']=bool(r['symbolic_zero'] or r['max_rel_err']<1e-25); C.append(r)
def manual(i,ref,ans,ok,note): C.append(dict(id=i,reference=ref,model_answer=ans,note=note,symbolic_zero=None,max_rel_err=None,equivalent=bool(ok)))
chi,Cc,K,g=sp.symbols('chi C K_S g')
add('S006','12chi + C^2 - K_S^2 - (4-4g)','C^2 - K_S^2 + 12chi + 4g - 4',12*chi+Cc**2-K**2-(4-4*g),Cc**2-K**2+12*chi+4*g-4)
c=Symbol('c'); add('S009','c(1+sqrt3)/2','(1+sqrt3)/2 * c',c*(1+sqrt(3))/2,(1+sqrt(3))/2*c)
n=Symbol('n',positive=True)
add('S024','2^(n(n+3)/2)','2^((n^2+5n)/2)',2**(n*(n+3)/2),2**((n**2+5*n)/2),lambda:{n:sp.Integer(rng0.randint(1,30))})
add('S027','4(10^20-0.5)/(10^40+1)','(4*10^20-2)/(10^40+1)',4*(sp.Integer(10)**20-Rational(1,2))/(sp.Integer(10)**40+1),(4*sp.Integer(10)**20-2)/(sp.Integer(10)**40+1))
add('S036','tan(pi/n)/(2 tan(pi/(2n)))','cos^2(pi/(2n))/cos(pi/n)',tan(pi/n)/(2*tan(pi/(2*n))),cos(pi/(2*n))**2/cos(pi/n),lambda:{n:sp.Integer(rng0.randint(3,60))},
    note='reference "tan(pi/n)/2tan(pi/2n)" read as tan(pi/n)/(2 tan(pi/(2n))); checks n=3 gives 3/2 as stated in the question')
L,N=sp.symbols('L n',positive=True)
add('S037','(n(6L^2+4-4L)+L^3+2L(1-L))/(48n^3)','(3L^2-2L+2)/(24n^2)+(L^3-2L^2+2L)/(48n^3)',(N*(6*L**2+4-4*L)+L**3+2*L*(1-L))/(48*N**3),(3*L**2-2*L+2)/(24*N**2)+(L**3-2*L**2+2*L)/(48*N**3),
    lambda:{L:R(.1,10),N:R(1,100)})
for i in ('S052','S092'): add(i,'(1-1/(pi+1))/log(pi+1)','pi/((1+pi) ln(1+pi))',(1-1/(pi+1))/log(pi+1),pi/((1+pi)*log(1+pi)),note='log in the reference read as the natural logarithm')
F1,F2=sp.symbols('F1 F2')
for i in ('S055','S056'): add(i,'(1-F1-F2+22F1F2)/21','(22F1F2-F1-F2+1)/21',(1-F1-F2+22*F1*F2)/21,(22*F1*F2-F1-F2+1)/21)
ok=all(sum(Rational(100,2*(k-i)+1) for i in range(1,k+1))==100*k-sum(Rational(2*(j-1)*100,2*j-1) for j in range(2,k+1)) for k in range(1,61))
manual('S058','sum_{i=1}^n 100/(2(n-i)+1) - m','100n - m - sum_{k=2}^n 2(k-1)100/(2k-1)',ok,'checked exactly for n=1..60 (the -m term is identical on both sides)')
def sg(x): return (x>0)-(x<0)
ok=True; rr=random.Random(7)
for _ in range(2000):
    nn=rr.randint(1,9); dA=rr.choice([-1,1])*rr.uniform(.1,5); dB=rr.choice([-1,1])*rr.uniform(.1,5); an,bn,S=rr.uniform(0,3),rr.uniform(0,3),rr.uniform(0,30)
    ref=-(-1)**nn*sg(dA*dB)*an*bn-S; mod=-S-sg((-1)**nn*dA*dB)*an*bn; ok&=abs(ref-mod)<1e-12
for i in ('S062','S093'): manual(i,'-(-1)^n s(|AB|) a_n b_n - sum_{i<=n-1} a_i b_i','-sum_{i=1}^{n-1} a_i b_i - s((-1)^n |A||B|) a_n b_n',ok,
    's = sign, |.| = determinant, so |AB| = |A||B|; 2000 random draws of n, determinants (both signs), a_n, b_n and the sum')
gam=Symbol('gamma',positive=True)
add('S083','omega0/16 (2+3gamma-6gamma^2), omega0=sqrt(3gamma)','-sqrt(3gamma)(6gamma^2-3gamma-2)/16',sqrt(3*gam)/16*(2+3*gam-6*gam**2),-sqrt(3*gam)*(6*gam**2-3*gam-2)/16,
    note='omega0 = sqrt(3 gamma) is given in the question')
add('S084','(2pi)^((n^2-n)/4) (n!)^(-1/2)','(2pi)^(n(n-1)/4)/sqrt(n!)',(2*pi)**((n**2-n)/4)*factorial(n)**Rational(-1,2),(2*pi)**(n*(n-1)/4)/sqrt(factorial(n)),lambda:{n:sp.Integer(rng0.randint(1,40))})
imp=lambda p,q:(not p) or q; nor=lambda p,q:not(p or q); nand=lambda p,q:not(p and q); iff=lambda p,q:p==q
ref=lambda a,b,c,d: iff(nand(nor(a,b),not nor(c,b)), not imp(d, not((not a) or b)))
m50=lambda a,b,c,d: not iff(nand(d,imp(a,b)), nand(c,nor(a,b)))
m95=lambda a,b,c,d: (not imp(b,not d)) or (not imp(not b, imp(not a, iff(d,c))))
for i,f,txt in (('S050',m50,'not((d NAND (a->b)) <-> (c NAND (a NOR b)))'),('S095',m95,'not(b -> not d) or not(not b -> (not a -> (d <-> c)))')):
    rows=list(itertools.product([False,True],repeat=4)); diff=[r for r in rows if ref(*r)!=f(*r)]
    manual(i,'((a NOR b) NAND not(c NOR b)) <-> not(d -> not(not a or b))',txt,not diff,f'truth table over a,b,c,d (16 rows); rows that differ: {len(diff)}')
s=Symbol('s'); H=Matrix([[(s-1)/(s+1),1],[2/(s**2-1),0]])
def lcf(D,Nm):
    eq=sp.simplify(D.inv()*Nm-H)==sp.zeros(2,2); M=D.row_join(Nm); minors=[sp.factor(M[:,[i,j]].det()) for i,j in itertools.combinations(range(4),2)]
    g0=0
    for x in minors: g0=gcd(g0,sp.expand(x))
    return eq, sp.degree(g0,s)==0 if g0!=0 else False
Dref=Matrix([[-s,s-1],[1,s-1]]); Nref=Matrix([[2-s,-s],[1,1]]); e0,c0=lcf(Dref,Nref)
for i,D,Nm,txt in (('S074',Matrix([[1,s-1],[0,s**2-1]]),Matrix([[1,1],[2,0]]),'D=[1, s-1; 0, s^2-1], N=[1, 1; 2, 0]'),('S076',Matrix([[s+1,0],[1,s-1]]),Matrix([[s-1,s+1],[1,1]]),'D=[s+1, 0; 1, s-1], N=[s-1, s+1; 1, 1]')):
    e,cp=lcf(D,Nm)
    manual(i,'N=[2-s, -s; 1, 1], D=[-s, s-1; 1, s-1]',txt,e and cp,f'a left coprime factorization is not unique; checked D^-1 N = H: {e}; left coprime (2x2 minors of [D N] share no root): {cp}. Reference itself: D^-1 N = H {e0}, coprime {c0}')
json.dump(C,open('audit/selection_audit_20261117/cas_results.json','w'),indent=1)
for r in C: print(r['id'],'equivalent' if r['equivalent'] else 'NOT equivalent','| symbolic',r['symbolic_zero'],'| relerr',r['max_rel_err'],'|',r['note'][:160])
