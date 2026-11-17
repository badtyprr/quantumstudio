"""Finite numerical diagnosis; successful verification does not mean intended phase success."""
import cmath
import hashlib
import json
import math
from pathlib import Path
import re


def audit_program(text, n):
    if n not in (3, 4):
        raise AssertionError('UNREVIEWED_COUNTING_WIDTH')
    filename = 'default.qasm' if n == 4 else 'three-counting.qasm'
    rows = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert lines[:5] == ['OPENQASM 3.0;', 'include "stdgates.inc";', f'qubit[{n}] q;', 'qubit[1] psi;', f'bit[{n}] b;']
    assert lines[-n:] == [f'b[{i}] = measure q[{i}];' for i in range(n)]
    operations = []
    for line in lines[5:-n]:
        match = re.fullmatch(r'(h|rx|rz|cx|cz|swap)(?:\((-?\d+(?:\.\d+)?)\))? (.+);', line)
        assert match, line
        gate, angle, operands = match.groups()
        wires = []
        for operand in operands.split(', '):
            if operand == 'psi[0]':
                wires.append(n)
            else:
                wire = re.fullmatch(r'q\[([0-9]+)\]', operand)
                assert wire and int(wire[1]) < n
                wires.append(int(wire[1]))
        assert len(wires) == (2 if gate in ('cx', 'cz', 'swap') else 1)
        assert (angle is not None) == (gate in ('rx', 'rz'))
        if n in wires:
            assert gate == 'cz' and wires[1] == n, 'Preparation unexpectedly present'
        operations.append((gate, float(angle) if angle is not None else None, wires))
    for prepared in (False, True):
        size = 1 << (n + 1)
        state = [complex(i == int(prepared)) for i in range(size)]
        for gate, angle, wires in operations:
            masks = [1 << (n - wire) for wire in wires]
            if gate == 'cz':
                state = [-value if i & masks[0] and i & masks[1] else value for i, value in enumerate(state)]
            elif gate in ('cx', 'swap'):
                updated = [0j] * size
                for i, value in enumerate(state):
                    target = (i ^ masks[1] if i & masks[0] else i) if gate == 'cx' else (
                        i ^ masks[0] ^ masks[1] if bool(i & masks[0]) != bool(i & masks[1]) else i)
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
        probabilities = {format(i, f'0{n}b')[::-1]: abs(state[2 * i]) ** 2 + abs(state[2 * i + 1]) ** 2
                         for i in range(1 << n)}
        expected = ('1' if prepared else '0') + '0' * (n - 1)
        assert abs(sum(probabilities.values()) - 1) < 1e-12
        assert abs(probabilities[expected] - 1) < 1e-12
        rows.append(dict(program=filename, sha256=hashlib.sha256(text.encode()).hexdigest(), counting_qubits=n,
                         gates=len(operations), authored_initial_psi_one=prepared,
                         expected_dominant_output=expected, probabilities=probabilities,
                         generated_preparation_present=False))
    return rows


def run(default_source, three_source):
    compatibility = json.loads(Path('qb004-compatibility.json').read_text(encoding='utf-8'))
    setup = json.loads(Path('setup-evidence.json').read_text(encoding='utf-8'))
    translated = [c for c in compatibility['commands'] if c['translated']]
    if not compatibility['restored'] or len(translated) != 1 or translated[0]['exit_code'] != 0 or not setup['accepted']:
        raise AssertionError('SETUP_OR_COMPATIBILITY_FAILED')
    Path('default.qasm').write_bytes(default_source.encode())
    Path('three-counting.qasm').write_bytes(three_source.encode())
    expected = {
        'unitary.qasm': '09e04bf4c5c542219f681ba6a3e7d49a129906f0ab09e25fb4a84e43cbfcc980',
        'prepare_state.qasm': 'aaaf45b8b30a2d1d022542ae79977363c5ae0a73e2814a3109eefc826b759a50',
        'default.qasm': '52ef5e5ffae1cf92b6278ce83b3879c68b198bb414515c1fe0df77904ec19994',
        'three-counting.qasm': 'b0209a54e19acfa94b4bde2620ca199da8b3428187955e10322aa3793840945c',
        'qpe.qasm': 'c7ca5070a608169d3ef985d4298a4ecc703eceae7e4f14e43bd1c9a5ac12eb8a',
        'iqft.qasm': '63503ff41ba7a12ee92ce272fdbde7d9d807203567fdbc26b57926c39c8e58ad',
    }
    actual = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in expected}
    if actual != expected:
        raise AssertionError('INPUT_OR_GENERATED_SOURCE_CHANGED')
    mathematics = audit_program(default_source, 4) + audit_program(three_source, 3)
    return dict(accepted=True, intended_algorithm_passed=False,
                source_finding='QB006-SOURCE-01: preparation gate defined but never invoked',
                artifacts=actual, mathematics=mathematics, whole_notebook_complete=False,
                provider_jobs_submitted=False, native_execution_performed=False,
                convention='q0 most significant state-vector bit; psi least significant; classical b[n-1]...b[0]',
                scope='Verification of selected local execution and reproduced source discrepancy',
                limitations=['Prepared input is an authored diagnostic, not an original notebook result',
                             'Double precision with literal decimals; probabilities are not exact zeros or ones',
                             'Provider, GUI, package, exact default/prepared execution and release remain open'])


if __name__ == '__main__':
    print(json.dumps(run(module_str, qasm_str)))
