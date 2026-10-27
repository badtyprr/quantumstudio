"""Pinned DEV-07 sources, direct probability oracles and a separate state witness."""
import argparse, ast, base64, copy, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser()
for option in ('adapter','worker','frozen','upstream'):p.add_argument('--'+option,type=Path,required=option=='adapter')
a=p.parse_args();root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('compiler',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
manifest=json.loads((root/'fixtures/dev07-upstream.json').read_text(encoding='utf-8'));checks=0
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(a.worker.resolve().parent/'data')) if a.worker else os.environ

def process(command,data):
 result=subprocess.run([str(v) for v in command],input=data,capture_output=True,timeout=60,env=env)
 assert result.returncode==0,result.stderr.decode(errors='replace')
 return json.loads(result.stdout.decode('utf-8-sig'))
def bridge(model):return process([a.adapter.resolve()],json.dumps(model).encode())
def run(payload,expected):
 global checks
 if not a.worker:return
 for exact in (True,False):
  result=process([a.worker.resolve(),'--exact-circuit' if exact else '--sample'],base64.b64decode(payload['exact' if exact else 'sampled']))
  if exact:
   actual={key:float(process([a.worker.resolve(),'--json','--approx'],value.encode())['text'].replace('−','-')) for key,value in result['probabilities'].items()}
  else:actual={key:value/10000 for key,value in result['counts'].items()}
  assert all(abs(actual.get(key,0)-expected.get(key,0))<(1e-12 if exact else .025) for key in set(actual)|set(expected)),(actual,expected)
  checks+=1

if a.upstream:assert subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD']).decode().strip()==manifest['revision']
for fixture in manifest['fixtures']:
 source=fixture['source'];name=fixture['name'];assert hashlib.sha256(source.encode()).hexdigest()==fixture['sha256'];checks+=1
 if a.upstream:
  tree=ast.parse((a.upstream/fixture['path']).read_text(encoding='utf-8'))
  original=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.lineno==fixture['line'])
  assert original==source;checks+=1
 if not fixture['accepted']:
  try:compiler.convert(source,classical=True)
  except (ValueError,NotImplementedError,KeyError) as error:assert fixture['diagnostic'] in str(error);checks+=1
  else:raise AssertionError('Update the explicitly deferred alias-call evidence: '+name)
  if a.frozen:
   result=subprocess.run([str(a.frozen.resolve()),'--classical'],input=source.encode(),capture_output=True,timeout=60)
   assert result.returncode and not result.stdout and fixture['diagnostic'] in result.stderr.decode(errors='replace');checks+=1
  continue
 model=compiler.convert(source,classical=True);payload=bridge(model);checks+=1
 if a.frozen:assert process([a.frozen.resolve(),'--classical'],source.encode())==model;checks+=1
 restored=compiler.convert(payload['source'],classical=True);again=bridge(restored);checks+=1
 if name.endswith('with_continue'):expected={key:.25 for key in ('000','001','100','101')}
 elif name.endswith('with_break'):expected={'000':.5,'001':.5}
 else:expected={'':1} # Original has no outputs: execution smoke only.
 run(payload,expected);run(again,expected)
 if name.endswith('unroll_qasm_output'):
  # Independently derived original order: H0,CX01,H1,CX12,H2,CX23.
  # Its inverse maps the expected PURE state to zero; measuring all-zero with
  # probability one witnesses relative phases as well as populations. Append
  # this observer to a COPY of each model, never to the unchanged source.
  for candidate in (model,restored):
   observed=copy.deepcopy(candidate)
   observed['Registers']=[dict(Name='audit',Size=4)];observed['OutputBits']=[3,2,1,0]
   observed['Steps'] += [dict(Kind='Gate',Expression=gate,Wires=wires) for gate,wires in [('CNOT',[2,3]),('H',[2]),('CNOT',[1,2]),('H',[1]),('CNOT',[0,1]),('H',[0])]]
   observed['Steps'] += [dict(Kind='Measure',Wires=[wire],ClassicalBit=wire) for wire in range(4)]
   run(bridge(observed),{'0000':1})
 print('PASS:',name,flush=True)
print(f'PASS: {checks} pinned DEV-07 checks; unmeasured state uses a separately labeled inverse witness; alias calls remain deferred.')
