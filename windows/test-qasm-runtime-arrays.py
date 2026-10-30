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
spec = importlib.util.spec_from_file_location('runtime_array_import', root / 'qasm-import.py')
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
    'def f(int x)->int {return x+1;} int z=6;int i=0;array[int,2] a;a[i]=f(z);output bit c;c=bool(a[i]==7);',
    'def f(int x)->float[64] {return float[64](x+1);} int z=6;int i=0;array[float[64],2] a;a[i]=f(z);output bit c;c=bool(a[i]==7.0);',
    'array[int,1] a;bit b="0";output bit c;c=1;if(b==1){c=bool(a[0]);}',
    'array[int,1] a;bit b="0";output bit c;c=!(bool(b) && bool(a[0]));',
    'array[int,1] a;bit b="1";output bit c;c=bool(b) || bool(a[0]);',
    'array[int,2,3] a; a[1,2]=7; bit c=bool(a[-1,-1]==7);',
    'int i=1; array[int[8],2] a={3,4};a[i]+=2;bit c=bool(a[i]==6);',
    'qubit q;h q;bit b=measure q;array[int,2] a;int i=int[2](bool(b));a[i]=7;output bit c;c=bool(a[i]==7);',
    'bit b="1";array[bool,2] a={false,false};if(b==1){a[1]=true;}output bit c;c=bool(a[1]);',
    'int i=0;array[float[32],1] a={16777217.0};output bit c;c=bool(a[i]==16777216.0);',
    'float[64] i=1.0;array[int,2] a={2,7};output bit c;c=bool(a[int(i)]==7);',
    'float[64] i=1.0;array[float[64],2] a={2.0,7.0};output bit c;c=bool(a[int(i)]==7.0);',
    'int i=0;array[angle[8],1] a={pi};a[i]+=angle[8](pi);output bit c;c=bool(a[i]==angle[8](0.0));',
    'int i=0;array[int,2,2] a={{1,2},{3,4}};output bit c;c=bool(a[i+1][i+1]==4);',
    'int i=0;array[int,2] a={2,3};for int j in [0:1]{a[j]+=i;i+=1;}output bit c;c=bool(a[1]==4);',
    'int i=0;array[int,2] a={2,3};if(i==0){int j=1;a[j]=7;}output bit c;c=bool(a[1]==7);',
    'int i=0;array[int,0] a;output bit c;c=bool(sizeof(a)==0);',
    'const uint[2] N=5;int i=0;array[int,N] a;a[i]=1;output bit c;c=bool(sizeof(a)==1);',
    'const int N=0;array[int,N] a;output bit c;c=bool(sizeof(a)==0);',
    'const int N=-1;array[int,2] a={1,2};output bit c;c=bool(a[N]==2);',
    'int i=0;array[int,2] a={2,3};{int a=1;bit local=bool(a);}output bit c;c=bool(a[i]==2);',
    'array[int,5000] big;array[int,2] a={1,2};int i=0;output bit c;c=bool(a[i]==1);',
):
    source='OPENQASM 3.0;include "stdgates.inc";'+source
    try:
        original=compile_source(source);restored=compile_source(original['source'])
        execute(original,'1');execute(restored,'1')
    except Exception as error:raise AssertionError(source) from error

for source in (
    'int i=0;array[int,2] a;bit c=bool(a[i]);',
    'int i=2;array[int,2] a;a[i]=1;',
    'int i=-3;array[int,2] a;a[i]=1;',
    'int i;array[int,2] a;a[i]=1;',
):
    encoded=compile_source('OPENQASM 3.0;'+source)
    execute(encoded,None,error=True)

for index in ('2','-3','18446744073709551615'):
    source='OPENQASM 3.0;def f(int x)->int {return 1/x;}int z=0;'+('uint[64]' if index=='18446744073709551615' else 'int')+' i='+index+';array[int,2] a;a[i]=f(z);'
    original=compile_source(source);restored=compile_source(original['source'])
    execute(original,None,error='array');execute(restored,None,error='array')

for suffix in ('=1;','=f(z);'):
    source='OPENQASM 3.0;def f(int x)->int {return 1/x;}int z=0;int bad=2;array[int,2,2] a;a[bad,f(z)]'+suffix
    original=compile_source(source);restored=compile_source(original['source'])
    execute(original,None,error='array');execute(restored,None,error='array')

print(f'PASS: {checks} runtime array source checks.')
