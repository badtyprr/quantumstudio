"""Reject incorrect retained-state claims independently of SDK availability."""
import contextlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import tempfile
import unittest

WITNESS = Path(__file__).resolve().parent / 'witnesses/qb018.py'

class Simulator:
    def __init__(self, values):
        self.values = values

    def state_vector(self, *args, **kwargs):
        return self.values

def ghz_state():
    result = [0j] * 16
    result[0] = result[-1] = 1/math.sqrt(2)
    return result

class WitnessTests(unittest.TestCase):
    def run_witness(self, states):
        namespace = dict(zip(('cirq_sim', 'pyq_sim', 'sim'), map(Simulator, states)))
        namespace.update(main_loaded=object(), squin_mod=object(), ghz=object())
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    runpy.run_path(str(WITNESS), init_globals=namespace)
                report = json.loads(output.getvalue())
                self.assertEqual(report, json.loads(Path('qb018-state-evidence.json').read_text(encoding='utf-8')))
                return report
            finally:
                os.chdir(original)

    def test_independent_global_phases_are_accepted(self):
        state = ghz_state()
        report = self.run_witness([state, [1j*x for x in state], [-x for x in state]])
        self.assertTrue(report['accepted'])
        self.assertEqual(len(report['authored_rerun_routes']), 3)
        self.assertEqual(report['oracle_complex_controls'], 3)

    def test_wrong_relative_phase_rejected_in_every_route(self):
        wrong = ghz_state()
        wrong[-1] *= -1
        for index in range(3):
            with self.subTest(route=index):
                states = [ghz_state() for _ in range(3)]
                states[index] = wrong
                with self.assertRaisesRegex(AssertionError, 'STATE_FIDELITY'):
                    self.run_witness(states)

    def test_invalid_shape_nonfinite_and_norm_rejected(self):
        invalid = [[], ghz_state()[:-1], [complex(float('nan'))]*16,
                   [complex(float('inf'))]*16, [2*x for x in ghz_state()]]
        for values in invalid:
            with self.subTest(values=repr(values[:1])):
                with self.assertRaises(AssertionError):
                    self.run_witness([values, ghz_state(), ghz_state()])

    def test_wrong_basis_support_rejected(self):
        wrong = [0j]*16
        wrong[1] = wrong[14] = 1/math.sqrt(2)
        with self.assertRaisesRegex(AssertionError, 'STATE_FIDELITY'):
            self.run_witness([ghz_state(), wrong, ghz_state()])

if __name__ == '__main__':
    unittest.main(verbosity=2)
