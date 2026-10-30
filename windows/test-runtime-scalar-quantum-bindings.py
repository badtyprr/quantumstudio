"""Wire preflight save/load, source helpers, export and both engines."""
import argparse,base64,copy,importlib.util,json,os,subprocess
from pathlib import Path
from pyqasm.exceptions import ValidationError
p=argparse.ArgumentParser();p.add_argument('--adapter',type=Path,required=True);p.add_argument('--worker',type=Path);p.add_argument('--frozen',type=Path);args=p.parse_args()
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wire_reference_import',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
checks=0
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data')) if args.worker else os.environ
def integer(value):return dict(Kind='IntegerConstant',Signedness='Signed',Width=0,Value=str(value&((1<<64)-1)))
def target(candidates,index):return dict(Candidates=candidates,Index=index)
def preflight(targets):return dict(Kind='CheckWireReferences',WireTargets=targets,WireSource='model.qasm:4:2')
base=dict(Version=18,Qubits=3,Registers=[dict(Name='c',Size=3)],OutputBits=[2,1,0],Variables=[dict(Name='i',Signedness='Signed',Width=0)],NumericVariables=[],Arrays=[],LoopConditionBudget=1000000,Steps=[])
variable=dict(Kind='IntegerVariable',Signedness='Signed',Width=0,Slot=0)
def adapt(document,invalid=False,marker=None):
 global checks
 result=subprocess.run([str(args.adapter.resolve())],input=json.dumps(document).encode(),capture_output=True,timeout=30);checks+=1
 if invalid:
  assert result.returncode and not result.stdout,result.stdout
  if marker:assert marker.encode() in result.stderr,result.stderr
  return
 assert result.returncode==0,result.stderr
 return json.loads(result.stdout)
def compile_source(source):
 global checks
 document=compiler.convert(source,classical=True);checks+=1
 if args.frozen:
  result=subprocess.run([str(args.frozen.resolve()),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert result.returncode==0,result.stderr
  assert json.loads(result.stdout)==document;checks+=1
 return document
def execute(encoded,expected='000',error=False):
 global checks
 if not args.worker:return
 for exact in (True,False):
  result=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(encoded['exact' if exact else 'sampled']),capture_output=True,env=env,timeout=45);checks+=1
  if error:
   assert result.returncode and not result.stdout,result.stdout
   continue
  assert result.returncode==0,result.stderr
  values=json.loads(result.stdout)['probabilities' if exact else 'counts']
  assert values=={expected:'1' if exact else 10000},values
def roundtrip(document,expected='000',error=False):
 encoded=adapt(document);execute(encoded,expected,error)
 reimported=adapt(compile_source(encoded['source']));execute(reimported,expected,error)
 return encoded
# Each fixture observes the physical wire after binding, including nested forwarding.
for source,expected in (
 ('def f(qubit a)->bool{x a;return true;}qubit[2] q;for int i in [0:1]{bool ok=f(q[i+0]);}output bit[2] r;r=measure q;', '11'),
 ('def f(qubit a){x a;}qubit[3] q;int i=1;f(q[i]);output bit[3] r;r=measure q;', '010'),
 ('def f(qubit a){x a;}def g(qubit a){f(a);}qubit[3] q;int i=2;g(q[i]);output bit[3] r;r=measure q;', '100'),
 ('def f(qubit a){x a;}qubit[3] q;let a=q[{2,0}];int i=1;f(a[i]);output bit[3] r;r=measure q;', '001'),
 ('def f(qubit a,int n){x a;}def mutate(mutable array[int,1] a)->int{a[0]=1;return 0;}qubit[2] q;array[int,1] a={0};f(q[a[0]],mutate(a));output bit[2] r;r=measure q;', '01'),
 ('def f(qubit a){x a;}qubit[2] q;for int i in [0:1]{f(q[i]);}output bit[2] r;r=measure q;', '11'),
 ('def f(qubit a,qubit[2] b){x a;x b;}qubit[3] q;qubit[2] p;int i=2;f(q[i],p);output bit[3] r;r[0]=measure q[2];r[1]=measure p[0];r[2]=measure p[1];','111'),
):
 roundtrip(compile_source('OPENQASM 3.0;include "stdgates.inc";'+source),expected)
for source in (
 'def f(qubit a,qubit b){x a;}qubit[2] q;int i=1;f(q[i],q[1]);output bit r;r=0;',
 'def f(qubit a,qubit[2] b){x a;}qubit[2] q;int i=1;f(q[i],q);output bit r;r=0;',
 'def f(qubit a){x a;}qubit[2] q;int i=-1;f(q[i]);output bit r;r=0;',
):roundtrip(compile_source('OPENQASM 3.0;include "stdgates.inc";'+source),'0',error=True)
# A bad first selector must win over a later actual's arithmetic failure.
source='OPENQASM 3.0;include "stdgates.inc";def fail(int z)->int{return 1/z;}def f(qubit a,int n){x a;}qubit[2] q;int i=2;f(q[i],fail(0));output bit r;r=0;'
encoded=adapt(compile_source(source))
if args.worker:
 for exact in (True,False):
  result=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(encoded['exact' if exact else 'sampled']),capture_output=True,env=env,timeout=45)
  assert result.returncode and not result.stdout and b'zero' not in result.stderr.lower(),result.stderr
  assert b'wire' in result.stderr.lower() or b'qubit' in result.stderr.lower(),result.stderr
  checks+=1
for source in (
 'def f(qubit a,int n){x a;}qubit[2] q;int n=1;f(q[0.5],n);',
 'def f(qubit a,int n){x a;}qubit[2] q;int n=1;if(false){f(q[true],n);}',
):
 try:compile_source('OPENQASM 3.0;include "stdgates.inc";'+source)
 except (ValueError,ValidationError):checks+=1
 else:raise AssertionError('Accepted invalid selector: '+source)
print('PASS: %d scalar quantum binding checks.'%checks)
