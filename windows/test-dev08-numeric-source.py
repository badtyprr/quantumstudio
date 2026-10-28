"""DEV-08 numeric sources with separately appended inverse-state witnesses."""
import argparse, ast, struct, base64, copy, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from fractions import Fraction
p=argparse.ArgumentParser()
for option in ('adapter','worker','frozen','upstream'):p.add_argument('--'+option,type=Path,required=option=='adapter')
a=p.parse_args();root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('compiler',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
manifest=json.loads((root/'fixtures/dev08-numeric-upstream.json').read_text(encoding='utf-8'));checks=0
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(a.worker.resolve().parent/'data')) if a.worker else os.environ

def process(command,data):
 result=subprocess.run([str(v) for v in command],input=data,capture_output=True,timeout=60,env=env)
 assert result.returncode==0,(result.returncode,result.stderr.decode(errors='replace'),str(command))
 return json.loads(result.stdout.decode('utf-8-sig'))
def bridge(model):return process([a.adapter.resolve()],json.dumps(model).encode())
def run(payload,expected):
 global checks
 if not a.worker:return
 for exact in (True,False):
  result=process([a.worker.resolve(),'--exact-circuit' if exact else '--sample'],base64.b64decode(payload['exact' if exact else 'sampled']))
  if exact:
   actual={}
   for key,value in result['probabilities'].items():
    text=process([a.worker.resolve(),'--json','--approx'],value.encode())['text']
    number=complex(text.replace('\u2212','-').replace(' ','').replace('i','j'))
    assert abs(number.imag)<1e-12,number
    actual[key]=number.real
  else:actual={key:value/10000 for key,value in result['counts'].items()}
  assert all(abs(actual.get(key,0)-expected.get(key,0))<(1e-12 if exact else .025) for key in set(actual)|set(expected)),(actual,expected)
  checks+=1

if a.upstream:assert subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD']).decode().strip()==manifest['revision']
angle=Fraction(struct.unpack('f',struct.pack('f',3.14))[0])
for fixture in manifest['fixtures']:
 source=fixture['source'];name=fixture['name'];assert hashlib.sha256(source.encode()).hexdigest()==fixture['sha256'];checks+=1
 if a.upstream:
  tree=ast.parse((a.upstream/fixture['path']).read_text(encoding='utf-8'))
  original=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.lineno==fixture['line'])
  assert original==source;checks+=1
 model=compiler.convert(source,classical=True);payload=bridge(model);checks+=1
 if a.frozen:assert process([a.frozen.resolve(),'--classical'],source.encode())==model;checks+=1
 restored=compiler.convert(payload['source'],classical=True);checks+=1
 run(payload,{'':1});run(bridge(restored),{'':1})
 if name=='test_function_call_with_return':
  # Independently assert the declared public result, then observe its raw
  # binary32 value on a copy. The unchanged source has no terminal observer.
  matches=[(slot,var) for slot,var in enumerate(model['NumericVariables']) if var['Name']=='r']
  assert len(matches)==1 and matches[0][1]==dict(Name='r',NumericKind='Float',Width=32),matches
  slot,_=matches[0];observed=copy.deepcopy(model)
  comparison=dict(Kind='NumericCompare',RealLeft=dict(Kind='Variable',Slot=slot,NumericKind='Float',Width=32),
                  RealRight=dict(Kind='TypedConstant',NumericKind='Float',Width=32,ValueBits=str(struct.unpack('>I',struct.pack('>f',3.14))[0])))
  test=dict(Kind='IntegerCompare',Operator='Equal',Left=comparison,Right=dict(Kind='IntegerConstant',Signedness='Signed',Width=0,Value='0'))
  offset=sum(register['Size'] for register in observed['Registers'])
  observed['Registers'].append(dict(Name='audit_return',Size=1));observed['OutputBits']=[offset]
  observed['Steps'].append(dict(Kind='Assign',Wires=[offset],ClassicalValue=test))
  witness=bridge(observed);run(witness,{'1':1});run(bridge(compiler.convert(witness['source'],classical=True)),{'1':1});checks+=1
 # Originals have no outputs. Append an independently derived inverse to
 # copies, then measure zero. This witnesses the zero-input pure state up to
 # global phase, not the full operator or an unused classical return value.
 if name=='test_simple_function_call':ops=[('Rx('+str(-3*angle)+')',[0])]
 elif name=='test_update_variable_in_function':ops=[('Rx('+str(-2*angle)+')',[0])]
 elif name=='test_function_call_with_return':ops=[('H',[0])]
 else:ops=[('Rx('+str(-angle)+')',[1]),('H',[1])]*3
 for candidate in (model,restored):
  observed=copy.deepcopy(candidate);n=observed['Qubits']
  observed['Registers']=[dict(Name='audit',Size=n)];observed['OutputBits']=list(reversed(range(n)))
  observed['Steps'] += [dict(Kind='Gate',Expression=gate,Wires=wires) for gate,wires in ops]
  observed['Steps'] += [dict(Kind='Measure',Wires=[wire],ClassicalBit=wire) for wire in range(n)]
  run(bridge(observed),{'0'*n:1})
 print('PASS:',name,flush=True)
print(f'PASS: {checks} pinned numeric-call source checks; separate inverse witnesses cover zero-input states.')
