"""Finite generated-artifact binding and independent integer-state checks."""
import hashlib
import json
from pathlib import Path


def audit_generated(text, secret):
    """Check this finite generator output, not general OpenQASM conformance.

    State amplitudes are integers divided by sqrt(2)**hadamards. The
    independently derived BV answer has data bit i equal to secret[i].
    """
    if secret not in ('1011', '101'):
        raise AssertionError('UNREVIEWED_SECRET')
    n = len(secret)
    statements = [line.strip() for line in text.splitlines() if line.strip()]
    declarations = ['OPENQASM 3.0;', 'include "stdgates.inc";',
                    f'qubit[{n}] q;', 'qubit[1] ancilla;', f'bit[{n}] b;']
    operations = ([('h', i) for i in range(n)] + [('x', n), ('h', n)]
                  + [('cx', i, n) for i, bit in enumerate(secret) if bit == '1']
                  + [('h', i) for i in range(n)])
    def wire(i):
        return 'ancilla[0]' if i == n else f'q[{i}]'
    gates = [f'{op[0]} ' + ', '.join(wire(i) for i in op[1:]) + ';' for op in operations]
    measurements = [f'b[{i}] = measure q[{i}];' for i in range(n)]
    if statements != declarations + gates + measurements:
        raise AssertionError('GENERATED_STRUCTURE_OR_MEASUREMENT_CHANGED')
    state = [1] + [0] * ((1 << (n + 1)) - 1)
    hadamards = 0
    for name, q, *rest in operations:
        if name == 'h':
            for i in range(len(state)):
                if not i & (1 << q):
                    j = i | (1 << q)
                    state[i], state[j] = state[i] + state[j], state[i] - state[j]
            hadamards += 1
        else:
            target = q if name == 'x' else rest[0]
            updated = [0] * len(state)
            for i, amplitude in enumerate(state):
                j = i ^ (1 << target) if name == 'x' or i & (1 << q) else i
                updated[j] = amplitude
            state = updated
    answer = sum(int(bit) << i for i, bit in enumerate(secret))
    expected = [0] * len(state)
    expected[answer], expected[answer + (1 << n)] = 1 << n, -(1 << n)
    if state != expected or sum(a * a for a in state) != 1 << hadamards:
        raise AssertionError('BERNSTEIN_VAZIRANI_STATE_MISMATCH')
    return dict(secret_in_q0_first_order=secret, displayed_data=format(answer, f'0{n}b'),
                data_probability='1', ancilla='minus', integer_state=state,
                hadamards=hadamards, amplitude_denominator=f'sqrt(2)^{hadamards}',
                basis_convention=f'q0 least significant; ancilla bit {n}',
                scope='Authored unitary-prefix state calculation, not native phase observation')


def run(first_program, second_program):
    compatibility = json.loads(Path('qb004-compatibility.json').read_text(encoding='utf-8'))
    setup = json.loads(Path('setup-evidence.json').read_text(encoding='utf-8'))
    translations = [c for c in compatibility['commands'] if c['translated']]
    if (not compatibility['restored'] or len(translations) != 1
            or translations[0]['exit_code'] != 0 or not setup['accepted']):
        raise AssertionError('WINDOWS_COMPATIBILITY_OR_SETUP_FAILED')
    Path('cell08.qasm').write_bytes(first_program.encode())
    Path('cell24.qasm').write_bytes(second_program.encode())
    expected = {
        'cell08.qasm': 'd0ffe44c9eea26c2f04e206e5b9cfac8321ffbfb8d9781d0eba53c4ee3e03a44',
        'cell24.qasm': '4ac4ae45a616bb3a66aecba7567fe1334693d500bf5a9165e9b6144d449fe9ce',
        'oracle.qasm': '00ca08a9b091c46c942bc1f1878ccc69e922a0500b61c79a11b87c8c4debc4b1',
        'bernvaz.qasm': '9f9eb3c6537bf209ff7c98fae8a5e2e77e1e135597d81569bf978498100f977e',
    }
    actual = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in expected}
    if actual != expected:
        raise AssertionError('GENERATED_SOURCE_CHANGED')
    mathematics = [audit_generated(first_program, '1011'), audit_generated(second_program, '101')]
    return dict(accepted=True, generated_artifacts=actual, mathematics=mathematics, provider_jobs_submitted=False,
                whole_notebook_complete=False, native_execution_performed=False,
                scope='Selected original local cells with explicit Windows command adapter',
                limitations=['Native execution and generated-module controls require separate evidence',
                             'Provider, job, result processing and histogram cells excluded'])


if __name__ == '__main__':
    print(json.dumps(run(module_str, qasm_str)))
