"""Finite source audit; NumPy/SciPy are independent oracles, not product dependencies.

Inputs/outputs and source cells are preserved in --output (outside the checkout).
--baseline records missing eigen operations without claiming a solver rejection.
No notebook code, chemistry package, provider, or optimizer is executed.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import scipy
import scipy.linalg


def parse_number(text):
    text = text.replace('−', '-').replace('∕', '/').replace('⋅', '*').replace('^', '**')
    text = re.sub(r'(?<=[\d)])\s*i\b', '*i', text)
    def value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, complex)):
            return node.value
        if isinstance(node, ast.Name) and node.id == 'i':
            return 1j
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub): return -value(node.operand)
            if isinstance(node.op, ast.UAdd): return value(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = value(node.left), value(node.right)
            for op, fn in [(ast.Add, lambda: a+b), (ast.Sub, lambda: a-b),
                           (ast.Mult, lambda: a*b), (ast.Div, lambda: a/b), (ast.Pow, lambda: a**b)]:
                if isinstance(node.op, op): return fn()
        raise ValueError('Non-numeric output: ' + text)
    return complex(value(ast.parse(text, mode='eval').body))


def number(z):
    z = complex(z)
    return format(z.real, '.17g') if z.imag == 0 else '(' + format(z.real, '.17g') + '+(' + format(z.imag, '.17g') + ')*i)'


def literal(matrix):
    return '[' + ';'.join(','.join(number(z) for z in row) for row in matrix) + ']'


def packed(matrix):
    a = np.asarray(matrix)
    return dict(real=a.real.tolist(), imag=a.imag.tolist())


def source_call(source, name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id == name) or
                                         (isinstance(node.func, ast.Attribute) and node.func.attr == name)):
            return node
    raise ValueError('Missing source call ' + name)


def pauli_matrix(word):
    # Tensor construction and independent bit-action construction must agree.
    paulis = {'I': np.eye(2), 'X': np.array([[0, 1], [1, 0]]),
              'Y': np.array([[0, -1j], [1j, 0]]), 'Z': np.diag([1, -1])}
    tensor = np.array([[1]])
    for letter in word: tensor = np.kron(tensor, paulis[letter])
    bits = np.zeros_like(tensor, dtype=complex)
    for col in range(len(bits)):
        row, phase = col, 1
        for q, letter in enumerate(reversed(word)):
            on = bool(col & (1 << q))
            if letter in 'XY': row ^= 1 << q
            if letter == 'Y': phase *= -1j if on else 1j
            if letter == 'Z' and on: phase *= -1
        bits[row, col] = phase
    np.testing.assert_array_equal(tensor, bits)
    return tensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', required=True, type=Path)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--definitions', type=Path, help='Explicit definitions for an unpackaged native build')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {}
    manifest = json.loads(Path(__file__).with_name('chemistry-diagonalization-source-manifest.json').read_text(encoding='utf-8'))
    for row in manifest:
        data = (args.sources / (row['id'] + '.ipynb')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256'], 'Source hash mismatch'
        sources[row['id']] = json.loads(data)['cells']
    def text(row, cell): return ''.join(sources[row][cell]['source'])
    cases = []
    def add(name, row, cell, matrix, expression=None, adaptation='Literal matrix/Pauli translation only'):
        matrix = np.asarray(matrix, dtype=complex)
        np.testing.assert_allclose(matrix, matrix.conj().T, atol=1e-12, rtol=0)
        eig, vec = scipy.linalg.eigh(matrix, driver='evd')
        np.testing.assert_allclose(matrix @ vec, vec * eig, atol=2e-10, rtol=0)
        np.testing.assert_allclose(vec.conj().T @ vec, np.eye(len(eig)), atol=1e-12, rtol=0)
        cases.append(dict(id=name, row=row, cell=cell, original_cell=sources[row][cell],
                          adaptation=adaptation, matrix=matrix, expression=expression or literal(matrix), values=eig, vectors=vec))
    hcall = source_call(text('IBM-112', 2), 'SparsePauliOp')
    labels = ast.literal_eval(hcall.args[0])
    coeffs = ast.literal_eval(next(k.value for k in hcall.keywords if k.arg == 'coeffs'))
    h2 = sum(c * pauli_matrix(p) for p, c in zip(labels, coeffs))
    h2expr = '+'.join('(' + number(c) + ')*pauli("' + p + '")' for p, c in zip(labels, coeffs))
    add('h2-four-qubit', 'IBM-112', 2, h2, h2expr)
    pairs = ast.literal_eval(source_call(text('IBM-091', 16), 'from_list').args[0])
    add('vqe-complex', 'IBM-091', 16, sum(c * pauli_matrix(p) for p, c in pairs),
        '+'.join('(' + number(c) + ')*pauli("' + p + '")' for p, c in pairs))
    for name, row, cell in [('krylov-three', 'IBM-092', 4), ('krylov-five', 'IBM-092', 20),
                             ('sqd-eight', 'IBM-093', 4), ('sqd-new-eight', 'IBM-093', 33)]:
        add(name, row, cell, ast.literal_eval(source_call(text(row, cell), 'array').args[0]))
    original = cases[4]['matrix']
    for index, cell in [([3, 5], 8), ([0, 3, 6], 14), ([3, 5, 7], 19)]:
        add('sqd-projection-' + str(cell), 'IBM-093', cell, original[np.ix_(index, index)], adaptation='Source computational-basis projection')
    index = [0, 2, 5, 6]
    add('sqd-new-projection', 'IBM-093', 36, cases[5]['matrix'][np.ix_(index, index)], adaptation='Source computational-basis projection')
    add('heisenberg-degenerate', 'IBM-109', 2, sum(pauli_matrix(p) for p in ['XX', 'YY', 'ZZ']),
        'pauli("XX")+pauli("YY")+pauli("ZZ")')
    # Explicit adaptation of the lesson's generalized problem to its 3x3 A.
    a = cases[2]['matrix']; start = np.array([1, 0, 0]); k = np.column_stack([start, a@start, a@a@start])
    overlap = k.conj().T @ k; projected = k.conj().T @ a @ k
    svalues, svectors = scipy.linalg.eigh(overlap)
    whitening = (svectors / np.sqrt(svalues)) @ svectors.conj().T
    generalized, generalized_vectors = scipy.linalg.eigh(projected, overlap)
    np.testing.assert_allclose(projected @ generalized_vectors, (overlap @ generalized_vectors) * generalized, atol=2e-10, rtol=0)
    np.testing.assert_allclose(generalized_vectors.conj().T @ overlap @ generalized_vectors, np.eye(3), atol=2e-10, rtol=0)
    add('krylov-whitened', 'IBM-092', 50, whitening @ projected @ whitening,
        'qpower(' + literal(overlap) + ',-1/2)*' + literal(projected) + '*qpower(' + literal(overlap) + ',-1/2)',
        'Derived nonorthogonal K=[v,Av,A^2v] for cell4 A; S=K* K, H=K* A K; not original 10-qubit sampled data')
    definitions = args.definitions or args.worker.parent / 'data'
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(definitions))
    records = []
    def run(expression):
        process = subprocess.run([str(args.worker), '--json', '--approx'], input=('quantum:' + expression).encode(),
                                 capture_output=True, timeout=90, env=env, cwd=args.output)
        record = dict(input='quantum:' + expression, argv=['--json', '--approx'], returncode=process.returncode,
                      stdout=process.stdout.decode('utf-8', errors='replace'), stderr=process.stderr.decode('utf-8', errors='replace'))
        records.append(record)
        try:
            data = json.loads(record['stdout'])
            result = np.array([[parse_number(x) for x in row] for row in data['cells']], dtype=complex)
            if not data['cells']:
                match = re.fullmatch(r'matrix\((\d+),(\d+),\[(.*)\]\)', data['copy_text'], re.S)
                if match:
                    result = np.array([parse_number(x) for x in match[3].split(',')]).reshape(int(match[1]), int(match[2]))
                else:
                    result = np.asarray(parse_number(data['text']))
            record['numeric'] = True
            return result
        except (ValueError, KeyError, SyntaxError):
            record['numeric'] = False
            return None
    passed = 0
    try:
        for case in cases:
            expr = case['expression']; h = case['matrix']; n = len(h)
            actual = run(expr)
            np.testing.assert_allclose(actual, h, atol=2e-8 if 'whitened' in case['id'] else 2e-10, rtol=0)
            passed += 1
            state = case['vectors'][:, 0:1]
            norm = run('dagger(' + literal(state) + ')*' + literal(state))
            expectation = run('expect(' + expr + ',' + literal(state) + ')')
            np.testing.assert_allclose(norm, 1, atol=2e-10, rtol=0)
            np.testing.assert_allclose(expectation, case['values'][0], atol=2e-8, rtol=0)
            passed += 2
            values = run('heigenvalues(' + expr + ')')
            vectors = run('heigenvectors(' + expr + ')')
            if args.baseline:
                assert values is None and vectors is None, 'Baseline unexpectedly has numerical eigen outputs'
                continue
            assert values.shape == (n, 1) and vectors.shape == (n, n)
            np.testing.assert_allclose(values[:, 0], case['values'], atol=2e-8, rtol=0)
            np.testing.assert_allclose(vectors.conj().T @ vectors, np.eye(n), atol=2e-9, rtol=0)
            np.testing.assert_allclose(h @ vectors, vectors * values[:, 0], atol=2e-8, rtol=0)
            # Compare whole spectral projectors, never arbitrary phase or repeated-eigenvalue bases.
            for eigenvalue in case['values']:
                selected = np.abs(case['values'] - eigenvalue) < 1e-8
                np.testing.assert_allclose(vectors[:, selected] @ vectors[:, selected].conj().T,
                                           case['vectors'][:, selected] @ case['vectors'][:, selected].conj().T, atol=2e-8, rtol=0)
            passed += 2
        # Normalized source SQD vector is approximate for the four-decimal H.
        psi = np.zeros(8); psi[3] = .8; psi[5] = .6
        energy = float(np.vdot(psi, original @ psi).real)
        notes = dict(sqd_rounded_vector_residual=float(np.linalg.norm(original@psi-energy*psi)),
                     sqd_rounded_vector_energy=energy, h2_computational_diagonal=h2.diagonal().real.tolist(),
                     h2_ground_energy=float(cases[0]['values'][0]), nuclear_repulsion=0.7199689944489797,
                     h2_electronic_ground_energy=float(cases[0]['values'][0] - 0.7199689944489797),
                     overlap_eigenvalues=svalues.tolist(), overlap_condition=float(np.linalg.cond(overlap)),
                     generalized_eigenvalues=generalized.tolist())
        (args.output/'summary.json').write_text(json.dumps(dict(passed_operations=passed, baseline=args.baseline, notes=notes), indent=2))
    finally:
        provenance = dict(worker=str(args.worker), worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                          definitions=str(definitions),
                          definition_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in definitions.glob('*.xml')},
                          numpy=np.__version__, scipy=scipy.__version__, baseline=args.baseline)
        (args.output/'results.json').write_text(json.dumps(dict(provenance=provenance, records=records), indent=2), encoding='utf-8')
        fixtures = [{key: packed(value) if isinstance(value, np.ndarray) else value for key, value in case.items()} for case in cases]
        (args.output/'fixtures.json').write_text(json.dumps(fixtures, indent=2), encoding='utf-8')
    print(json.dumps(dict(passed_operations=passed, cases=len(cases), baseline=args.baseline)))


if __name__ == '__main__':
    main()
