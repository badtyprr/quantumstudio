"""Negative controls for the corrected local provider examples."""
import math
import unittest
from unittest.mock import patch

from witnesses import provider_qasm


class ProviderQasmTests(unittest.TestCase):
    def test_invalid_state_with_valid_counts(self):
        source = 'OPENQASM 2; include "stdgates.inc"; qubit[2] q; h q[0]; cx q[0],q[1];'
        endpoint = math.sqrt(0.5)
        for vector in ([endpoint, math.nan, 0, endpoint], [endpoint, 0, 0, -endpoint]):
            with self.subTest(vector=vector), patch.object(provider_qasm, "LocalSimulator") as backend:
                result = backend.return_value.run.return_value.result.return_value
                result.measurement_counts = {"00": 50, "11": 50}
                result.values = [vector]
                with self.assertRaises(AssertionError):
                    provider_qasm.verify(source)


if __name__ == "__main__":
    unittest.main()
