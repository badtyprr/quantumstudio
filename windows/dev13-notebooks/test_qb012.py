import unittest

import numpy as np
from braket.circuits import Circuit
from witnesses.qb012 import verify


class ConversionOperatorTests(unittest.TestCase):
    def test_global_phase_is_immaterial(self):
        operator = Circuit().h(0).cnot(0, 1).to_unitary()
        np.testing.assert_allclose(verify(operator, 1j * operator), [0, 0], atol=1e-12)

    def test_both_conversions_must_preserve_every_column(self):
        operator = Circuit().h(0).cnot(0, 1).to_unitary()
        wrong = operator.copy()
        wrong[:, 1] *= -1
        for pair in ((wrong, operator), (operator, wrong)):
            with self.assertRaises(ValueError):
                verify(*pair)
