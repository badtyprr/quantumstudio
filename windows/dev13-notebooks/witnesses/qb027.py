"""Authored Braket local witnesses; importing this module uses only stdlib."""
import itertools
import json
import math

STATE_TOLERANCE = 1e-12
BELL_SHOTS = 4096
BELL_FREQUENCY_TOLERANCE = 0.05
ALGORITHM_SHOTS = 128


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def walsh_state(truth):
    """Independent Boolean character sum, data MSB then |-> ancilla."""
    size = len(truth)
    require(size >= 2 and size & (size - 1) == 0, 'TRUTH_SIZE')
    require(all(type(v) is int and v in (0, 1) for v in truth), 'TRUTH_BITS')
    coefficients = [sum((-1) ** (truth[x] + ((x & y).bit_count() % 2))
                        for x in range(size)) / size for y in range(size)]
    return [sign * a / math.sqrt(2) for a in coefficients for sign in (1, -1)]


def finite_cases():
    dj = [(f'dj_{"".join(map(str, t))}', 2, list(t))
          for t in itertools.product((0, 1), repeat=4) if sum(t) in (0, 2, 4)]
    bv = []
    for n, secret in [(2, s) for s in range(4)] + [(3, 1), (3, 4)]:
        bv.append((f'bv_{secret:0{n}b}', n,
                   [(x & secret).bit_count() % 2 for x in range(2**n)]))
    return dj + bv


def check_counts(counts, shots, width, allowed):
    require(isinstance(counts, dict) and bool(counts), 'COUNTS_EMPTY')
    require(all(isinstance(k, str) and len(k) == width and set(k) <= {'0', '1'}
                and type(v) is int and v > 0 for k, v in counts.items()), 'COUNTS_FORMAT')
    require(sum(counts.values()) == shots, 'COUNTS_TOTAL')
    require(set(counts) <= set(allowed), 'COUNTS_SUPPORT')


def state_residual(actual, expected):
    require(len(actual) == len(expected) and bool(actual), 'STATE_WIDTH')
    require(all(math.isfinite(complex(z).real) and math.isfinite(complex(z).imag)
                for z in list(actual) + list(expected)), 'STATE_NONFINITE')
    residual = max(abs(a-b) for a, b in zip(actual, expected))
    require(residual <= STATE_TOLERANCE, 'STATE_AMPLITUDES')
    return residual


