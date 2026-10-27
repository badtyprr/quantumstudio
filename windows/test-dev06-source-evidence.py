"""DEV-06 pinned-source evidence; references are independent dense matrices/values."""
import argparse,ast,base64,cmath,copy,hashlib,importlib.util,json,math,os,struct,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--adapter',type=Path,required=True);p.add_argument('--worker',type=Path);p.add_argument('--frozen',type=Path);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--fixtures',type=Path);p.add_argument('--upstream',type=Path);a=p.parse_args()
root=a.root.resolve();sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('compiler',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
manifest=json.loads((a.fixtures or root/'fixtures/dev06-upstream.json').read_text(encoding='utf-8'));checks=0
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(a.worker.resolve().parent/'data')) if a.worker else os.environ

def process(command,data):
 result=subprocess.run([str(x) for x in command],input=data,capture_output=True,timeout=60,env=env)
 assert result.returncode==0,result.stderr.decode(errors='replace')
 return json.loads(result.stdout.decode('utf-8-sig'))
def bridge(doc):
 return process([a.adapter.resolve()],json.dumps(doc).encode())
def run(payload,expected):
 global checks
 if not a.worker:return
 for exact in (True,False):
  result=process([a.worker.resolve(),'--exact-circuit' if exact else '--sample'],base64.b64decode(payload['exact' if exact else 'sampled']))
  values=result['probabilities' if exact else 'counts']
  if exact:
   assert set(values)=={expected},values
   value=process([a.worker.resolve(),'--json','--approx'],values[expected].encode())['text']
   assert abs(float(value.replace('\u2212','-'))-1)<1e-12,value
  else:assert values=={expected:10000},values
  checks+=1

