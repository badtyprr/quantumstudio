"""Runtime array source, save/load, export/reimport and both execution engines."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--adapter', type=Path, required=True)
p.add_argument('--worker', type=Path)
p.add_argument('--frozen', type=Path)
args = p.parse_args()
root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runtime_quantum_loop_import', root / 'qasm-import.py')
compiler = importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
checks = 0
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data')) if args.worker else os.environ

def compile_source(source):
    global checks
    result = compiler.convert(source, classical=True);checks += 1
    if args.frozen:
        run = subprocess.run([str(args.frozen.resolve()), '--classical'], input=source.encode(), capture_output=True, timeout=30)
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout) == result;checks += 1
    run = subprocess.run([str(args.adapter.resolve())], input=json.dumps(result).encode(), capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    checks += 1
    return json.loads(run.stdout)

def execute(encoded, expected, error=False):
    global checks
    if not args.worker:return
    for exact in (True, False):
        run = subprocess.run([str(args.worker.resolve()), '--exact-circuit' if exact else '--sample'], input=base64.b64decode(encoded['exact' if exact else 'sampled']), capture_output=True, env=env, timeout=45)
        checks += 1
        if error:
            assert run.returncode and not run.stdout, run.stdout
            if isinstance(error,str):assert error in run.stderr.decode(),run.stderr
            continue
        assert run.returncode == 0, run.stderr
        values = json.loads(run.stdout)['probabilities' if exact else 'counts']
        assert values == {expected: '1' if exact else 10000}, values


for body,expected in [('for int i in [0:1]{i=1;bool ok=f(q[i]);}', '00'), ('for int i in [0:1]{{int i=0;bool ok=f(q[i]);}}', '00'), ('for int i in [0:1]{bool ok=f(q[i]);break;}', '01'), ('for int i in [0:1]{bool ok=f(q[i]);continue;}', '11'), ('int n=1;for int i in [0:n]{bool ok=f(q[i]);}', '11'), ('for int i in [0:1]{for int i in [0:1]{bool ok=f(q[i]);}}', '00'), ('int n=1;for int i in {n,0,n}{bool ok=f(q[i]);}', '01'), ('int n=1;for int i in [n:-1:0]{bool ok=f(q[i]);}', '11')]:
    source='OPENQASM 3.0;include \"stdgates.inc\";def f(qubit a)->bool{x a;return true;}qubit[2] q;'+body+'output bit[2] r;r=measure q;'
    original=compile_source(source);restored=compile_source(original['source'])
    execute(original,expected);execute(restored,expected)

for source,expected in (
    ('def f(qubit a)->bool{x a;return true;}qubit[2] q;int n=2;for uint[1] i in [0:n]{bool ok=f(q[i]);}output bit[2] r;r=measure q;','10'),
    ('def f(qubit a)->bool{x a;return true;}qubit[2] q;for uint[1] i in [0:2]{bool ok=f(q[i]);}output bit[2] r;r=measure q;','10'),
    ('def f(qubit a){x a;}qubit[2] q;int n=1;for int i in [0:n]{f(q[i]);}output bit[2] r;r=measure q;','11'),
    ('def f(qubit a){x a;}qubit[2] q;for int i in {1,0,1}{f(q[i]);}output bit[2] r;r=measure q;','01'),
    ('def f(qubit a)->bool{x a;return true;}def g(qubit[2] q)->int{int bound=1;for int i in [0:bound]{bool ok=f(q[i]);return i;}return 9;}qubit[2] q;int n=g(q);output bit[2] r;output bit c;r=measure q;c=bool(n==0);','101'),
    ('def f(qubit a){x a;}qubit[2] q;qubit p;h p;bit b=measure p;int n=int(b);for int i in [n:n]{f(q[i]);}output bit c;bit[2] r;r=measure q;c=bool((n==0 && uint[2](r)==1) || (n==1 && uint[2](r)==2));','1'),
):
    original=compile_source('OPENQASM 3.0;include "stdgates.inc";'+source)
    restored=compile_source(original['source'])
    execute(original,expected);execute(restored,expected)

for body in (
    'int z=0;for int i in [0:z:1]{bool ok=f(q[i]);}',
    'int n=2;for int i in [0:n]{bool ok=f(q[i]);}',
    'int n=4096;for int i in [0:n]{bool ok=f(q[i]);}',
):
    original=compile_source('OPENQASM 3.0;include "stdgates.inc";def f(qubit a)->bool{x a;return true;}qubit[2] q;'+body)
    restored=compile_source(original['source'])
    try:execute(original,None,error=True);execute(restored,None,error=True)
    except Exception as error:raise AssertionError(body) from error
source='OPENQASM 3.0;def f(qubit a,qubit b)->bool{return true;}qubit[2] q;int n=1;for int i in [0:n]{bool ok=f(q[i],q[i]);}'
original=compile_source(source);restored=compile_source(original['source'])
execute(original,None,error=True);execute(restored,None,error=True)

print(f'PASS: {checks} runtime quantum call-loop checks.')
