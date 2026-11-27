# The next source cell reuses qc for the entangled reference state.
from qiskit.quantum_info import Statevector

_ibm102_first_state = Statevector.from_instruction(qc).data.copy()
