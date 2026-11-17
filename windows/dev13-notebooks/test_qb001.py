"""Finite source-witness controls: parity, ancilla phase and measured wiring."""
import unittest
from witnesses.qb001 import audit_unrolled, expected_operations, integer_state

FLAT = '''OPENQASM 3.0;
include "stdgates.inc";
qubit[4] q;
qubit[1] ancilla;
x ancilla[0];
h q[0]; h q[1]; h q[2]; h q[3]; h ancilla[0];
cx q[0], ancilla[0]; cx q[1], ancilla[0];
cx q[2], ancilla[0]; cx q[3], ancilla[0];
h q[0]; h q[1]; h q[2]; h q[3];
bit[4] result;
result[0] = measure q[0]; result[1] = measure q[1];
result[2] = measure q[2]; result[3] = measure q[3];
'''


class ParityWitnessTests(unittest.TestCase):
    def test_flat_parity_program(self):
        result = audit_unrolled(FLAT)
        self.assertEqual(result['expected_data'], '1111')
        self.assertEqual(result['integer_state'][15], 16)
        self.assertEqual(result['integer_state'][31], -16)

    def test_missing_ancilla_preparation_changes_data(self):
        state, count = integer_state(expected_operations()[1:])
        self.assertEqual(count, 9)
        self.assertEqual([(i, a) for i, a in enumerate(state) if a], [(0, 16), (16, 16)])

    def test_missing_oracle_control_changes_one_data_bit(self):
        operations = [op for op in expected_operations() if op != ('cx', 0, 4)]
        state, _ = integer_state(operations)
        self.assertEqual([(i, a) for i, a in enumerate(state) if a], [(14, 16), (30, -16)])

    def test_wrong_measurement_destination_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'SOURCE_OPERATION_SEQUENCE_CHANGED'):
            audit_unrolled(FLAT.replace('result[3] = measure', 'result[2] = measure'))

    def test_wrong_oracle_control_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'SOURCE_OPERATION_SEQUENCE_CHANGED'):
            audit_unrolled(FLAT.replace('cx q[3],', 'cx q[2],'))

    def test_extra_statement_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'UNEXPECTED_UNROLLED_STATEMENT'):
            audit_unrolled(FLAT+'reset ancilla[0];')


if __name__ == '__main__':
    unittest.main()
