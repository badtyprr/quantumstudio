"""Reject Fourier sign, wire, angle and output-destination regressions."""
from pathlib import Path
import unittest

from witnesses.qb005 import audit_unrolled

FIXTURES = Path(__file__).parent / 'fixtures'


class FourierTests(unittest.TestCase):
    def source(self, name):
        return (FIXTURES / f'qb005-{name}.qasm').read_text(encoding='utf-8')

    def test_both_three_qubit_operators(self):
        for name in ('qft3', 'iqft3'):
            result = audit_unrolled(self.source(name), name)
            self.assertEqual(result['basis_inputs'], 8)
            self.assertEqual(result['primitive_gates'], 55)
            self.assertLess(result['maximum_amplitude_error'], 1e-12)

    def test_four_qubit_operator_from_authored_unrolling(self):
        import pyqasm
        module = pyqasm.loads(self.source('qft4'))
        module.unroll()
        result = audit_unrolled(pyqasm.dumps(module), 'qft4')
        self.assertEqual(result['basis_inputs'], 16)
        self.assertLess(result['maximum_amplitude_error'], 1e-12)

    def test_sign_angle_and_wire_mutations(self):
        source = self.source('qft3')
        for old, new in [('rz(0.7853981633974483)', 'rz(-0.7853981633974483)'),
                         ('rx(1.5707963267948966)', 'rx(1.57)'),
                         ('cx qb[0], qb[1];', 'cx qb[1], qb[0];'),
                         ('swap qb[2], qb[0];', '')]:
            with self.subTest(old=old), self.assertRaises(AssertionError):
                audit_unrolled(source.replace(old, new, 1), 'qft3')

    def test_measurement_order_and_missing_destination(self):
        source = self.source('iqft3')
        for replacement in ('b[2] = measure q[0];', ''):
            with self.subTest(replacement=replacement), self.assertRaises(AssertionError):
                audit_unrolled(source.replace('b[0] = measure q[0];', replacement), 'iqft3')

    def test_unsupported_or_out_of_range_operations(self):
        source = self.source('qft3')
        for replacement in ('h qb[3];', 'reset qb[0];', 'rx(1e309) qb[0];'):
            with self.subTest(replacement=replacement), self.assertRaises(AssertionError):
                audit_unrolled(source.replace('h qb[0];', replacement, 1), 'qft3')


if __name__ == '__main__':
    unittest.main()
