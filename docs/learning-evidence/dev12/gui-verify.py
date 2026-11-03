"""Independently verify real GUI clipboard contents and numerical re-entries."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

package, evidence = map(Path, sys.argv[1:])
worker = package / 'quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(package / 'data'))
records = []


def evaluate(expression, approximate=False):
    process = subprocess.run([str(worker), '--json'] + (['--approx'] if approximate else []),
                             input=('quantum:' + expression).encode(), capture_output=True,
                             env=env, timeout=30)
    record = dict(expression=expression, approximate=approximate, returncode=process.returncode,
                  stdout=process.stdout.decode(), stderr=process.stderr.decode())
    records.append(record)
    assert process.returncode == 0 and not process.stderr, record
    return json.loads(process.stdout)


def matrix(result):
    return [[complex(x.replace('−', '-').replace(' ', '').replace('i', 'j'))
             for x in row] for row in result['cells']]


try:
    for prefix in ('copy', 'reentry'):
        texts = [(evidence / (prefix + '-' + str(i) + '.txt')).read_text(encoding='utf-8-sig')
                 for i in range(7)]
        identities = ['(' + texts[0] + ')-2',
                      'norm(vec((' + texts[1] + ')-(sqrt(3)*|100>-i*|111>)/2))',
                      'replace((' + texts[2] + '),x,pi/2)+471/2000',
                      '(' + texts[3] + ')+2']
        for expression in identities:
            result = evaluate(expression)
            assert result['text'] == '0' and not result['approximate'], result
        values = evaluate(texts[4], True)
        assert (values['rows'], values['columns']) == (3, 1)
        eigenvalues = [r[0] for r in matrix(values)]
        assert all(abs(a-b) < 1e-10 for a,b in zip(eigenvalues, [4-math.sqrt(2),4,4+math.sqrt(2)]))
        for index, operator, spectrum in [(5, [[4,-1,0],[-1,4,-1],[0,-1,4]], eigenvalues),
                                          (6, [[0,-1j],[1j,0]], [-1,1])]:
            vectors = evaluate(texts[index], True)
            n = len(operator)
            assert (vectors['rows'], vectors['columns']) == (n, n)
            v = matrix(vectors)
            for j in range(n):
                for r in range(n):
                    assert abs(sum(operator[r][c]*v[c][j] for c in range(n))-spectrum[j]*v[r][j]) < 1e-10
                for k in range(n):
                    assert abs(sum(v[r][j].conjugate()*v[r][k] for r in range(n))-int(j==k)) < 1e-10
    print('PASS: 14 independent GUI clipboard/re-entry comparisons')
finally:
    (evidence / 'independent-verification.json').write_text(json.dumps(dict(
        worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
        records=records), indent=2) + '\n', encoding='utf-8')
