"""Compare every generator column with direct dense master-equation algebra."""
import json
import os
from pathlib import Path
import random
import subprocess

root = Path(__file__).resolve().parents[1]
worker = root / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
rng = random.Random(4197)

def mul(a, b):
    return [[sum(a[r][k]*b[k][c] for k in range(len(b)))
             for c in range(len(b[0]))] for r in range(len(a))]

def adj(a):
    return [[complex(a[c][r]).conjugate() for c in range(len(a))]
            for r in range(len(a[0]))]

def literal(a):
    return '[' + ';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)'
                                   for z in row) for row in a) + ']'

for d in (2, 3, 4):
    def random_matrix():
        return [[complex(rng.randrange(-2, 3), rng.randrange(-2, 3))/4
                 for _ in range(d)] for _ in range(d)]
    m = random_matrix()
    h = [[m[r][c]+m[c][r].conjugate() for c in range(d)] for r in range(d)]
    collapses = [random_matrix(), random_matrix()]
    constructor = 'liouvillian(' + literal(h) + ',vector(' + ','.join(map(literal, collapses)) + '))'
    for j in range(d*d):
        rho = [[complex(r+d*c == j) for c in range(d)] for r in range(d)]
        left, right = mul(h, rho), mul(rho, h)
        expected = [[-1j*(left[r][c]-right[r][c]) for c in range(d)] for r in range(d)]
        for collapse in collapses:
            cd = adj(collapse)
            jump = mul(mul(collapse, rho), cd)
            rate = mul(cd, collapse)
            loss1, loss2 = mul(rate, rho), mul(rho, rate)
            for r in range(d):
                for c in range(d):
                    expected[r][c] += jump[r][c] - (loss1[r][c]+loss2[r][c])/2
        column = [[expected[r][c]] for c in range(d) for r in range(d)]
        expression = f'quantum:norm({constructor}basis({j},{d*d})-{literal(column)})'
        result = subprocess.run([str(worker), '--json'], input=expression,
                                encoding='utf-8', capture_output=True, env=env, timeout=20)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['text'] == '0', (d, j, data)
    print(f'PASS: all {d**4} complex generator entries at dimension {d} match direct master-equation algebra')
