"""Acceptance tests for numeric exponent/factor boundaries; red on released 52c37a2a."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from run import Q, parse_cell

ap = argparse.ArgumentParser()
ap.add_argument('--worker', type=Path, required=True)
ap.add_argument('--definitions', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--translator', type=Path, help='Use a separately built parser before the released evaluator')
a = ap.parse_args()
cases = []
for exponent in (0, 1, 2, -1):
    for power in (str(exponent), '{'+str(exponent)+'}'):
        expression = r'(-1)^'+power+r' \bigl( \vert 0\rangle - \vert 1\rangle \bigr)'
        sign = -1 if exponent % 2 else 1
        cases.append((expression, [Q(sign), Q(-sign)]))
cases += [
    ('2^2(3+4)', [Q(28)]),
    ('2(3+4)^2', [Q(98)]),
    ('(2(3+4))^2', [Q(196)]),
    ('2^3^2', [Q(512)]),
    ('2^-2', [Q('1/4')]),
    ('2^Tr(I)', [Q(4)]),
    ('2^1e0(3+4)', [Q(14)]),
    ('2^0.5(3+4)', [Q(0, 7)]),
    ('2^10_2(3+4)', [Q(28)]),
    ('(-1)^0*(|0>-|1>)', [Q(1), Q(-1)]),
    ('2^10(3+4)', [Q(7168)]),
    ('4^(1/2)(3+4)', [Q(14)]),
    ('4^{1/2}(3+4)', [Q(14)]),
    ('2^(-2)(8)', [Q(2)]),
    ('2(+3)^2', [Q(18)]),
    ('-2(3+4)', [Q(-14)]),
    ('3e-2(100)', [Q(3)]),
    ('2(3)(4)', [Q(24)]),
    ('sin(pi/2)', [Q(1)]),
    ('sqrt(4)(3+4)', [Q(14)]),
    ('2^sin(pi/2)', [Q(2)]),
    ('2^(3^2)', [Q(512)]),
]
rows = []
for expression, expected in cases:
    wire_input = 'quantum:'+expression
    if a.translator:
        translation = subprocess.run([str(a.translator)], input=expression.encode(), capture_output=True, timeout=30)
        assert translation.returncode == 0, translation.stderr.decode()
        wire_input = translation.stdout.decode().strip()
    p = subprocess.run([str(a.worker), '--json'], input=wire_input.encode(),
                       capture_output=True, timeout=30,
                       env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(a.definitions)))
    row = dict(input=expression, evaluator_input=wire_input, expected=[x.record() for x in expected],
               returncode=p.returncode, stdout=p.stdout.decode(), stderr=p.stderr.decode())
    try:
        value = json.loads(row['stdout'])
        cells = value['cells'] if value['rows'] else [[value['text']]]
        row['pass'] = (value['approximate'] is False and value['columns'] in (0, 1)
                       and [parse_cell(x[0]) for x in cells] == expected)
        if row['pass']:
            replay = subprocess.run([str(a.worker), '--json'], input=value['copy_text'].encode(),
                                    capture_output=True, timeout=30,
                                    env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(a.definitions)))
            row['copy_reentry'] = dict(returncode=replay.returncode, stdout=replay.stdout.decode(), stderr=replay.stderr.decode())
            copied = json.loads(replay.stdout.decode())
            copied_cells = copied['cells'] if copied['rows'] else [[copied['text']]]
            row['pass'] = (replay.returncode == 0 and copied['approximate'] is False
                           and copied['rows'] == value['rows'] and copied['columns'] == value['columns']
                           and [parse_cell(x[0]) for x in copied_cells] == expected)
    except (ValueError, KeyError, SyntaxError):
        row['pass'] = False
    rows.append(row)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(json.dumps(dict(passed=sum(r['pass'] for r in rows), total=len(rows),
                     failed=[r['input'] for r in rows if not r['pass']])))
raise SystemExit(0 if all(r['pass'] for r in rows) else 1)
