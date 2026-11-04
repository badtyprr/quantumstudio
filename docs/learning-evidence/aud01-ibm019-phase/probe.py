"""Exact finite phase-kickback audit; no SDK or whole-source certification."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

from inventory import inventory

spec = importlib.util.spec_from_file_location('analysis_audit', Path(__file__).parent.parent/'aud01-ibm019'/'run.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
Q = analysis.Q


def fixtures():
    result = []
    def add(name, ids, expr, expected, adaptation):
        result.append(dict(id=name, source_ids=ids, input='quantum:'+expr,
                           expected=[v.record() for v in expected], adaptation=adaptation))
    for b in range(2):
        for c in range(2):
            expected = [Q(int(i == b ^ c)) for i in range(2)]
            add(f'xor-{b}{c}', ['P02','P05'], f'|{b} ⊕ {c}>', expected,
                'Extract LHS; exhaust both declared bits; substitute literal bits.')
            add(f'power-{b}{c}', ['P02','P05'], f'X^{c} |{b}>', expected,
                'Extract RHS; exhaust both declared bits; preserve unbraced power.')
        add(f'not-{b}', ['P05'], f'|¬{b}>', [Q(int(i == 1-b)) for i in range(2)],
            'Extract complement term; substitute declared bit.')
        add(f'identity-{b}', ['P05'], f'I|{b}>', [Q(int(i==b)) for i in range(2)],
            'Extract identity term; I spelling adapts source blackboard bold.')
        add(f'basis-{b}', ['P05'], f'|{b}>', [Q(int(i==b)) for i in range(2)],
            'Extract unchanged basis term in c=0 branch.')
        add(f'x-{b}', ['P05'], f'X|{b}>', [Q(int(i==1-b)) for i in range(2)],
            'Extract X term in c=1 branch.')
    minus = [Q(0,'1/2'), Q(0,'-1/2')]
    add('eigenvector', ['P13'], 'X|->', [-v for v in minus], 'Extract left equality term.')
    add('negative-minus', ['P13'], '-|->', [-v for v in minus], 'Extract right equality term.')
    add('minus', ['P14'], r'\vert - \rangle', minus, 'Original unchanged.')
    add('eigenvalue', ['P16'], '-1', [Q(-1)], 'Original unchanged; scalar alone is not eigenrelation evidence.')
    for index, f in enumerate([(0,0),(0,1),(1,0),(1,1)], 1):
        matrix = '['+';'.join(','.join(str(int(row == col ^ (f[col & 1]<<1))) for col in range(4)) for row in range(4))+']'
        for a in range(2):
            for b in range(2):
                expected = [Q(int(i == ((b ^ f[a])*2+a))) for i in range(4)]
                add(f'oracle-{index}-{a}{b}', ['P06'], f'{matrix}*|{b}{a}>', expected,
                    'Replace U_f by explicit permutation matrix; exhaust four truth tables and both bits. Order |b a>.')
                add(f'factor-{index}-{a}{b}', ['P06'], f'(X^{f[a]} |{b}>)|{a}>', expected,
                    'Extract RHS and substitute f(a), a, b. Order |b a>.')
                add(f'xor-oracle-{index}-{a}{b}', ['P06'], f'|{b} ⊕ {f[a]}>|{a}>', expected,
                    'Extract middle equality term and substitute f(a), a, b.')
            # An unequal rational witness independently exercises linearity;
            # the exhaustive basis cases above establish the finite linear map.
            v = [Q() for _ in range(4)]
            v[a] = Q('3/5'); v[2+a] = Q('4/5')
            expected = analysis.oracle(v, f)
            add(f'linearity-{index}-{a}', ['P10','P11'], f'{matrix}*([3/5;4/5] ⊗ |{a}>)', expected,
                'Instantiate arbitrary psi by disclosed normalized [3/5;4/5] witness; not all-state symbolic proof.')
            add(f'linearity-rhs-{index}-{a}', ['P10'], f'(X^{f[a]}*[3/5;4/5]) ⊗ |{a}>', expected,
                'Extract RHS; same disclosed normalized rational witness and truth table.')
            expected = [Q() for _ in range(4)]
            expected[a] = minus[0]*Q((-1)**f[a]); expected[2+a] = minus[1]*Q((-1)**f[a])
            for kind, expr in [('oracle',f'{matrix}*(|->|{a}>)'),
                               ('power',f'(X^{f[a]} |->)|{a}>'),
                               ('phase',f'(-1)^{{{f[a]}}}*(|->|{a}>)')]:
                add(f'kickback-{index}-{a}-{kind}', ['P12'], expr, expected,
                    'Extract equality term; instantiate truth table and bit; make scalar grouping explicit.')
        p1 = [Q('1/2'),Q('1/2'),Q('-1/2'),Q('-1/2')]
        expected = analysis.oracle(p1,f)
        for kind, expr in [('direct',f'{matrix}*(|->|+>)'),
                           ('linear',f'1/sqrt(2)*{matrix}*(|->|0>)+1/sqrt(2)*{matrix}*(|->|1>)'),
                           ('factored',f'|-> ⊗ (((-1)^{{{f[0]}}}*|0>+(-1)^{{{f[1]}}}*|1>)/sqrt(2))')]:
            add(f'final-{index}-{kind}', ['P20'], expr, expected,
                'Extract one equality term; replace oracle/function values by explicit truth table; retain every global sign.')
    return result


def main():
    ap=argparse.ArgumentParser()
    for name in ('source','package','output'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--translator',type=Path)
    args=ap.parse_args()
    _, inv=inventory(args.source)
    args.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((args.package/'build-manifest.json').read_text())
    for entry in manifest['files']:
        assert hashlib.sha256((args.package/entry['path']).read_bytes()).hexdigest().lower()==entry['sha256'].lower(), entry['path']
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.package/'data'))
    def execute(expr):
        try:
            wire=expr
            if args.translator:
                source_expr=expr[8:] if expr.startswith('quantum:') else expr
                t=subprocess.run([str(args.translator)],input=source_expr.encode(),capture_output=True,timeout=20)
                if t.returncode:
                    return dict(input=expr,returncode=t.returncode,stdout=t.stdout.decode(),stderr=t.stderr.decode(),route='standalone parser rejection')
                wire='quantum:'+t.stdout.decode().strip()
            p=subprocess.run([str(args.package/'quantum-worker.exe'),'--json'], input=wire.encode(),capture_output=True,env=env,timeout=20)
            d=dict(input=expr,returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
            d['evaluator_input']=wire
            if p.returncode==0: d['actual']=json.loads(d['stdout'])
            return d
        except subprocess.TimeoutExpired:
            return dict(input=expr,status='timeout')
    def compare(d, expected):
        v=d.get('actual',{})
        if 'text' not in v: return False
        rows=v['cells'] if v['rows'] else [[v['text']]]
        try:
            return v['approximate'] is False and v['columns'] in (0,1) and [analysis.parse_cell(row[0]) for row in rows]==expected
        except (ValueError,SyntaxError,ZeroDivisionError):
            return False
    def save(name,value):
        (args.output/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
    literal=[dict(f, execution=execute('quantum:'+f['original'])) for f in inv['formulas']]
    save('literal.json',literal)
    cases=fixtures(); save('fixtures.json',cases)
    results=[]
    for f in cases:
        d=dict(f,execution=execute(f['input']))
        expected=[Q(*v) for v in f['expected']]
        d['pass']=compare(d['execution'],expected)
        if d['pass']:
            # Canonical worker text re-entry, not actual GUI Clipboard.
            d['reentry']=execute('quantum:'+d['execution']['actual']['text'])
            d['reentry_pass']=compare(d['reentry'],expected)
        results.append(d)
    save('checks.json',results)
    summary=dict(revision=manifest['revision'], verified_payload_files=len(manifest['files']),
                 translator_sha256=hashlib.sha256(args.translator.read_bytes()).hexdigest() if args.translator else None,
                 route='standalone parser plus retained quantum evaluator' if args.translator else 'released worker',
                 worker_sha256=hashlib.sha256((args.package/'quantum-worker.exe').read_bytes()).hexdigest(),
                 runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 literal_count=len(literal), finite_cases=len(cases),
                 passes=sum(d['pass'] for d in results),reentry_passes=sum(d.get('reentry_pass',False) for d in results),
                 failures=[d['id'] for d in results if not d['pass'] or not d.get('reentry_pass')])
    save('summary.json',summary); print(json.dumps(summary))
    return bool(summary['failures'])


if __name__=='__main__':
    raise SystemExit(main())
