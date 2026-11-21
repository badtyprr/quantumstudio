"""Negative controls for the local GHZ notebook witness."""
import unittest

from qiskit import QuantumCircuit
from witnesses.qb_ghz import check_endpoints, verify


class GhzChecks(unittest.TestCase):
    def test_invalid_counts(self):
        for counts in ({"000": 100}, {"000": 50, "101": 50},
                       {"000": 50, "111": 49}, {"000": 99, "111": 1}):
            with self.subTest(counts=counts), self.assertRaises(AssertionError):
                check_endpoints(counts, 3, 100)

    def test_relative_phase_and_measurement_order(self):
        for change in ("minus", "reversed"):
            q = QuantumCircuit(3, 3)
            q.h(0)
            q.cx(0, 1)
            q.cx(1, 2)
            if change == "minus":
                q.z(0)
            q.measure(range(3), [2, 1, 0] if change == "reversed" else range(3))
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify(q, None)


if __name__ == "__main__":
    unittest.main()