def identity(n):return [[complex(r==c) for c in range(n)] for r in range(n)]
def multiply(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def embed(matrix,wires,qubits):
 n=1<<qubits;out=[[0j]*n for _ in range(n)]
 for column in range(n):
  local=sum(((column>>wire)&1)<<(len(wires)-1-k) for k,wire in enumerate(wires))
  for target in range(1<<len(wires)):
   row=column
   for k,wire in enumerate(wires):row=(row&~(1<<wire))|(((target>>(len(wires)-1-k))&1)<<wire)
   out[row][column]=matrix[target][local]
 return out

def controlled(matrix):
 out=identity(2*len(matrix))
 for r,row in enumerate(matrix):
  for c,v in enumerate(row):out[len(matrix)+r][len(matrix)+c]=v
 return out
X=[[0,1],[1,0]];Y=[[0,-1j],[1j,0]];H=[[1/math.sqrt(2),1/math.sqrt(2)],[1/math.sqrt(2),-1/math.sqrt(2)]]
def phase(t):return [[1,0],[0,cmath.exp(1j*t)]]
def rx(t):return [[math.cos(t/2),-1j*math.sin(t/2)],[-1j*math.sin(t/2),math.cos(t/2)]]
def u3(t,f,l):return [[math.cos(t/2),-cmath.exp(1j*l)*math.sin(t/2)],[cmath.exp(1j*f)*math.sin(t/2),cmath.exp(1j*(f+l))*math.cos(t/2)]]
def reference(name,n):
 if name=='broadcast-u3':ops=[(u3(.5,.5,.5),[0]),(u3(.5,.5,.5),[1])]
 elif name=='controlled-u3':ops=[(controlled(u3(.5,.5,.5)),[0,1])]
 elif name=='global-phase':return [[v*cmath.exp(1j*(math.pi/4)) for v in row] for row in identity(1<<n)]
 elif name=='powers':return identity(1<<n)
 elif name=='negative-control':return [[complex(r==c)*( -1 if r==2 else 1) for c in range(4)] for r in range(4)]
 elif name in ('controlled-global-phase','phase'):ops=[(phase(1),[0])]
 elif name=='inverses':ops=[(H,[0]),(Y,[0]),(rx(-.5),[0]),([[1,0],[0,-1j]],[0]),(controlled(X),[1,2]),(controlled(controlled(X)),[0,1,2])]
 elif name=='discarded-sine':ops=[(X,[0])]
 else:return None
 out=identity(1<<n)
 for matrix,wires in ops:out=multiply(embed(matrix,wires,n),out)
 return out

def operator(doc,exported=False):
 out=identity(1<<doc['Qubits']);steps=doc['Steps']
 if exported and doc['Qubits']:
  # Export explicitly resets its zero-initialized program. Compare the unitary
  # suffix separately, and execute the complete exported program below.
  assert steps[:doc['Qubits']]==[dict(Kind='Reset',Wires=[k]) for k in range(doc['Qubits'])]
  steps=steps[doc['Qubits']:]
 for step in steps:
  if step['Kind']=='StoreInteger':continue # discarded-sine's unrelated scalar declaration
  assert step['Kind']=='Gate',step
  data=process([a.worker.resolve(),'--json','--approx'],('quantum: '+step['Expression']).encode())
  matrix=[[complex(v.replace('\u2212','-').replace(' ','').replace('i','j')) for v in row] for row in data['cells']]
  out=multiply(embed(matrix,step['Wires'],doc['Qubits']),out)
 return out

def observe(doc,name):
 # Trusted observation is appended to a COPY of the imported model. The source
 # fixture and its separately executed program remain byte-for-byte unchanged.
 result=copy.deepcopy(doc);values={'angle-bits':{'ang1':4,'ang2':120,'ang3':12,'ang4':8,'ang5':96,'ang6':32},'float-casts':{'f':1.5585244804918115,'b':1,'i':1,'u':1},'integer-casts':{'x':-3,'b':1,'ux':253,'f':-3.0}}[name]
 offset=sum(r['Size'] for r in doc['Registers']);tests=[]
 for slot,var in enumerate(doc.get('Variables',[])):
  width=var['Width'] or 64;value=values[var['Name']]&((1<<width)-1)
  tests.append(dict(Kind='IntegerCompare',Operator='Equal',Left=dict(Kind='IntegerVariable',Slot=slot,Signedness=var['Signedness'],Width=var['Width']),Right=dict(Kind='IntegerConstant',Signedness=var['Signedness'],Width=var['Width'],Value=str(value))))
 for slot,var in enumerate(doc.get('NumericVariables',[])):
  value=values[var['Name']];width=var['Width'];kind=var['NumericKind']
  raw=value if kind=='Angle' else struct.unpack('>I' if width==32 else '>Q',struct.pack('>f' if width==32 else '>d',value))[0]
  comparison=dict(Kind='NumericCompare',RealLeft=dict(Kind='Variable',Slot=slot,NumericKind=kind,Width=width),RealRight=dict(Kind='TypedConstant',NumericKind=kind,Width=width,ValueBits=str(raw)))
  tests.append(dict(Kind='IntegerCompare',Operator='Equal',Left=comparison,Right=dict(Kind='IntegerConstant',Signedness='Signed',Width=0,Value='0')))
 result['Registers'].append(dict(Name='audit',Size=len(tests)));result['OutputBits']=list(range(offset,offset+len(tests)))
 for k,test in enumerate(tests):result['Steps'].append(dict(Kind='Assign',Wires=[offset+k],ClassicalValue=test))
 return result,'1'*len(tests)

if a.upstream:
 revision=subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD']).decode().strip()
 assert revision==manifest['revision'],revision
for fixture in manifest['fixtures']:
 source=fixture['source'];assert hashlib.sha256(source.encode()).hexdigest()==fixture['sha256'];checks+=1
 if a.upstream:
  tree=ast.parse((a.upstream/fixture['path']).read_text(encoding='utf-8'))
  if 'extraction' in fixture:
   node=next(n for n in ast.walk(tree) if isinstance(n,ast.JoinedStr) and n.lineno==fixture['line'])
   assert all(isinstance(n,ast.Constant) or isinstance(n,ast.FormattedValue) and isinstance(n.value,ast.Name) and n.value.id=='expression' for n in node.values)
   original=''.join(n.value if isinstance(n,ast.Constant) else 'sin(1.0);' for n in node.values)
  else:original=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.lineno==fixture['line'])
  assert original==source,fixture['id'];checks+=1
 if not fixture['accepted']:
  try:compiler.convert(source,classical=True)
  except (ValueError,NotImplementedError,KeyError) as error:
   assert fixture['diagnostic'] in str(error),(fixture['id'],error);checks+=1
   if a.frozen:
    result=subprocess.run([str(a.frozen.resolve()),'--classical'],input=source.encode(),capture_output=True,timeout=60)
    assert result.returncode!=0 and not result.stdout and fixture['diagnostic'] in result.stderr.decode(errors='replace'),result.stderr;checks+=1
   continue
  raise AssertionError('Previously unsupported fixture now accepted; update evidence: '+fixture['id'])
 doc=compiler.convert(source,classical=True);payload=bridge(doc);checks+=1
 if a.frozen:
  assert process([a.frozen.resolve(),'--classical'],source.encode())==doc;checks+=1
 restored=compiler.convert(payload['source'],classical=True);again=bridge(restored);checks+=1
 name=fixture['id'];expected=reference(name,doc['Qubits'])
 if expected is not None:
  if a.worker:
   for candidate,exported in ((doc,False),(restored,True)):
    actual=operator(candidate,exported);error=max(abs(x-y) for ar,er in zip(actual,expected) for x,y in zip(ar,er));assert error<2e-12,(name,error);checks+=1
  run(payload,'');run(again,'')
 else:
  run(payload,'1101' if name=='integer-casts' else '');run(again,'1101' if name=='integer-casts' else '')
  observed,want=observe(doc,name);obs=bridge(observed);run(obs,want);run(bridge(compiler.convert(obs['source'],classical=True)),want)
 print('PASS:',name,flush=True)
print(f'PASS: {checks} pinned DEV-06 source checks; full operators include global phase; storage observers are separately labeled.')
