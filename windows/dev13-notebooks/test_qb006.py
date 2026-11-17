"""Preserve the original preparation discrepancy and validate companion staging."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from witnesses.qb006 import audit_program

ROOT = Path(__file__).parent


class PreparationTests(unittest.TestCase):
    def source(self, n):
        name = 'default' if n == 4 else 'three-counting'
        return (ROOT / f'fixtures/qb006-{name}.qasm').read_text(encoding='utf-8')

    def test_original_and_authored_inputs_stay_distinct(self):
        for n in (3, 4):
            original, control = audit_program(self.source(n), n)
            self.assertFalse(original['authored_initial_psi_one'])
            self.assertTrue(control['authored_initial_psi_one'])
            self.assertEqual(original['expected_dominant_output'], '0' * n)
            self.assertEqual(control['expected_dominant_output'], '1' + '0' * (n - 1))

    def test_hidden_preparation_cannot_be_accepted_as_original(self):
        with self.assertRaises(AssertionError):
            audit_program(self.source(3).replace('h q[0];', 'x psi[0];\nh q[0];', 1), 3)

    def test_missing_control_fails_prepared_diagnostic(self):
        with self.assertRaises(AssertionError):
            audit_program(self.source(3).replace('cz q[0], psi[0];', '', 1), 3)

    def test_reversed_measurement_is_rejected(self):
        with self.assertRaises(AssertionError):
            audit_program(self.source(3).replace('b[0] = measure q[0];', 'b[2] = measure q[0];'), 3)

    def test_unknown_width_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'WIDTH'):
            audit_program(self.source(3), 8)


class CompanionTests(unittest.TestCase):
    def test_pinned_files_and_no_overwrite(self):
        contract = json.loads((ROOT / 'contracts/qb006.json').read_text(encoding='utf-8'))
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                exec(contract['preamble'], {})
                for source in contract['companion_sources']:
                    self.assertEqual(hashlib.sha256(Path(source['name']).read_bytes()).hexdigest(), source['sha256'])
                Path('unitary.qasm').write_bytes(b'user-owned input')
                with self.assertRaises(FileExistsError):
                    exec(contract['preamble'], {})
                self.assertEqual(Path('unitary.qasm').read_bytes(), b'user-owned input')
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
