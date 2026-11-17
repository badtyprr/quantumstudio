"""QIR -> compiler -> saved model -> exact and sampled native engines."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess

import pyqir
from qir_import import import_qir
from test_qir_import import fixture, H, CX, M0, M1, O0, O1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-python', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent / 'data'))
    x0 = '  call void @__quantum__qis__x__body(ptr null)'
    x1 = '  call void @__quantum__qis__x__body(ptr inttoptr (i64 1 to ptr))'
    cases = [
        ('bell', fixture(H, CX, M0, M1, O0, O1), {'00': .5, '11': .5}),
        ('q0', fixture(x0, M0, M1, O0, O1), {'10': 1}),
        ('q1', fixture(x1, M0, M1, O0, O1), {'01': 1}),
        ('permuted', fixture(x0, M0, M1, O1, O0), {'01': 1}),
        ('snapshot', fixture(M0, O0, x0, M0, O0), {'01': 1}),
        ('duplicate', fixture(x0, M0, O0, O0), {'11': 1}),
        ('unrecorded', fixture(H, M0), {'': 1}),
        ('unitary', fixture(H, CX), {'': 1}),
        ('bell_inverse', fixture(H, CX, CX, H, M0, M1, O0, O1), {'00': 1}),
    ]
    results = []
    for name, raw, expected in cases:
        module = pyqir.Module.from_ir(pyqir.Context(), raw.decode())
        text_qasm = None
        for binary, source in ((False, raw), (True, module.bitcode)):
            label = name + ('-bitcode' if binary else '-ir')
            report = import_qir(source, bitcode=binary)
            if text_qasm is None:
                text_qasm = report['openqasm']
            assert report['openqasm'] == text_qasm
            compiled = subprocess.run([str(args.compiler_python), '-E', '-s', '-B',
                str(args.compiler), '--classical'], input=text_qasm.encode(), capture_output=True, timeout=30, check=True)
            circuit = json.loads(compiled.stdout)
            assert len(circuit['OutputBits']) == report['output_slots']
            adapted = subprocess.run([str(args.adapter)], input=compiled.stdout,
                                     capture_output=True, timeout=30, check=True)
            payloads = json.loads(adapted.stdout.decode('utf-8-sig'))
            (args.evidence / (label + '-circuit.json')).write_bytes(compiled.stdout)
            for kind, flag in (('exact', '--exact-circuit'), ('sampled', '--sample')):
                run = subprocess.run([str(args.worker), flag], input=base64.b64decode(payloads[kind]),
                    capture_output=True, env=env, timeout=30, check=True)
                (args.evidence / (label + '-' + kind + '.json')).write_bytes(run.stdout)
                data = json.loads(run.stdout)
                if kind == 'exact':
                    actual = {}
                    for bits, expression in data['probabilities'].items():
                        evaluated = subprocess.run([str(args.worker), '--json', '--approx'],
                            input=expression.encode(), capture_output=True, env=env, timeout=30, check=True)
                        actual[bits] = float(json.loads(evaluated.stdout)['text'].replace('−', '-'))
                    tolerance = 1e-10
                else:
                    assert sum(data['counts'].values()) == 10000
                    actual = {bits: count / 10000 for bits, count in data['counts'].items()}
                    tolerance = .025
                assert all(abs(actual.get(k, 0) - expected.get(k, 0)) <= tolerance
                           for k in set(actual) | set(expected)), (label, kind, actual, expected)
                results.append(dict(case=label, engine=kind, actual=actual, expected=expected))
    (args.evidence / 'results.json').write_bytes((json.dumps(results, indent=2) + '\n').encode())
    print(json.dumps(dict(checks=len(results), cases=len(cases), formats=2,
                         empty_output_cases_prove_only_output_disposition=True)))


if __name__ == '__main__':
    main()
