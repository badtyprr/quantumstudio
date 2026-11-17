"""Reject arithmetic, preparation and output-order regressions in QB003."""
import unittest
from pathlib import Path
from witnesses.qb003 import audit_operations, parse_operations


class AdderTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(__file__).parent / 'fixtures/qb003-unrolled.qasm').read_text(encoding='utf-8')
        self.operations = parse_operations(self.text)

    def test_full_basis_and_original_input(self):
        result = audit_operations(self.operations)
        self.assertEqual(result['basis_cases'], 1024)
        self.assertEqual(result['displayed_answer'], '10111')

    def test_comment_does_not_override_initialization(self):
        self.operations[13] = ('x', 1)
        with self.assertRaisesRegex(AssertionError, 'PREPARATION'):
            audit_operations(self.operations)

    def test_lost_carry_is_rejected(self):
        position = self.operations.index(('cx', 4, 9))
        self.operations[position] = ('cx', 3, 9)
        with self.assertRaisesRegex(AssertionError, 'PERMUTATION'):
            audit_operations(self.operations)

    def test_corrupted_uncomputation_is_rejected(self):
        self.operations[-6] = ('cx', 1, 5)
        with self.assertRaisesRegex(AssertionError, 'PERMUTATION'):
            audit_operations(self.operations)

    def test_reversed_measurement_destinations_are_rejected(self):
        self.operations[-5] = ('measure', 5, 4)
        with self.assertRaisesRegex(AssertionError, 'MEASUREMENT'):
            audit_operations(self.operations)

    def test_non_permutation_gate_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'UNEXPECTED_GATE'):
            parse_operations(self.text.replace('x b[0];', 'h b[0];'))


if __name__ == '__main__':
    unittest.main()
