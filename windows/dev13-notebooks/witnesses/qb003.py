"""Finite, authored structural and reversible-arithmetic checks for QB003."""
import hashlib
import json
from pathlib import Path


REGISTERS = {'cin': (0, 1), 'a': (1, 4), 'b': (5, 4), 'cout': (9, 1)}


def parse_operations(text):
    import openqasm3
    from openqasm3 import ast

    def index(node, registers):
        if (not isinstance(node, ast.IndexedIdentifier) or node.name.name not in registers
                or len(node.indices) != 1 or len(node.indices[0]) != 1
                or not isinstance(node.indices[0][0], ast.IntegerLiteral)):
            raise AssertionError('EXPECTED_SCALAR_INDEX')
        offset, width = registers[node.name.name]
        value = node.indices[0][0].value
        if not 0 <= value < width:
            raise AssertionError('WIRE_RANGE')
        return offset + value

    declarations, includes, operations = [], [], []
    for node in openqasm3.parse(text).statements:
        if isinstance(node, ast.Include):
            includes.append(node.filename)
        elif isinstance(node, ast.QubitDeclaration):
            declarations.append(('qubit', node.qubit.name, node.size.value))
        elif isinstance(node, ast.ClassicalDeclaration):
            if not isinstance(node.type, ast.BitType) or node.init_expression is not None:
                raise AssertionError('CLASSICAL_DECLARATION_CHANGED')
            declarations.append(('bit', node.identifier.name, node.type.size.value))
        elif isinstance(node, ast.QuantumReset):
            operations.append(('reset', index(node.qubits, REGISTERS)))
        elif isinstance(node, ast.QuantumGate):
            if node.arguments or node.modifiers or node.duration is not None:
                raise AssertionError('UNEXPECTED_GATE_OPTIONS')
            name = node.name.name
            if name not in ('x', 'cx', 'ccx') or len(node.qubits) != {'x': 1, 'cx': 2, 'ccx': 3}[name]:
                raise AssertionError('UNEXPECTED_GATE')
            wires = tuple(index(q, REGISTERS) for q in node.qubits)
            if len(set(wires)) != len(wires):
                raise AssertionError('DUPLICATE_GATE_WIRE')
            operations.append((name, *wires))
        elif isinstance(node, ast.QuantumMeasurementStatement):
            operations.append(('measure', index(node.measure.qubit, REGISTERS),
                               index(node.target, {'ans': (0, 5)})))
        else:
            raise AssertionError('UNEXPECTED_STATEMENT')
    expected = [('qubit', name, width) for name, (_, width) in REGISTERS.items()]
    if declarations != expected + [('bit', 'ans', 5)] or includes != ['stdgates.inc']:
        raise AssertionError('DECLARATIONS_CHANGED')
    return operations


def apply_gates(state, gates):
    for name, *wires in gates:
        if name not in ('x', 'cx', 'ccx'):
            raise AssertionError('NON_UNITARY_CORE')
        if all(state & (1 << q) for q in wires[:-1]):
            state ^= 1 << wires[-1]
    return state


def audit_operations(operations):
    resets = [('reset', q) for q in range(10)]
    initialization = [('x', q) for q in (5, 6, 7, 4, 8)]
    measurements = [('measure', 5 + q, q) for q in range(4)] + [('measure', 9, 4)]
    if operations[:15] != resets + initialization or operations[-5:] != measurements:
        raise AssertionError('SOURCE_PREPARATION_OR_MEASUREMENT_CHANGED')
    core = operations[15:-5]
    if len(core) != 25:
        raise AssertionError('ADDER_CORE_SIZE')
    # Exhaustive basis permutation: arithmetic expectation is independent of gate decomposition.
    outputs = []
    for state in range(1024):
        carry_in, a, b, carry_out = state & 1, (state >> 1) & 15, (state >> 5) & 15, state >> 9
        total = a + b + carry_in
        expected = carry_in | (a << 1) | ((total & 15) << 5) | ((carry_out ^ (total >> 4)) << 9)
        actual = apply_gates(state, core)
        if actual != expected:
            raise AssertionError('ADDER_PERMUTATION_MISMATCH')
        outputs.append(actual)
    if len(set(outputs)) != 1024:
        raise AssertionError('NON_BIJECTIVE_ADDER')
    initialized = apply_gates(0, initialization)
    final = apply_gates(initialized, core)
    answer = sum(((final >> q) & 1) << c for _, q, c in measurements)
    if answer != 23 or ((final >> 1) & 15) != 8 or final & 1:
        raise AssertionError('ORIGINAL_RESULT_MISMATCH')
    return dict(basis_cases=1024, original_inputs=[8, 15], original_carry_in=0,
                answer=answer, displayed_answer=format(answer, '05b'),
                input_a_preserved=True, input_carry_preserved=True,
                carry_output_xor_verified=True, all_basis_outputs_distinct=True)


def run(program, source):
    from pyqasm import dumps
    if program.num_qubits != 10 or program.num_clbits != 5:
        raise AssertionError('RESOURCE_COUNTS_CHANGED')
    unrolled = dumps(program)
    result = audit_operations(parse_operations(unrolled))
    Path('original.qasm').write_bytes(source.encode())
    Path('unrolled.qasm').write_bytes(unrolled.encode())
    return dict(accepted=True, arithmetic=result,
                original_sha256=hashlib.sha256(source.encode()).hexdigest(),
                unrolled_sha256=hashlib.sha256(unrolled.encode()).hexdigest(),
                source_comment_one_is_actual_eight=True, native_execution_performed=False,
                provider_jobs_submitted=False,
                scope='Original notebook plus authored Boolean basis-permutation audit; no native state observation')


if __name__ == '__main__':
    print(json.dumps(run(module, adder_qasm_str)))
