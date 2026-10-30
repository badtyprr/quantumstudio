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
for source,expected in (
 ('def f(qubit[2] a)->bit[2]{return measure a;}qubit[3] q;x q[2];int start=1;output bit[2] r;r=f(q[start:start+1]);','10'),
 ('def f(qubit[2] a)->bool{return true;}qubit[3] q;bool ok=f(q[0:1]);output bit r;r=ok;','1'),
 ('def f(qubit[2] a)->bool{return true;}qubit[2] q;let b=q;bool ok=f(b);output bit r;r=ok;','1'),
 ('def f(qubit a){x a;}def g(qubit[2] a,int i){f(a[i]);}qubit[3] q;int start=1;int i=0;g(q[start:start+1],i);output bit[3] r;r=measure q;','010'),
 ('def f(qubit[2] a,int i){x a[i];}def g(qubit[2] a,int i){f(a,i);}qubit[3] q;int start=1;int i=0;g(q[start:start+1],i);output bit[3] r;r=measure q;','010'),
 ('def mutate(mutable array[int,1] a)->int{a[0]=0;return 0;}def f(qubit[2] a,int i){x a[i];}qubit[3] q;array[int,1] a={1};f(q[a[0]:a[0]+1],mutate(a));output bit[3] r;r=measure q;','010'),
 ('def f(qubit[2] a,int i){x a[i];}qubit[3] q;int start=1;int i=0;f(q[start:start+1],i);output bit[3] r;r=measure q;','010'),
 ('def f(qubit[2] a,int i){x a;}qubit[3] q;int start=1;int i=0;f(q[start:start+1],i);output bit[3] r;r=measure q;','110'),
 ('def f(qubit[2] a,int i){x a[i];}qubit[3] q;let a=q[{2,0}];int i=1;f(a,i);output bit[3] r;r=measure q;','001'),
 ('def f(qubit[2] a,int i){x a[i];}qubit[3] q;int i=1;f(q[1:2],i);output bit[3] r;r=measure q;','100'),
 ('def f(qubit[2] a,int i){x a[i];}def g(qubit[2] a,int i){f(a,i);}qubit[3] q;int i=1;g(q[{2,0}],i);output bit[3] r;r=measure q;','001'),
):roundtrip(compile_source('OPENQASM 3.0;include "stdgates.inc";'+source),expected)
for source in (
 'def f(qubit[2] a,int i){x a[i];}qubit[3] q;int start=1;int i=-1;f(q[start:start+1],i);output bit r;r=0;',
 'def f(qubit[2] a,int i){x a[i];}qubit[3] q;int start=1;int i=2;f(q[start:start+1],i);output bit r;r=0;',
 'def f(qubit[2] a,int i){x a;}qubit[3] q;int start=-1;int i=0;f(q[start:start+1],i);output bit r;r=0;',
 'def f(qubit[2] a,int i){x a;}qubit[3] q;int stop=2;int i=0;f(q[0:stop],i);output bit r;r=0;',
 'def f(qubit[2] a,qubit[2] b,int i){x a;}qubit[3] q;int start=1;int i=0;f(q[0:start],q[start:start+1],i);output bit r;r=0;',
):roundtrip(compile_source('OPENQASM 3.0;include "stdgates.inc";'+source),'0',error=True)
for source in (
 'def f(qubit[2] a,int i){x a;}qubit[3] q;int i=0;f(q[true:2],i);',
 'def f(qubit[2] a,int i){x a;}qubit[3] q;bool step=true;int i=0;f(q[1:step:2],i);',
 'def f(qubit[2] a,int i){x a[true];}qubit[3] q;int start=1;f(q[start:start+1],0);',
 'def f(qubit[2] a,int i){x a[0.5];}qubit[3] q;int start=1;if(false){f(q[start:start+1],0);}',
):
 try:compile_source('OPENQASM 3.0;include "stdgates.inc";'+source)
 except (ValueError,ValidationError):checks+=1
 else:raise AssertionError('Accepted invalid formal selector: '+source)
# Validate a range prefix before evaluating a later selector call.
source='OPENQASM 3.0;include "stdgates.inc";def fail(int z)->int{return 1/z;}def f(qubit[2] a){x a;}qubit[3] q;int start=9;f(q[start:fail(0)]);output bit r;r=0;'
encoded=adapt(compile_source(source))
if args.worker:
 for exact in (True,False):
  result=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(encoded['exact' if exact else 'sampled']),capture_output=True,env=env,timeout=45)
  assert result.returncode and not result.stdout and b'zero' not in result.stderr.lower(),result.stderr
  checks+=1
print('PASS: %d quantum register view checks.'%checks)
