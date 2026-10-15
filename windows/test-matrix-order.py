"""Hermitian order checked with exact integer congruences of known inertia."""
import json
import random
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
WORKER=ROOT/'dist/QuantumStudio/quantum-worker.exe'
checks=0

def run(expression,approximate=False):
    return subprocess.run([str(WORKER),'--json']+(['--approx'] if approximate else []),
                          input='quantum:'+expression,encoding='utf-8',capture_output=True,timeout=60)

def verify(expression,expected,approximate=False):
    global checks
    result=run(expression,approximate)
    assert result.returncode==0,(expression,result.returncode,result.stderr)
    data=json.loads(result.stdout)
    assert data['text']==str(int(expected)),(expression,data)
    checks+=1

def matrix(a):
    def entry(z):
        r,i=int(z.real),int(z.imag)
        if i==0:return str(r)
        return f'({r}+({i})*i)'
    return '['+';'.join(','.join(entry(x) for x in row) for row in a)+']'

rng=random.Random(1919)
for n in (2,3,4,6):
    for trial in range(3):
        # Lower-triangular, unit-diagonal T is invertible exactly.
        t=[[complex(1 if r==c else rng.randrange(-2,3) if r>c else 0,
                    rng.randrange(-2,3) if r>c else 0) for c in range(n)] for r in range(n)]
        patterns=[[1+r for r in range(n)],[0]+[1]*(n-1),[1]*(n-1)+[0],[-1]+[1]*(n-1),[-1]*n]
        for d in patterns:
            a=[[sum(t[r][k]*d[k]*t[c][k].conjugate() for k in range(n)) for c in range(n)] for r in range(n)]
            source=matrix(a)
            verify(source+'>=0',min(d)>=0)
            verify(source+'>0',min(d)>0)
            verify('0<='+source,min(d)>=0,True)
            if n<=4:
                # A noncommuting Hermitian baseline checks A>=B as A-B>=0.
                b=[[complex(r+1) if r==c else complex(0,1 if r<c else -1) for c in range(n)] for r in range(n)]
                shifted=[[a[r][c]+b[r][c] for c in range(n)] for r in range(n)]
                verify(matrix(shifted)+'>='+matrix(b),min(d)>=0)

for expr,value in [
    ('[1,-1;-1,1]>=0',1),('[1,2;2,1]>=0',0),('[0,1;1,0]>=0',0),
    ('[0,0,0;0,1,0;0,0,0]>=0',1),('[0,0,0;0,1,0;0,0,0]>0',0),
    ('0<=density(|i>)<=I',1),('0<density(|i>)<I',0),
    ('I>=1',1),('I>1',0),('I<2',1),('2>I',1),('identity(3)>=1',1),
    ('-I<0',1),('-I<=0',1),('X<=0',0),('Z>=X',0),
    ('[1,1;1,1+1e-80]>0',1),('[1,1;1,1-1e-80]>=0',0),
    ('[1,1;1,1+1e-80]>=0',1),('[1,1;1,1-1e-80]>0',0),
    ('[1,sqrt(2);sqrt(2),2]>=0',1),('[1,sqrt(2);sqrt(2),2]>0',0),
    ('[1,i;-i,1]>=0',1),('identity(64)>0',1),('0identity(64)>=0',1),
    ('I=I',1),('3>=2',1),('1<2<3',1)]:
    verify(expr,value)
for relation in ['>=','≥','≽','⪰',r'\succeq',r'\succcurlyeq',r'\geq']:
    verify('density(|->) '+relation+' 0',1)
for relation in ['<=','≤','≼','⪯',r'\preceq',r'\preccurlyeq',r'\leq']:
    verify('0 '+relation+' density(|i>)',1)
for relation in ['>','≻',r'\succ']:
    verify('I '+relation+' 0',1)
for relation in ['<','≺',r'\prec']:
    verify('0 '+relation+' I',1)
verify(r'\begin{pmatrix}3/4&i/8\\-i/8&1/4\end{pmatrix}\succeq0',1)

invalid=['[1,1;0,1]>=0','[i,0;0,1]>=0','I>=identity(3)',
         '|0>>=0','[1,2]>=0','I>=i','[x,0;0,1]>=0',
         '[interval(-1,1),0;0,1]>=0','[infinity,0;0,1]>=0',
         'identity(65)>=0']
for expr in invalid:
    result=run(expr)
    assert result.returncode!=0,(expr,result.stdout)
print(f'PASS: {checks} exact matrix-order, inertia, singularity, tiny-pivot and notation checks; {len(invalid)} invalid inputs.')
