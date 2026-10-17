"""Source/frozen classical import equivalence and optional worker outcome checks."""
import argparse,importlib.util,json,os,subprocess,sys
from fractions import Fraction
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
spec=importlib.util.spec_from_file_location('qasm_expression_adapter',root/'windows/qasm-import.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; '
cases=[
 ('copy','qubit q; bit a; bit b; x q; a=measure q; b=a; a=0;',{'10':'1'}),
 ('overlap','qubit q; bit[3] c="001"; c[1:2]=c[0:1];',{'011':'1'}),
 ('initializer','qubit q; bit c=1; if(c) x q; c=measure q;',{'1':'1'}),
 ('loop','qubit q; bit[3] c; for int i in [0:2] {c[i]=1;}',{'111':'1'}),
 ('compound','qubit q; bit[4] c="1010"; c^="0011"; c<<=1;',{'0010':'1'}),
 ('reverse','qubit q; bit[3] c="001"; c[0:2]=c[2:-1:0];',{'100':'1'}),
 ('bit63','qubit q; bit[64] c; c[63]=1;',{'1'+'0'*63:'1'}),
 ('parity','qubit[3] q; bit[3] c; h q[0]; h q[1]; c[0]=measure q[0]; c[1]=measure q[1]; if(c[0]^c[1]) x q[2]; c[2]=measure q[2];',dict.fromkeys(['000','011','101','110'],'1/4')),
 ('branch-once','qubit q; bit c=1; if(c){c=0; x q;} c=measure q;',{'1':'1'}),
 ('comparison','qubit q; bit[2] c="10"; bit d; if(c>1 && c!=3) {d=1;}',{'110':'1'}),
 ('registers','qubit q; bit[2] c="10"; bit[2] d="10"; if(c==d){c=0;}',{'1000':'1'}),
]
checks=0
hooks=tuple(getattr(adapter.QasmVisitor,name) for name in ['_visit_classical_assignment','_visit_classical_declaration','_visit_branching_statement'])
rejected=['qubit q; bit c=2;', 'qubit q; bit[2] c; c="1";',
          'qubit q; bit[2] c; c[0]=c[2];', 'qubit q; bit[3] c; c[0:2]=c[0:1];',
          'qubit q; bit c=1; while(c==1){c=0;}',
          'qubit q; bit c; c=measure q; rx(float(c)) q;',
          'qubit[2] q; bit c=1; x q[c];',
          'qubit[2] q; bit c=1; c=measure q[c];',
          'qubit q; bit[2] c; bit d=1; c[d]=measure q;',
          'qubit q; bit[2] c; let d=c; d=1;',
          'qubit q; bit c; c+=1;', 'qubit q; bit[2] c; if(c>4) x q;']
for body in rejected:
 try:adapter.convert(header+body,classical=True)
 except Exception:checks+=1
 else:raise AssertionError('Unsupported or invalid source was accepted: '+body)
 assert tuple(getattr(adapter.QasmVisitor,name) for name in ['_visit_classical_assignment','_visit_classical_declaration','_visit_branching_statement'])==hooks
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=(header+body).encode(),capture_output=True,timeout=30)
  assert result.returncode!=0 and result.stderr and not result.stdout,(body,result.stdout);checks+=1
def n(*v):return ''.join(str(x)+'\n' for x in v).encode()
ops=['And','Or','Xor','ShiftLeft','ShiftRight','Equal','NotEqual','Less','LessEqual','Greater','GreaterEqual']
def expression(e):
 k=e['Kind']
 if k=='Constant':return n(0,e['Width'],e['Value'])
 if k=='Read':return n(1,len(e['Bits']),*e['Bits'])
 if k=='Complement':return n(2)+expression(e['Left'])
 return n(3,ops.index(e['Operator']))+expression(e['Left'])+expression(e['Right'])
def steps(body):
 out=b''
 for s in body:
  kind=s['Kind']
  if kind=='Assign':out+=n(7,len(s['Wires']),*s['Wires'])+expression(s['ClassicalValue'])
  elif kind in ('Branch','ExpressionBranch'):
   out+=(n(6,s['Mask'],s['Value']) if kind=='Branch' else n(8)+expression(s['ClassicalValue']))
   for key in ['WhenTrue','WhenFalse']:out+=n(len(s[key]))+steps(s[key])
  elif kind=='Measure':out+=n(1,s['Wires'][0],s['ClassicalBit'])
  else:
   assert kind=='Gate';matrix=s['Expression'].encode();out+=n(0,len(s['Wires']),*s['Wires'],len(matrix))+matrix
 return out
for name,body,expected in cases:
 source=header+body;circuit=adapter.convert(source,classical=True)
 assert circuit['Version']==3,(name,circuit)
 # The overlap case must retain a simultaneous read of both old source bits.
 if name=='overlap':assert circuit['Steps'][1]=={'Kind':'Assign','Wires':[1,2],'ClassicalValue':{'Kind':'Read','Bits':[0,1]}}
 checks+=1
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert result.returncode==0 and json.loads(result.stdout)==circuit,(name,result.stderr);checks+=1
 if a.worker:
  worker=a.worker.resolve();bits=sum(r['Size'] for r in circuit['Registers']);output=circuit['OutputBits']
  for exact in (True,False):
   payload=(b'QEXACT2\n' if exact else b'QSAMPLE3\n')+n(circuit['Qubits'])+(b'' if exact else n(10000,1731))+n(bits,len(output),*output,len(circuit['Steps']))+steps(circuit['Steps'])
   run=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30,env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data')))
   assert run.returncode==0 and not run.stderr,(name,run.stderr);value=json.loads(run.stdout)
   if exact:assert {k:Fraction(v) for k,v in value['probabilities'].items()}=={k:Fraction(v) for k,v in expected.items()},(name,value)
   else:
    actual=value['counts'];assert set(actual)==set(expected) and sum(actual.values())==10000,(name,value)
    for k,v in expected.items():assert abs(actual[k]/10000-float(Fraction(v)))<.04,(name,value)
   checks+=1
print('PASS: '+str(checks)+' classical expression import checks.')
