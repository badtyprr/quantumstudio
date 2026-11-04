import json, sys
import numpy as np
from qiskit.quantum_info import Statevector
checks = []
for case, truth in [(1, (0, 0)), (2, (0, 1)), (3, (1, 0)), (4, (1, 1))]:
    oracle = deutsch_function(case)
    # Independent definition: |x,y> maps to |x,y xor f(x)>.
    for x in (0, 1):
        for y in (0, 1):
            basis = x + 2*y
            expected_basis = x + 2*(y ^ truth[x])
            actual = Statevector.from_int(basis, 4).evolve(oracle).data
            expected = np.zeros(4); expected[expected_basis] = 1
            if not np.allclose(actual, expected, atol=1e-12, rtol=0):
                raise AssertionError((case, x, y, actual))
    expected_bit = truth[0] ^ truth[1]
    circuit = compile_circuit(oracle)
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    expected_state = np.zeros(4, dtype=complex)
    expected_state[expected_bit] = (-1)**truth[0] / np.sqrt(2)
    expected_state[expected_bit + 2] = -expected_state[expected_bit]
    residual = float(np.max(np.abs(state.data - expected_state)))
    if residual > 1e-12: raise AssertionError((case, state.data, expected_state))
    probabilities = state.probabilities([0])
    expected = [1-expected_bit, expected_bit]
    if not np.allclose(probabilities, expected, atol=1e-12, rtol=0):
        raise AssertionError((case, probabilities))
    counts = AerSimulator().run(circuit, shots=256, seed_simulator=1731).result().get_counts()
    if counts != {str(expected_bit): 256}: raise AssertionError((case, counts))
    label = deutsch_algorithm(oracle)
    if label != ('balanced' if expected_bit else 'constant'): raise AssertionError(label)
    checks.append(dict(case=case, truth=list(truth), state_residual=residual, probabilities=probabilities.tolist(), counts=counts, label=label))
errors = []
for invalid in (0, 5):
    try: deutsch_function(invalid)
    except ValueError as error: errors.append(dict(input=invalid, type=type(error).__name__, message=str(error)))
    else: raise AssertionError('invalid case accepted')
print(json.dumps(dict(checks=checks, expected_errors=errors, kernel_executable=sys.executable, kernel_version=sys.version)))
