"""Serial fresh execution of the pinned DEV-11 fixtures and cost controls."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    assert digest == args.sha256, 'Worker hash differs'
    args.output.mkdir(parents=True, exist_ok=False)
    directory = Path(__file__).parent
    spec = importlib.util.spec_from_file_location('oracle', directory / 'probe.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    fixtures = json.loads(gzip.decompress((directory / 'fixtures.json.gz').read_bytes()))
    controls = []
    for label, expression, expected in [
        ('identity-alone', 'qidentity(512)', 'I' * 9),
        ('Y-alone', 'pauli("IIIIIIYII")', 'IIIIIIYII'),
        ('identity-square', 'qidentity(512)*qidentity(512)', 'I' * 9),
        ('Y-square', 'pauli("IIIIIIYII")*pauli("IIIIIIYII")', 'I' * 9),
        ('X-square', 'pauli("IIIIIIXII")*pauli("IIIIIIXII")', 'I' * 9),
        ('trace-identity', 'trace(qidentity(512)*qidentity(512))', '512'),
        ('trace-Y', 'trace(pauli("IIIIIIYII")*pauli("IIIIIIYII"))', '512'),
        ('trace-X', 'trace(pauli("IIIIIIXII")*pauli("IIIIIIXII"))', '512'),
    ]:
        controls.append(dict(id=label, expression='quantum:' + expression,
                             comparison='scalar' if expected == '512' else 'pauli',
                             expected=expected, timeout=12))
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.parent / 'data'))
    records = []
    for repetition in (1, 2):
        for fixture in controls + fixtures:
            name = str(repetition) + '-' + fixture['id']
            record = dict(id=fixture['id'], repetition=repetition,
                          expression=fixture['expression'], timeout=fixture.get('timeout', 90))
            started = time.perf_counter()
            try:
                process = subprocess.run([str(args.worker), '--json'],
                    input=fixture['expression'].encode(), capture_output=True,
                    env=env, cwd=args.output, timeout=record['timeout'])
                record['seconds'] = time.perf_counter() - started
                (args.output / (name + '.stdout')).write_bytes(process.stdout)
                (args.output / (name + '.stderr')).write_bytes(process.stderr)
                record.update(returncode=process.returncode,
                              stdout_sha256=hashlib.sha256(process.stdout).hexdigest())
                kind = fixture['comparison']
                if kind in ('reject', 'capacity', 'syntax'):
                    passed = oracle.expected_rejection(fixture['id'], process.returncode,
                                                       process.stderr.decode())
                else:
                    assert process.returncode == 0, process.stderr.decode()
                    data = json.loads(process.stdout)
                    record['approximate'] = data['approximate']
                    if kind == 'scalar':
                        passed = data['text'] == fixture['expected']
                    elif kind == 'vector':
                        passed = data['copy_text'].replace(' ', '') == 'vector(' + ','.join(map(str, fixture['expected'])) + ')'
                    else:
                        actual = oracle.numeric_cells(data)
                        expected = (oracle.matrix(fixture['expected']) if kind == 'pauli' else
                                    [[complex(*x) for x in row] for row in fixture['expected']])
                        assert len(actual) == len(expected) and all(len(a) == len(e) for a, e in zip(actual, expected)), 'Shape mismatch'
                        phase = 1
                        if fixture.get('allow_common_global_phase'):
                            phase = next(a / e for ar, er in zip(actual, expected)
                                         for a, e in zip(ar, er) if abs(e) > 1e-12)
                        residual = max(abs(a - phase * e) for ar, er in zip(actual, expected) for a, e in zip(ar, er))
                        record.update(residual=residual, phase=[complex(phase).real, complex(phase).imag])
                        passed = (residual == 0 if kind == 'pauli' else residual < 1e-12) and abs(abs(phase) - 1) < 1e-12
                    passed = passed and data['approximate'] is False
                record['passed'] = passed
            except Exception as error:
                record.update(passed=False, error=str(error), seconds=time.perf_counter() - started)
            records.append(record)
            (args.output / 'results.json').write_text(json.dumps(dict(worker=str(args.worker),
                sha256=digest, records=records), indent=2))
            print(name, round(record['seconds'], 3), record['passed'], flush=True)
    return 0 if all(r['passed'] for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
