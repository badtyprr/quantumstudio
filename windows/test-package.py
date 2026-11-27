"""Verify the actual portable ZIP without extracting or executing its contents."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import tarfile
import zipfile


def verify_notebooks(source_archive, packaged):
    """Compare the portable runtime to the separately verified source distribution."""
    expected = set()
    with tarfile.open(source_archive, 'r:gz') as source:
        for member in source:
            parts = PurePosixPath(member.name).parts
            if not member.isfile() or parts[1:3] != ('windows', 'dev13-notebooks'):
                continue
            relative = PurePosixPath(*parts[3:])
            if len(relative.parts) == 1 and (relative.name == '.gitattributes' or relative.match('test_*.py')):
                continue
            name = str(relative)
            if name in expected:
                raise ValueError('Duplicate notebook source file: ' + name)
            expected.add(name)
            if name not in packaged:
                raise ValueError('Missing notebook file: ' + name)
            with source.extractfile(member) as stream:
                digest = hashlib.sha256(stream.read()).hexdigest()
            if packaged[name] != digest:
                raise ValueError('Notebook differs from source distribution: ' + name)
    extra = packaged.keys() - expected
    if extra:
        raise ValueError('Unexpected notebook files: ' + ', '.join(sorted(extra)))


def verify(archive, revision, candidate, source_archive=None):
    with zipfile.ZipFile(archive) as package:
        files = {}
        for entry in package.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename:
                raise ValueError('Unsafe archive path: ' + entry.filename)
            if entry.is_dir():
                continue
            if entry.filename in files:
                raise ValueError('Duplicate archive member: ' + entry.filename)
            files[entry.filename] = entry
        prefix = 'QuantumStudio/'
        manifest_name = prefix + 'build-manifest.json'
        manifest = json.loads(package.read(manifest_name).decode('utf-8-sig'))
        if manifest['revision'] != revision or manifest['candidate'] is not candidate:
            raise ValueError('Incorrect source revision or release type')
        expected = {manifest_name}
        notebooks = {}
        for item in manifest['files']:
            name = prefix + item['path']
            if name in expected:
                raise ValueError('Duplicate manifest member: ' + name)
            expected.add(name)
            digest = hashlib.sha256()
            with package.open(name) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest().lower() != item['sha256'].lower():
                raise ValueError('Incorrect file hash: ' + name)
            if item['path'].startswith('notebooks/'):
                notebooks[item['path'][len('notebooks/'):]] = digest.hexdigest()
        if set(files) != expected:
            raise ValueError('Archive contents differ from the manifest')
        for name in ('QuantumStudio.exe', 'quantum-worker.exe', 'qalc.exe',
                     'qasm-import/qasm-import.exe', 'Notation-guide.html',
                     'README.txt', 'LICENSE.txt', 'Research-notes.md',
                     'notebooks/run.py', 'notebooks/execution.py',
                     'notebooks/prepare_transpiler_wheels.py',
                     'notebooks/contracts/qb011.json', 'notebooks/witnesses/qb011.py',
                     'notebooks/profiles/transpiler-pyquil-win-py312.json',
                     'notebooks/transpiler-pyquil-requirements.lock'):
            if prefix + name not in files:
                raise ValueError('Missing required package file: ' + name)
        if not any(name.startswith(prefix + 'data/') and name.endswith('.xml') for name in files):
            raise ValueError('Missing calculator definitions')
        if source_archive is not None:
            verify_notebooks(source_archive, notebooks)
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--candidate', action='store_true')
    parser.add_argument('--source-archive', help='Compare every notebook runtime file to this source tarball.')
    args = parser.parse_args()
    count = verify(args.archive, args.revision, args.candidate, args.source_archive)
    print(f'PASS: {count} ZIP files verified against source revision and manifest hashes.')
