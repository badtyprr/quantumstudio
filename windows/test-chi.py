"""Independent complex process-matrix checks from Pauli expansion coefficients."""
import itertools
import json
import os
from pathlib import Path
import random
import subprocess

root = Path(__file__).resolve().parents[1]
worker = root / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
paulis = [[[1, 0], [0, 1]], [[0, 1], [1, 0]],
          [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]]

def tensor(a, b):
    return [[x*y for x in ar for y in br] for ar in a for br in b]

def literal(a):
    return '[' + ';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)'
                                   for z in row) for row in a) + ']'

rng = random.Random(7513)
for qubits in (1, 2):
    d = 2**qubits
    kraus = [[[complex(rng.randrange(-2, 3), rng.randrange(-2, 3))/4
               for _ in range(d)] for _ in range(d)] for _ in range(3)]
    basis = []
    for axes in itertools.product(range(4), repeat=qubits):
        p = [[1]]
        for axis in axes:
            p = tensor(p, paulis[axis])
        basis.append(p)
    traces = [[sum(p[r][c]*k[c][r] for r in range(d) for c in range(d))
               for p in basis] for k in kraus]
    expected = [[sum(t[i]*t[j].conjugate() for t in traces)/d
                 for j in range(d*d)] for i in range(d*d)]
    constructor = 'chi(vector(' + ','.join(literal(k) for k in kraus) + '))'
    # Compare all complex columns with exact dyadic reference coefficients.
    for j in range(d*d):
        column = [[expected[i][j]] for i in range(d*d)]
        expression = f'quantum:norm({constructor}basis({j},{d*d})-{literal(column)})'
        result = subprocess.run([str(worker), '--json'], input=expression,
                                encoding='utf-8', capture_output=True, env=env, timeout=20)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['text'] == '0', (qubits, j, data)
    print(f'PASS: all {d**4} complex chi entries for {qubits} qubits match independent Pauli traces')
