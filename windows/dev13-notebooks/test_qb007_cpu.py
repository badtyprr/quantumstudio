"""Cross-check the authored diagonal-cost audit against exhaustive small grids."""
import itertools
import random
import unittest

import numpy as np
from witnesses.qb007_cpu import classical_minimum, sample_energies


def reference_cost(bits, h, jr, jc):
    n = len(h)
    spin = lambda row, col: 1 - 2 * bits[row * n + col]
    total = 0
    for row in range(n):
        for col in range(n):
            total += h[row][col] * spin(row, col)
            if row + 1 < n:
                total += jr[row][col] * spin(row, col) * spin(row + 1, col)
            if col + 1 < n:
                total += jc[row][col] * spin(row, col) * spin(row, col + 1)
    return total


class CostAuditTests(unittest.TestCase):
    def test_all_basis_samples_and_minimum_on_small_grids(self):
        for n in (1, 2, 3):
            for seed in range(4):
                rng = random.Random(seed)
                matrix = lambda rows, cols: [[rng.choice([-1, 1]) for _ in range(cols)] for _ in range(rows)]
                h, jr, jc = matrix(n, n), matrix(n - 1, n), matrix(n, n - 1)
                inputs = list(itertools.product((0, 1), repeat=n * n))
                expected = [reference_cost(bits, h, jr, jc) for bits in inputs]
                with self.subTest(n=n, seed=seed):
                    self.assertEqual(sample_energies(np.asarray(inputs), h, jr, jc).tolist(), expected)
                    minimum, certificate = classical_minimum(h, jr, jc)
                    self.assertEqual(minimum, min(expected))
                    self.assertEqual(reference_cost(sum(certificate, []), h, jr, jc), minimum)

    def test_five_by_five_ferromagnetic_certificate(self):
        h = [[-1] * 5 for _ in range(5)]
        jr, jc = [[-1] * 5 for _ in range(4)], [[-1] * 4 for _ in range(5)]
        minimum, certificate = classical_minimum(h, jr, jc)
        self.assertEqual(minimum, -65)
        self.assertEqual(certificate, [[0] * 5 for _ in range(5)])

    def test_invalid_shape_or_coefficients_rejected(self):
        for h, jr, jc in [([[1, 1]], [], [[]]), ([[0]], [], [[]]),
                          ([[True]], [], [[]]), ([[1]], [[1]], [[]])]:
            with self.subTest(h=h, jr=jr), self.assertRaises(AssertionError):
                classical_minimum(h, jr, jc)

    def test_invalid_measurements_rejected(self):
        for values in (np.asarray([0]), np.asarray([[0, 1]]), np.asarray([[2]]), np.asarray([[np.nan]])):
            with self.subTest(values=values), self.assertRaises(AssertionError):
                sample_energies(values, [[1]], [], [[]])


if __name__ == '__main__':
    unittest.main()
