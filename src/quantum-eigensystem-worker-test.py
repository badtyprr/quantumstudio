#!/usr/bin/env python3
"""Public Hermitian eigensystem route, numerical residuals and Copy/re-entry."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else
              'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()
checks = 0


def evaluate(expression, success=True):
    global checks
    result = subprocess.run([str(worker), '--json'], input=('quantum:' + expression).encode(),
                            capture_output=True, timeout=30)
    checks += 1
    assert (result.returncode == 0) == success, (expression, result.stderr)
    if not success:
        assert not result.stdout and b'Hermitian' in result.stderr, (expression, result.stderr)
        return
    assert not result.stderr, (expression, result.stderr)
    return json.loads(result.stdout)


def cells(result):
    return [[complex(x.replace('−', '-').replace(' ', '').replace('i', 'j'))
             for x in row] for row in result['cells']]


def verify(expression, matrix, expected):
    n = len(matrix)
    values = evaluate('heigenvalues(' + expression + ')')
    vectors = evaluate('heigenvectors(' + expression + ')')
    assert values['approximate'] and vectors['approximate']
    assert (values['rows'], values['columns']) == (n, 1)
    assert (vectors['rows'], vectors['columns']) == (n, n)
    eigenvalues, eigenvectors = cells(values), cells(vectors)
    # Public values have 12-digit precision metadata; compare with 1e-10 here.
    for k in range(n):
        value = eigenvalues[k][0]
        assert abs(value-expected[k]) < 1e-10, (expression, value, expected[k])
        for r in range(n):
            assert abs(sum(matrix[r][c]*eigenvectors[c][k] for c in range(n)) -
                       value*eigenvectors[r][k]) < 1e-10
        for j in range(n):
            assert abs(sum(eigenvectors[r][j].conjugate()*eigenvectors[r][k]
                           for r in range(n)) - int(j == k)) < 1e-10
    for result in (values, vectors):
        replay = evaluate(result['copy_text'])
        assert (replay['rows'], replay['columns']) == (result['rows'], result['columns'])
        assert all(abs(a-b) < 1e-10 for ar,br in zip(cells(result),cells(replay)) for a,b in zip(ar,br))


# IBM-092 cell4 tridiagonal matrix: analytic sine modes, 4-2cos(k*pi/4).
verify('[4,-1,0;-1,4,-1;0,-1,4]', [[4,-1,0],[-1,4,-1],[0,-1,4]],
       [4-math.sqrt(2), 4, 4+math.sqrt(2)])
# Complex phase and repeated eigenvalue controls, independent of source prose.
verify('[0,-i;i,0]', [[0,-1j],[1j,0]], [-1,1])
verify('[2,0,0;0,2,0;0,0,-1]', [[2,0,0],[0,2,0],[0,0,-1]], [-1,2,2])
verify('matrix(1,1,[7])', [[7]], [7])
verify('[0,0;0,0]', [[0,0],[0,0]], [0,0])
for name in ('heigenvalues', 'heigenvectors'):
    for bad in ('[1,2;0,1]', '[1,2,3;4,5,6]', '[x,0;0,1]', '[inf,0;0,1]',
                'qidentity(65)', '2'):
        evaluate(name + '(' + bad + ')', False)
print('PASS:', checks, 'Hermitian eigensystem worker requests')
