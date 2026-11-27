import math
import unittest

from qiskit import QuantumCircuit
from witnesses.ibm052 import check_uniform_messages, winning_probability


class EntanglementChecks(unittest.TestCase):
    def test_correct_win_rate_with_biased_marginals_is_rejected(self):
        circuit = QuantumCircuit(2)
        circuit.ry(math.pi / 4, 0)
        with self.assertRaisesRegex(ValueError, "Unexpected CHSH probability"):
            winning_probability(circuit, 0, 0)

    def test_correct_decoding_of_a_stuck_coin_is_rejected(self):
        messages = {f"{c} {d} {c} {d}" for c in "01" for d in "01"}
        with self.assertRaisesRegex(ValueError, "Missing or unexpected"):
            check_uniform_messages({"0 0 0 0": 1024}, messages)
