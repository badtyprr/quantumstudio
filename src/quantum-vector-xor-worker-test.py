#!/usr/bin/env python3
"""IBM-062 authored vector-XOR adaptations and established boundary controls."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess

# Literal IBM-062 cell 0 eq002, preserving source order and seven-bit width.
WORDS = '0000000 1100001 1010010 0110011 0110100 1010101 1100110 0000111 1111000 0011001 0101010 1001011 1001100 0101101 0011110 1111111'.split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=Path, default=Path(os.environ.get('QUANTUM_WORKER', 'quantum-worker.exe' if os.name == 'nt' else 'quantum-worker')))
    ap.add_argument('--definitions', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    args.worker = args.worker.resolve()
    env = dict(os.environ)
    if args.definitions:
        env['QALCULATE_DEFINITIONS_DIR'] = str(args.definitions)
    elif (args.worker.parent / 'data').is_dir():
        env['QALCULATE_DEFINITIONS_DIR'] = str(args.worker.parent / 'data')
    records = []

    def execute(expression):
        p = subprocess.run([str(args.worker), '--json'], input=expression.encode(), capture_output=True, timeout=10, env=env)
        d = dict(input=expression, returncode=p.returncode, stdout=p.stdout.decode(), stderr=p.stderr.decode())
        if p.returncode == 0:
            d['actual'] = json.loads(p.stdout)
        return d

    def value(name, expression, expected):
        d = execute(expression)
        a = d.get('actual', {})
        d.update(id=name, expected=expected, passed=a.get('copy_text') == expected and a.get('approximate') is False)
        records.append(d)
        if d['passed']:
            c = execute(a['copy_text'])
            b = c.get('actual', {})
            c.update(id=name + '-copy', expected=expected, passed=b.get('copy_text') == expected and b.get('approximate') is False)
            records.append(c)

    def vector(word):
        return 'vector(' + ','.join(word) + ')'

    for a, b in itertools.product(WORDS, repeat=2):
        expected = ''.join(str(int(x != y)) for x, y in zip(a, b))
        assert expected in WORDS
        value('source-closure-' + a + '-' + b, f'xor({vector(a)},{vector(b)})', vector(expected))
    controls = [
        ('minimal', 'xor([0,0],[1,0])', 'vector(1,0)'),
        ('reverse', 'xor([1,0],[0,0])', 'vector(1,0)'),
        ('asymmetric', 'xor([0,0],[0,1])', 'vector(0,1)'),
        ('long-left', 'xor([0,0,1],[1,0])', 'vector(1,0,1)'),
        ('long-right', 'xor([1,0],[0,0,1])', 'vector(1,0,1)'),
        ('empty', 'xor(vector(),vector())', 'vector()'),
        ('empty-left', 'xor(vector(),[0,1])', 'vector(0,1)'),
        ('empty-right', 'xor([0,1],vector())', 'vector(0,1)'),
        ('one-entry', 'xor([0],[1])', '1'),
        ('truth-overlap', 'xor([0,0],[2,-3])', 'vector(1,1)'),
        ('truth-tail', 'xor(vector(),[2,-3,0])', 'vector(1,0,0)'),
        ('binary-control', 'qbitxor([0,0],[1,0])', 'vector(1,0)'),
    ]
    for name, expression, expected in controls:
        value(name, expression, expected)
    symbolic = execute('xor([x,0],[0,1])')
    copied = symbolic.get('actual', {}).get('copy_text')
    symbolic.update(id='symbolic-retained', passed=symbolic['returncode'] == 0 and 'x' in (copied or ''))
    records.append(symbolic)
    for route, form in [('original', 'xor([x,0],[0,1])')] + ([('copied', copied)] if copied else []):
        for bit in (0, 1):
            value(f'symbolic-{route}-{bit}', f'replace({form},x,{bit})', f'vector({bit},1)')
    # Scalar xor retains integer bitwise semantics, unlike vector logical entries.
    for a, b in itertools.product(range(4), repeat=2):
        value(f'scalar-{a}-{b}', f'xor({a},{b})', str(a ^ b))
    summary = dict(worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(), checks=len(records),
                   passed=sum(r['passed'] for r in records), failures=[r['id'] for r in records if not r['passed']])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dict(summary=summary, records=records), indent=2), encoding='utf-8')
    print(json.dumps(summary))
    return int(bool(summary['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
