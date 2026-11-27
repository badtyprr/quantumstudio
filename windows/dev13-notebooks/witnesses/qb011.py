"""Verify the original randomized conversion chain and its full operator."""
import json

import numpy as np


def operator_error(start, finish, qubits):
    dimension = 2 ** qubits
    if start.shape != (dimension, dimension) or finish.shape != start.shape:
        raise ValueError("Conversion changed the operator dimensions")
    # Use a largest-magnitude entry to estimate the phase without a small divisor.
    pivot = np.unravel_index(np.argmax(np.abs(start)), start.shape)
    if abs(start[pivot]) == 0 or abs(finish[pivot]) == 0:
        raise ValueError("Missing operator amplitude")
    phase = finish[pivot] / start[pivot]
    error = float(np.max(np.abs(finish - (phase / abs(phase)) * start)))
    if not np.isfinite(error) or error > 1e-7:
        raise ValueError("Conversion changed the operator")
    return error


if __name__ == "__main__":
    from braket.circuits import Circuit as BraketCircuit
    from cirq import Circuit as CirqCircuit
    from pyquil import Program
    from pytket.circuit import Circuit as TketCircuit
    from qiskit import QuantumCircuit

    chain = [(circuit_start, CirqCircuit), (braket_circuit, BraketCircuit),
             (pyquil_circuit, Program), (qiskit_circuit, QuantumCircuit),
             (pytket_circuit, TketCircuit), (circuit_finish, CirqCircuit)]
    if not all(isinstance(program, expected) for program, expected in chain):
        raise ValueError("The notebook skipped a conversion stage")
    qubits = len(circuit_start.all_qubits())
    error = operator_error(start_u, finish_u, qubits)
    print(json.dumps(dict(accepted=True, qubits=qubits, dimension=start_u.shape[0],
                          max_operator_error=error, stages=[type(p).__module__ + "." +
                          type(p).__name__ for p, _ in chain]), allow_nan=False))
