import unittest

from qiskit import QuantumCircuit
from witnesses.qb019 import verify


class LocalBernsteinVaziraniTests(unittest.TestCase):
    def test_ancilla_and_bit_order(self):
        # The expected two-bit secret "10" occupies wires 0 and 1 in source order.
        circuit = QuantumCircuit(3)
        circuit.x([0, 2])
        circuit.measure_all()
        self.assertEqual(verify(circuit, "10", {"101": 100})["measured_word"], "101")
        for counts in ({"110": 100}, {"001": 100}, {"101": 99}):
            with self.subTest(counts=counts), self.assertRaises(AssertionError):
                verify(circuit, "10", counts)
        with self.assertRaises(AssertionError):
            verify(circuit, "01", {"110": 100})


if __name__ == "__main__":
    unittest.main()
