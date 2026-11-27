"""Compare the four source circuits to independently constructed amplitudes."""
import json
from math import pi

import numpy as np
from qiskit.quantum_info import Statevector


def rx(angle):
    cosine = np.cos(angle / 2)
    sine = -1j * np.sin(angle / 2)
    return np.array([[cosine, sine], [sine, cosine]])


def two_local_reference():
    zero = np.array([1, 0, 0, 0])
    first_layer = np.kron(rx(pi / 3), rx(pi / 2))
    controlled_z = np.diag([1, 1, 1, -1])
    final_layer = np.kron(rx(pi / 2), rx(pi / 3))
    return final_layer @ controlled_z @ first_layer @ zero


def feature_reference():
    x, y = 0.1, 0.2
    parity = (pi - x) * (pi - y)
    phases = np.exp(2j * np.array([0, x + parity, y + parity, x + y]))
    hadamard = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    layer = np.diag(phases) @ np.kron(hadamard, hadamard)
    return layer @ layer @ np.array([1, 0, 0, 0])


if __name__ == "__main__":
    basis = np.eye(8)
    states = [
        (_ibm102_first_state, basis[1]),
        (Statevector.from_instruction(qc).data, (basis[4] + basis[7]) / np.sqrt(2)),
        (Statevector.from_instruction(reference_circuit).data, two_local_reference()),
        (Statevector.from_instruction(zz_feature_map_reference).data, feature_reference()),
    ]
    fidelities = []
    for actual, expected in states:
        fidelity = float(abs(np.vdot(expected, actual)) ** 2)
        if not np.isclose(fidelity, 1.0, rtol=0, atol=1e-12):
            raise ValueError("Reference state fidelity differs: " + str(fidelity))
        fidelities.append(fidelity)
    print(json.dumps(dict(accepted=True, fidelities=fidelities)))
