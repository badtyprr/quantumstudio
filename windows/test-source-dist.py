"""Verify a generated Automake tarball against tracked quantum project inputs.

Run from a Git checkout: python windows/test-source-dist.py ARCHIVE.tar.gz
This checks the artifact contents, not just the distribution manifest.
"""
import argparse
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
args = parser.parse_args()
tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True,
                         capture_output=True).stdout.decode('utf-8').split('\0')
expected = [name for name in tracked if name.startswith('windows/')
            or name.startswith('libqalculate/Quantum')
            or name.startswith('src/quantum')
            or name in ('src/quantum-worker.cc', 'tests/quantum.batch',
                        'docs/quantum-notation.md', 'docs/ibm-learning-sections.json',
                        'docs/learning-source-inventory.json', 'docs/qbraid-notebook-audit.json')]
assert expected, 'No project inputs discovered'
with tarfile.open(args.archive, 'r:gz') as archive:
    members = {}
    roots = set()
    for entry in archive.getmembers():
        path = PurePosixPath(entry.name)
        assert not path.is_absolute() and '..' not in path.parts, entry.name
        roots.add(path.parts[0])
        if entry.isfile():
            relative = '/'.join(path.parts[1:])
            assert relative not in members, 'Duplicate archive member: '+relative
            members[relative] = entry
    assert len(roots) == 1, roots
    for name in expected:
        assert name in members, 'Missing source distribution input: '+name
        content = archive.extractfile(members[name]).read()
        assert content == (root/name).read_bytes(), 'Stale source distribution input: '+name
    assert not any(name.startswith(('.tools/', 'dist/')) or '__pycache__' in name
                   or name.endswith(('.exe', '.pyc')) for name in members), 'Generated build output included'
print(f'PASS: {len(expected)} quantum build, test and research inputs match the source tarball byte for byte.')
