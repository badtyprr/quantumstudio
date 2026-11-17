"""Audit the original full CPU sample; no GPU or ground-state optimization claim."""
import hashlib
import json
from pathlib import Path


def validate_coefficients(h, jr, jc):
    n = len(h)
    if (not 1 <= n <= 5 or len(jr) != n - 1 or len(jc) != n
            or any(len(row) != n for row in h + jr)
            or any(len(row) != n - 1 for row in jc)
            or any(type(value) is not int or value not in (-1, 1)
                   for row in h + jr + jc for value in row)):
        raise AssertionError('INVALID_ISING_COEFFICIENTS')
    return n


def classical_minimum(h, jr, jc):
    """Exact row dynamic programming for this measured diagonal cost function."""
    n = validate_coefficients(h, jr, jc)
    states = [[1 - 2 * ((bits >> i) & 1) for i in range(n)] for bits in range(1 << n)]

    def row_energy(row, state):
        return (sum(h[row][i] * state[i] for i in range(n))
                + sum(jc[row][i] * state[i] * state[i + 1] for i in range(n - 1)))

    costs = [row_energy(0, state) for state in states]
    paths = [[i] for i in range(len(states))]
    for row in range(1, n):
        next_costs, next_paths = [], []
        for state_index, state in enumerate(states):
            candidate, previous_index = min(
                (costs[j] + sum(jr[row - 1][i] * previous[i] * state[i] for i in range(n)), j)
                for j, previous in enumerate(states))
            next_costs.append(row_energy(row, state) + candidate)
            next_paths.append(paths[previous_index] + [state_index])
        costs, paths = next_costs, next_paths
    best = min(range(len(costs)), key=costs.__getitem__)
    spins = [states[i] for i in paths[best]]
    return costs[best], [[(1 - value) // 2 for value in row] for row in spins]


def sample_energies(measurements, h, jr, jc):
    import numpy as np
    n = validate_coefficients(h, jr, jc)
    values = np.asarray(measurements)
    if values.ndim != 2 or values.shape[1] != n * n or not np.isin(values, [0, 1]).all():
        raise AssertionError('INVALID_MEASUREMENTS')
    spins = 1 - 2 * values.astype(np.int64).reshape(-1, n, n)
    return ((spins * np.asarray(h)).sum(axis=(1, 2))
            + (spins[:, :-1, :] * spins[:, 1:, :] * np.asarray(jr).reshape(n - 1, n)).sum(axis=(1, 2))
            + (spins[:, :, :-1] * spins[:, :, 1:] * np.asarray(jc).reshape(n, n - 1)).sum(axis=(1, 2)))


def run(length, h, jr, jc, qubits, circuit, results, cpu_time, energy_func, obj_func):
    import cirq
    import numpy as np
    if length != 5 or qubits != cirq.GridQubit.square(5) or set(circuit.all_qubits()) != set(qubits):
        raise AssertionError('ORIGINAL_GRID_CHANGED')
    measurements = results.measurements['x']
    if measurements.shape != (10000, 25) or results.repetitions != 10000:
        raise AssertionError('ORIGINAL_SHOT_COUNT_CHANGED')
    measurement_ops = [op for op in circuit.all_operations() if cirq.is_measurement(op)]
    if (len(measurement_ops) != 1 or measurement_ops[0].qubits != tuple(qubits)
            or cirq.measurement_key_name(measurement_ops[0]) != 'x'):
        raise AssertionError('MEASUREMENT_ORDER_CHANGED')
    energies = sample_energies(measurements, h, jr, jc)
    source_energy = energy_func(length, h, jr, jc)
    if any(int(source_energy(row)) != int(expected) for row, expected in zip(measurements, energies)):
        raise AssertionError('SOURCE_ROW_ENERGY_MISMATCH')
    mean = float(energies.mean())
    if abs(float(obj_func(results)) - mean) > 1e-12:
        raise AssertionError('SOURCE_MEAN_MISMATCH')
    ground, minimizing_bits = classical_minimum(h, jr, jc)
    certificate = sample_energies(np.asarray(minimizing_bits).reshape(1, 25), h, jr, jc)
    if int(certificate[0]) != ground or int(energies.min()) < ground:
        raise AssertionError('CLASSICAL_BOUND_MISMATCH')
    counts = {}
    for row in measurements:
        key = ''.join(str(int(bit)) for bit in row)
        counts[key] = counts.get(key, 0) + 1
    if sum(counts.values()) != 10000:
        raise AssertionError('COUNT_TOTAL')
    Path('qb007-cpu-counts.json').write_text(json.dumps(counts, sort_keys=True), encoding='utf-8')
    report = dict(accepted=True, original_grid=5, qubits=25, shots=10000,
        coefficients=dict(h=h, jr=jr, jc=jc), sampled_energy=mean,
        exact_classical_minimum=ground, minimizing_bits=minimizing_bits,
        source_row_energy_checks=10000, original_cpu_seconds=float(cpu_time),
        measurement_sha256=hashlib.sha256(measurements.astype(np.uint8).tobytes()).hexdigest(),
        ground_state_optimization_performed=False, gpu_benchmark_executed=False,
        speedup_verified=False, whole_notebook_complete=False,
        scope='Original full CPU workload with authored CPU initialization and independent sample-cost audit',
        limitations=['Random coefficients and samples are original and unseeded; timings are observations only',
                     'Classical minimum concerns the source diagonal cost function, not a general quantum Hamiltonian',
                     'No independent full 25-qubit state-vector equivalence or native QuantumStudio execution claim',
                     'GPU construction/benchmark and speedup cells excluded'])
    Path('qb007-cpu-witness.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(run(length, h, jr, jc, qubits, circuit, results, cpu_time, energy_func, obj_func)))
