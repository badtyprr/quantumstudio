"""Verify the actual portable ZIP without extracting or executing its contents."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile


def verify(archive, revision, candidate):
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
        if set(files) != expected:
            raise ValueError('Archive contents differ from the manifest')
        for name in ('QuantumStudio.exe', 'quantum-worker.exe', 'qalc.exe',
                     'qasm-import/qasm-import.exe', 'Notation-guide.html',
                     'README.txt', 'LICENSE.txt', 'Research-notes.md'):
            if prefix + name not in files:
                raise ValueError('Missing required package file: ' + name)
        if not any(name.startswith(prefix + 'data/') and name.endswith('.xml') for name in files):
            raise ValueError('Missing calculator definitions')
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    count = verify(args.archive, args.revision, args.candidate)
    print(f'PASS: {count} ZIP files verified against source revision and manifest hashes.')
