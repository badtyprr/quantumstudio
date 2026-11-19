"""Independent Grover probabilities and rejection checks for notebook evidence."""
from fractions import Fraction
import math
import unittest

from witnesses.qb008 import expected_state, verify_results, verify_source


class GroverTests(unittest.TestCase):
    def test_known_target_probabilities(self):
        for depth, target in enumerate([Fraction(1, 8), Fraction(25, 32),
                                        Fraction(121, 128), Fraction(169, 512)]):
            self.assertEqual(expected_state(depth)[2][5], target)

    def test_global_phase_and_counts(self):
        for depth in range(4):
            numerators, divisor, probabilities = expected_state(depth)
            state = [1j * n / (divisor * math.sqrt(8)) for n in numerators]
            counts = {format(i, '03b'): int(p * 1024) for i, p in enumerate(probabilities)}
            self.assertEqual(verify_results(state, counts, depth, 1024)['target_probability'],
                             str(probabilities[5]))
            wrong = state.copy()
            wrong[0] *= -1
            with self.assertRaisesRegex(AssertionError, 'GROVER_STATE_MISMATCH'):
                verify_results(wrong, counts, depth, 1024)
            for bad in [float('nan'), float('inf')]:
                wrong = state.copy()
                wrong[7] = bad
                with self.assertRaises(AssertionError):
                    verify_results(wrong, counts, depth, 1024)
            with self.assertRaisesRegex(AssertionError, 'GROVER_SAMPLE_MISMATCH'):
                verify_results(state, {'000': 1024}, depth, 1024)
            with self.assertRaisesRegex(AssertionError, 'INVALID_COUNTS'):
                verify_results(state, {'000': 1023}, depth, 1024)

    def test_source_measurement_and_oracle_are_bound(self):
        header = 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] qb;\nbit[3] cb;\nh qb;\n'
        iteration = ('x qb[1];\nctrl(2) @ z qb[1], qb[2], qb[0];\nx qb[1];\n'
                     'h qb;\nx qb;\nctrl(2) @ z qb[0], qb[1], qb[2];\nx qb;\nh qb;\n')
        for depth in range(4):
            source = header + iteration * depth + 'cb = measure qb;\n'
            verify_source(source, depth)
            for changed in [source.replace('cb = measure qb;', 'cb[0] = measure qb[2];'),
                            source.replace('h qb;', 'x qb;', 1),
                            source + 'x qb[0];\n']:
                with self.assertRaises(AssertionError):
                    verify_source(changed, depth)
        with self.assertRaises(AssertionError):
            verify_source((header + iteration).replace('x qb[1];', 'x qb[0];') + 'cb = measure qb;', 1)

    def test_unreviewed_depths_rejected(self):
        for depth in [-1, 4, True, 1.0]:
            with self.assertRaises(AssertionError):
                expected_state(depth)


if __name__ == '__main__':
    unittest.main()
