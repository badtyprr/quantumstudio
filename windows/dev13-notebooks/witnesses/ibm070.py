"""Check the lesson unitary, classical wiring and measured Bell distribution."""
import json

import numpy as np
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator


def verify(circuit):
    measurements = [
        (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
        for item in circuit.data if item.operation.name == "measure"
    ]
    if circuit.num_clbits != 2 or sorted(measurements) != [(0, 0), (1, 1)]:
        raise ValueError("Measurement wiring differs from the source circuit")
    unitary = Operator(circuit.remove_final_measurements(inplace=False)).data
    # Qubit zero is the rightmost bit. Apply H on that bit, then CX to bit one.
    expected = np.array([[1, 1, 0, 0], [0, 0, 1, -1],
                         [0, 0, 1, 1], [1, -1, 0, 0]]) / np.sqrt(2)
    if not np.allclose(unitary, expected, rtol=0, atol=1e-12):
        raise ValueError("Bell preparation unitary differs")
    shots = 4096
    counts = AerSimulator().run(circuit, shots=shots, seed_simulator=70).result().get_counts()
    if set(counts) != {"00", "11"} or sum(counts.values()) != shots or abs(counts["00"] / shots - 0.5) > 0.05:
        raise ValueError("Bell sampling differs from the expected distribution")
    return dict(accepted=True, max_operator_error=float(np.max(np.abs(unitary - expected))),
                measurement_wiring=measurements, counts=counts)


if __name__ == "__main__":
    print(json.dumps(verify(qc)))
