"""Exercise the portable verifier with internally consistent ZIP manifests."""
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
import tempfile
import unittest
import zipfile


verify = runpy.run_path(str(Path(__file__).with_name('test-package.py')))['verify']


class NotebookDistributionTest(unittest.TestCase):
    def test_source_comparison(self):
        required = ('QuantumStudio.exe', 'quantum-worker.exe', 'qalc.exe', 'qasm-import/qasm-import.exe',
                    'Notation-guide.html', 'README.txt', 'LICENSE.txt', 'Research-notes.md', 'data/test.xml')
        runtime = ('run.py', 'execution.py', 'prepare_transpiler_wheels.py', 'contracts/qb011.json',
                   'witnesses/qb011.py', 'profiles/transpiler-pyquil-win-py312.json',
                   'transpiler-pyquil-requirements.lock', 'observers/example.py')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.tar.gz'
            with tarfile.open(source, 'w:gz') as archive:
                for name in (*runtime, 'test_example.py', '.gitattributes'):
                    entry = tarfile.TarInfo('project/windows/dev13-notebooks/' + name)
                    entry.size = 1
                    archive.addfile(entry, io.BytesIO(b'x'))
            for scenario, expected_error in [('complete', None), ('missing', 'Missing notebook file'),
                                             ('changed', 'differs from source'), ('extra', 'Unexpected notebook files')]:
                with self.subTest(scenario=scenario):
                    files = dict.fromkeys(required, b'x')
                    files.update(dict.fromkeys(('notebooks/' + name for name in runtime), b'x'))
                    if scenario == 'missing':
                        del files['notebooks/observers/example.py']
                    elif scenario == 'changed':
                        files['notebooks/observers/example.py'] = b'y'
                    elif scenario == 'extra':
                        files['notebooks/test_example.py'] = b'x'
                    manifest = {'revision': 'test', 'candidate': True, 'files': [
                        {'path': name, 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files.items()]}
                    files['build-manifest.json'] = json.dumps(manifest).encode()
                    archive_path = Path(directory) / 'portable.zip'
                    with zipfile.ZipFile(archive_path, 'w') as archive:
                        for name, data in files.items():
                            archive.writestr('QuantumStudio/' + name, data)
                    if expected_error:
                        with self.assertRaisesRegex(ValueError, expected_error):
                            verify(archive_path, 'test', True, source)
                    else:
                        self.assertEqual(verify(archive_path, 'test', True, source), len(files))


if __name__ == '__main__':
    unittest.main()
