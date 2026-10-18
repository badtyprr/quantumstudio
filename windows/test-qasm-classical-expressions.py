"""Source/frozen classical import equivalence and optional worker outcome checks."""
import argparse,importlib.util,json,os,subprocess,sys
from fractions import Fraction
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
spec=importlib.util.spec_from_file_location('qasm_expression_adapter',root/'windows/qasm-import.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; '
unicode_name='𝑎'*31
cases=[
 ('computed-xor','bit[3] c;bit r;r=uint[3](c ^ "111")==7;',{'1000':'1'}),
 ('computed-negative','bit[3] c;bit r;r=int[3](~c)==-1;',{'1000':'1'}),
 ('computed-store','bit[3] c;int[8] a=uint[3](c ^ "111");bit r;r=a==7;',{'1000':'1'}),
 ('computed-predicate','bit c;int[8] a=int[8](c==0);c=a==1;',{'1':'1'}),
 ('computed-guard','int a;bit c;int[8] b=int[8](true || a==0);c=b==1;',{'1':'1'}),
 ('computed-undefined','int a;bit c;int[8] b=int[8](a==0);c=b==0;',None),
 ('computed-not','bit c;int[8] a=int[8](!c);c=a==1;',{'1':'1'}),
 ('computed-bool','int a=-2;int[8] b=int[8](bool(a));bit c;c=b==1;',{'1':'1'}),
 ('computed-popcount','bit[3] c="101";uint n=uint(popcount(c));bit r;r=n==2;',{'1101':'1'}),
 ('computed-measurement','qubit q;bit c;h q;c=measure q;int[8] a=int[8](c==1);c=0;c=a==1;',{'0':'1/2','1':'1/2'}),
 ('variable-boolean-literal','int[8] a=int[8](true);bit c;c=a==1;',{'1':'1'}),
 ('scope-unicode','int '+unicode_name+'=1;bit c;{int '+unicode_name+'=2;c='+unicode_name+'==2;}c=c && '+unicode_name+'==1;',{'1':'1'}),
 ('scope-shadow','int a=1; bit c; if(a==1){int a=2; c=a==2;} c=c && a==1;',{'1':'1'}),
 ('scope-siblings','bit c=1; if(c){int a=2;c=a==2;}else{int a=3;c=a==2;}',{'1':'1'}),
 ('scope-else','bit c; if(c){int a=2;c=a==3;}else{int a=3;c=a==3;}',{'1':'1'}),
 ('scope-nested','int a=1; bit c; if(a==1){int a=2;if(a==2){int a=3;c=a==3;}c=c && a==2;}c=c && a==1;',{'1':'1'}),
 ('scope-loop','int sum=0; bit c; for int i in [0:2]{int t=i;sum+=t;}c=sum==3;',{'1':'1'}),
 ('scope-fresh','bit c; for int i in [0:1]{int t;if(i==0){t=7;}else{c=t==7;}}',None),
 ('scope-loop-shadow','int i=7;bit c;for int i in [0:2]{c=i==2;}c=c && i==7;',{'1':'1'}),
 ('scope-block','int a=1;bit c;{int a=2;c=a==2;}c=c && a==1;',{'1':'1'}),
 ('scope-collision','int a_scope_1=9;bit c;{int a=2;c=a==2;}c=c && a_scope_1==9;',{'1':'1'}),
 ('scope-constant-width','bit c=1;if(c){const uint n=8;int[n] t=7;c=t==7;}',{'1':'1'}),
 ('scope-self-initializer','int a=1;bit c;{int a=a+1;c=a==2;}',None),
 ('scope-measurement','qubit q;bit c;h q;c=measure q;if(c){int a=8;c=a==8;}else{int a=3;c=a==8;}',{'0':'1/2','1':'1/2'}),
 ('variable-arithmetic','int[8] counter=3; bit c; counter=counter**2-1; c=counter==8;',{'1':'1'}),
 ('variable-compound','int counter=3; bit c; counter+=2; counter*=3; counter-=1; counter/=2; counter%=4; c=counter==3;',{'1':'1'}),
 ('variable-undefined','int[8] counter; bit c; c=counter==0;',None),
 ('variable-guard','int counter; bit c; if(false && counter==0){c=1;}',{'0':'1'}),
 ('variable-initialize-later','int counter; bit c; counter=8; if(counter==8){c=1;}',{'1':'1'}),
 ('variable-cast','uint[8] a=255; int[8] b=int[8](a); bit c; c=b<0;',{'1':'1'}),
 ('variable-bitcast','uint[3] a=5; bit[3] c; c=bit[3](a);',{'101':'1'}),
 ('variable-bool','int a=-1; bit c; c=bool(a);',{'1':'1'}),
 ('variable-narrow','uint[3] a=8; bit c; c=a==0;',{'1':'1'}),
 ('variable-branch','int a=1; bit c; if(a==1){a=2; c=1;}else{a=3;} c=a==2;',{'1':'1'}),
 ('variable-loop','int counter=0; bit c; for int i in [0:2]{counter+=i;} c=counter==3;',{'1':'1'}),
 ('variable-const-width','const uint WIDTH=8; int[WIDTH] a=7; bit c; c=a==7;',{'1':'1'}),
 ('variable-measurement','qubit q; bit c; bit r; int[8] a; h q; c=measure q; a=int[1](c); r=a<0;',{'00':'1/2','11':'1/2'}),
 ('variable-history','qubit q; bit c; int a; h q; c=measure q; if(c){a=8;}else{a=3;} c=0; reset q; c=a==8;',{'0':'1/2','1':'1/2'}),
 ('variable-zero','int a=0; bit c; c=1/a==0;',None),
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
 ('boolean-zero','bit[3] c; bit r; r=bool(c);',{'0000':'1'}),
 ('boolean-literal-zero','bit r; r=bool("00");',{'0':'1'}),
 ('boolean-literal-nonzero','bit r; r=bool("10");',{'1':'1'}),
 ('boolean-literal-branch','bit r; if(bool("10")){r=1;}',{'1':'1'}),
 ('boolean-nonzero','bit[3] c="100"; bit r; if(bool(c)){r=1;}',{'1100':'1'}),
 ('boolean-nested','bit[3] c="100"; bit r; r=bool(bool(c));',{'1100':'1'}),
 ('boolean-popcount','bit[3] c="100"; bit r; r=bool(popcount(c));',{'1100':'1'}),
 ('typed-boolean-negative','bit[3] c="100"; bit r; r=bool(int[3](c));',{'1100':'1'}),
 ('typed-boolean-arithmetic','bit[3] c="100"; bit r; r=bool(int[3](c)-int[3](c));',{'0100':'1'}),
 ('typed-boolean-guard','bit[3] c; bit r; if(bool(c) && 6/int[3](c)==3){r=1;}',{'0000':'1'}),
 ('boolean-measure','qubit q; bit c; bit r; h q; c=measure q; r=bool(c);',{'00':'1/2','11':'1/2'}),
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
rejected += ['int[0] a;','uint[65] a;','int a=3; int[a] b;','int a=1; while(a){a=0;}',
             'int a=1; qubit[2] q; x q[a];','int a=1; qubit q; rx(a) q;',
             'int a=1; def f() -> int {return a;}','int a=1; int a=2;',
             'int a=1; bit[2] c; c[a]=1;','float a=1.0;','int a=b; int b=1;', 'int '+('a'*65)+';']
rejected += ['bit c;{int a=1;}c=a==1;', 'bit c;{int a=1;int a=2;}', 'bit c;for int i in [0:2]{int a=1;break;}', 'bit c;for int i in [0:2]{int a=1;continue;}', 'bit c;while(false){int a=1;}', 'bit c;{int '+('a'*65)+';}']
rejected += ['int '+('𝑎'*33)+';', 'int a=1;bit c;{const int a=2;c=a==2;}']
rejected += ['bit[3] c;int a=uint[2](~c);','bit[3] c;int a=int[3](popcount(c));',
             'bit[3] c;int a=uint[3](c ^ "11");','bit[3] c;bit r;r=false && uint[2](~c)==0;']
boolean_broad='c'
for _ in range(8):boolean_broad='('+boolean_broad+' | '+boolean_broad+')'
rejected.append('bit c; bit r; r=bool('+boolean_broad+');') # Comparison plus zero exceeds 512 nodes.
rejected.append('bit c;int a=int(bool('+boolean_broad+'));') # Mixed Boolean/integer tree shares one budget.
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
 if k=='IntegerFromBits':return n(5)+t+expression(e['Left'])
 if k=='IntegerConstant':return n(0)+t+n(e['Value'])
 if k=='IntegerRead':return n(1)+t+n(*e['Bits'])
 if k=='IntegerVariable':return n(4)+t+n(e['Slot'])
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
  elif kind=='ClearInteger':out+=n(10,s['VariableSlot'])
  elif kind=='StoreInteger':out+=n(9,s['VariableSlot'])+integer_expression(s['IntegerValue'])
  elif kind=='Reset':out+=n(2,s['Wires'][0])
  elif kind=='Measure':out+=n(1,s['Wires'][0],s['ClassicalBit'])
  else:
   assert kind=='Gate';matrix=s['Expression'].encode();out+=n(0,len(s['Wires']),*s['Wires'],len(matrix))+matrix
 return out
for name,body,expected in cases:
 source=header+body;circuit=adapter.convert(source,classical=True)
 assert circuit['Version']==(6 if name.startswith('computed-') else 5 if name.startswith(('variable-','scope-')) else 4 if name.startswith('typed-') or name in ('comparison','logical-assignment','logical-nested','logical-and-or') else 3),(name,circuit)
 if name=='scope-siblings':
  branch=next(step for step in circuit['Steps'] if step['Kind']=='Branch')
  assert branch['WhenTrue'][-1]['Kind']==branch['WhenFalse'][-1]['Kind']=='ClearInteger'
  assert branch['WhenTrue'][-1]['VariableSlot']!=branch['WhenFalse'][-1]['VariableSlot']
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
   declarations=b''
   if circuit['Version']>=5:
    protocol=b'QEXACT4\n' if exact else b'QSAMPLE5\n'
    if circuit['Version']==6:protocol=b'QEXACT5\n' if exact else b'QSAMPLE6\n'
    declarations=n(len(circuit['Variables']))+b''.join(n(0 if v['Signedness']=='Signed' else 1,v['Width']) for v in circuit['Variables'])
   payload=protocol+n(circuit['Qubits'])+(b'' if exact else n(10000,1731))+n(bits)+declarations+n(len(output),*output,len(circuit['Steps']))+steps(circuit['Steps'])
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
