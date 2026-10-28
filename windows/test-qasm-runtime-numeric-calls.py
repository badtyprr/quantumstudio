"""Runtime numeric subroutine activation and return regression checks."""
import argparse, base64, copy, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--adapter',type=Path,required=True);parser.add_argument('--worker',type=Path);parser.add_argument('--frozen',type=Path)
args=parser.parse_args();spec=importlib.util.spec_from_file_location('wire_import',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
checks=0;header='OPENQASM 3.0; include "stdgates.inc"; '
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data')) if args.worker else os.environ

def compile(source):
    global checks
    result=compiler.convert(source,classical=True);checks+=1
    if args.frozen:
        p=subprocess.run([str(args.frozen.resolve()),'--classical'],input=source.encode(),capture_output=True,timeout=30)
        assert p.returncode==0,p.stderr
        assert json.loads(p.stdout)==result;checks+=1
    return result
def adapt(model,success=True):
    global checks
    p=subprocess.run([str(args.adapter.resolve())],input=json.dumps(model).encode(),capture_output=True,timeout=30)
    assert (p.returncode==0)==success,p.stderr.decode(errors='replace');checks+=1
    if success:return json.loads(p.stdout)
    assert not p.stdout
def execute(encoded,exact,expected=None,error=None):
    global checks
    if not args.worker:return
    p=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(encoded['exact' if exact else 'sampled']),capture_output=True,env=env,timeout=45)
    checks+=1
    if error:
        assert p.returncode and not p.stdout and error in p.stderr.decode(),p.stderr
        return
    assert p.returncode==0,p.stderr
    result=json.loads(p.stdout)
    if exact:
        actual={}
        for k,v in result['probabilities'].items():
            p=subprocess.run([str(args.worker.resolve()),'--json','--approx'],input=v.encode(),capture_output=True,env=env,timeout=30)
            assert p.returncode==0,p.stderr
            actual[k]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
    else:actual={k:v/10000 for k,v in result['counts'].items()}
    assert all(abs(actual.get(k,0)-expected.get(k,0))<(1e-12 if exact else .025) for k in set(actual)|set(expected)),(actual,expected)

cases=[
 ('def f(float[32] x)->float[32]{float[32] y=x;x+=2;return y;} float[32] x=3;float[32] y=f(x);bit c=bool(x==3 && y==3);',{'1':1}),
 ('def f(float[32] x)->float[32]{return x+1;} float[64] x=16777216;float[64] y=f(x);bit c=bool(y==16777216);',{'1':1}),
 ('def f(float[64] x)->float[64]{return x+1;} float[32] x=16777216;float[64] y=f(x);bit c=bool(y==16777217);',{'1':1}),
 ('def f(angle[8] x)->angle[8]{x+=angle[8]("00000001");return x;}angle[8] x=angle[8]("11111111");angle[8] y=f(x);bit c=bool(y==angle[8]("00000000") && x==angle[8]("11111111"));',{'1':1}),
 ('def f(float[64] x)->float[64]{return x+1;}def g(float[64] x)->float[64]{float[64] y=f(x);return f(y);}float[64] x=2;float[64] y=g(x);bit c=bool(y==4);',{'1':1}),
 ('def f(float[64] x)->float[64]{while(x>0){if(x==2){return x;}x-=1;}return 0;}float[64] x=3;float[64] y=f(x);bit c=bool(y==2);',{'1':1}),
 ('def f(float[64] x)->float[64]{float[64] y=x;return y;}float[64] total=0;for int i in [0:2]{total+=f(float[64](i));}bit c=bool(total==3);',{'1':1}),
 ('def f(float[64] x)->float[64]{return x;}qubit[2] q;h q[0];bit m=measure q[0];float[64] x=f(float[64](uint[1](m)));ry(pi*x) q[1];bit c=measure q[1];',{'00':.5,'11':.5}),
 ('def f(float[64] x)->float[64]{return sqrt(x);}float[64] x=-1;bit c=false && bool(f(x));',{'0':1}),
]
for source,expected in cases:
    try:
        original=adapt(compile(header+source));roundtrip=adapt(compile(original['source']))
        for exact in (True,False):
            for encoded in (original,roundtrip):execute(encoded,exact,expected)
    except Exception as error:raise AssertionError(source) from error
for source in [
 'def f(float x)->float{if(x>0){return x;}}float x=0;f(x);',
 'def f(angle[8] x)->angle[8]{}angle[8] x=0;f(x);',
 'def f(float x)->float{float y;return y;}float x=0;float y=f(x);',
 'def f(float x)->float{if(x>0){return x;}}int n=1;while(n>=0){float y=f(float(n));n-=1;}',
]:
    original=adapt(compile(header+source));roundtrip=adapt(compile(original['source']))
    for exact in (True,False):
        for encoded in (original,roundtrip):execute(encoded,exact,error='before initialization')
for source,message in [
 ('def f(float[16] x)->float[16]{return x;}float x=1;float y=f(x);','Use float32/64'),
 ('def f(float x)->float{return x;}qubit q;bit m=measure q;float y=f(float(int(m)));','Unsupported classical bit expression'),
]:
    try:compile(header+source)
    except (ValueError,NotImplementedError) as error:
        assert message.lower() in str(error).lower(),str(error);checks+=1
    else:raise AssertionError('Invalid numeric call accepted: '+source)
print(f'PASS: {checks} runtime numeric subroutine checks.')
