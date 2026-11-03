#!/usr/bin/env python3
"""Exact DEV-17 worker checks; independent rational matrices and Copy re-entry."""
import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
from fractions import Fraction as F
from pathlib import Path


def projector(n, index):
    return [[F(r == c == index) for c in range(n)] for r in range(n)]


def outer(vector, norm):
    return [[F(x * y, norm) for y in vector] for x in vector]


def tensor(a, b):
    return [[x * y for x in ar for y in br] for ar in a for br in b]


def matrix_text(matrix):
    return '[' + ';'.join(','.join(str(x) for x in row) for row in matrix) + ']'


def exact_copy_cells(text):
    # Display cells may use rounded decimals even for exact rational results.
    # Copy is the lossless representation; compare every rational entry there.
    match = re.fullmatch(r'matrix\((\d+),(\d+),\[(.*)\]\)', text)
    if not match:
        raise ValueError('Expected an explicit rational matrix copy: ' + text)
    rows, columns = int(match[1]), int(match[2])
    cells = [F(''.join(x.replace('\u2212', '-').replace('\u2215', '/').split())) for x in match[3].split(',')]
    if len(cells) != rows * columns:
        raise ValueError('Copy matrix dimensions and entries disagree')
    return [cells[i * columns:(i + 1) * columns] for i in range(rows)]


