"""Authored runtime-wire import/save/export/execution and error regressions."""
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
 ('qubit[3] q;int i=0;x q[i];i=2;x q[i];bit[3] c=measure q;',{'101':1}),
 ('qubit[3] q;int n=2;for int i in [0:n] {x q[i];}bit[3] c=measure q;',{'111':1}),
 ('qubit[3] q;let a=q[{2,0}];int i=0;x a[i];i=1;x a[i];bit[3] c=measure q;',{'101':1}),
 ('qubit[4] q;let a=q[3:-2:0];int i=1;x a[i];bit[4] c=measure q;',{'0010':1}),
 ('qubit s;qubit[2] q;h s;bit m=measure s;int i=int(m);x q[i];bit[2] c=measure q;',{'010':.5,'101':.5}),
 ('qubit[2] q;x q[1];bit m=1;int i=int(m);m=measure q[i];bit c=m;',{'11':1}),
 ('qubit[2] q;h q[0];cx q[0],q[1];int i=1;reset q[i];bit[2] c=measure q;',{'00':.5,'01':.5}),
 ('qubit[2] q;int i=1;float f=1;ry(pi*f) q[i];bit[2] c=measure q;',{'10':1}),
 ('qubit[2] q;int i=0;int j=1;x q[i];ctrl @ ry(pi) q[i],q[j];bit[2] c=measure q;',{'11':1}),
 ('qubit[2] s;qubit[2] q;int i=1;x s[i];cx s[i],q;bit[2] c=measure q;',{'11':1}),
 ('qubit[2] q;int i;bit b=0;if(b==1){x q[i];}bit[2] c=measure q;',{'000':1}),
 ('qubit[2] q;int i=1;if(true){int i=0;x q[i];}x q[i];bit[2] c=measure q;',{'11':1}),
]
for source,expected in cases:
    try:
        model=compile(header+source);assert model['Version']==14
        original=adapt(model);roundtrip=adapt(compile(original['source']))
        for exact in (True,False):
            for encoded in (original,roundtrip):execute(encoded,exact,expected)
    except Exception as error:raise AssertionError(source) from error

for source,message in [
 ('int i=-1;qubit[2] q;x q[i];','Wire index is outside'),
 ('int i=2;qubit[2] q;x q[i];','Wire index is outside'),
 ('uint[64] i=18446744073709551615;qubit[2] q;x q[i];','Wire index is outside'),
 ('int i;qubit[2] q;x q[i];','Wire index:'),
 ('int i=1;int j=1;qubit[2] q;cx q[i],q[j];','wires must be distinct'),
 ('int i=1;qubit[2] q;let a=q[{1,0}];cx a[i],q[0];','wires must be distinct'),
 ('int i=2;qubit[2] q;pow(0) @ x q[i];','Wire index is outside'),
 ('int i=0;qubit[2] q;x q[1/i];','Wire index:'),
 ('int i=0;qubit[2] q;cx q[i],q;','wires must be distinct'),
]:
    try:
        original=adapt(compile(header+source));roundtrip=adapt(compile(original['source']))
        for exact in (True,False):
            for encoded in (original,roundtrip):execute(encoded,exact,error=message)
    except Exception as error:raise AssertionError(source) from error

for source in ['float i=1.5;qubit[2] q;x q[i];','bool i=true;qubit[2] q;x q[i];',
               'int i=1;qubit[2] q;x q[0:i];','int i=1;qubit[2] q;bit[2] b;b[i]=measure q[0];']:
    try:compile(header+source)
    except (ValueError,NotImplementedError):checks+=1
    else:raise AssertionError('Unsupported index accepted: '+source)

# Valid saved models need not contain the importer's separate preflight step.
# A selected scalar phase must retain target errors even though gphase has no target.
for index in (0,2):
    model=compile(header+f'qubit[2] q;int i={index};x q[i];')
    step=next(n for n in model['Steps'] if 'WireTargets' in n)
    step['Expression']='(exp(i*(1))*I)'
    model['Steps']=[n for n in model['Steps'] if 'WireTargets' not in n]+[step]
    original=adapt(model);roundtrip=adapt(compile(original['source']))
    for exact in (True,False):
        for encoded in (original,roundtrip):execute(encoded,exact,{'':1},'Wire index is outside' if index==2 else None)

# A decomposed interaction uses the second operand first; its exported preflight
# must still report the first operand's bounds error before the undefined second.
model=compile(header+'qubit[2] q;int i=2;int j;cx q[i],q[j];')
step=next(n for n in model['Steps'] if 'WireTargets' in n)
step['Expression']='XXMinusYY(0.5,0.2)'
model['Steps']=[n for n in model['Steps'] if 'WireTargets' not in n]+[step]
original=adapt(model);roundtrip=adapt(compile(original['source']))
for exact in (True,False):
    for encoded in (original,roundtrip):execute(encoded,exact,error='Wire index is outside')

# Raw JSON cannot bypass the operation/arity/schema checks, even in an untaken body.
model=compile(header+'qubit[2] q;int i=0;x q[i];bit[2] c=measure q;')
selected=next(n for n in model['Steps'] if 'WireTargets' in n)
for mutate in [lambda m,s:m.update(Version=13),lambda m,s:s.update(WireSource='x'*513),
               lambda m,s:s.update(WireTargets=[]),lambda m,s:s.update(Wires=[1]),
               lambda m,s:s['WireTargets'][0].update(Candidates=[2]),
               lambda m,s:s['WireTargets'][0].update(Candidates=[True]),
               lambda m,s:s['WireTargets'][0].update(Unknown=1),
               lambda m,s:s.update(Kind='Reset',Expression=None,Wires=[0,1])]:
    changed=copy.deepcopy(model);step=next(n for n in changed['Steps'] if 'WireTargets' in n);mutate(changed,step);adapt(changed,False)

# Runtime diagnostics retain an included file's original line after compilation.
with tempfile.TemporaryDirectory(prefix='wire source ') as folder:
    path=Path(folder);(path/'main.qasm').write_text('OPENQASM 3; include "stdgates.inc"; include "nested.inc";',encoding='utf-8')
    (path/'nested.inc').write_text('qubit[2] q;\nint i=3;\nx q[i];\n',encoding='utf-8')
    for command in [[sys.executable,str(root/'qasm-import.py')]]+([[str(args.frozen.resolve())]] if args.frozen else []):
        p=subprocess.run(command+['--classical','--source-file',str(path/'main.qasm')],capture_output=True,timeout=30)
        assert p.returncode==0,p.stderr
        result=json.loads(p.stdout);circuit=result['Circuit'] if 'Circuit' in result else result
        if isinstance(circuit,str):circuit=json.loads(circuit)
        encoded=adapt(circuit)
        for exact in (True,False):execute(encoded,exact,error='nested.inc:3:1: Wire index is outside')
print(f'PASS: {checks} runtime wire import/model/export checks.')
