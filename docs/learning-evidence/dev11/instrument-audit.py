"""Finite DEV-11d instrument/channel audit; no third-party dependencies.

The oracle uses ordinary complex matrix arithmetic, independently of the worker.
Every invocation, expected matrix and raw response is retained before assertion.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('oracle_parser', Path(__file__).with_name('probe-release.py'))
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def eye(n):
    return [[complex(r == c) for c in range(n)] for r in range(n)]


def outer(v):
    return [[x * y.conjugate() for y in v] for x in v]


def tensor(a, b):
    return [[x * y for x in ar for y in br] for ar in a for br in b]


def add(*matrices):
    return [[sum(values) for values in zip(*rows)] for rows in zip(*matrices)]


def scale(a, x):
    return [[x * z for z in row] for row in a]


def mul(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def adj(a):
    return [[x.conjugate() for x in row] for row in zip(*a)]


def channel(kraus, rho):
    return add(*(mul(mul(k, rho), adj(k)) for k in kraus))


def instrument(groups, labels=None):
    labels = labels or list(range(len(groups)))
    return 'instrument(vector(' + ','.join(map(str, labels)) + '),vector(' + ','.join(
        'vector(' + ','.join(group) + ')' for group in groups) + '))'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=Path, required=True)
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--worker-sha256', default='42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d',
                    help='Expected worker hash; explicitly override for an integration build')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    worker_hash = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    if worker_hash != args.worker_sha256:
        raise SystemExit('Worker hash mismatch; identify the intended build explicitly')
    source_manifest = json.loads(Path(__file__).with_name('source-manifest.json').read_text())
    sources = []
    for row in source_manifest:
        if row['id'] in ('IBM-056', 'IBM-058'):
            raw = (args.sources / (row['id'] + '.ipynb')).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['notebook']['sha256']
            sources.append(row)
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.parent / 'data'))
    records = []

    def run(name, expression, expected=None, rejection=None, pending=None):
        record = dict(name=name, expression=expression, expected=parser.pack(expected) if expected is not None else None,
                      rejection=rejection, pending=pending)
        records.append(record)
        try:
            result = subprocess.run([str(args.worker), '--json'], input=('quantum:' + expression).encode(),
                                    capture_output=True, timeout=90, env=env)
            record.update(returncode=result.returncode, stdout=result.stdout.decode('utf-8'), stderr=result.stderr.decode('utf-8'))
            if rejection is not None:
                assert result.returncode == 2 and result.stderr.decode().strip() == rejection
            else:
                assert result.returncode == 0, record
                value = json.loads(result.stdout)
                assert value['approximate'] is False
                if expected is not None:
                    actual = parser.numeric_cells(value)
                    # The engine represents one-row matrices as vectors.
                    if not actual and value['copy_text'].startswith('vector('):
                        actual = [[parser.parse_complex(x) for x in value['copy_text'][7:-1].split(',')]]
                    assert len(actual) == len(expected) and all(len(a) == len(e) for a, e in zip(actual, expected))
                    assert max(abs(a-e) for ar, er in zip(actual, expected) for a, e in zip(ar, er)) < 1e-12
                if pending:
                    assert pending in value['copy_text'], value
            record['passed'] = True
        except Exception as error:
            record['passed'] = False
            record['failure'] = str(error)
        finally:
            (args.output / 'results.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        return json.loads(record['stdout']) if record.get('returncode') == 0 else None

    def matrix_case(name, expression, expected, copy=False):
        value = run(name, expression, expected)
        if copy and value:
            run(name + '-copy', value['copy_text'], expected)

    # IBM-058: distinct eigenvalues, each of multiplicity two, in 00,01,10,11 order.
    p = ['(pauli("II")+pauli("ZZ"))/2', '(pauli("II")-pauli("ZZ"))/2']
    zz = instrument([[x] for x in p], [1, -1])
    for s, indices in enumerate(((0, 3), (1, 2))):
        expected = [[complex(r == c and r in indices) for c in range(4)] for r in range(4)]
        matrix_case('zz-projector-' + str(s), p[s], expected)
    state = '(|00>+i*|11>+2*|01>+2*i*|10>)/sqrt(10)'
    matrix_case('zz-probabilities', 'matrix(1,2,probabilities(' + zz + ',' + state + '))', [[.2, .8]])
    for label, v in ((1, [1, 0, 0, 1j]), (-1, [0, 1, 1j, 0])):
        expected = scale(outer(v), .5)
        matrix_case('zz-conditional-' + str(label), 'poststate(' + zz + ',' + state + ',' + str(label) + ')', expected, True)
    for label, state, v in ((1, '(|00>+|11>)/sqrt(2)', [1, 0, 0, 1]),
                             (-1, '(|01>-|10>)/sqrt(2)', [0, 1, -1, 0])):
        matrix_case('bell-preserved-' + str(label), 'poststate(' + zz + ',' + state + ',' + str(label) + ')', scale(outer(v), .5))

    run('zero-outcome-rejected', 'poststate(' + zz + ',|00>,-1)',
        rejection='A zero-probability outcome has no normalized post-measurement state.')
    run('wrong-state-dimension', 'probabilities(' + zz + ',|0>)',
        rejection='Measurement state dimensions are incompatible.')
    run('incomplete-instrument', 'measurementvalid(' + instrument([[p[0]]]) + ')',
        rejection='Invalid measurement: effects must sum to identity.')
    run('unnormalized-state', 'probabilities(' + zz + ',2*|00>)',
        rejection='Measurement states must be positive semidefinite and normalized.')
    run('negative-state', 'probabilities(' + zz + ',[2,0,0,0;0,-1,0,0;0,0,0,0;0,0,0,0])',
        rejection='Measurement states must be positive semidefinite and normalized.')
    symbolic = run('symbolic-selector', 'poststate(' + zz + ',(|00>+|01>)/sqrt(2),x)', pending='qpoststate(')
    if symbolic:
        copied = run('symbolic-selector-copy', symbolic['copy_text'], pending='qpoststate(')
        if copied:
            matrix_case('symbolic-selector-substitution', 'replace(' + copied['copy_text'] + ',x,-1)', outer([0j, 1+0j, 0j, 0j]))
            run('symbolic-selector-invalid', 'replace(' + copied['copy_text'] + ',x,3)',
                rejection='The requested outcome label is not present in this instrument.')
    unknown = instrument([['a*(' + p[0] + ')'], [p[1]]])
    symbolic = run('unknown-completeness', 'measurementvalid(' + unknown + ')', pending='qmeasurementvalid(')
    if symbolic:
        run('unknown-completeness-copy', symbolic['copy_text'], pending='qmeasurementvalid(')
        run('invalid-completeness-substitution', 'replace(' + symbolic['copy_text'] + ',a,2)',
            rejection='Invalid measurement: effects must sum to identity.')

    # Finite known-site code adaptation: ZZI and XXX commute; each joint sector
    # has rank two. Logical columns (000+111)/sqrt2, (001+110)/sqrt2.
    # Reference is leftmost, physical error acts on first of three code qubits.
    phi = '(|0000>+|0111>+|1001>+|1110>)/2'
    v = [complex(i in (0, 7, 9, 14)) / 2 for i in range(16)]
    rho = outer(v)
    signs = [(1, 1), (-1, 1), (-1, -1), (1, -1)]  # I,X,Y,Z
    projectors = ['((pauli("III")+(' + str(s) + ')*pauli("ZZI"))*(pauli("III")+(' + str(t) + ')*pauli("XXX")))/4' for s, t in signs]
    corrections = ['pauli("' + w + 'II")' for w in 'IXYZ']
    bare = instrument([['I@(' + p + ')'] for p in projectors])
    x = [[0j, 1+0j], [1+0j, 0j]]
    y = [[0j, -1j], [1j, 0j]]
    z = [[1+0j, 0j], [0j, -1+0j]]
    paulis = [eye(2), x, y, z]
    error_vectors = [mul(tensor(eye(2), tensor(e, eye(4))), [[q] for q in v]) for e in paulis]
    error_states = [outer([r[0] for r in vec]) for vec in error_vectors]
    g0 = tensor(z, tensor(z, eye(2)))
    g1 = tensor(x, tensor(x, x))
    for s, (a, b) in enumerate(signs):
        expected = scale(mul(add(eye(8), scale(g0, a)), add(eye(8), scale(g1, b))), .25)
        matrix_case('joint-projector-' + str(s), projectors[s], expected)
    # Keep the relative Y=iXZ phase observable before measuring the ancilla.
    unitary_state = '(I@(((I+i*X+i*Y+i*Z)/2)@pauli("II")))*(' + phi + ')'
    tagged = '+'.join('(|' + format(s, '02b') + '>)@((I@(' + projectors[s] + '))*(' + unitary_state + '))' for s in range(4))
    controlled = '+'.join('(|' + format(s, '02b') + '>)@((I@(' + corrections[s] + '*(' + projectors[s] + ')))*(' + unitary_state + '))' for s in range(4))
    amplitudes = [.5, .5j, .5j, .5j]
    matrix_case('coherent-syndrome-phases', tagged,
                [[amplitudes[s]*r[0]] for s, vec in enumerate(error_vectors) for r in vec])
    matrix_case('coherent-controlled-recovery', controlled,
                [[a*q] for a in amplitudes for q in v], True)
    cases = [
        ('unitary', ['(I+i*X+i*Y+i*Z)/2'], [.25]*4,
         [scale(add(eye(2), scale(x, 1j), scale(y, 1j), scale(z, 1j)), .5)]),
        ('damping', ['[1,0;0,3/5]', '[0,4/5;0,0]'], [16/25, 4/25, 4/25, 1/25],
         [[[1+0j, 0j], [0j, .6+0j]], [[0j, .8+0j], [0j, 0j]]]),
    ]
    for name, errors, weights, independent_errors in cases:
        noise = instrument([['I@(('+e+')@pauli("II"))' for e in errors]])
        noisy = 'poststate(' + noise + ',' + phi + ',0)'
        noise_expected = channel([tensor(eye(2), tensor(e, eye(4))) for e in independent_errors], rho)
        matrix_case(name + '-noise-reference', noisy, noise_expected)
        matrix_case(name + '-syndrome-probabilities', 'matrix(1,4,probabilities(' + bare + ',' + noisy + '))', [weights])
        for s in range(4):
            matrix_case(name + '-conditional-' + str(s), 'poststate(' + bare + ',' + noisy + ',' + str(s) + ')', error_states[s])
        # Compose in physical order: error, syndrome projection, correction.
        corrected = [['I@(' + corrections[s] + '*(' + projectors[s] + ')*((' + e + ')@pauli("II")))' for e in errors] for s in range(4)]
        recovery = instrument(corrected)
        matrix_case(name + '-corrected-probabilities', 'matrix(1,4,probabilities(' + recovery + ',' + phi + '))', [weights])
        for s in range(4):
            matrix_case(name + '-recovered-' + str(s), 'poststate(' + recovery + ',' + phi + ',' + str(s) + ')', rho)
        total = instrument([[k for group in corrected for k in group]])
        matrix_case(name + '-unconditional-channel', 'poststate(' + total + ',' + phi + ',0)', rho, True)
        # Independently expected uncorrected discretization, not deterministic syndrome action.
        measured = instrument([['I@(('+p+')*(('+e+')@pauli("II")))' for p in projectors for e in errors]])
        matrix_case(name + '-discretized-channel', 'poststate(' + measured + ',' + phi + ',0)',
                    add(*(scale(m, w) for m, w in zip(error_states, weights))), True)
        flagged = instrument([['(|' + format(s, '02b') + '>)@(' + k + ')' for s, group in enumerate(corrected) for k in group]])
        syndrome = [[complex(weights[r] if r == c else 0) for c in range(4)] for r in range(4)]
        matrix_case(name + '-classical-syndrome-reference-product', 'poststate(' + flagged + ',' + phi + ',0)', tensor(syndrome, rho))

    summary = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   worker=str(args.worker), worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                   runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   sources=sources, tests=len(records), passed=sum(r['passed'] for r in records))
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    assert summary['worker_sha256'] == worker_hash, 'Worker changed during audit'
    print(json.dumps({k: summary[k] for k in ('tests', 'passed', 'worker_sha256')}))
    return int(summary['tests'] != summary['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
