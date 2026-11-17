"""Authored structural and integer-state checks after all original QB001 cells."""
import hashlib
import json
from pathlib import Path


def expected_operations():
    return ([('x', 4)] + [('h', q) for q in range(5)]
            + [('cx', q, 4) for q in range(4)]
            + [('h', q) for q in range(4)]
            + [('measure', q, q) for q in range(4)])


def integer_state(operations):
    """Little-endian wires; omit sqrt(2) factors and retain their exact count."""
    state = [1] + [0]*31
    hadamards = 0
    for operation in operations:
        name, q, *rest = operation
        if name == 'measure':
            continue
        if name == 'h':
            for i in range(32):
                if not i & (1 << q):
                    j = i | (1 << q)
                    state[i], state[j] = state[i]+state[j], state[i]-state[j]
            hadamards += 1
        elif name in ('x', 'cx'):
            target = q if name == 'x' else rest[0]
            updated = [0]*32
            for i, value in enumerate(state):
                j = i ^ (1 << target) if name == 'x' or i & (1 << q) else i
                updated[j] = value
            state = updated
        else:
            raise ValueError('UNSUPPORTED_CONTROL_GATE')
    return state, hadamards


def audit_unrolled(text):
    import openqasm3
    from openqasm3 import ast

    def index(node, register):
        if (not isinstance(node, ast.IndexedIdentifier) or node.name.name != register
                or len(node.indices) != 1 or len(node.indices[0]) != 1
                or not isinstance(node.indices[0][0], ast.IntegerLiteral)):
            raise AssertionError('EXPECTED_SCALAR_INDEX')
        return node.indices[0][0].value

    def wire(node):
        if node.name.name == 'q':
            q = index(node, 'q')
            if not 0 <= q < 4:
                raise AssertionError('DATA_WIRE_RANGE')
            return q
        if index(node, 'ancilla') != 0:
            raise AssertionError('ANCILLA_WIRE_RANGE')
        return 4

    operations, declarations, includes = [], [], []
    for node in openqasm3.parse(text).statements:
        if isinstance(node, ast.Include):
            includes.append(node.filename)
        elif isinstance(node, ast.QubitDeclaration):
            declarations.append(('qubit', node.qubit.name, node.size.value))
        elif isinstance(node, ast.ClassicalDeclaration):
            if not isinstance(node.type, ast.BitType) or node.init_expression is not None:
                raise AssertionError('CLASSICAL_DECLARATION_CHANGED')
            declarations.append(('bit', node.identifier.name, node.type.size.value))
        elif isinstance(node, ast.QuantumGate):
            if node.modifiers or node.arguments or node.duration is not None:
                raise AssertionError('GATE_MODIFIERS_CHANGED')
            operations.append((node.name.name, *(wire(q) for q in node.qubits)))
        elif isinstance(node, ast.QuantumMeasurementStatement):
            operations.append(('measure', wire(node.measure.qubit), index(node.target, 'result')))
        else:
            raise AssertionError('UNEXPECTED_UNROLLED_STATEMENT')
    if includes != ['stdgates.inc'] or declarations != [('qubit', 'q', 4), ('qubit', 'ancilla', 1), ('bit', 'result', 4)]:
        raise AssertionError('DECLARATIONS_CHANGED')
    if operations != expected_operations():
        raise AssertionError('SOURCE_OPERATION_SEQUENCE_CHANGED')
    state, hadamards = integer_state(operations)
    expected = [0]*32
    expected[15], expected[31] = 16, -16
    if state != expected or hadamards != 9 or sum(a*a for a in state) != 2**hadamards:
        raise AssertionError('PARITY_ORACLE_STATE_MISMATCH')
    return dict(operations=operations, integer_state=state, hadamards=hadamards,
                amplitude_denominator='sqrt(2)^9', expected_data='1111',
                data_probability='1', ancilla='minus', basis_convention='q0 least significant; ancilla bit4')


def run(program, original_qasm):
    from pyqasm import dumps
    unrolled = dumps(program)
    if program.num_qubits != 5 or program.num_clbits != 4:
        raise AssertionError('RESOURCE_COUNTS_CHANGED')
    result = audit_unrolled(unrolled)
    Path('original.qasm').write_bytes(original_qasm.encode())
    Path('unrolled.qasm').write_bytes(unrolled.encode())
    return dict(accepted=True, original_qasm_sha256=hashlib.sha256(original_qasm.encode()).hexdigest(),
                unrolled_qasm_sha256=hashlib.sha256(unrolled.encode()).hexdigest(),
                structural_and_authored_state_checks=result,
                native_execution_performed=False, provider_jobs_submitted=False,
                scope='all original notebook cells plus authored finite structural/state witness',
                limitations=['Integer state is an authored interpretation, not a native worker state observation',
                             'No general unroller, GUI, linked-article or released acceptance claim'])


if __name__ == '__main__':
    print(json.dumps(run(program, qasm)))