def contraction(matrix, dims, removed):
    """Independent definition: sum diagonal blocks via explicit basis tuples."""
    kept = [i for i in range(len(dims)) if i not in removed]
    tuples = list(itertools.product(*(range(dims[i]) for i in kept)))
    traced = list(itertools.product(*(range(dims[i]) for i in removed)))

    def index(retained, discarded):
        digits = dict(zip(kept, retained))
        digits.update(zip(removed, discarded))
        result = 0
        for i, dimension in enumerate(dims):
            result = result * dimension + digits[i]
        return result

    return [[sum((matrix[index(a, t)][index(b, t)] for t in traced), F(0))
             for b in tuples] for a in tuples]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, default=Path(os.environ.get('QUANTUM_WORKER', 'quantum-worker.exe' if os.name == 'nt' else 'quantum-worker')))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--revision', default='unspecified; identify via binary manifest')
    args = parser.parse_args()
    worker = args.worker.resolve()
    sha = hashlib.sha256(worker.read_bytes()).hexdigest()
    env = dict(os.environ)
    if (worker.parent / 'data').is_dir():
        env['QALCULATE_DEFINITIONS_DIR'] = str(worker.parent / 'data')
    rows = []

    def run(expression):
        result = subprocess.run([str(worker), '--json'], input='quantum: ' + expression,
                                encoding='utf-8', capture_output=True, env=env, timeout=60)
        return dict(input=expression, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    def check(name, expression, expected):
        row = run(expression)
        row.update(name=name, expected=[[str(x) for x in r] for r in expected])
        try:
            value = json.loads(row['stdout'])
            row['passed'] = (row['exit_code'] == 0 and not row['stderr'] and value['approximate'] is False
                             and value['rows'] == len(expected) and value['columns'] == len(expected[0])
                             and exact_copy_cells(value['copy_text']) == expected)
        except (ValueError, KeyError, TypeError):
            row['passed'] = False
        rows.append(row)
        if row['passed']:
            copied = run(value['copy_text'])
            replay = json.loads(copied['stdout']) if copied['exit_code'] == 0 else {}
            copied.update(name=name + ' result Copy/re-entry', passed=(copied['exit_code'] == 0 and not copied['stderr']
                          and replay.get('rows') == len(expected) and replay.get('columns') == len(expected[0])
                          and replay.get('approximate') is False and replay.get('cells') == value['cells']
                          and exact_copy_cells(replay.get('copy_text', '')) == expected))
            rows.append(copied)

    def mapped(matrix, labels, dims):
        return 'subsystems(' + matrix + ',[' + ','.join(labels) + '],[' + ','.join(map(str, dims)) + '])'

    def trace(name, matrix, labels, dims, removed, expected, tex=False):
        value = mapped(matrix, labels, dims)
        chosen = [labels[i] for i in removed]
        expression = (r'\operatorname{Tr}_{' + ','.join(r'\mathsf{' + x + '}' for x in chosen) + '}(' + value + ')'
                      if tex else 'ptrace(' + value + ',[' + ','.join(chosen) + '])')
        check(name, expression, expected)

    half_identity = [[F(1, 2), F(0)], [F(0), F(1, 2)]]
    for a, b in [('00', '11'), ('01', '10')]:
        for sign in ['+', '-']:
            for removed in [0, 1]:
                trace('Bell ' + a + sign + b + ' discard ' + str(removed),
                      f'density((|{a}>{sign}|{b}>)/sqrt(2))', ['B', 'A'], [2, 2], [removed], half_identity)
    rho = [[F(1, 2), 0, 0, 0], [0, 0, 0, 0], [0, 0, F(1, 4), F(1, 4)], [0, 0, F(1, 4), F(1, 4)]]
    right_mixture = [[F(3, 4), F(1, 4)], [F(1, 4), F(1, 4)]]
    for labels in [['A', 'B'], ['B', 'A'], ['X', 'Z'], ['pi', 'i'], ['sin', 'vector'], ['ancilla_2', 'data']]:
        for removed, expected in [(0, right_mixture), (1, half_identity)]:
            for tex in [False, True]:
                trace('IBM mixture ' + str(labels) + str(removed) + str(tex), matrix_text(rho), labels, [2, 2], [removed], expected, tex)
    for removed in [0, 1]:
        trace('product |01> ' + str(removed), 'density(|01>)', ['B', 'A'], [2, 2], [removed], projector(2, 1 - removed))
    qutrit = outer([1, 2, 3], 14)
    plus = outer([1, 1], 2)
    product = tensor(projector(2, 1), qutrit)
    trace('2x3 left', matrix_text(product), ['Z', 'A'], [2, 3], [0], qutrit)
    trace('2x3 right', matrix_text(product), ['Z', 'A'], [2, 3], [1], projector(2, 1))
    reversed_product = tensor(qutrit, projector(2, 1))
    trace('physically permuted factors', matrix_text(reversed_product), ['A', 'Z'], [3, 2], [1], qutrit)
    three = tensor(tensor(projector(2, 1), qutrit), plus)
    trace('middle factor 2x3x2', matrix_text(three), ['C', 'A', 'B'], [2, 3, 2], [1], tensor(projector(2, 1), plus), True)
    trace('multiple factors reverse selection', matrix_text(three), ['C', 'A', 'B'], [2, 3, 2], [2, 0], qutrit, True)
    correlated = outer([1, 2, 3, 4, 5, 6], 91)
    for removed in [0, 1]:
        trace('correlated 2x3 ' + str(removed), matrix_text(correlated), ['right', 'left'], [2, 3], [removed], contraction(correlated, [2, 3], [removed]))

    # A copied evaluated declaration, not merely its input text, must carry the
    # same order/dimensions. Re-enter and use each retained mapping independently.
    for labels, dims, matrix, expected in [(['B', 'A'], [2, 2], rho, right_mixture),
                                          (['X', 'pi'], [2, 3], product, qutrit)]:
        declaration = run(mapped(matrix_text(matrix), labels, dims))
        value = json.loads(declaration['stdout']) if declaration['exit_code'] == 0 else {}
        copied = value.get('copy_text', '')
        replay = run(copied) if copied else dict(exit_code=-1, stdout='', stderr='No copy_text')
        replay_value = json.loads(replay['stdout']) if replay['exit_code'] == 0 else {}
        declaration.update(name='evaluated mapping Copy/re-entry ' + str(labels), replay=replay,
                           passed=declaration['exit_code'] == 0 and not declaration['stderr'] and replay['exit_code'] == 0
                           and not replay['stderr'] and replay_value.get('copy_text') == copied and bool(copied))
        rows.append(declaration)
        if copied:
            check('trace copied mapping ' + str(labels), 'ptrace(' + copied + ',' + labels[0] + ')', expected)

    value = mapped(matrix_text(rho), ['A', 'B'], [2, 2])
    for expression, diagnostic in [
        ('ptrace(' + value + ',missing)', 'Unknown subsystem label'),
        ('ptrace(' + value + ',[B,B])', 'Duplicate traced subsystem labels'),
        (mapped(matrix_text(rho), ['A', 'A'], [2, 2]), 'Duplicate subsystem labels'),
        (mapped(matrix_text(rho), ['A', 'B'], [2, 3]), 'dimension product must equal'),
        ('subsystems([1,0,0;0,1,0],[A,B],[2,3])', 'square matrix'),
        ('subsystems(' + value + ',[B,A],[2,2])', 'nested redeclarations'),
        ('ptrace(' + value + ',A,[2,2])', 'already supplies dimensions'),
        ('ptrace(' + value + ',0)', 'not numeric indices'),
        ('ptrace(ptrace(' + value + ',A),B)', 'explicit subsystems'),
        (r'\operatorname{Tr}_{\mathsf{B}}(' + matrix_text(rho) + ')', 'explicit subsystems'),
    ]:
        row = run(expression)
        row.update(name='rejection: ' + diagnostic, expected=diagnostic,
                   passed=row['exit_code'] == 2 and not row['stdout'] and diagnostic in row['stderr'])
        rows.append(row)
    assert hashlib.sha256(worker.read_bytes()).hexdigest() == sha
    report = dict(revision=args.revision, worker=str(worker), worker_sha256=sha, results=rows,
                  checks=len(rows), passed=sum(r['passed'] for r in rows))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    failures = [r['name'] for r in rows if not r['passed']]
    print(json.dumps(dict(checks=len(rows), passed=report['passed'], failures=failures)))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
