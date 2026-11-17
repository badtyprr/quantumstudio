"""Independent finite Fourier comparison; literal decimal rotations are not rounded."""
import cmath
import hashlib
import json
import math
from pathlib import Path
import re


def audit_unrolled(text, name):
    n, register, classical, inverse = {
        'qft3': (3, 'qb', 'cb', False),
        'iqft3': (3, 'q', 'b', True),
        'qft4': (4, 'qb', 'cb', False),
    }[name]
    size = 1 << n
    statements = [x.strip() for x in text.splitlines() if x.strip()]
    assert statements[:4] == ['OPENQASM 3.0;', 'include "stdgates.inc";', f'qubit[{n}] {register};', f'bit[{n}] {classical};']
    if inverse:
        assert statements[-n:] == [f'b[{i}] = measure q[{i}];' for i in range(n)]
        statements = statements[:-n]
    operations = []
    for line in statements[4:]:
        match = re.fullmatch(r'(h|rx|rz|cx|swap)(?:\((-?\d+(?:\.\d+)?)\))? (.+);', line)
        assert match, line
        gate, angle, operands = match.groups()
        wires = []
        for operand in operands.split(', '):
            wire = re.fullmatch(re.escape(register) + r'\[([0-9]+)\]', operand)
            assert wire and int(wire[1]) < n, line
            wires.append(int(wire[1]))
        assert len(wires) == (2 if gate in ('cx', 'swap') else 1)
        assert (angle is not None) == (gate in ('rx', 'rz'))
        operations.append((gate, float(angle) if angle is not None else None, wires))
    columns = []
    for basis in range(size):
        state = [complex(i == basis) for i in range(size)]
        for gate, angle, wires in operations:
            masks = [1 << (n - 1 - wire) for wire in wires]
            if gate in ('cx', 'swap'):
                updated = [0j] * size
                for i, value in enumerate(state):
                    if gate == 'cx':
                        target = i ^ masks[1] if i & masks[0] else i
                    else:
                        target = i ^ masks[0] ^ masks[1] if bool(i & masks[0]) != bool(i & masks[1]) else i
                    updated[target] = value
                state = updated
            else:
                if gate == 'h':
                    matrix = [[1 / math.sqrt(2), 1 / math.sqrt(2)], [1 / math.sqrt(2), -1 / math.sqrt(2)]]
                elif gate == 'rx':
                    matrix = [[math.cos(angle / 2), -1j * math.sin(angle / 2)], [-1j * math.sin(angle / 2), math.cos(angle / 2)]]
                else:
                    matrix = [[cmath.exp(-1j * angle / 2), 0], [0, cmath.exp(1j * angle / 2)]]
                for i in range(size):
                    if not i & masks[0]:
                        j = i | masks[0]
                        a, b = state[i], state[j]
                        state[i] = matrix[0][0] * a + matrix[0][1] * b
                        state[j] = matrix[1][0] * a + matrix[1][1] * b
        columns.append(state)
    reverse = lambda value: int(format(value, f'0{n}b')[::-1], 2)
    phase = columns[0][0] * math.sqrt(size)
    phase /= abs(phase)
    error = max(abs(columns[x][y] - phase * cmath.exp(((-1 if inverse else 1) * 2j * math.pi / size) *
        (reverse(x) * reverse(y) if inverse else x * y)) / math.sqrt(size)) for x in range(size) for y in range(size))
    assert error < 1e-12, (name, error)
    return dict(program=name, sha256=hashlib.sha256(text.encode()).hexdigest(), basis_inputs=size,
        primitive_gates=len(operations), terminal_measurements=n if inverse else 0,
        convention='q[0]/qb[0] most significant state-vector bit',
        comparison='bit-reversed negative Fourier matrix' if inverse else 'positive Fourier matrix',
        global_phase=[phase.real, phase.imag], maximum_amplitude_error=error,
        columns=[[[a.real, a.imag] for a in column] for column in columns])


def run(qft_source, inverse_source, four_source):
    import pyqasm
    compatibility = json.loads(Path('qb004-compatibility.json').read_text(encoding='utf-8'))
    setup = json.loads(Path('setup-evidence.json').read_text(encoding='utf-8'))
    translated = [c for c in compatibility['commands'] if c['translated']]
    if not compatibility['restored'] or len(translated) != 1 or translated[0]['exit_code'] != 0 or not setup['accepted']:
        raise AssertionError('SETUP_OR_COMPATIBILITY_FAILED')
    programs = {'qft3.qasm': qft_source, 'iqft3.qasm': inverse_source, 'qft4.qasm': four_source}
    for name, text in programs.items():
        Path(name).write_bytes(text.encode())
    expected = {
        'qft3.qasm': 'b231708aa972a348eb4dd310e46f7649b963bb838ac726834be19d3ff18f6902',
        'iqft3.qasm': 'f92c9700786608fcf8a0f447736f9972402d1c5835dc23f7198ba86f34495568',
        'qft4.qasm': 'f1911e218d7bff25c6d816b540d27ef5eb2784e5936d4d5c6fa32b9445899cc1',
        'qft.qasm': '7bf04a0b18b5b804cb562dbc5293599f26f94a0b7358b26c4b6be379243bd3a3',
        'iqft.qasm': 'bd3fac2c91ce0ca586461713c329015dd108a3c33c27ef8751e771f54bc38c8a',
    }
    actual = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in expected}
    if actual != expected:
        raise AssertionError('GENERATED_SOURCE_CHANGED')
    four = pyqasm.loads(four_source)
    four.unroll()
    four_unrolled = pyqasm.dumps(four)
    Path('authored-qft4-unrolled.qasm').write_bytes(four_unrolled.encode())
    mathematics = [audit_unrolled(qft_source, 'qft3'), audit_unrolled(inverse_source, 'iqft3'),
                   audit_unrolled(four_unrolled, 'qft4')]
    return dict(accepted=True, generated_artifacts=actual, mathematics=mathematics,
                whole_notebook_complete=False, provider_jobs_submitted=False, native_execution_performed=False,
                scope='Selected original local cells, explicit Windows adapter, authored numerical Fourier checks',
                limitations=['Four-qubit unrolling is authored verification, not an original source cell',
                             'Unitary-prefix numerical comparisons retain literal decimals; no exact phase claim',
                             'No QFT/inverse-QFT composition identity across different conventions',
                             'Provider/results/histogram, GUI, package and release not verified'])


if __name__ == '__main__':
    print(json.dumps(run(qft_str, iqft_str, qasm_str)))
