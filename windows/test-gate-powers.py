"""Independent known-spectrum checks for principal fractional unitary powers."""
import cmath
import json
import math
import os
import re
from pathlib import Path
import subprocess

worker = Path(__file__).resolve().parents[1] / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
def literal(matrix):
    return '[' + ';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)' for z in row) for row in matrix) + ']'
def evaluate(expression, approximate=False):
    assert len(expression.encode())<=32768
    result = subprocess.run([str(worker),'--json']+(['--approx'] if approximate else []), input=expression,
                            encoding='utf-8', capture_output=True, env=env, timeout=30)
    assert result.returncode == 0, (expression[:100], result.stderr)
    return json.loads(result.stdout)

def error_bound(text):
    text = text.replace('−','-')
    interval = re.fullmatch(r'interval\(([^,]+),\s*([^\)]+)\)',text)
    return max(abs(float(v)) for v in interval.groups()) if interval else abs(complex(text.replace(' ','').replace('i','j')))

checks = 0
for n in (2,3,4,8,16):
    # +/- phases share the eigenvalues of Re(U); +/-pi uses the +pi branch.
    phases = [0.37*(-1)**k*(1+k//2) for k in range(n)]
    phases[-1] = math.pi
    for pattern in (phases, [0.8 if k%2 else -0.8 for k in range(n)]):
        basis = [[cmath.exp(1j*(2*math.pi*r*k/n+math.sin(r+1)))/math.sqrt(n)
                  for k in range(n)] for r in range(n)]
        def spectral(exponent):
            return [[sum(basis[r][k]*cmath.exp(1j*exponent*pattern[k])*basis[c][k].conjugate()
                         for k in range(n)) for c in range(n)] for r in range(n)]
        matrix = literal(spectral(1))
        for exponent in (0.5, -0.5, 0.3, 1.7):
            expected = literal(spectral(exponent))
            result = evaluate(f'qnorm(qvec(qpower({matrix},{exponent})-{expected}))')
            error = error_bound(result['text'])
            assert result['approximate'] and error<2e-10, (n,exponent,error)
            checks += 1
    print(f'PASS: dense complex {n}x{n} powers, branch cut and degenerate cosine eigenspaces')

for n in (2,3,8,16):
    basis = [[cmath.exp(1j*(2*math.pi*r*k/n+math.cos(r+1)))/math.sqrt(n)
              for k in range(n)] for r in range(n)]
    for eigenvalues in ([float(k+1) for k in range(n)], [(-1.0)**k*(k+1) for k in range(n)], [float(k) for k in range(n)]):
        def hermitian_spectral(exponent):
            values = [complex(x)**exponent for x in eigenvalues]
            return [[sum(basis[r][k]*values[k]*basis[c][k].conjugate() for k in range(n)) for c in range(n)] for r in range(n)]
        for exponent in ((0.5,0.3) if eigenvalues[0]==0 else (0.5,-0.5,0.3)):
            result = evaluate(f'qnorm(qvec(qpower({literal(hermitian_spectral(1))},{exponent})-{literal(hermitian_spectral(exponent))}))')
            assert error_bound(result['text'])<2e-10, (n,eigenvalues,exponent,result)
            checks += 1
    print(f'PASS: dense complex {n}x{n} Hermitian powers, including negative and zero eigenvalues')

# The numerical path is required for these larger dense matrices. Inspect the
# full matrix through a scalar residual, beyond the JSON cell-display limit.
for bits in (5,6):
    expression = f'quantum:tr((QFT({bits})^(1/2)*QFT({bits})^(1/2)-QFT({bits}))†(QFT({bits})^(1/2)*QFT({bits})^(1/2)-QFT({bits})))'
    result = evaluate(expression, True)
    assert error_bound(result['text'])<1e-16, result
    checks += 1
print(f'{checks} independent gate-power checks passed')
