"""Independent Schmidt-spectrum checks, including dense complex local bases."""
import cmath
import json
import math
import os
from pathlib import Path
import subprocess

worker = Path(__file__).resolve().parents[1] / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
for a, b in ((2, 2), (2, 3), (3, 3), (4, 4), (4, 8), (8, 8)):
    probabilities = [(k+1)/(a*(a+1)/2) for k in range(a)]
    # Independent Fourier bases and row phases preserve Schmidt coefficients.
    u = [[cmath.exp(1j*(2*math.pi*r*k/a+math.sin(r+1)))/math.sqrt(a)
          for k in range(a)] for r in range(a)]
    v = [[cmath.exp(1j*(2*math.pi*r*k/b+math.cos(r+1)))/math.sqrt(b)
          for k in range(a)] for r in range(b)]
    ket = [sum(math.sqrt(probabilities[k])*u[r][k]*v[s][k] for k in range(a))
           for r in range(a) for s in range(b)]
    literal = '[' + ';'.join(f'({z.real:.17g}+({z.imag:.17g})*i)' for z in ket) + ']'
    negativity = (sum(math.sqrt(p) for p in probabilities)**2-1)/2
    for name, expected in (('negativity', negativity), ('lognegativity', math.log2(1+2*negativity))):
        for subsystem in (0, 1):
            expression = f'q{name}dim({literal},{subsystem},[{a},{b}])'
            result = subprocess.run([str(worker), '--json'], input=expression,
                                    encoding='utf-8', capture_output=True, env=env, timeout=30)
            assert result.returncode == 0, (a,b,name,result.stderr)
            data = json.loads(result.stdout)
            assert data['approximate'] and abs(float(data['text'])-expected)<2e-10, (a,b,name,data,expected)
    print(f'PASS: dense complex {a}x{b} bipartition, both subsystems and measures')
