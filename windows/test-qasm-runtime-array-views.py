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
spec = importlib.util.spec_from_file_location('runtime_view_import', root / 'qasm-import.py')
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
    'def f(readonly array[int,2,2] a)->int{return a[0][0]+a[0][1];}array[int,4,3] a={{1,2,3},{4,5,6},{7,8,9},{10,11,12}};int k=1;output bit c;c=bool(f(a[k:2][1:2])==11);',
    'array[int,3,3] a={{1,2,3},{4,5,6},{7,8,9}};array[int,2,2] b={{10,11},{12,13}};int k=1;a[k:2][1:2]=b;output bit c;c=bool(a[1,1]==10 && a[2,2]==13 && a[0,1]==2);',
    'def f(mutable array[int,2,2] a){a[1][0]=17;}array[int,3,3] a={{1,2,3},{4,5,6},{7,8,9}};f(a[1:2][1:2]);output bit c;c=bool(a[2,1]==17 && a[1,1]==5);',
    'array[int,4] a={1,2,3,4};int k=1;output bit c;c=bool(a[k:3][2]==4);',
):
    original=compile_source('OPENQASM 3.0;'+source)
    restored=compile_source(original['source'])
    execute(original,'1');execute(restored,'1')

for source in (
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,4] a;uint s=1;output bit c;c=bool(f(a[0:s:3])==4);',
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,4] a;uint s=4096;output bit c;c=bool(f(a[0:s:3])==1);',
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,3] a;uint[64] s=18446744073709551615;output bit c;c=bool(f(a[0:s:2])==1);',
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,3] a;uint[64] s=18446744073709551615;output bit c;c=bool(f(a[2:s:0])==0);',
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,3] a;int[64] s=-9223372036854775808;output bit c;c=bool(f(a[2:s:0])==1);',
    'array[int,2,3] a;int k=1;output bit c;c=bool(sizeof(a[k])==3);',
    'array[int,2,3] a;int k=1;output bit c;c=bool(sizeof(a[k:k],1)==3);',
    'def f(readonly array[int,#dim=2] a)->uint{return sizeof(a[0:0],1);} array[int,2,3] a;output bit c;c=bool(f(a)==3);',
    'def f(readonly array[int,#dim=1] a)->int{return a[0];} array[int,3] a={1,2,3};output bit c;c=bool(f(a[:-1:0])==3);',
    'qubit q;def set(mutable array[int[32], #dim=1] target){target[0]=1;} array[int[32],1] a={0};set(a);if(a[0]==1)x q;output bit c;c=measure q;',
    'def set(mutable array[int[32], #dim=1] target){target[0]=1;} bit c="0";array[int[32],1] a={0};if(c==1){set(a);}output bit ok;ok=bool(a[0]==0);',
    'def f(mutable array[int,#dim=1] a){a[0]=9;} qubit q;h q;bit b=measure q;array[int,2] a={1,2};int k=int(b);f(a[k:k]);output bit c;c=bool(a[k]==9);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 3;} array[int,4] a={1,2,3,4};array[int,1] b={1};output bit c;c=bool(a[b[0]:m(b)][0]==2);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 9;} array[int,4] a={1,2,3,4};array[int,1] b={1};a[b[0]:3][0]=m(b);output bit c;c=bool(a[1]==9 && a[2]==3);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 9;} def f(mutable array[int,#dim=1] a,mutable array[int,1] b){a[b[0]]=m(b);} array[int,4] a={1,2,3,4};array[int,1] b={1};f(a,b);output bit c;c=bool(a[1]==9 && a[2]==3);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 0;} def f(mutable array[int,#dim=1] a,int x){a[0]=9;} array[int,4] a={1,2,3,4};array[int,1] b={1};f(a[b[0]:3],m(b));output bit c;c=bool(a[1]==9 && a[2]==3);',
    'def m(mutable array[int,1] b)->int{b[0]=2;return 3;} def f(mutable array[int,#dim=1] a){a[0]=9;} array[int,4] a={1,2,3,4};array[int,1] b={1};f(a[b[0]:m(b)]);output bit c;c=bool(a[1]==9 && a[2]==3);',
    'def f(mutable array[float[32],#dim=1] a){a[0]=16777217.0;} array[float[32],2] a;int k=1;f(a[k:1]);output bit c;c=bool(a[1]==16777216.0);',
    'def f(readonly array[bool,#dim=1] a)->bool{return a[0];} array[bool,2] a={false,true};int k=1;output bit c;c=f(a[k:1]);',
    'def f(readonly array[int,#dim=2] a)->int{return a[0,1];} array[int,2,3] a={{1,2,3},{4,5,6}};int k=1;output bit c;c=bool(f(a[k:k,1:2])==6);',
    'def f(mutable array[int,#dim=1] a){a[0]=9;} array[int,4] a={1,2,3,4};int k=-1;f(a[k:-1:0]);output bit c;c=bool(a[3]==9);',
    'def f(mutable array[int,#dim=1] a,mutable array[int,#dim=1] b){a[0]=7;b[0]=8;} array[int,4] a={1,2,3,4};int k=0;f(a[k:2:2],a[1:2:3]);output bit c;c=bool(a[0]==7 && a[1]==8);',
    'def f(readonly array[int,#dim=1] a,readonly array[int,#dim=1] b)->int{return a[0]+b[0];} array[int,2] a={3,4};output bit c;c=bool(f(a,a)==6);',
    'def f(readonly array[int,#dim=1] a,mutable array[int,#dim=1] b){b[0]=9;} array[int,2] a={3,4};f(a,a);output bit c;c=bool(a[0]==9);',
    'def f(readonly array[int,#dim=2] a)->uint{return sizeof(a,1);} array[int,0,3] a;output bit c;c=bool(f(a)==3);',
    'def f(mutable array[int,#dim=1] a){a[0]=9;} array[int,4] a={1,2,3,4};int k=1;f(a[k:3]);output bit c;c=bool(a[1]==9);',
    'def f(readonly array[int,#dim=1] a){} array[int,4] a;int k=1;f(a[k:3]);output bit c;c=1;',
    'def f(mutable array[int,2] a){a[1]=9;} array[int,4] a={1,2,3,4};int k=1;f(a[k:2]);output bit c;c=bool(a[2]==9);',
    'def f(readonly array[int,#dim=1] a)->uint{return sizeof(a);} array[int,4] a;int k=1;output bit c;c=bool(f(a[k:3])==3);',
    'def f(mutable array[int,#dim=1] a){a[0]=9;} def g(mutable array[int,#dim=1] a){f(a[1:2]);} array[int,4] a={1,2,3,4};g(a);output bit c;c=bool(a[1]==9);',
    'array[int,4] a={1,2,3,4};int k=1;output bit c;c=bool(a[k:3][0]==2);',
    'array[int,4] a;int k=1;output bit c;c=bool(sizeof(a[k:3])==3);',
    'array[int,2,3] a;int k=1;output bit c;c=bool(sizeof(a[k:k])==1);',
    'array[int,2,3] a={{1,2,3},{4,5,6}};int k=1;output bit c;c=bool(a[k,0:2][2]==6);',
    'array[int,4] a={1,2,3,4};int k=3;output bit c;c=bool(a[k:-1:0][1]==3);',
    'array[int,4] a={1,2,3,4};int k=-3;output bit c;c=bool(a[k:-1][-1]==4);',
    'array[int,4] a={1,2,3,4};int k=1;a[k:3][1]=9;output bit c;c=bool(a[2]==9);',
    'array[float[32],4] a={1.0,2.0,3.0,4.0};int k=1;a[k:3][1]=9.0;output bit c;c=bool(a[2]==9.0);',
    'array[int,4] a;int k=0;output bit c;c=bool(sizeof(a[3:1])==0);',
    'array[int,0,3] a;int k=0;output bit c;c=bool(sizeof(a[:,1:2],0)==0 && sizeof(a[:,1:2],1)==2);',
    'array[int,4] a={1,2,3,4};output bit c;c=1;int k=0;while(k<3){c=c & bool(a[k:3][0]==k+1);k+=1;}',
    'array[int,4] a;output bit c;c=1;int k=8;if(k==0){c=bool(a[k:3][0]);}',
):
    source='OPENQASM 3.0;include "stdgates.inc";'+source
    try:
        original=compile_source(source);execute(original,'1')
        execute(compile_source(original['source']),'1')
    except Exception as error:raise AssertionError(source) from error
for suffix in ('a[k:3][0]','a[0:3][k]','sizeof(a[k:3])'):
    source='OPENQASM 3.0;array[int,4] a={1,2,3,4};int k=8;output bit c;c=bool('+suffix+');'
    execute(compile_source(source),'',error=True)
for source in (
    'def f(mutable array[int,#dim=1] a,mutable array[int,#dim=1] b){} array[int,4] a;f(a[0:2],a[2:3]);',
    'def f(readonly array[int,2] a){} array[int,4] a;f(a);',
    'def f(readonly array[int,#dim=1] a){} array[int,4] a;int k=8;f(a[k:3]);',
):execute(compile_source('OPENQASM 3.0;'+source),'',error=True)
for source in (
    'def f(readonly array[int,#dim=1] a){a[0]=9;} array[int,2] a;f(a);',
    'def f(mutable array[int,#dim=1] a){} def g(readonly array[int,#dim=1] a){f(a);} array[int,2] a;g(a);',
):
    try:compiler.convert('OPENQASM 3.0;'+source,classical=True)
    except ValueError:checks+=1
    else:raise AssertionError('Expected readonly rejection: '+source)
print('PASS: %d runtime array view source checks.'%checks)
