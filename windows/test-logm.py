"""Compare matrix logarithms with independently prescribed complex spectra."""
import cmath
import json
import math
import os
from pathlib import Path
import re
import subprocess

worker = Path(__file__).resolve().parents[1] / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
def literal(matrix):
    return '['+';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)' for z in row) for row in matrix)+']'
def evaluate(expression, timeout=30):
    assert len(expression.encode())<=32768
    result = subprocess.run([str(worker),'--json','--approx'], input=expression,
                            encoding='utf-8', capture_output=True, env=env, timeout=timeout)
    assert result.returncode==0, (expression[:120],result.stderr)
    data = json.loads(result.stdout)
    text = data['text'].replace('−','-')
    interval = re.fullmatch(r'interval\(([^,]+),\s*([^\)]+)\)',text)
    error = max(abs(float(v)) for v in interval.groups()) if interval else abs(complex(text.replace(' ','').replace('i','j')))
    assert error<2e-9, data

checks = 0
for n in (2,3,4,8,16):
    basis = [[cmath.exp(1j*(2*math.pi*r*k/n+math.sin(r+1)))/math.sqrt(n)
              for k in range(n)] for r in range(n)]
    phases = [0.31*(-1)**k*(1+k//2) for k in range(n)]
    phases[-1] = math.pi
    spectra = [([cmath.exp(1j*p) for p in phases],[1j*p for p in phases]),
               ([cmath.exp(1j*(0.8 if k%2 else -0.8)) for k in range(n)],[1j*(0.8 if k%2 else -0.8) for k in range(n)]),
               ([complex(k+1) for k in range(n)],[complex(math.log(k+1)) for k in range(n)]),
               ([complex((-1)**k*(k+1)) for k in range(n)],[complex(math.log(k+1),math.pi if k%2 else 0) for k in range(n)])]
    if n<=8:
        for scale in (1e-200,1e200):
            spectra.append(([complex(scale*(k+1)) for k in range(n)], [complex(math.log(scale)+math.log(k+1)) for k in range(n)]))
    def matrix(values):
        return [[sum(basis[r][k]*values[k]*basis[c][k].conjugate() for k in range(n)) for c in range(n)] for r in range(n)]
    for values, logarithms in spectra:
        actual = literal(matrix(values));expected = literal(matrix(logarithms))
        evaluate(f'qnorm(qvec(qlogm({actual})-{expected}))')
        checks += 1
    print(f'PASS: {n}x{n} dense unitary and Hermitian logarithms match independent spectra')

for expression in (
    'quantum:norm(vec(expm(logm(H*S))-H*S))',
    'quantum:norm(vec(expm(logm(iSWAP))-iSWAP))',
    'quantum:norm(vec(logm(H*S)†+logm(H*S)))',
    'quantum:norm(evolution(i*logm(H*S),1)|0>-H*S|0>)',
    'quantum:norm(vec(expm(logm(SWAP))-SWAP))',
    'quantum:tr((expm(logm(QFT(6)))-QFT(6))†(expm(logm(QFT(6)))-QFT(6)))',
):
    evaluate(expression,180 if 'QFT(6)' in expression else 30);checks += 1
print(f'{checks} independent logarithm and reconstruction checks passed')