def run(source_circuit):
    # Imports and native execution occur only in the separately reserved run.
    from importlib.metadata import version
    import numpy as np
    from braket.circuits import Circuit
    from braket.circuits.serialization import IRType
    from braket.devices import LocalSimulator
    from braket.default_simulator.state_vector_simulator import StateVectorSimulator

    delegate = StateVectorSimulator()
    device = LocalSimulator(delegate)
    backend = f'{type(delegate).__module__}.{type(delegate).__name__}'
    require(backend == 'braket.default_simulator.state_vector_simulator.StateVectorSimulator',
            'LOCAL_BACKEND_IDENTITY')

    def sampled(circ, shots, width, allowed):
        result = device.run(circ, shots=shots).result()
        require(list(result.measured_qubits) == list(range(width)), 'MEASURED_QUBIT_ORDER')
        counts = {str(k): int(v) for k, v in result.measurement_counts.items()}
        check_counts(counts, shots, width, allowed)
        return dict(shots=shots, counts=counts, measured_qubits=list(result.measured_qubits))

    def state(circ, expected):
        circ.state_vector()
        result = device.run(circ, shots=0).result()
        actual = [complex(v) for v in result.values[0]]
        residual = state_residual(actual, expected)
        return dict(state=[[z.real, z.imag] for z in actual],
                    expected=[[complex(z).real, complex(z).imag] for z in expected],
                    residual=residual, shots=0)

    before = source_circuit.to_ir(ir_type=IRType.OPENQASM).source
    bell = sampled(source_circuit, BELL_SHOTS, 2, {'00', '11'})
    require(all(abs(bell['counts'].get(k, 0)/BELL_SHOTS-.5) <= BELL_FREQUENCY_TOLERANCE
                for k in ('00', '11')), 'BELL_FREQUENCY')
    require(source_circuit.to_ir(ir_type=IRType.OPENQASM).source == before,
            'ORIGINAL_CIRCUIT_MUTATED')
    states = {'bell': state(Circuit().h(0).cnot(0, 1),
                            [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)]),
              'phase_bell': state(Circuit().h(0).cnot(0, 1).s(0),
                                  [1/math.sqrt(2), 0, 0, 1j/math.sqrt(2)])}
    ordering = []
    for which, key in [(0, '100'), (2, '001')]:
        expected = [0]*8; expected[int(key, 2)] = 1
        control = Circuit().i(0).i(1).i(2).x(which)
        analytic = state(control, expected)
        control = Circuit().i(0).i(1).i(2).x(which).measure([0, 1, 2])
        ordering.append(dict(qubit=which, state=analytic,
                             sampling=sampled(control, ALGORITHM_SHOTS, 3, {key})))

    def algorithm(n, truth, measure):
        # Reversible Boolean truth permutation implements the oracle. Expected
        # amplitudes come from walsh_state, never from this matrix or Braket.
        dim = 2**(n+1)
        matrix = np.zeros((dim, dim), dtype=complex)
        for x, fx in enumerate(truth):
            for ancilla in (0, 1):
                matrix[2*x+(ancilla ^ fx), 2*x+ancilla] = 1
        circ = Circuit()
        for q in range(n): circ.h(q)
        circ.x(n).h(n)
        circ.unitary(targets=list(range(n+1)), matrix=matrix)
        for q in range(n): circ.h(q)
        if measure: circ.measure(list(range(n)))
        return circ

    algorithms = []
    for label, n, truth in finite_cases():
        expected = walsh_state(truth)
        probs = [abs(expected[2*y])**2 + abs(expected[2*y+1])**2 for y in range(2**n)]
        support = {f'{y:0{n}b}' for y, p in enumerate(probs) if p > STATE_TOLERANCE}
        # All promised n=2 functions are affine; these 14 cases are deterministic.
        require(len(support) == 1, 'FINITE_CASE_NOT_DETERMINISTIC')
        algorithms.append(dict(case=label, truth=truth, expected_data_probabilities=probs,
            state=state(algorithm(n, truth, False), expected),
            sampling=sampled(algorithm(n, truth, True), ALGORITHM_SHOTS, n, support)))

    negatives = []
    for label, circ, shots, fragment in [
        ('empty', Circuit(), 1, 'at least one non-zero-qubit gate'),
        ('zero_shots_without_result', Circuit().h(0), 0, 'No result types specified'),
        ('state_at_positive_shots', Circuit().h(0).state_vector(), 1,
         'StateVector or Amplitude cannot be specified when shots>0')]:
        try:
            device.run(circ, shots=shots)
        except ValueError as error:
            require(fragment in str(error), 'NEGATIVE_DIAGNOSTIC_'+label)
            negatives.append(dict(case=label, type=type(error).__name__, message=str(error)))
        else:
            raise AssertionError('NEGATIVE_ACCEPTED_'+label)
    return dict(accepted=True, route='selected-cells/direct-native-execution',
        whole_notebook_complete=False, selected_source_cells=[6], backend=backend,
        packages={name:version(name) for name in ('amazon-braket-sdk',
                    'amazon-braket-default-simulator','amazon-braket-schemas','numpy')},
        original_measured_bell=bell, original_serialized_source=before,
        original_circuit_preserved=True, authored_states=states, ordering=ordering,
        algorithms=algorithms, negatives=negatives, state_tolerance=STATE_TOLERANCE,
        bell_frequency_tolerance=BELL_FREQUENCY_TOLERANCE,
        seed=None, sampling='Unseeded backend-owned default_rng; statistical Bell bound only',
        serialization='SDK-internal OpenQASM serialization, no manual QASM adaptation or QIR',
        limitations=['Only original cell6 construction executes; local simulation and algorithms authored',
                     'No original AWS SV1 job, provider credentials or whole QB027 notebook acceptance',
                     'No exact stochastic count replay or all-backend/gate/noise compatibility claim'])


if __name__ == '__main__':
    print(json.dumps(run(circuit)))
