"""Source/frozen classical import equivalence and optional worker outcome checks."""
import argparse,importlib.util,json,os,subprocess,sys
from fractions import Fraction
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
spec=importlib.util.spec_from_file_location('qasm_expression_adapter',root/'windows/qasm-import.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; '
cases=[
 ('typed-power','bit[3] c=2; bit r; if(int[3](c)**3==8){r=1;}',{'1010':'1'}),
 ('typed-power-right','bit[3] c=2; bit r; if(int[3](c)**3**2==512){r=1;}',{'1010':'1'}),
 ('typed-power-left','bit[3] c=2; bit r; if((int[3](c)**3)**2==64){r=1;}',{'1010':'1'}),
 ('typed-power-unary','bit[3] c=2; bit r; if(-int[3](c)**2 == -4){r=1;}',{'1010':'1'}),
 ('typed-power-negative-base','bit[3] c=2; bit r; if((-int[3](c))**2 == 4){r=1;}',{'1010':'1'}),
 ('typed-power-runtime-exponent','bit[3] c=3; bit r; if(2**int[3](c)==8){r=1;}',{'1011':'1'}),
 ('typed-power-negative-exponent','bit[3] c=7; bit r; if(2**int[3](c)==0){r=1;}',None),
 ('typed-power-overflow','bit[8] c=63; bit r; if(2**int[8](c)==0){r=1;}',None),
 ('typed-power-guard','bit[3] c=7; bit r; if(false && 2**int[3](c)==0){r=1;}',{'0111':'1'}),
 ('typed-power-wrap','bit[64] c=2; c=bit[64](uint[64](uint[64](c)**64));',{'0'*64:'1'}),
 ('typed-power-measure','qubit q; bit c; bit r; h q; c=measure q; if(2**uint[1](c)==2){r=1;}',{'00':'1/2','11':'1/2'}),
 ('classical-only-initializer','bit c=1;',{'1':'1'}),
 ('classical-only-overlap','bit[3] c="001"; c[1:2]=c[0:1];',{'011':'1'}),
 ('classical-only-functions','bit[3] c="101"; if(popcount(c)==2){c=rotl(c,1);}',{'011':'1'}),
 ('static-cast','qubit q; bit[3] c; c=int[3](1);',{'001':'1'}),
 ('literal-signed-cast','qubit q; bit[3] c; c=rotl("001",int[3]("111"));',{'100':'1'}),
 ('rotate-left','qubit q; bit[3] c="001"; c=rotl(c,1);',{'010':'1'}),
 ('rotate-negative','qubit q; bit[3] c="001"; c=rotr(c,-1);',{'010':'1'}),
 ('rotate-cast','qubit q; bit[3] c="111"; c=rotl("001",int[3](c));',{'100':'1'}),
 ('rotate-unsigned','qubit q; bit[3] c="111"; c=rotl("001",uint[3](c));',{'010':'1'}),
 ('popcount-branch','qubit q; bit[3] c="101"; if(popcount(c)==2){c="111";}',{'111':'1'}),
 ('popcount-literal','qubit q; bit c; if(popcount("111")==3){c=1;}',{'1':'1'}),
 ('rotate-count','qubit q; bit[3] c="101"; c=rotl(c,popcount(c));',{'110':'1'}),
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
 ('logical-assignment','bit a=1; bit b=0; bit r; r=a || b;',{'101':'1'}),
 ('logical-nested','bit a=1; bit b=0; if(a){if(a || b){b=1;}} a=0;',{'10':'1'}),
 ('logical-and-or','bit a=1; bit b=0; bit r; if((a==1 || b==1) && b==0){r=1;}',{'101':'1'}),
 ('typed-negative','bit[8] c="11111111"; bit r; if(int[8](c)<0){r=1;}',{'111111111':'1'}),
 ('typed-unsigned','bit[8] c="11111111"; bit r; if(uint[8](c)>0){r=1;}',{'111111111':'1'}),
 ('typed-narrowing','bit[8] c; bit r; if(int[8](c)<int[8](255)){r=1;}',{'000000000':'1'}),
 ('typed-minus','bit[8] c="00000010"; bit r; if(-int[8](c)<0){r=1;}',{'100000010':'1'}),
 ('typed-guard-zero','bit[8] c; bit r; if(int[8](c)!=0 && 6/int[8](c)==3){r=1;}',{'000000000':'1'}),
 ('typed-guard-two','bit[8] c="00000010"; bit r; if(int[8](c)!=0 && 6/int[8](c)==3){r=1;}',{'100000010':'1'}),
 ('typed-measurement','qubit q; bit c; bit r; h q; c=measure q; if(int[1](c)<0){r=1;}',{'00':'1/2','11':'1/2'}),
 ('typed-zero','bit[8] c; bit r; if(6/int[8](c)==3){r=1;}',None),
 ('typed-overflow','bit[64] c=1; if(int(c)+9223372036854775807>0){c[0]=0;}',None),
 ('typed-machine','bit[64] c; if(int(c)==0){c[0]=1;} ',{'0'*63+'1':'1'}),
 ('typed-bitcast','bit[3] c="011"; c=bit[3](int[3](int[3](c)+1));',{'100':'1'}),
 ('typed-bitcast-negative','bit[3] c="111"; c=bit[3](uint[3](int[3](c)));',{'111':'1'}),
 ('typed-bitcast-compare','bit[3] c="011"; bit r; if(bit[3](int[3](c))==3){r=1;}',{'1011':'1'}),
 ('typed-bitcast-measure','qubit q; bit c; h q; c=measure q; c=bit[1](int[1](c));',{'0':'1/2','1':'1/2'}),
 ('typed-bitcast-skipped','bit[3] c; if(c==1){c=bit[3](int[3](1/int[3](c)));}',{'000':'1'}),
 ('typed-bitcast-divzero','bit[3] c; c=bit[3](int[3](1/int[3](c)));',None),
 ('typed-bitcast-wide','bit[64] c=1; c=bit[64](uint[64](c));',{'0'*63+'1':'1'}),
 ('registers','qubit q; bit[2] c="10"; bit[2] d="10"; if(c==d){c=0;}',{'1000':'1'}),
]
checks=0
hooks=tuple(getattr(adapter.QasmVisitor,name) for name in ['_visit_classical_assignment','_visit_classical_declaration','_visit_branching_statement'])
rejected=['bit[8] c=8; bit r; if(int[c](c)<0){r=1;}','bit[8] c; bit r; if(int[7](c)<0){r=1;}', 'bit[8] c; bit r; if(int[8](c)+c>0){r=1;}', 'bit[8] c; bit r; if(int[0](c)<0){r=1;}', 'bit[8] c; bit r; if(int[8](c)<-9223372036854775809){r=1;}', 'qubit q; bit[3] c; c=rotl(c);',
          'qubit q; bit[3] c; c=rotr(c,1,2);',
          'qubit q; bit[3] c; c=rotl(c,-9223372036854775809);',
          'qubit q; bit[3] c; c=rotl(c,int[4](c));',
          'qubit q; bit[3] c; c=rotl(c,c);',
          'qubit q; bit c; if(popcount(c,c)==1){c=1;}', 'qubit q; bit c=2;', 'qubit q; bit[2] c; c="1";',
          'qubit q; bit[2] c; c[0]=c[2];', 'qubit q; bit[3] c; c[0:2]=c[0:1];',
          'qubit q; bit c=1; while(c==1){c=0;}',
          'qubit q; bit c; c=measure q; rx(float(c)) q;',
          'qubit[2] q; bit c=1; x q[c];',
          'qubit[2] q; bit c=1; c=measure q[c];',
          'qubit q; bit[2] c; bit d=1; c[d]=measure q;',
          'qubit q; bit[2] c; let d=c; d=1;',
          'qubit q; bit c; c+=1;', 'qubit q; bit[2] c; if(c>4) x q;']
rejected += ['bit[3] c; c=bit[3](int[3](c)+1);','bit[3] c; c=bit[3](int(c));','bit[3] c; c=bit[2](int[3](c));','bit[3] c; c=bit[c](int[3](c));','bit[3] c; c=bit[0](int[3](c));','bit[64] c; c=bit[64](int(c));']
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
 if k=='IntegerBits':return n(8)+integer_expression(e['Left'])
 if k=='IntegerCompare':return n(6,ops.index(e['Operator'])-5)+integer_expression(e['Left'])+integer_expression(e['Right'])
 if k=='Logical':return n(7,0 if e['Operator']=='And' else 1)+expression(e['Left'])+expression(e['Right'])
 if k=='Complement':return n(2)+expression(e['Left'])
 if k=='PopulationCount':return n(4)+expression(e['Left'])
 if k=='Rotate':return n(5,0 if e['RotationDirection']=='Left' else 1,0 if e['DistanceInterpretation']=='Unsigned' else 1)+expression(e['Left'])+expression(e['Right'])
 return n(3,ops.index(e['Operator']))+expression(e['Left'])+expression(e['Right'])
def integer_expression(e):
 k=e['Kind']
 if k=='IntegerBinary':return n(3,['Add','Subtract','Multiply','Divide','Remainder','Power'].index(e['Operator']))+integer_expression(e['Left'])+integer_expression(e['Right'])
 t=n(0 if e['Signedness']=='Signed' else 1,e['Width'])
 if k=='IntegerConstant':return n(0)+t+n(e['Value'])
 if k=='IntegerRead':return n(1)+t+n(*e['Bits'])
 assert k=='IntegerCast'
 return n(2)+t+integer_expression(e['Left'])

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
 assert circuit['Version']==(4 if name.startswith('typed-') or name in ('comparison','logical-assignment','logical-nested','logical-and-or') else 3),(name,circuit)
 if name.startswith('classical-only-'):assert circuit['Qubits']==0,(name,circuit)
 # The overlap case must retain a simultaneous read of both old source bits.
 if name=='overlap':assert circuit['Steps'][1]=={'Kind':'Assign','Wires':[1,2],'ClassicalValue':{'Kind':'Read','Bits':[0,1]}}
 checks+=1
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert result.returncode==0 and json.loads(result.stdout)==circuit,(name,result.stderr);checks+=1
 if a.worker:
  worker=a.worker.resolve();bits=sum(r['Size'] for r in circuit['Registers']);output=circuit['OutputBits']
  for exact in (True,False):
   protocol=(b'QEXACT3\n' if exact else b'QSAMPLE4\n') if circuit['Version']==4 else (b'QEXACT2\n' if exact else b'QSAMPLE3\n')
   payload=protocol+n(circuit['Qubits'])+(b'' if exact else n(10000,1731))+n(bits,len(output),*output,len(circuit['Steps']))+steps(circuit['Steps'])
   run=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30,env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data')))
   if expected is None:
    assert run.returncode!=0 and run.stderr and not run.stdout,(name,run.stdout);checks+=1;continue
   assert run.returncode==0 and not run.stderr,(name,run.stderr);value=json.loads(run.stdout)
   if exact:assert {k:Fraction(v) for k,v in value['probabilities'].items()}=={k:Fraction(v) for k,v in expected.items()},(name,value)
   else:
    actual=value['counts'];assert set(actual)==set(expected) and sum(actual.values())==10000,(name,value)
    for k,v in expected.items():assert abs(actual[k]/10000-float(Fraction(v)))<.04,(name,value)
   checks+=1
print('PASS: '+str(checks)+' classical expression import checks.')
