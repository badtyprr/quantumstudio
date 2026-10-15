"""Independent prescribed-spectrum checks for Schmidt coefficients."""
import cmath, math, json, os, subprocess
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(expression):
    p=subprocess.run([str(worker),'--json'],input=expression,encoding='utf-8',capture_output=True,env=env,timeout=30)
    assert p.returncode==0,(expression[:100],p.stderr)
    data=json.loads(p.stdout)
    assert data['approximate'],data
    return [float(row[0].replace('−','-')) for row in data['cells']]
checks=0
for dims,selected in [([2,2],[0]),([2,3],[1]),([2,3,4],[0,2]),([4,4],[0]),([8,8],[1]),([16,16],[0])]:
    n=math.prod(dims);a=math.prod(dims[i] for i in selected);b=n//a;rank=min(a,b)
    for deficient in (False,True):
        values=[(0 if deficient and k>=rank//2 else (k+1)) for k in range(rank)]
        weight=math.sqrt(sum(v*v for v in values));values=[v/weight for v in values]
        # Distinct Fourier bases with row phases: U diag(values) V^T.
        u=[[cmath.exp(1j*(2*math.pi*r*k/a+math.sin(r+1)))/math.sqrt(a) for k in range(rank)] for r in range(a)]
        v=[[cmath.exp(1j*(2*math.pi*r*k/b+math.cos(r+2)))/math.sqrt(b) for k in range(rank)] for r in range(b)]
        amplitudes=[]
        for index in range(n):
            left=right=0;stride=n
            for j,d in enumerate(dims):
                stride//=d;digit=(index//stride)%d
                if j in selected:left=left*d+digit
                else:right=right*d+digit
            amplitudes.append(sum(u[left][k]*values[k]*v[right][k] for k in range(rank)))
        # Nine decimal digits suffice for the independent absolute-error check.
        literal='['+';'.join(f'({z.real:.9g}+({z.imag:.9g})*i)' for z in amplitudes)+']'
        expression='qschmidtdim('+literal+',vector('+','.join(map(str,selected))+'),vector('+','.join(map(str,dims))+'))'
        assert len(expression.encode())<=32000
        actual=evaluate(expression);expected=sorted(values,reverse=True)
        assert len(actual)==rank and max(abs(x-y) for x,y in zip(actual,expected))<2e-9,(dims,selected,actual,expected)
        checks+=1
        complement=[k for k in range(len(dims)) if k not in selected]
        other='qschmidtdim('+literal+',vector('+','.join(map(str,complement))+'),vector('+','.join(map(str,dims))+'))'
        alternate=evaluate(other)
        assert len(alternate)==rank and max(abs(x-y) for x,y in zip(actual,alternate))<2e-11,(dims,actual,alternate)
        checks+=1
for scale in ('1','1e200','1e-200'):
    actual=evaluate('quantum:schmidt_coeffs('+scale+'*(|00>+1e-12|11>),0)')
    assert abs(actual[0]-1)<1e-11 and abs(actual[1]-1e-12)<1e-23,actual
    checks+=1
rotated=evaluate('quantum:schmidt_coeffs((H@H)(|00>+1e-12|11>),0)')
assert abs(rotated[1]-1e-12)<2e-16,rotated
checks+=1
actual=evaluate('quantum:schmidt_coeffs(vec(QFT(5)),[0,1,2,3,4])')
assert len(actual)==32 and max(abs(v-1/math.sqrt(32)) for v in actual)<2e-11,actual
checks+=1
print(f'PASS: {checks} Schmidt checks: prescribed complex spectra, mixed dimensions, nonadjacent partitions, rank deficiency, small coefficients, scaling, and 1024 amplitudes.')
