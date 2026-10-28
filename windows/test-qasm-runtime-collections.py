"""Finite runtime collection iteration regression checks."""
import argparse, base64, hashlib, copy, importlib.util, json, os, subprocess, sys, tempfile
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
 ('def f(qubit a){x a;}qubit[2] q;for int i in {0,1}{f(q[i]);}bit[2] c=measure q;',{'11':1}),
 ('bool yes=false;for bool b in {false,true,false}{yes=yes || b;}bit c=yes;',{'1':1}),
 ('int a=2;int total=0;for int i in {a,1,a}{total=total*10+i;}bit c=bool(total==212);',{'1':1}),
 ('int a=1;int total=0;for int i in {a,a}{a=9;total+=i;i=7;}bit c=bool(total==2);',{'1':1}),
 ('int total=0;for int i in {1,2,3,4}{if(i==2){continue;}if(i==4){break;}total+=i;}bit c=bool(total==4);',{'1':1}),
 ('float total=0;for float f in {0.5,1.5,2.0}{total+=f;}bit c=bool(total==4);',{'1':1}),
 ('angle[8] total=0;for angle[8] a in {angle[8]("11111111"),angle[8]("00000001")}{total+=a;}bit c=bool(total==angle[8]("00000000"));',{'1':1}),
 ('int i=9;int total=0;for int i in {1,2}{for int j in {1,2}{if(j==2){continue;}total+=i;}}bit c=bool(total==3 && i==9);',{'1':1}),
 ('def f(float x)->float{for float y in {x,2.0}{if(y>0){return y;}}return 0;}float x=3;float y=f(x);bit c=bool(y==3);',{'1':1}),
 ('qubit q;h q;bit m=measure q;int total=0;for int i in {int[2](bool(m)),1}{total+=i;}bit c=bool(total==2);',{'00':.5,'11':.5}),
]
for source,expected in cases:
    try:
        original=adapt(compile(header+source));roundtrip=adapt(compile(original['source']))
        for exact in (True,False):
            for encoded in (original,roundtrip):execute(encoded,exact,expected)
    except Exception as error:raise AssertionError(source) from error
source=header+'int total=0;for int i in {'+','.join(map(str,range(64)))+'}{total+=i;}bit c=bool(total==2016);'
original=adapt(compile(source));roundtrip=adapt(compile(original['source']))
for encoded in (original,roundtrip):execute(encoded,True,{'1':1})
try:compile(header+'for int i in {'+','.join(['1']*65)+'}{}')
except ValueError as error:assert 'at most 64 values' in str(error);checks+=1
else:raise AssertionError('Collection value limit not enforced')
# Snapshot evaluation is left-to-right, including nested calls and errors.
source=header+'def f(float x)->float{float y;return y;}float x=-1;for float i in {sqrt(x),f(x)}{}'
original=adapt(compile(source));roundtrip=adapt(compile(original['source']))
for exact in (True,False):
    for encoded in (original,roundtrip):execute(encoded,exact,error='must be finite')
fixture=json.loads((root/'fixtures/dev08-collection-upstream.json').read_text(encoding='utf-8'))
assert hashlib.sha256(fixture['source'].encode()).hexdigest()==fixture['sha256'];checks+=1
original=adapt(compile(fixture['source']));roundtrip=adapt(compile(original['source']))
# H on all four zero-state wires gives a uniform distribution; subsequent CNOT
# gates permute those amplitudes. Original terminal measurements are retained.
expected={format(value,'04b'):1/16 for value in range(16)}
for exact in (True,False):
    for encoded in (original,roundtrip):execute(encoded,exact,expected)
print(f'PASS: {checks} runtime collection checks.')
