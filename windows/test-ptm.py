"""Independent dense Kraus-to-PTM checks using the defining trace formula."""
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

def multiply(a, b):
    return [[sum(a[r][k]*b[k][c] for k in range(len(b)))
             for c in range(len(b[0]))] for r in range(len(a))]

def dagger(a):
    return [[complex(a[c][r]).conjugate() for c in range(len(a))]
            for r in range(len(a[0]))]

def tensor(a, b):
    return [[x*y for x in ar for y in br] for ar in a for br in b]

def literal(a):
    return '[' + ';'.join(','.join(f'({z.real:g}+({z.imag:g})*i)'
                                   for z in row) for row in a) + ']'

rng = random.Random(1097)
for qubits in (1, 2):
    d = 2**qubits
    # Dyadic complex entries preserve exact decimal outputs. These completely
    # positive maps need not preserve trace; conversion must not normalize them.
    kraus = [[[complex(rng.randrange(-2, 3), rng.randrange(-2, 3))/4
               for _ in range(d)] for _ in range(d)] for _ in range(2)]
    basis = []
    for axes in itertools.product(range(4), repeat=qubits):
        p = [[1]]
        for axis in axes:
            p = tensor(p, paulis[axis])
        basis.append(p)
    constructor = 'ptm(vector(' + ','.join(literal(k) for k in kraus) + '))'
    for j, p in enumerate(basis):
        branches = [multiply(multiply(k, p), dagger(k)) for k in kraus]
        evolved = [[sum(b[r][c] for b in branches) for c in range(d)]
                   for r in range(d)]
        expected = []
        for q in basis:
            product = multiply(q, evolved)
            expected.append(sum(product[k][k] for k in range(d))/d)
        expression = f'quantum:{constructor}basis({j},{d*d})'
        result = subprocess.run([str(worker), '--json'], input=expression,
                                encoding='utf-8', capture_output=True, env=env, timeout=20)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        actual = [float(row[0].replace('−', '-')) for row in data['cells']]
        assert len(actual) == len(expected), data
        assert max(abs(a-b) for a, b in zip(actual, expected)) < 1e-12, (qubits, j, actual, expected)
    print(f'PASS: all {d*d*d*d} entries of a dense complex {qubits}-qubit PTM match the independent trace formula')
