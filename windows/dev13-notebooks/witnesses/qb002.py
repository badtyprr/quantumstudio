"""Finite structural and state oracle for QB002's original transformation chain."""
import json
import math
from pathlib import Path


def structure(text):
    import openqasm3
    from openqasm3 import ast

    def index(node, name):
        if (not isinstance(node, ast.IndexedIdentifier) or node.name.name != name
                or len(node.indices) != 1 or len(node.indices[0]) != 1
                or not isinstance(node.indices[0][0], ast.IntegerLiteral)):
            raise AssertionError('SCALAR_INDEX_REQUIRED')
        return node.indices[0][0].value

    declarations, operations = [], []
    for node in openqasm3.parse(text).statements:
        if isinstance(node, ast.Include):
            if node.filename != 'stdgates.inc':
                raise AssertionError('UNEXPECTED_INCLUDE')
        elif isinstance(node, ast.QubitDeclaration):
            declarations.append(('qubit', node.qubit.name, node.size.value))
        elif isinstance(node, ast.ClassicalDeclaration):
            if not isinstance(node.type, ast.BitType) or node.init_expression is not None:
                raise AssertionError('UNEXPECTED_CLASSICAL_DECLARATION')
            declarations.append(('bit', node.identifier.name, node.type.size.value))
        elif isinstance(node, ast.QuantumGate):
            if node.modifiers or node.duration is not None:
                raise AssertionError('UNEXPECTED_GATE_MODIFIER')
            angles = []
            for argument in node.arguments:
                if not isinstance(argument, ast.FloatLiteral):
                    raise AssertionError('UNEXPECTED_GATE_ARGUMENT')
                angles.append(argument.value)
            operations.append((node.name.name, tuple(index(q, 'q') for q in node.qubits), tuple(angles)))
        elif isinstance(node, ast.QuantumBarrier):
            operations.append(('barrier', tuple(index(q, 'q') for q in node.qubits), ()))
        elif isinstance(node, ast.QuantumMeasurementStatement):
            operations.append(('measure', (index(node.measure.qubit, 'q'),), (index(node.target, 'c'),)))
        else:
            raise AssertionError('UNEXPECTED_STATEMENT')
    return declarations, operations


def expected_operations(*, barrier=True, measurements=True, reverse=False):
    def wire(q):
        return 6-q if reverse else q
    gates = [('h', (0,), ()), ('h', (1,), ()), ('cx', (0, 1), ())]
    gates += [('rx', (q,), (0.5,)) for q in range(3, 7)]
    gates += [('ccx', (0, 1, 2), ())]
    if barrier:
        gates.append(('barrier', tuple(range(6)), ()))
    if measurements:
        gates += [('measure', (q,), (q,)) for q in range(6)]
    return [(name, tuple(wire(q) for q in wires), args) for name, wires, args in gates]


def unitary_state(operations):
    """Seven logical wires, little-endian; measurement-free prefix only."""
    state = [1+0j] + [0j]*127
    measured = False
    for name, wires, args in operations:
        if name == 'measure':
            measured = True
            continue
        if name == 'barrier':
            continue
        if measured:
            raise AssertionError('NONTERMINAL_MEASUREMENT')
        if name in ('cx', 'ccx'):
            controls, target = wires[:-1], wires[-1]
            updated = [0j]*128
            for i, value in enumerate(state):
                j = i ^ (1 << target) if all(i & (1 << c) for c in controls) else i
                updated[j] = value
            state = updated
        elif name in ('h', 'rx'):
            q = wires[0]
            for i in range(128):
                if i & (1 << q):
                    continue
                j = i | (1 << q)
                a, b = state[i], state[j]
                if name == 'h':
                    state[i], state[j] = (a+b)/math.sqrt(2), (a-b)/math.sqrt(2)
                else:
                    c, s = math.cos(args[0]/2), -1j*math.sin(args[0]/2)
                    state[i], state[j] = c*a+s*b, s*a+c*b
        else:
            raise AssertionError('UNSUPPORTED_STATE_GATE')
    return state


def audit(snapshots):
    if [s['after_original_cell'] for s in snapshots] != [10, 13, 20, 25]:
        raise AssertionError('CHECKPOINT_SEQUENCE')
    states = []
    for row in snapshots:
        stage = row['after_original_cell']
        width = 10 if stage == 10 else 7
        declarations, operations = structure(row['qasm'])
        if declarations != [('qubit', 'q', width), ('bit', 'c', 10)]:
            raise AssertionError('RESOURCE_DECLARATIONS')
        if (row['qubits'], row['classical_bits']) != (width, 10):
            raise AssertionError('RESOURCE_METADATA')
        if operations != expected_operations(barrier=stage < 20, reverse=stage == 25):
            raise AssertionError('TRANSFORMATION_OPERATIONS')
        state = unitary_state(operations)
        if stage == 25:
            state = [state[int(f'{i:07b}'[::-1], 2)] for i in range(128)]
        states.append(state)
        if stage >= 20:
            new_declarations, new_operations = structure(row['new_qasm'])
            if (not row['distinct_objects'] or new_declarations != [('qubit', 'q', 7), ('bit', 'c', 10)]
                    or new_operations != expected_operations(barrier=False, measurements=False)):
                raise AssertionError('COPY_ISOLATION_OR_MEASUREMENT_REMOVAL')
    if snapshots[2]['new_qasm'] != snapshots[3]['new_qasm']:
        raise AssertionError('COPY_CHANGED_AFTER_REVERSE')
    # Analytic product: uniform q0/q1, q2=AND, independent Rx(0.5) on q3..6.
    expected = []
    for i in range(128):
        if ((i >> 2) & 1) != ((i & 1) & ((i >> 1) & 1)):
            expected.append(0j)
            continue
        amplitude = .5+0j
        for q in range(3, 7):
            amplitude *= -1j*math.sin(.25) if i & (1 << q) else math.cos(.25)
        expected.append(amplitude)
    residual = max(abs(a-b) for state in states for a, b in zip(state, expected))
    if residual > 1e-12 or abs(sum(abs(a)**2 for a in expected)-1) > 1e-12:
        raise AssertionError('INDEPENDENT_STATE_MISMATCH')
    return dict(accepted=True, source_claim_six_qubits=False, actual_remaining_qubits=7,
                original_qubits=10, classical_bits=10, measured_qubits=6,
                state_residual=residual, state_scope='authored unitary-prefix interpretation; not native state observation',
                copied_module_isolated=True, provider_jobs_submitted=False,
                source_findings=['q[3:6] includes q6; prose saying q6 is idle and six qubits remain is incorrect'])


if __name__ == '__main__':
    Path('original.qasm').write_bytes(qasm_str.encode())
    print(json.dumps(audit(_qb002_snapshots)))
