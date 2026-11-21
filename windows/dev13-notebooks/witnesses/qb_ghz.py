"""Validate the GHZ circuit constructed in the original notebook cell."""
import json
import math

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator


def check_endpoints(counts, width, shots):
    endpoints = ("0" * width, "1" * width)
    if set(counts) != set(endpoints) or sum(counts.values()) != shots:
        raise AssertionError((width, shots, counts))
    if abs(counts[endpoints[0]] - shots / 2) > 6 * math.sqrt(shots / 4):
        raise AssertionError((width, shots, counts))
    return [counts[key] for key in endpoints]


def verify(circuit, ghz):
    if circuit.num_qubits != 3 or circuit.num_clbits != 3:
        raise AssertionError("Expected the original three-qubit measured circuit")
    actual = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    expected = np.zeros(8, dtype=complex)
    expected[[0, 7]] = 1 / math.sqrt(2)
    residual = float(np.max(np.abs(actual.data - expected)))
    if residual > 1e-12:
        raise AssertionError(residual)

    backend = AerSimulator(method="matrix_product_state")
    samples = []
    for width, shots in ((3, 1000), (30, 1000), (100, 200)):
        measured = circuit if width == 3 else ghz(width)
        wires = [(measured.find_bit(op.qubits[0]).index, measured.find_bit(op.clbits[0]).index)
                 for op in measured.data if op.operation.name == "measure"]
        if sorted(wires) != [(i, i) for i in range(width)]:
            raise AssertionError("Measurements must preserve the original wire indexes")
        counts = backend.run(measured, shots=shots, seed_simulator=7).result().get_counts()
        endpoints = check_endpoints(counts, width, shots)
        # The coherent plus state has even parity in the X basis. An
        # incoherent mixture also passes the Z-basis endpoint test.
        rotated = measured.remove_final_measurements(inplace=False)
        rotated.h(range(width))
        rotated.measure_all()
        x_counts = backend.run(rotated, shots=shots, seed_simulator=11).result().get_counts()
        if sum(x_counts.values()) != shots or any(bits.count("1") % 2 for bits in x_counts):
            raise AssertionError("GHZ coherence check failed")
        samples.append(dict(width=width, shots=shots, endpoint_counts=endpoints, even_parity_shots=shots))
    return dict(accepted=True, local_backend="Aer CPU matrix product state", state_residual=residual, samples=samples)


if __name__ == "__main__":
    print(json.dumps(verify(circuit, ghz), allow_nan=False))
