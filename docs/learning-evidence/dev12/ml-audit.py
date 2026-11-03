"""Finite manual ML adaptations. Standard library only; never executes SDK cells.

Outputs are exclusive-created outside disposable checkouts. Every amplitude and
probability is checked, with no global-phase fitting and no sampled equality.
"""
import argparse
import cmath
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dev11_probe', HERE.parent / 'dev11/probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
TOL = 1e-12


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oracle(n, operations):
    """Independent full row/column embedding, not backend stride traversal."""
    state = [1 + 0j] + [0j] * ((1 << n) - 1)
    for name, a, b, angle in operations:
        c, s = math.cos(angle / 2), math.sin(angle / 2)
        gates = {'H': [[2**-.5, 2**-.5], [2**-.5, -2**-.5]],
                 'X': [[0, 1], [1, 0]], 'Rx': [[c, -1j*s], [-1j*s, c]],
                 'Ry': [[c, -s], [s, c]],
                 'Rz': [[cmath.exp(-.5j*angle), 0], [0, cmath.exp(.5j*angle)]],
                 'P': [[1, 0], [0, cmath.exp(1j*angle)]]}
        if name in ('CZ', 'CP'):
            phase = -1 if name == 'CZ' else cmath.exp(1j*angle)
            state = [v * (phase if ((i >> (n-1-a)) & (i >> (n-1-b)) & 1) else 1)
                     for i, v in enumerate(state)]
        elif name == 'CNOT':
            state = [state[i ^ ((1 << (n-1-b)) if i & (1 << (n-1-a)) else 0)]
                     for i in range(1 << n)]
        else:
            gate = gates[name]
            mask = 1 << (n-1-a)
            state = [sum(gate[int(bool(r & mask))][int(bool(k & mask))] * state[k]
                         for k in range(1 << n) if (r & ~mask) == (k & ~mask))
                     for r in range(1 << n)]
    return state


def custom_map(data):
    # IBM099 cell30: Qiskit q0 is least significant; backend wire0 is MSB.
    n = len(data) // 2
    edges = [(0, 2), (3, 4), (2, 5), (1, 4), (2, 3), (4, 6)]
    return ([('Ry', n-1-q, 0, math.pi/2) for q in range(n)] +
            [('CZ', n-1-a, n-1-b, 0) for a, b in edges] +
            [op for q in range(n) for op in
             [('Rz', n-1-q, 0, -2*data[2*q+1]), ('Rx', n-1-q, 0, -2*data[2*q])]])


def classifier(data, weights, edges):
    n = len(data)
    # Explicit manual expansion of z_feature_map default two repetitions and
    # P(2*x), then IBM100 cell12 or45. No SDK parameter sorting assumed.
    return ([op for _ in range(2) for q in range(n) for op in
             [('H', n-1-q, 0, 0), ('P', n-1-q, 0, 2*data[q])]] +
            [('Ry', n-1-q, 0, weights[q]) for q in range(n)] +
            [('CNOT', n-1-a, n-1-b, 0) for a, b in edges] +
            [('Rx', n-1-q, 0, weights[n+q]) for q in range(n)])


def expect_parity(state):
    return sum((-1)**i.bit_count() * abs(a)**2 for i, a in enumerate(state))


