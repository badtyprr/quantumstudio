import unittest

from qiskit import QuantumCircuit
from witnesses.qb020 import verify


class BellSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.bell = QuantumCircuit(2)
        self.bell.h(0)
        self.bell.cx(0, 1)
        self.counts = {"00": 98, "11": 102}

    def test_measured_bell(self):
        self.bell.measure_all()
        self.assertEqual(verify(self.bell, 1.0, self.counts)["shots"], 200)

    def test_wrong_relative_phase(self):
        self.bell.z(1)
        with self.assertRaises(AssertionError):
            verify(self.bell, 1.0, self.counts)

    def test_incorrect_results(self):
        for zz, counts in [(0.0, self.counts), (float("nan"), self.counts),
                           (1.0, {"01": 98, "10": 102}), (1.0, {"00": 1, "11": 199}),
                           (1.0, {"00": 100, "11": 99})]:
            with self.subTest(zz=zz, counts=counts), self.assertRaises(AssertionError):
                verify(self.bell, zz, counts)
