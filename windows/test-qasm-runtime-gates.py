"""Runtime gates: import, saved model, export and both engines against analytic results."""
import argparse, base64, importlib.util, json, math, os, subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--adapter',type=Path,required=True)
parser.add_argument('--worker',type=Path)
parser.add_argument('--frozen',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_gates',root/'qasm-import.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
header='OPENQASM 3; include "stdgates.inc"; '
checks=0
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data')) if args.worker else os.environ

def compile(source,published=False):
    global checks
    result=compiler.convert(source,classical=True,published_u=published)
    if args.frozen:
        command=[str(args.frozen.resolve()),'--classical']+(['--published-u'] if published else [])
        frozen=subprocess.run(command,input=source.encode(),capture_output=True,timeout=30)
        assert frozen.returncode==0,frozen.stderr.decode()
        assert json.loads(frozen.stdout)==result
        checks+=1
    return result

def bridge(circuit):
    result=subprocess.run([str(args.adapter.resolve())],input=json.dumps(circuit).encode(),capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr.decode()
    return json.loads(result.stdout.decode('utf-8-sig'))

def execute(payloads,expected):
    global checks
    if not args.worker:return
    for exact in (True,False):
        payload=base64.b64decode(payloads['exact' if exact else 'sampled'])
        result=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,env=env,timeout=30)
        assert result.returncode==0,result.stderr.decode()
        data=json.loads(result.stdout)
        if exact:
            actual={}
            for key,value in data['probabilities'].items():
                result=subprocess.run([str(args.worker.resolve()),'--json','--approx'],input=value.encode(),capture_output=True,env=env,timeout=30)
                assert result.returncode==0,result.stderr.decode()
                actual[key]=float(json.loads(result.stdout)['text'].replace('\u2212','-'))
        else:actual={key:value/10000 for key,value in data['counts'].items()}
        tolerance=1e-10 if exact else .025
        assert all(abs(actual.get(key,0)-expected.get(key,0))<tolerance for key in set(actual)|set(expected)),(actual,expected,exact)
        checks+=1

cases=[
 ('int n=1; qubit q; h q; p(pi*n) q; h q; bit c=measure q;',{'1':1}),
 ('int n=1; qubit[2] q; h q[0]; x q[1]; ctrl @ p(pi*n) q[0],q[1]; h q[0]; bit c=measure q[0];',{'1':1}),
 ('int n=1; qubit q; h q; ctrl @ gphase(pi*n) q; h q; bit c=measure q;',{'1':1}),
 ('int n=1; qubit q; gphase(n); bit c=measure q;',{'0':1}),
 ('int n=1; qubit q; inv @ ry(pi*n) q; bit c=measure q;',{'1':1}),
 ('int n=2; qubit q; pow(n) @ ry(pi/2) q; bit c=measure q;',{'1':1}),
 ('int n=1; qubit[2] q; negctrl @ ry(pi*n) q[0],q[1]; bit c=measure q[1];',{'1':1}),
 ('int n=1; qubit[3] q; x q[0]; ctrl @ negctrl @ ry(pi*n) q[0],q[1],q[2]; bit c=measure q[2];',{'1':1}),
 ('int n=1; qubit[2] q; p(pi*n) q; bit[2] c=measure q;',{'00':1}),
 ('int n=1; qubit control; qubit[2] target; x control; ctrl @ ry(pi*n) control,target; bit[2] c=measure target;',{'11':1}),
 ('int n=1; qubit[2] q; x q[1]; crx(pi*n) q[1],q[0]; bit[2] c=measure q;',{'11':1}),
 ('qubit[2] q; h q[0]; bit c=measure q[0]; u3(pi*uint[1](c),.3,.7) q[1]; bit d=measure q[1];',{'00':.5,'11':.5}),
 ('int n=1; qubit q; u3(float(n),.3,.7) q; bit c=measure q;',{'0':math.cos(.5)**2,'1':math.sin(.5)**2}),
 ('int n=1; qubit q; u3(float(n),.3,.7) q; inv @ u3(float(n),.3,.7) q; bit c=measure q;',{'0':1}),
 ('def f(int x,qubit q){p(pi*x) q;return;} int n=0; qubit q; h q; f(n,q); n=1; f(n,q); h q; bit c=measure q;',{'1':1}),
 ('int n=1; qubit[2] q; h q[0]; ctrl @ u3(float(n),.3,.7) q[0],q[1]; h q[0]; bit c=measure q[0];',{'0':(1+math.cos(.5))/2,'1':(1-math.cos(.5))/2}),
]
for source,expected in cases:
    circuit=compile(header+source)
    assert circuit['Version']==12,circuit
    original=bridge(circuit)
    try:
        execute(original,expected)
        imported=compile(original['source'])
        execute(bridge(imported),expected)
    except Exception as error:raise AssertionError(source) from error
    checks+=2

# Published U contributes a phase relative to the inactive control branch.
source='int n=1; qubit[2] q; h q[0]; ctrl @ U(float(n),.3,.7) q[0],q[1]; h q[0]; bit c=measure q[0];'
expected={'0':(1+math.cos(.5)**2)/2,'1':(1-math.cos(.5)**2)/2}
original=bridge(compile(header+source,True))
execute(original,expected)
for published in (True,False):
    execute(bridge(compile(original['source'],published)),expected)

if args.worker:
    for source,message in (
        ('int missing; int zero=0; qubit q; pow(1/zero) @ U(1.0,float(missing),0) q;', 'Integer variable read before initialization'),
        ('int missing; qubit q; pow(0) @ U(1.0,0,float(missing)) q;', 'Integer variable read before initialization'),
        ('int zero=0; qubit q; pow(1/zero) @ U(1.0,.3,.7) q;', 'Integer division by zero'),
    ):
        original=bridge(compile(header+source,True))
        restored=bridge(compile(original['source']))
        for payloads in (original,restored):
            for exact in (True,False):
                result=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(payloads['exact' if exact else 'sampled']),capture_output=True,env=env,timeout=30)
                assert result.returncode!=0 and not result.stdout and message in result.stderr.decode(),result.stderr
                checks+=1

for source in (
 'int n=1; qubit[2] q; ctrl @ p(n) q[0],q[0];',
 'int n=1; qubit[4] q; ctrl(3) @ p(n) q[0],q[1],q[2],q[3];',
 'int n=1; qubit q; ctrl(n) @ p(n) q;',
 'int n=1; qubit[2] a; qubit[3] b; ctrl @ p(n) a,b;',
 'int n=1; qubit q; u3(n,1) q;',
 'gate p(a) q {rx(a) q;} int n=1; qubit q; p(n) q;',
):
    try:compiler.convert(header+source,classical=True)
    except Exception:checks+=1
    else:raise AssertionError('Invalid gate accepted: '+source)
print(f'PASS: {checks} runtime gate import checks.')
