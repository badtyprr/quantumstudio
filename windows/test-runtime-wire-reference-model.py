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
valid=preflight([target([2,0],variable),target([1,2],integer(0))])
d=copy.deepcopy(base);d['Steps']=[dict(Kind='StoreInteger',VariableSlot=0,IntegerValue=integer(1)),valid,dict(Kind='Gate',Expression='X',Wires=[0])]+[dict(Kind='Measure',Wires=[i],ClassicalBit=i) for i in range(3)]
roundtrip(d,'001')
for targets in ([target([0],integer(0))]*25,[target([2,0],integer(0)),target([1,2],integer(1))],[target([0,1],integer(-1))],[target([0],variable)]):
 d=copy.deepcopy(base);d['Steps']=[preflight(targets)];roundtrip(d,error=True)
d=copy.deepcopy(base);d['Steps']=[dict(Kind='Branch',Mask='1',Value='1',WhenTrue=[valid],WhenFalse=[])];roundtrip(d)
for version in (14,17):
 d=copy.deepcopy(base);d['Version']=version;d['Steps']=[valid];adapt(d,invalid=True)
for change in ('missing','empty','26','candidate','slot','body','expression','wires','type','extra'):
 d=copy.deepcopy(base);step=copy.deepcopy(valid);d['Steps']=[step]
 if change=='missing':del step['WireTargets']
 elif change=='empty':step['WireTargets']=[]
 elif change=='26':step['WireTargets']=[target([0],integer(0))]*26
 elif change=='candidate':step['WireTargets'][0]['Candidates']=[3]
 elif change=='slot':step['WireTargets'][0]['Index']['Slot']=2
 elif change=='body':step['WhenTrue']=[]
 elif change=='expression':step['Expression']='X'
 elif change=='wires':step['Wires']=[0]
 elif change=='type':step['WireTargets'][0]['Index']['Width']=32
 elif change=='extra':step['WireTargets'][0]['Unexpected']=True
 adapt(d,invalid=True)
# Shared expression budget includes all targets, even through separate roots.
large=integer(0)
for _ in range(7):large=dict(Kind='IntegerBinary',Operator='Add',Left=copy.deepcopy(large),Right=copy.deepcopy(large))
d=copy.deepcopy(base);d['Steps']=[preflight([target([0],large)]*3)];adapt(d,invalid=True,marker='512')
# Type/bounds validation survives an untaken branch, while value reads stay lazy.
d=copy.deepcopy(base);bad=copy.deepcopy(valid);bad['WireTargets'][0]['Index']['Slot']=99
d['Steps']=[dict(Kind='Branch',Mask='1',Value='1',WhenTrue=[bad],WhenFalse=[])];adapt(d,invalid=True)
for source in (
 'def c(qubit a,qubit b){}qubit[3] q;int i=1;c(q[i],q[2]);output bit r;r=0;',
 'def c(qubit a){}qubit[2] q;bit b=0;if(b==1){c(q[-1]);}output bit r;r=0;',
 'def c(qubit a){}qubit[3] q;let a=q[{2,0}];int i=1;c(a[i]);output bit r;r=0;',
 'def c(qubit a){}qubit[2] q;int i=0;for int j in [0:1]{c(q[i]);i+=1;}output bit r;r=0;',
):roundtrip(compile_source('OPENQASM 3.0;'+source),'0')
for source in (
 'def c(qubit a){}qubit[2] q;c(q);',
 'def c(qubit a){}qubit[2] q;float i=0.5;c(q[i]);',
 'def c(qubit a){}qubit[2] q;c(q[true]);',
):
 try:compile_source('OPENQASM 3.0;'+source)
 except (ValueError,ValidationError):checks+=1
 else:raise AssertionError('Accepted invalid quantum actual: '+source)
print('PASS: %d wire reference model/source checks.'%checks)
