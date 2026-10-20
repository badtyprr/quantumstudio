"""Preserve runtime rotation expressions instead of compiler initial values."""
import argparse,base64,importlib.util,json,math,os,struct,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--frozen',type=Path);parser.add_argument('--adapter',type=Path);parser.add_argument('--worker',type=Path)
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('runtime_angles',root/'qasm-import.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; '
checks=0
def compile(source):
 global checks
 result=adapter.convert(header+source,classical=True);checks+=1
 if args.frozen:
  p=subprocess.run([str(args.frozen.resolve()),'--classical'],input=(header+source).encode(),capture_output=True,timeout=30)
  assert p.returncode==0,(source,p.stderr)
  assert json.loads(p.stdout)==result,(source,p.stdout,result)
  checks+=1
 assert result['Version']==11 and 'Variables' in result and 'LoopConditionBudget' in result,result
 return result
def rotations(circuit):
 result=[]
 def visit(steps):
  for step in steps:
   if step['Kind']=='Rotation':result.append(step)
   visit(step.get('WhenTrue',[]));visit(step.get('WhenFalse',[]))
 visit(circuit['Steps']);return result
for gate in ('rx','ry','rz'):
 result=compile('qubit[2] q;h q[0];bit c=measure q[0];'+gate+'(pi*uint[1](c)) q[1];bit d=measure q[1];')
 rotation=rotations(result)[0];assert rotation['Axis']==gate[-1].upper() and rotation['Wires']==[1]
 assert rotation['Angle']['Kind']=='Binary' and rotation['Angle']['Right']['Kind']=='Integer'
for source in ('int n=1;qubit q;ry(pi*n) q;n=0;ry(pi*n) q;',
 'int n=2;qubit q;for int i in [0:n]{rx(i) q;}',
 'qubit q;h q;bit c=measure q;if(c){int n=1;rz(pi*n) q;}',
 'int n=1;qubit[2] q;ry(pi*n) q;',
 'int n=1;qubit q;while(n>0){ry(pi*n) q;n=0;}'):
 assert rotations(compile(source))
for expression,kind in (('n/2','Integer'),('float[64](n)/2','Binary'),('n/2.0','Binary'),('-float[64](n)','Binary')):
 angle=rotations(compile('int n=1;qubit q;ry('+expression+') q;'))[0]['Angle']
 assert angle['Kind']==kind,(expression,angle)
# Mutation and repeated compilations must not retain a previous visitor hook/state.
for _ in range(3):
 result=compile('int n=1;qubit q;ry(n) q;n=2;ry(n) q;')
 r=rotations(result);assert len(r)==2 and r[0]['Angle']==r[1]['Angle']
for source in ('int n=1;qubit q;inv @ ry(n) q;',
 'int n=1;qubit q;p(n) q;',
 'int n=1;qubit q;gphase(n);',
 'int n=1;qubit q;ry(float[32](n)) q;',
 'int n=1;qubit q;ry(sin(n)) q;'):
 try:adapter.convert(header+source,classical=True)
 except Exception:checks+=1
 else:raise AssertionError('Unsupported runtime angle accepted: '+source)
if args.adapter:
 for source,expected in (
  ('qubit[2] q;h q[0];bit c=measure q[0];ry(pi*uint[1](c)) q[1];bit d=measure q[1];',{'00':.5,'11':.5}),
  ('int n=1;qubit q;ry(n/2) q;bit c=measure q;',{'0':1}),
  ('int n=1;qubit q;ry(float[64](n)/2) q;bit c=measure q;',{'0':math.cos(.25)**2,'1':math.sin(.25)**2}),
  ('int n=0;qubit q;ry(pi*n) q;n=1;ry(pi*n) q;bit c=measure q;',{'1':1}),
  ('int n=1;qubit[2] q;ry(pi*n) q;bit[2] c=measure q;',{'11':1}),
 ):
  circuit=compile(source)
  p=subprocess.run([str(args.adapter.resolve())],input=json.dumps(circuit).encode(),capture_output=True,timeout=30)
  assert p.returncode==0,(source,p.stderr);payloads=json.loads(p.stdout.decode('utf-8-sig'));checks+=1
  for exact in (True,False):
   payload=base64.b64decode(payloads['exact' if exact else 'sampled'])
   assert payload.startswith(b'QEXACT10\n' if exact else b'QSAMPLE11\n')
   if not args.worker:continue
   env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data'))
   p=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30,env=env)
   assert p.returncode==0,(source,p.stderr);result=json.loads(p.stdout)
   if exact:
    actual={}
    for key,value in result['probabilities'].items():
     p=subprocess.run([str(args.worker.resolve()),'--json','--approx'],input=value.encode(),capture_output=True,timeout=30,env=env)
     assert p.returncode==0,p.stderr
     actual[key]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
   else:actual={key:value/10000 for key,value in result['counts'].items()}
   tolerance=1e-10 if exact else .02
   assert all(abs(actual.get(k,0)-expected.get(k,0))<tolerance for k in set(actual)|set(expected)),(source,exact,actual,expected)
   checks+=1
print(f'PASS: {checks} runtime angle import checks.')
