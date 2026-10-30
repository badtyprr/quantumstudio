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
spec = importlib.util.spec_from_file_location('runtime_bit_alias_import', root / 'qasm-import.py')
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


for source in (
    'def f(bit[2] b)->int{let a=b;int n=0;for bit v in a{n=2*n+int(v);}return n;}bit[2] b="10";int n=f(b);output bit c;c=bool(n==1);',
    'def m(mutable array[int,1] a)->int{a[0]=2;return 3;}bit[4] b="1010";array[int,1] i={1};let a=b[i[0]:m(i)];int n=0;for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==5);',
    'bit[4] b="1010";let a=b[0:3];int n=0;for bit v in a[1:2]{n=2*n+int(v);}output bit c;c=bool(n==2);',
    'bit[4] b="1010";let a=b[-2:-1];int n=0;for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==1);',
    'bit[4] b="1010";let a=b[1:3];int n=0;for bit v in a{n=2*n+int(v);b="0000";v=0;}output bit c;c=bool(n==5);',
    'bit[2] b="10";bit[2] d="01";let a=b;int n=0;{let a=d;for bit v in a{n=2*n+int(v);}}for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==9);',
    'bit[4] b="1010";int n=0;for int k in [0:1]{let a=b[k:k];for bit v in a{n=2*n+int(v);}}output bit c;c=bool(n==1);',
    'bit[4] b="1010";let a=b[0:1]++b[2:3];let d=a[1:2];int n=0;for bit v in d{n=2*n+int(v);}output bit c;c=bool(n==2);',
    'bit[2] b="10";bit[2] d="01";int n=0;for bit v in b++d{n=2*n+int(v);}output bit c;c=bool(n==6);',
    'bit[4] b="1010";let a=b[0:3];int n=0;for bit v in a{if(v==0){continue;}n+=1;break;}output bit c;c=bool(n==1);',
    'qubit q;h q;bit z=measure q;int k=int(z);bit[2] b="10";let a=b[k:k];int n=0;for bit v in a{n+=int(v);}output bit c;c=bool(n==k);',
    'bit[4] b="1010";let a=b[1:3];int n=0;for bit v in a {n=2*n+int(v);}output bit c;c=bool(n==5);',
    'bit[4] b="1010";int k=1;let a=b[k:3];k=0;b="0110";int n=0;for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==6);',
    'bit[2] b="10";bit[2] d="01";let a=b++d;int n=0;for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==6);',
    'bit[4] b="1010";let a=b[{3,1,0}];int n=0;for bit v in a{n=2*n+int(v);}output bit c;c=bool(n==6);',
    'bit[4] b="1010";let a=b[0:3];let d=a[3:-1:0];int n=0;for bit v in d{n=2*n+int(v);}output bit c;c=bool(n==10);',
    'bit[4] b="1010";let a=b[1];int n=0;for bit v in a{n+=int(v);}output bit c;c=bool(n==1);',
):
    original=compile_source('OPENQASM 3.0;'+source)
    restored=compile_source(original['source'])
    execute(original,'1');execute(restored,'1')
for source in (
    'bit[4] b;let a=b[0:2]++b[2:3];',
    'bit[4] b;let a=b[{1,1}];',
    'bit[4] b;int k=5;let a=b[k:k];',
    'bit[4] b;int k=2;let a=b[k:1];',
):
    original=compile_source('OPENQASM 3.0;'+source)
    restored=compile_source(original['source'])
    execute(original,None,error=True);execute(restored,None,error=True)
for source in (
    'bit[2] b;let a=b[true:1];',
    'bit[2] b;let a=b[0.5:1];',
    'bit[2] b;qubit q;let a=b++q;',
    'let a=b;bit[2] b;',
    'bit[2] b;let a=b;{bit[2] b;let d=b;for bit v in d{}}',
):
    try:compiler.convert('OPENQASM 3.0;'+source,classical=True)
    except (ValueError,NotImplementedError):checks+=1
    else:raise AssertionError('Expected alias rejection: '+source)

source='OPENQASM 3.0;bit[64] b="'+('1'*64)+'";let a=b;int n=0;for bit v in a{n+=int(v);}if(n!=64){int bad=1/0;}'
original=compile_source(source);restored=compile_source(original['source'])
execute(original,'1'*64);execute(restored,'1'*64)

print(f'PASS: {checks} classical-bit alias iteration checks.')
