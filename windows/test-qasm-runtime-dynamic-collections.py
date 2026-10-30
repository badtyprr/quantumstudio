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
 'array[int,2] a={1,2};int n=0;for int v in a{n+=v;break;}output bit c;c=n==1;',
 'array[int,2] a={1,2};int n=0;for int v in a{n+=v;continue;}output bit c;c=n==3;',

 'array[int,65] a;for int i in [0:64]{a[i]=i;}int n=0;for int v in a{n+=v;}output bit c;c=n==2080;',
 'def f(readonly array[int,#dim=1] a)->int{for int v in a{if(v==2){return v;}}return 0;}array[int,3] a={1,2,3};int n=0;for int i in [0:2]{n+=f(a[i:2]);}output bit c;c=n==4;',
 'array[int,3] a={1,2,3};int first=2;int last=0;int n=0;for int v in a[first:last]{n+=v;}output bit c;c=n==0;',
 'array[float[32],2] a={16777217.0,0.5};int k=0;float n=0;for float v in a[k:1]{n+=v;}output bit c;c=n==16777216.5;',
 'array[angle[8],2] a={pi,pi};int k=1;angle[8] n=0;for angle[8] v in a[k:-1:0]{n+=v;}output bit c;c=n==angle[8](0.0);',
 'bit[4] a="1101";int k=1;int n=0;for int j in [0:1]{for bit v in a[k:3]{n+=int(v);}a="1111";}output bit c;c=n==5;',

 'bit[4] a="1101";int k=1;int n=0;for bit v in a[k:3]{a="0000";n=n*2+int(v);k=0;}output bit c;c=n==3;',
 'bit[4] a="1101";int k=3;int n=0;for bit v in a[k:-1:0]{n=n*2+int(v);}output bit c;c=n==13;',

 'array[int,4] a={1,2,3,4};int k=1;int n=0;for int v in a[k:3]{a[2]=9;k=0;n=n*10+v;v=0;}output bit c;c=n==234;',
 'def f(readonly array[int,#dim=1] a)->int{int n=0;for int v in a{n=n*10+v;}return n;}array[int,4] a={1,2,3,4};int k=3;output bit c;c=f(a[k:-1:1])==432;',
 'array[int,2,3] a={{1,2,3},{4,5,6}};int k=1;int n=0;for int v in a[k]{n+=v;}output bit c;c=n==15;',
 'array[int,3] a;a[1]=5;int k=1;int n=0;for int v in a[k:k]{n+=v;}output bit c;c=n==5;',
 'array[int,0] a;int n=0;for int v in a{n+=v;}output bit c;c=n==0;',
 'array[int,3] a={1,2,3};int n=0;int k=0;for int j in [0:1]{for int v in a[k:2]{if(v==2){continue;}n+=v;}a[0]=4;}output bit c;c=n==11;',
):
    source='OPENQASM 3.0;include "stdgates.inc";'+source
    try:
        original=compile_source(source);execute(original,'1')
        execute(compile_source(original['source']),'1')
    except Exception as error:raise AssertionError(source) from error
for source in (
 'array[int,3] a;a[0]=1;int k=0;for int v in a[k:1]{break;}',
 'array[int,2] a={1,2};int k=2;for int v in a[k:1]{}',
 'array[int,2] a={1,2};int step=0;for int v in a[0:step:1]{}',
 'bit[3] a="111";int k=-1;for bit v in a[k:2]{}',
 'bit[3] a="111";uint[64] k=18446744073709551615;for bit v in a[k:2]{}',
):
    original=compile_source('OPENQASM 3.0;'+source);execute(original,'',error=True)
    execute(compile_source(original['source']),'',error=True)
for source in (
 'qubit q;int n=1;for int i in [0:n]{break;bogus q;}',
 'qubit q;int n=1;for int i in [0:n]{continue;bogus q;}',
 'bit[3] b="101";for bit v in b[0.5:1]{}',
 'bit[3] b="101";float f=0.5;for bit v in b[f:1]{}',
):
    try:compiler.convert('OPENQASM 3.0;'+source,classical=True)
    except (ValueError,RuntimeError):checks+=1
    else:raise AssertionError('Accepted invalid collection: '+source)
print('PASS: %d dynamic array iteration checks.'%checks)
