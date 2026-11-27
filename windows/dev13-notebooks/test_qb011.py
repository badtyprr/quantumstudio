import unittest

import numpy as np

from witnesses.qb011 import operator_error


class TranspilerChainTests(unittest.TestCase):
    def test_global_phase(self):
        start = np.array([[0, 1j], [1, 0]])
        self.assertAlmostEqual(operator_error(start, 1j * start, 1), 0)

    def test_changed_relative_phase(self):
        start = np.eye(4)
        finish = start.copy()
        finish[-1, -1] = -1
        with self.assertRaisesRegex(ValueError, "changed the operator"):
            operator_error(start, finish, 2)

    def test_wrong_number_of_qubits(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            operator_error(np.eye(2), np.eye(2), 2)
