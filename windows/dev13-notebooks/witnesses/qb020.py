import json

import numpy as np
from qiskit.quantum_info import Statevector


def verify(circuit, expectation, counts):
    reference = Statevector(np.array([1, 0, 0, 1]) / np.sqrt(2))
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    if not state.equiv(reference):
        raise AssertionError("Circuit did not prepare the positive-phase Bell state")
    if not np.isclose(expectation, 1, rtol=0, atol=1e-10):
        raise AssertionError("Unexpected ZZ expectation")
    if set(counts) != {"00", "11"} or sum(counts.values()) != 200:
        raise AssertionError("Unexpected Bell measurement outcomes or shot total")
    if abs(counts["00"] - 100) > 6 * np.sqrt(50):
        raise AssertionError("Bell measurements exceeded six standard deviations")
    return dict(accepted=True, zz=expectation, counts=dict(counts), shots=200)


if __name__ == "__main__":
    print(json.dumps(verify(circ, float(result[0].data.evs), measurement_counts), allow_nan=False))
