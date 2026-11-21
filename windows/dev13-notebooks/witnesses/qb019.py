"""Check the notebook circuit against its Bernstein-Vazirani phase oracle."""
import json
import numpy as np
from qiskit.quantum_info import Statevector

def verify(circuit, secret, counts):
    width = len(secret)
    if not width or set(secret) - {"0", "1"} or circuit.num_qubits != width + 1:
        raise AssertionError("Invalid oracle width")
    # The source puts the first character on wire zero and measures the
    # ancilla. Qiskit displays classical bits from highest to lowest.
    expected = "1" + secret[::-1]
    reference = np.zeros(2 ** (width + 1), dtype=complex)
    reference[int(expected, 2)] = 1
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    residual = float(np.max(np.abs(state.data - reference)))
    if residual > 1e-12 or counts != {expected: 100}:
        raise AssertionError((expected, residual, counts))
    return dict(accepted=True, secret=secret, measured_word=expected,
                sampler="Qiskit StatevectorSampler", counts=counts, state_residual=residual)

if __name__ == "__main__":
    print(json.dumps(verify(qiskit_circuit, s, counts), allow_nan=False))
