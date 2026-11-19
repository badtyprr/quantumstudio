"""Independent integer Grover recurrence against original QASM and SDK results."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def expected_state(depth):
    if type(depth) is not int or not 0 <= depth <= 3:
        raise AssertionError('UNREVIEWED_DEPTH')
    numerators, divisor = [1] * 8, 1
    for _ in range(depth):
        numerators[5] *= -1
        total = sum(numerators)
        numerators = [4 * a - total for a in numerators]
        divisor *= 4
    probabilities = [Fraction(a * a, divisor * divisor * 8) for a in numerators]
    assert sum(probabilities) == 1
    return numerators, divisor, probabilities


def verify_source(source, depth):
    expected_state(depth)
    header = ['OPENQASM 3;', 'include "stdgates.inc";', 'qubit[3] qb;', 'bit[3] cb;', 'h qb;']
    iteration = ['x qb[1];', 'ctrl(2) @ z qb[1], qb[2], qb[0];', 'x qb[1];',
                 'h qb;', 'x qb;', 'ctrl(2) @ z qb[0], qb[1], qb[2];', 'x qb;', 'h qb;']
    lines = [' '.join(line.split()) for line in source.splitlines() if line.strip()]
    if lines != header + iteration * depth + ['cb = measure qb;']:
        raise AssertionError('ORACLE_DIFFUSER_OR_MEASUREMENT_CHANGED')


def verify_results(amplitudes, counts, depth, shots):
    numerators, divisor, probabilities = expected_state(depth)
    if len(amplitudes) != 8 or shots != 1024 or not all(math.isfinite(abs(a)) for a in amplitudes):
        raise AssertionError('ORIGINAL_DIMENSION_OR_SHOTS_CHANGED')
    expected = [a / (divisor * math.sqrt(8)) for a in numerators]
    phase = amplitudes[5] / expected[5]
    if not math.isfinite(abs(phase)) or abs(phase) == 0:
        raise AssertionError('INVALID_TARGET_AMPLITUDE')
    phase /= abs(phase)
    residual = max(abs(a - phase * e) for a, e in zip(amplitudes, expected))
    if not math.isfinite(residual) or residual >= 1e-12:
        raise AssertionError('GROVER_STATE_MISMATCH')
    if (sum(counts.values()) != shots or any(type(k) is not str or len(k) != 3
            or set(k) - {'0', '1'} or type(v) is not int or v < 0 for k, v in counts.items())):
        raise AssertionError('INVALID_COUNTS')
    for basis, probability in enumerate(probabilities):
        p = float(probability)
        tolerance = 6 * math.sqrt(p * (1 - p) / shots) + 2 / shots
        if abs(counts.get(format(basis, '03b'), 0) / shots - p) > tolerance:
            raise AssertionError('GROVER_SAMPLE_MISMATCH')
    return dict(depth=depth, integer_amplitudes=numerators, divisor=divisor,
                amplitude_normalization='divisor*sqrt(8)', target='101',
                target_probability=str(probabilities[5]), probabilities=[str(p) for p in probabilities],
                sdk_state_residual=residual, counts=dict(counts), shots=shots)


def run(captures, restored, circuits, batch_counts, local, shots, example, last_qasm):
    from qiskit.qasm3 import loads
    from qiskit.quantum_info import Statevector
    if local is not True or not restored or len(captures) != 4 or len(circuits) != 4 or len(batch_counts) != 4:
        raise AssertionError('ORIGINAL_LOCAL_BATCH_OR_CAPTURE_CHANGED')
    rows = []
    for depth, (capture, circuit, counts) in enumerate(zip(captures, circuits, batch_counts)):
        if capture['depth'] != depth or capture['qubits'] != 3:
            raise AssertionError('CAPTURE_ORDER_CHANGED')
        source = capture['source']
        verify_source(source, depth)
        if circuit != loads(source) or circuit.num_qubits != 3 or circuit.num_clbits != 3:
            raise AssertionError('ORIGINAL_LOADED_CIRCUIT_CHANGED')
        measurements = [op for op in circuit.data if op.operation.name == 'measure']
        if len(measurements) != 3 or any(circuit.find_bit(op.qubits[0]).index != i
                or circuit.find_bit(op.clbits[0]).index != i for i, op in enumerate(measurements)):
            raise AssertionError('MEASUREMENT_MAPPING_CHANGED')
        amplitudes = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False)).data
        result = verify_results(amplitudes, counts, depth, shots)
        result['qasm_sha256'] = hashlib.sha256(source.encode()).hexdigest()
        result['amplitudes'] = [[float(a.real), float(a.imag)] for a in amplitudes]
        Path(f'original-depth{depth}.qasm').write_bytes(source.encode())
        rows.append(result)
    if example != captures[1]['source'] or last_qasm != captures[3]['source']:
        raise AssertionError('ORIGINAL_EXAMPLE_OR_FINAL_SOURCE_CHANGED')
    report = dict(accepted=True, original_builder_restored=True, rows=rows,
                  source_capture='Original function return values observed during original cell7',
                  cloud_branch_executed=False, native_execution_performed=False,
                  scope='All original cells executed on original local simulator branch; independent Grover verification',
                  limitations=['Statevector extraction is authored verification; simulator sampling remains unseeded',
                               'No IBM branch, linked-material, native, GUI/package or release acceptance claim'])
    Path('qb008-witness.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(_qb008_captures, _qb008_builder_restored, circuits, batch_counts,
                         USE_SIMULATOR, shots, qasm_example, qasm)))
