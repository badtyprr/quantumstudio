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
spec = importlib.util.spec_from_file_location('runtime_copy_import', root / 'qasm-import.py')
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
    'def m(mutable array[int,1] a)->int{a[0]=9;return 1;} array[int,1] a={1};a[0]+=m(a);output bit c;c=bool(a[0]==2);',
    'def m(mutable array[float[32],1] a)->float[32]{a[0]=9.0;return 1.0;} array[float[32],1] a={1.0};a[0]+=m(a);output bit c;c=bool(a[0]==2.0);',
    'array[int,2] a;array[int,3] b;bit go="0";if(go==1){b=a;}output bit c;c=1;',
    'def m(mutable array[int,1] a)->int{a[0]=9;return 2;} array[int,1] a={1};array[int,2] b={a[0],m(a)};output bit c;c=bool(b[0]==1 && b[1]==2 && a[0]==9);',
    'def m(mutable array[int,2] a)->int{a[0]=9;return 1;} array[int,2] a={1,2};array[int,4] b=a ++ a[0:m(a)];output bit c;c=bool(b[0]==1 && b[1]==2 && b[2]==9 && b[3]==2);',
    'def m(mutable array[int,3] a)->int{a[0]=9;return 0;} array[int,3] a;a[0]=1;array[int,2] b=a[0:0] ++ a[m(a):0];output bit c;c=bool(b[0]==1 && b[1]==9);',
    'array[int,4] a={1,2,3,4};int k=1;a[k:3]=a[0:2];output bit c;c=bool(a[0]==1 && a[1]==1 && a[2]==2 && a[3]==3);',
    'array[int,4] a={1,2,3,4};int k=1;a[0:2]=a[k:3];output bit c;c=bool(a[0]==2 && a[1]==3 && a[2]==4 && a[3]==4);',
    'array[int,4] a={1,2,3,4};int k=3;a[k:-1:0]=a;output bit c;c=bool(a[0]==4 && a[3]==1);',
    'array[int,3] a={1,2,3};a=a[1:2] ++ a[0:0];output bit c;c=bool(a[0]==2 && a[1]==3 && a[2]==1);',
    'array[int,2] a={1,2};array[int,4] b=a ++ a;output bit c;c=bool(b[0]==1 && b[1]==2 && b[2]==1 && b[3]==2);',
    'array[int,2,2] a={{1,2},{3,4}};array[int,4,2] b=a ++ a;output bit c;c=bool(b[0,0]==1 && b[3,1]==4);',
    'array[int,2,3] a={{1,2,3},{4,5,6}};int k=1;a[k]=a[0];output bit c;c=bool(a[1,0]==1 && a[1,2]==3);',
    'array[int,0,3] a;array[int,0,3] b=a;output bit c;c=bool(sizeof(b,0)==0 && sizeof(b,1)==3);',
    'array[float[32],2] a={16777217.0,0.5};array[float[32],2] b=a;output bit c;c=bool(b[0]==16777216.0 && b[1]==0.5);',
    'def f(mutable array[int,#dim=1] a,readonly array[int,#dim=1] b){a=b;} array[int,4] a={1,2,3,4};f(a[1:3],a[0:2]);output bit c;c=bool(a[3]==3);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 2;} array[int,4] a={1,2,3,4};array[int,1] b={1};a[b[0]:3]=a[0:m(b)];output bit c;c=bool(a[1]==1 && a[2]==2 && a[3]==3);',
):
    source='OPENQASM 3.0;include "stdgates.inc";'+source
    try:
        original=compile_source(source);execute(original,'1')
        execute(compile_source(original['source']),'1')
    except Exception as error:raise AssertionError(source) from error
for source in (
    'array[int,2] a;array[int,2] b={1,2};b=a;',
    'array[int,2] a;array[int,3] b;b=a;',
    'array[int,2,3] a;array[int,3,2] b;b=a;',
):execute(compile_source('OPENQASM 3.0;'+source),'',error=True)
for source in (
    'def f(readonly array[int,2] a,readonly array[int,2] b){a=b;} array[int,2] a;f(a,a);',
    'array[int[32],2] a;array[int[16],2] b;b=a;',
    'def f(readonly array[int,#dim=1] a){} array[int,2] a;f(a ++ a);',
):
    try:compiler.convert('OPENQASM 3.0;'+source,classical=True)
    except ValueError:checks+=1
    else:raise AssertionError('Accepted invalid copy: '+source)
print('PASS: %d runtime array copy source checks.'%checks)