def main():
    parser = argparse.ArgumentParser()
    for name in ('worker', 'native', 'sources', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifests = json.loads((HERE/'ml-source-manifest.json').read_text())
    for row in manifests:
        for ext in ('html', 'ipynb'):
            if ext in row:
                assert digest(args.sources/(row['id']+'.'+ext)) == row[ext]['sha256']
    dataset = args.sources/'dataset_graph7.csv'
    assert digest(dataset) == json.loads((HERE/'ml-data-manifest.json').read_text())['sha256']
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.parent/'data'))
    scalar = []

    def worker_case(name, row, cell, expression, expected, exact=False, raw=False):
        flags = ['--json'] + ([] if exact else ['--approx'])
        run = subprocess.run([str(args.worker), *flags], input=('' if raw else 'quantum:')+expression,
                             encoding='utf-8', capture_output=True, env=env, timeout=60)
        record = dict(id=name, source=row, cell=cell, expression=expression,
                      expected=[[complex(v).real, complex(v).imag] for v in expected],
                      stdout=run.stdout, stderr=run.stderr, returncode=run.returncode, exact=exact, raw=raw)
        try:
            output = json.loads(run.stdout)
            actual = ([probe.parse_complex(x[0]) for x in output['cells']]
                      if output['cells'] else [probe.parse_complex(output['text'])])
            record['pass'] = (run.returncode == 0 and len(actual) == len(expected) and
                              max(abs(a-b) for a, b in zip(actual, expected)) < TOL and
                              (not exact or not output['approximate']))
            # Actual canonical serialization re-entry, not comparison of text alone.
            replay = subprocess.run([str(args.worker), *flags], input='quantum:'+output['copy_text'],
                                    encoding='utf-8', capture_output=True, env=env, timeout=60)
            record['reentry_stdout'] = replay.stdout
            again = json.loads(replay.stdout)
            values = ([probe.parse_complex(x[0]) for x in again['cells']]
                      if again['cells'] else [probe.parse_complex(again['text'])])
            record['pass'] &= replay.returncode == 0 and len(values) == len(expected) and max(abs(a-b) for a,b in zip(values,expected)) < TOL
        except (ValueError, KeyError, SyntaxError):
            record['pass'] = False
        scalar.append(record)

    worker_case('amplitude-4-8-5', 'IBM-098', 6, '(4*|00>+8*|01>+5*|10>)/sqrt(105)',
                [x/math.sqrt(105) for x in (4,8,5,0)], True)
    worker_case('amplitude-six', 'IBM-098', 8, '(9*|000>+8*|001>+6*|010>+2*|011>+9*|100>+2*|101>)/sqrt(270)',
                [x/math.sqrt(270) for x in (9,8,6,2,9,2,0,0)], True)
    worker_case('angle-pi-half', 'IBM-098', 11, 'Ry(pi/2)*|0>', [2**-.5]*2, True)
    worker_case('phase-pi-half', 'IBM-098', 16, 'S*H*|0>', [2**-.5,1j*2**-.5], True)
    worker_case('dense-angle', 'IBM-098', 22, 'Rz(7*pi/4)*Ry(3*pi/8)*|0>',
                [cmath.exp(-7j*math.pi/8)*math.cos(3*math.pi/16), cmath.exp(7j*math.pi/8)*math.sin(3*math.pi/16)])
    # All four probabilities, plus normalization, are independently derivable.
    worker_case('phase-tensor', 'IBM-098', 38, 'tensor(Rz(pi/3),Rz(pi/2))*tensor(H,H)*|00>',
                [cmath.exp(1j*((1 if i&2 else -1)*math.pi/6+(1 if i&1 else -1)*math.pi/4))/2 for i in range(4)])
    # Rz differs from source P by global phase; this fixture uses the stated Rz
    # convention and compares its phase directly. Source-P coverage is above.
    for index, angle in enumerate((0, math.pi/3, math.pi, -0.47)):
        worker_case(f'objective-{index}', 'IBM-100', 20,
                    f'(expect(Z,Ry({angle})*|0>)-1)^2', [(math.cos(angle)-1)**2])
        worker_case(f'gradient-{index}', 'IBM-100', 20,
                    f'diff((expect(Z,Ry(x)*|0>)-1)^2,x,1,{angle})', [2*(1-math.cos(angle))*math.sin(angle)])
    edges = [(0,1),(0,2),(1,2),(1,3),(2,4),(3,4)]
    # This adaptation labels graph vertex q by native/MSB-first wire q.
    # Source SparsePauliOp q0 is LSB: reverse the displayed ket to compare.
    ham = '+'.join('pauli("'+''.join('Z' if q in edge else 'I' for q in range(5))+'")/2' for edge in edges)
    for i in range(32):
        bits = [int(x) for x in format(i,'05b')]
        cut = sum(bits[a] != bits[b] for a,b in edges)
        worker_case(f'maxcut-{i:05b}', 'IBM-119', 65, f'expect({ham},|{i:05b}>)-3', [-cut], True)
        source_label = format(i, '05b')[::-1]
        source_integer = int(source_label, 2)
        source_spins = [1-2*((source_integer >> q) & 1) for q in range(5)]
        source_energy = sum(source_spins[a]*source_spins[b]/2 for a,b in edges)-3
        assert source_energy == -cut
        scalar[-1].update(
            adaptation='Graph vertex q maps to native MSB-first wire q; source Qiskit ket label is reversed.',
            graph_vertex_bits=bits, native_ket_label=format(i, '05b'),
            source_qiskit_ket_label=source_label, source_qiskit_integer=source_integer,
            source_diagonal_energy=source_energy)

    rows = [[float(x) for x in row] for row in csv.reader(dataset.open())]
    cases = []

    def add(name, n, ops, source, cells, adaptation):
        cases.append(dict(id=name, qubits=n, operations=ops, source=source,
                          cells=cells, adaptation=adaptation))

    for i in range(3):
        add(f'kernel-data-{i}', 7, custom_map(rows[i][:-1]), 'IBM-099', [26,30,32],
            'Original seven-qubit feature map; first three pinned CSV rows; theta=pi/2; no training.')
    data_points = [[math.pi/2,math.pi/2,0,.1,.2,.3,.4,.5],
                   [math.pi/2,0,.1,.2,math.pi/2,.3,.4,.5]]
    weights = [(q-7)*.07 for q in range(16)]
    for i,data in enumerate(data_points):
        add(f'classifier-{i}',8,classifier(data,weights,[(0,1),(1,2),(2,3)]),'IBM-100',[10,12,16,18,20],
            'Original eight-qubit first ansatz; authored noiseless/mixed pixel values and fixed weights, no RNG or training.')
    # Independent half-turn/source-diagonal witness, deliberately reduced 2x2.
    fields = [1,-1,-1,1]
    couplings = [(0,2,1),(1,3,-1),(0,1,-1),(2,3,1)]
    ops = [('H',q,0,0) for q in range(4)] + [('P',q,0,.3*math.pi) for q in range(4) if fields[q] == 1]
    for a,b,j in couplings:
        if j == -1: ops += [('X',a,0,0),('X',b,0,0)]
        ops += [('CP',a,b,.3*math.pi)]
        if j == -1: ops += [('X',a,0,0),('X',b,0,0)]
    ops += [('Rx',q,0,.3*math.pi) for q in range(4)]
    add('qbraid-reduced',4,ops,'QB-007',[9,11,14,17,23,25],
        'Pinned 2x2 fields/couplings; Rx replaces XPow up to known global exp(i*pi*t/2) per qubit; no phase fitting, CPU/GPU SDK or optimizer.')
    for i in range(3):
        for j in range(3):
            inverse = [(g,a,b,-t if g in ('Ry','Rx','Rz','P','CP') else t)
                       for g,a,b,t in reversed(cases[j]['operations'])]
            add(f'overlap-{i}-{j}',7,cases[i]['operations']+inverse,'IBM-099',[30,32],
                'Complete U(j) dagger U(i) probabilities, including actual diagonal execution; no forced diagonal or finite shots.')
    payload = ''.join(f"{c['qubits']} {len(c['operations'])}\n" + ''.join(f'{g} {a} {b} {t:.17g}\n' for g,a,b,t in c['operations']) for c in cases)
    (args.output/'native-input.txt').write_text(payload)
    run = subprocess.run([str(args.native)],input=payload,encoding='utf-8',capture_output=True,timeout=60)
    (args.output/'native-stdout.txt').write_text(run.stdout)
    (args.output/'native-stderr.txt').write_text(run.stderr)
    assert run.returncode == 0 and len(run.stdout.splitlines()) == len(cases)
    states = []
    for case,line in zip(cases,run.stdout.splitlines()):
        numbers = list(map(float,line.split()))
        actual = [complex(a,b) for a,b in zip(numbers[::2],numbers[1::2])]
        expected = oracle(case['qubits'],case['operations'])
        error = max(abs(a-b) for a,b in zip(actual,expected))
        probability_error = max(abs(abs(a)**2-abs(b)**2) for a,b in zip(actual,expected))
        norm = sum(abs(a)**2 for a in actual)
        case.update(expected=[[a.real,a.imag] for a in expected], actual=[[a.real,a.imag] for a in actual],
                    amplitude_error=error, probability_error=probability_error, norm=norm,
                    passed=len(actual)==len(expected) and error<TOL and probability_error<TOL and abs(norm-1)<TOL)
        states.append(actual)
    gram = [[sum(a.conjugate()*b for a,b in zip(u,v)) for v in states[:3]] for u in states[:3]]
    kernel = [[abs(z)**2 for z in row] for row in gram]
    # All principal minors for a 3x3 Hermitian matrix establish finite PSD up
    # to tolerance (not an eigenvalue API or a parameterized-family proof).
    def minors(matrix):
        out=[]
        for width in (1,2,3):
            for subset in itertools.combinations(range(3),width):
                total=0j
                for perm in itertools.permutations(range(width)):
                    sign=(-1)**sum(perm[i]>perm[j] for i in range(width) for j in range(i+1,width))
                    total += sign * product(matrix[subset[i]][subset[perm[i]]] for i in range(width))
                out.append(total)
        return out
    gram_minors, kernel_minors = minors(gram), minors(kernel)
    psd = all(abs(z.imag)<TOL and z.real >= -TOL for z in gram_minors+kernel_minors)
    hermitian = max(abs(gram[i][j]-gram[j][i].conjugate()) for i in range(3) for j in range(3)) < TOL
    symmetric = max(abs(kernel[i][j]-kernel[j][i]) for i in range(3) for j in range(3)) < TOL
    diagonal = max(abs(kernel[i][i]-1) for i in range(3)) < TOL
    predictions = [expect_parity(v) for v in states[3:5]]
    expected_predictions = [expect_parity(oracle(c['qubits'],c['operations'])) for c in cases[3:5]]
    labels = [-1,1]
    mse = sum((x-y)**2 for x,y in zip(predictions,labels))/2
    for i,x in enumerate(predictions):
        worker_case(f'classifier-expectation-{i}','IBM-100',16,
                    'qexpect(qpauliword(8,0,255,0),matrix(256,1,['+','.join(probe.exprnum(complex(*a)) for a in cases[3+i]['actual'])+']))', [expected_predictions[i]], raw=True)
    worker_case('classifier-mse','IBM-100',20,f'(({predictions[0]}+1)^2+({predictions[1]}-1)^2)/2',[mse])
    energy=[]
    for i in range(16):
        spins=[1-2*((i>>(3-q))&1) for q in range(4)]
        energy.append(sum(h*s for h,s in zip(fields,spins))+sum(j*spins[a]*spins[b] for a,b,j in couplings))
    qenergy = sum(e*abs(a)**2 for e,a in zip(energy,states[5]))
    overlap_error = max(abs(abs(states[6+i*3+j][0])**2-kernel[i][j]) for i in range(3) for j in range(3))
    qham = '+'.join(f'({h})*pauli("'+''.join('Z' if k==q else 'I' for k in range(4))+'")' for q,h in enumerate(fields))
    qham += '+' + '+'.join(f'({j})*pauli("'+''.join('Z' if k in (a,b) else 'I' for k in range(4))+'")' for a,b,j in couplings)
    for i,e in enumerate(energy):
        worker_case(f'qbraid-energy-{i:04b}','QB-007',23,f'expect({qham},|{i:04b}>)',[e],True)
    report = dict(tolerance=TOL,overlap_error=overlap_error, execution='manual mathematical adaptations; no SDK, training, sampling, GUI or hardware',
                  provenance={name:dict(path=str(path),sha256=digest(path)) for name,path in [('worker',args.worker),('native',args.native),('script',Path(__file__))]},
                  scalar=scalar, circuits=cases, kernel=kernel, gram=[[[z.real,z.imag] for z in row] for row in gram],
                  gram_principal_minors=[[z.real,z.imag] for z in gram_minors],kernel_principal_minors=[[z.real,z.imag] for z in kernel_minors],
                  psd=psd,hermitian=hermitian,symmetric=symmetric,diagonal=diagonal,
                  classifier=dict(data=data_points,weights=weights,labels=labels,predictions=predictions,mse=mse,training=False),
                  qbraid=dict(fields=fields,couplings=couplings,energies=energy,expectation=qenergy))
    report['passed'] = all(r['pass'] for r in scalar) and all(c['passed'] for c in cases) and psd and hermitian and symmetric and diagonal and overlap_error<TOL
    (args.output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],worker_cases=len(scalar),circuits=len(cases),failed=[r['id'] for r in scalar if not r['pass']])))
    return not report['passed']


def product(values):
    result=1
    for value in values:
        result *= value
    return result


if __name__ == '__main__':
    raise SystemExit(main())
