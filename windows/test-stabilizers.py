"""Check native stabilizer operations against independent numeric eigenspaces."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np

worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),'Y':np.array([[0,-1j],[1j,0]]),'Z':np.diag([1,-1])}
def matrix(label):
    result=np.array([[1]])
    sign=-1 if label.startswith('-') else 1
    for letter in label.lstrip('-'):
        result=np.kron(result,P[letter])
    return sign*result
def generators(labels):
    return 'vector('+','.join('pauli("'+label+'")' for label in labels)+')'
def run(expr,approx=False):
    return subprocess.run([str(worker),'--json']+(['--approx'] if approx else []),input='quantum:'+expr,
                          encoding='utf-8',capture_output=True,timeout=60)
def text(expr):
    p=run(expr);assert p.returncode==0,(expr,p.stderr);return json.loads(p.stdout)['text']
def literal(a):
    return '['+';'.join(','.join(f'({complex(v).real:.17g})+({complex(v).imag:.17g})*i' for v in row) for row in a)+']'
def compare(expr,expected):
    if expected.size>128:
        for c in range(expected.shape[1]):
            compare('('+expr+')basis('+str(c)+','+str(expected.shape[1])+')',expected[:,c:c+1])
        return
    p=run('norm(vec(('+expr+')-('+literal(expected)+')))',True)
    assert p.returncode==0,(expr,p.stderr)
    value=complex(json.loads(p.stdout)['text'].replace('−','-').replace(' ','').replace('i','j'))
    assert abs(value)<1e-10,(expr,value)

valid=invalid=0
labels=[''.join(x) for x in itertools.product('IXYZ',repeat=2)]
labels+=['-'+x for x in labels]
for pair in itertools.combinations_with_replacement(labels,2):
    a,b=map(matrix,pair)
    source=generators(pair)
    commuting=np.allclose(a@b,b@a)
    if commuting:
        values,vectors=np.linalg.eigh(a+b)
        space=vectors[:,np.isclose(values,2)]
    if not commuting or space.shape[1]==0:
        p=run('stabilizer_dimension('+source+')')
        assert p.returncode!=0,(pair,p.stdout)
        invalid+=1
        continue
    expected=space@space.conj().T
    assert text('stabilizer_dimension('+source+')')==str(space.shape[1]),pair
    compare('stabilizer_projector('+source+')',expected)
    valid+=1

assert text('stabilizer_dimension(vector(pauli("XX"),pauli("ZZ"),pauli("-YY")))')=='1'
compare('stabilizer_projector(vector(pauli("XX"),pauli("ZZ"),pauli("-YY")))',matrix('II')*0+np.array([[.5,0,0,.5],[0,0,0,0],[0,0,0,0],[.5,0,0,.5]]))
assert run('stabilizer_projector(vector(pauli("XX"),pauli("ZZ"),pauli("YY")))').returncode!=0

# IBM's five-qubit code: every weight-one Pauli error has a distinct nonzero syndrome.
code=['XZZXI','IXZZX','XIXZZ','ZXIXZ']
source=generators(code)
assert text('stabilizer_dimension('+source+')')=='2'
values,vectors=np.linalg.eigh(sum(map(matrix,code)))
space=vectors[:,np.isclose(values,4)]
compare('stabilizer_projector('+source+')',space@space.conj().T)
syndromes=set()
for wire in range(5):
    for axis in 'XYZ':
        label='I'*wire+axis+'I'*(4-wire)
        error=matrix(label)
        expected=[int(not np.allclose(matrix(g)@error,error@matrix(g))) for g in code]
        got=text('stabilizer_syndrome('+source+',pauli("'+label+'"))')
        wanted='['+'  '.join(map(str,expected))+']'
        assert got==wanted,(label,got,wanted)
        assert any(expected) and tuple(expected) not in syndromes
        syndromes.add(tuple(expected))

for bad in ['vector()','vector(X,Z)','vector(X,2X)','vector(H)','vector(iX)','vector(-I)',
            'vector(X,X@X)','vector([1,0,0;0,1,0;0,0,1])','vector(pauli("XX"),pauli("ZZ"),pauli("YY"))']:
    assert run('stabilizer_projector('+bad+')').returncode!=0,bad
assert text('stabilizer_dimension(I)')=='2'
assert text('stabilizer_dimension(pauli("IIIIIIIII"))')=='512'
assert text('stabilizer_syndrome(vector(Z),iX)')=='1'
print(f'PASS: {valid} two-qubit eigenspace projectors, {invalid} invalid generator pairs, five-qubit code dimension/projector and 15 distinct error syndromes, validation and nine-qubit bounds.')
