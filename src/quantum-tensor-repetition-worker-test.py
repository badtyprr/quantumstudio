#!/usr/bin/env python3
"""IBM-020 explicit tensor repetition; independent one-hot expectations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=Path, default=Path(os.environ.get('QUANTUM_WORKER', 'quantum-worker.exe' if os.name == 'nt' else 'quantum-worker')))
    ap.add_argument('--definitions', type=Path)
    ap.add_argument('--translator', type=Path)
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
        d = dict(input=expression)
        if args.translator:
            p = subprocess.run([str(args.translator)], input=expression.encode(), capture_output=True, timeout=10)
            if p.returncode:
                return dict(d, returncode=p.returncode, stderr=p.stderr.decode())
            expression = p.stdout.decode().strip()
        d['evaluator_input'] = 'quantum:' + expression
        p = subprocess.run([str(args.worker), '--json'], input=d['evaluator_input'].encode(), capture_output=True, timeout=20, env=env)
        d.update(returncode=p.returncode, stdout=p.stdout.decode(), stderr=p.stderr.decode())
        if p.returncode == 0:
            d['actual'] = json.loads(p.stdout)
        return d

    def matches(a, n, index, bra):
        if a.get('approximate') is not False:
            return False
        if n == 0:
            return a.get('copy_text') == '1' and a.get('rows') == 0 and a.get('columns') == 0
        bits = [str(int(i == index)) for i in range(2 ** n)]
        if bra:
            return a.get('rows') == 0 and a.get('columns') == 0 and a.get('copy_text') == 'vector(' + ','.join(bits) + ')'
        return a.get('rows') == 2 ** n and a.get('columns') == 1 and a.get('cells') == [[v] for v in bits]

    def value(name, expression, n, index, bra=False):
        d = execute(expression)
        d.update(id=name, expected=dict(qubits=n, index=index, bra=bra), passed=matches(d.get('actual', {}), n, index, bra))
        records.append(d)
        if d['passed']:
            c = execute(d['actual']['copy_text'])
            c.update(id=name + '-copy', expected=d['expected'], passed=matches(c.get('actual', {}), n, index, bra))
            records.append(c)

    def reject(name, expression, diagnostic):
        d = execute(expression)
        d.update(id=name, passed=d['returncode'] == 2 and diagnostic in d.get('stderr', ''))
        records.append(d)

    def tex(bit, count, bra=False):
        label = str(bit) + r'^{\otimes ' + str(count) + '}'
        return (r'\langle ' + label + r' \vert') if bra else (r'\vert ' + label + r' \rangle')

    for bit in (0, 1):
        for n in range(11):
            index = (2 ** n - 1) * bit
            for bra in (False, True):
                value(f'tex-{bit}-{n}-{bra}', tex(bit, n, bra), n, index, bra)
            value(f'natural-{bit}-{n}', f'|{bit}^({n})>', n, index)
        for bra in (False, True):
            expr = tex(bit, 'n', bra)
            d = execute(expr)
            copy = d.get('actual', {}).get('copy_text')
            d.update(id=f'symbolic-{bit}-{bra}', passed=d['returncode'] == 0 and 'qtensorpow' in (copy or ''))
            records.append(d)
            for route, form in [('original', expr)] + ([('copied', copy)] if copy else []):
                for n in (0, 1, 3, 10):
                    value(f'substitute-{bit}-{bra}-{route}-{n}', f'replace({form},n,{n})', n, (2 ** n - 1) * bit, bra)
                for bad in ('-1', '1/2', 'i', '11'):
                    reject(f'count-{bit}-{bra}-{route}-{bad}', f'replace({form},n,{bad})', 'Tensor power requires an integer exponent from 0 to 10')
    for n in (1, 2, 3):
        value(f'flip-{n}', f'tensorpow(X,{n})*' + tex(0, n), n, 2 ** n - 1)
        value(f'append-{n}', tex(0, n) + '|1>', n + 1, 1)
        value(f'prepend-{n}', '|1>' + tex(0, n), n + 1, 2 ** n)
    summary = dict(worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                   translator_sha256=hashlib.sha256(args.translator.read_bytes()).hexdigest() if args.translator else None,
                   route='standalone parser plus retained evaluator' if args.translator else 'integrated worker',
                   checks=len(records), passed=sum(r['passed'] for r in records), failures=[r['id'] for r in records if not r['passed']])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dict(summary=summary, records=records), indent=2), encoding='utf-8')
    print(json.dumps(summary))
    return int(bool(summary['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
