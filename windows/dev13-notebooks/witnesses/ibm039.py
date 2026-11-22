"""Verify the source's measurements, linear algebra and gate sequence."""
import json
import numpy as np

initial = np.array([(1 + 2j) / 3, -2 / 3])
phase = np.exp(1j * np.pi / 4)
a, b = (1 + phase) / 2, (1 - phase) / 2
unitary = np.array([[b, a], [1j*a, 1j*b]])
final = unitary[:, 0]
measured = int(outcome)
post = np.zeros(2, dtype=complex)
post[measured] = initial[measured] / abs(initial[measured])
samples = [(_ibm039_first_counts, 1000, 5/9), (dict(statistics), 4000, abs(final[0])**2)]
for counts, shots, probability in samples:
    if set(counts) != {"0", "1"} or sum(counts.values()) != shots:
        raise AssertionError(counts)
    if abs(counts["0"] - shots * probability) > 6 * np.sqrt(shots * probability * (1 - probability)):
        raise AssertionError(counts)
accepted = (u.is_valid() and not w.is_valid()
            and np.allclose(M @ M, [[1, .75], [0, .25]])
            and np.allclose(_ibm039_initial, initial)
            and np.allclose(state.data, post)
            and np.allclose(v.data, final)
            and np.allclose(Operator.from_circuit(circuit).data, unitary))
print(json.dumps({"accepted": bool(accepted), "measurement": measured,
                  "first_counts": {k: int(v) for k, v in samples[0][0].items()},
                  "circuit_counts": {k: int(v) for k, v in samples[1][0].items()}}))
