"""Check the CNOT twirls drawn in IBM-082, with the top wire as control."""
import itertools
import numpy as np

identity = np.eye(2, dtype=complex)
x = np.array([[0, 1], [1, 0]])
y = np.array([[0, -1j], [1j, 0]])
z = np.diag([1, -1])
gates = {"I": identity, "X": x, "Y": y, "Z": z}
cnot = np.eye(4, dtype=complex)[[0, 1, 3, 2]]

def pair(labels):
    return np.kron(gates[labels[0]], gates[labels[1]])

# Read each wire left to right in twirl-4.avif and twirl-check.avif.
for before, after in [("II", "II"), ("ZI", "ZI"), ("XI", "XX"), ("XY", "YZ")]:
    dressed = pair(after) @ cnot @ pair(before)
    assert any(np.array_equal(dressed, sign * cnot) for sign in (1, -1))
    for word in itertools.product(range(2), repeat=2):
        column = 2 * word[0] + word[1]
        assert np.argmax(abs(dressed[:, column])) == 2 * word[0] + (word[0] ^ word[1])
# XY4 uses two X gates and two pi rotations about Y.
pulse = (-1j * y) @ x
assert np.array_equal(pulse @ pulse, identity)
print("Verified four CNOT twirls on every computational basis input and the XY4 cycle.")
