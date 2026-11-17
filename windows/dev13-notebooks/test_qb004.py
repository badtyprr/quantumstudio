"""Source mutations and adapter failures must not become QB004 acceptance."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from witnesses.qb004 import audit_generated

ROOT = Path(__file__).parent


class MathematicsTests(unittest.TestCase):
    def test_original_outputs_and_order(self):
        for secret, display in [('1011', '1101'), ('101', '101')]:
            text = (ROOT / f'fixtures/qb004-{secret}.qasm').read_text(encoding='utf-8')
            self.assertEqual(audit_generated(text, secret)['displayed_data'], display)

    def test_source_mutations_rejected(self):
        text = (ROOT / 'fixtures/qb004-1011.qasm').read_text(encoding='utf-8')
        for old, new in [('x ancilla[0];', ''), ('cx q[2], ancilla[0];', ''),
                         ('b[0] = measure q[0];', 'b[3] = measure q[0];'),
                         ('bit[4] b;', 'bit[5] b;'), ('h q[3];', 'x q[3];')]:
            with self.subTest(old=old), self.assertRaisesRegex(AssertionError, 'STRUCTURE'):
                audit_generated(text.replace(old, new, 1), '1011')


class Aliases:
    def __init__(self, original):
        self.commands = {} if original is None else {'cat': original}

    def is_alias(self, name):
        return name in self.commands

    def retrieve_alias(self, name):
        return self.commands[name]

    def define_alias(self, name, command):
        self.commands[name] = command

    def undefine_alias(self, name):
        del self.commands[name]


class Shell:
    def __init__(self, alias=None, exit_code=0, error=None):
        self.alias_manager = Aliases(alias)
        self.user_ns = {}
        self.calls = []
        self.exit_code = exit_code
        self.error = error

    def system(self, command):
        self.calls.append(command)
        self.user_ns['_exit_code'] = self.exit_code
        if self.error:
            raise self.error


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.previous)

    def load(self, shell):
        namespace = {'get_ipython': lambda: shell}
        exec(compile((ROOT / 'observers/qb004_windows.py').read_text(encoding='utf-8'),
                     'qb004_windows.py', 'exec'), namespace)
        return namespace['_qb004_windows']

    def test_exact_command_only_and_prior_alias_restored(self):
        import sys
        import subprocess
        shell = Shell(alias='custom-cat')
        adapter = self.load(shell)
        command = f'"{sys.executable}" -m pip install \'qbraid[visualization]\' qbraid-algorithms'
        shell.system(command)
        shell.system('echo unchanged')
        self.assertEqual(shell.calls, [subprocess.list2cmdline([sys.executable, '-m', 'pip',
                          'install', 'qbraid[visualization]', 'qbraid-algorithms']), 'echo unchanged'])
        adapter.restore()
        self.assertEqual(shell.alias_manager.retrieve_alias('cat'), 'custom-cat')
        self.assertTrue(adapter.restored)

    def test_nonzero_exit_preserved_for_setup_observer(self):
        shell = Shell(exit_code=7)
        adapter = self.load(shell)
        shell.system('failed command')
        self.assertEqual(shell.user_ns['_exit_code'], 7)
        self.assertEqual(adapter.commands[0]['exit_code'], 7)
        adapter.restore()
        self.assertFalse(shell.alias_manager.is_alias('cat'))

    def test_exception_recorded_and_cleanup_restores(self):
        shell = Shell(error=RuntimeError('child failed'))
        adapter = self.load(shell)
        with self.assertRaisesRegex(RuntimeError, 'child failed'):
            shell.system('raises')
        adapter.restore()
        evidence = json.loads(Path('qb004-compatibility.json').read_text(encoding='utf-8'))
        self.assertTrue(evidence['restored'])
        self.assertEqual(len(evidence['commands']), 1)


if __name__ == '__main__':
    unittest.main()
