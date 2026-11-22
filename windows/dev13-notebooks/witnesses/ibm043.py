"""Check the notebook against independently constructed arrays in Qiskit bit order."""
import json
import numpy as np

display = _ibm043_display
h = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
identity = np.eye(2)
flip = np.array([[0, 1], [1, 0]])
phi_expected = np.array([1, -1j, 1, -1j]) / 2
basis = np.arange(8)
three_qubits = np.isin(basis, [1, 2, 4]).astype(float) / np.sqrt(3)

for actual, expected in [
    (_ibm043_first, [0, 1, 0, 0]),
    (phi.data, phi_expected),
    ((plus ^ minus_i).data, phi_expected),
    (H.tensor(Id).data, np.kron(h, identity)),
    (H.tensor(Id).tensor(X).data, np.kron(np.kron(h, identity), flip)),
    ((H ^ Id ^ X).data, np.kron(np.kron(h, identity), flip)),
    (phi.evolve(H ^ Id).data, np.array([1, -1j, 0, 0]) / np.sqrt(2)),
    (psi.evolve(CX).data, np.array([1, 0, 0, 1]) / np.sqrt(2)),
    (w.data, three_qubits),
]:
    np.testing.assert_equal(np.shape(actual), np.shape(expected))
    np.testing.assert_allclose(actual, expected, atol=1e-14, rtol=0)

if len(_ibm043_measurements) != 2:
    raise AssertionError("Expected both original partial measurements")
outcomes = []
for width, (outcome, amplitudes) in enumerate(_ibm043_measurements, 1):
    if len(outcome) != width or set(outcome) - {"0", "1"}:
        raise AssertionError(outcome)
    indices = basis % (2 ** width)
    probabilities = np.bincount(indices, weights=np.abs(three_qubits) ** 2, minlength=2 ** width)
    np.testing.assert_allclose(w.probabilities(list(range(width))), probabilities, atol=1e-14, rtol=0)
    projected = np.where(indices == int(outcome, 2), three_qubits, 0)
    probability = np.vdot(projected, projected).real
    if probability == 0:
        raise AssertionError("Impossible partial measurement")
    np.testing.assert_equal(amplitudes.shape, projected.shape)
    np.testing.assert_allclose(amplitudes, projected / np.sqrt(probability), atol=1e-14, rtol=0)
    outcomes.append({"width": width, "outcome": outcome, "probability": float(probability)})
print(json.dumps({"accepted": True, "partial_measurements": outcomes}))
