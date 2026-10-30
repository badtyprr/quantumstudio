"""Unchanged pinned sources and independent operator witnesses on model copies."""
import argparse, ast, base64, copy, hashlib, importlib.util, json, os, struct, subprocess, sys
from pathlib import Path

p=argparse.ArgumentParser()
for option in ('adapter','worker','frozen','upstream'):
    p.add_argument('--'+option,type=Path,required=option=='adapter')
a=p.parse_args();root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('compiler',root/'qasm-import.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
manifest=json.loads((root/'fixtures/dev08-upstream.json').read_text(encoding='utf-8'));checks=0
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
            actual={key:float(process([a.worker.resolve(),'--json','--approx'],value.encode())['text'].replace('\u2212','-')) for key,value in result['probabilities'].items()}
        else:actual={key:value/10000 for key,value in result['counts'].items()}
        assert all(abs(actual.get(key,0)-expected.get(key,0))<(1e-10 if exact else .025) for key in set(actual)|set(expected)),(actual,expected)
        checks+=1

def gate(name,wire):return dict(Kind='Gate',Expression=name,Wires=[wire])

angles={'test_passing_array_to_function':10,'test_passing_subarray_to_function':14,
        'test_passing_array_with_dim_identifier':3,'test_pass_multiple_arrays_to_function':18}
if a.upstream:assert subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD']).decode().strip()==manifest['revision']
for fixture in manifest['fixtures']:
    source=fixture['source'];name=fixture['name']
    assert hashlib.sha256(source.encode()).hexdigest()==fixture['sha256'];checks+=1
    if a.upstream:
        tree=ast.parse((a.upstream/fixture['path']).read_text(encoding='utf-8'))
        original=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.lineno==fixture['line'])
        assert original==source;checks+=1
    model=compiler.convert(source,classical=True);payload=bridge(model);checks+=1
    if a.frozen:assert process([a.frozen.resolve(),'--classical'],source.encode())==model;checks+=1
    restored=compiler.convert(payload['source'],classical=True);again=bridge(restored);checks+=1
    # These originals have no outputs; this checks execution, not their operator.
    run(payload,{'':1});run(again,{'':1})
    qubits=model['Qubits']
    if name=='test_return_values_from_function':
        angle=struct.unpack('f',struct.pack('f',3.14))[0]
        inverse=[gate('Rx('+repr(-angle)+')',1),gate('Rx('+repr(-angle)+')',0),gate('H',0)]
    else:inverse=[gate('Rx('+str(-angles[name])+')',0)] if name in angles else []
    # Every computational basis state fixes each column up to phase. The equal
    # superposition fixes relative column phases; +i adds a complex-state check.
    preparations=[]
    for bits in range(1<<qubits):
        prefix=[gate('X',wire) for wire in range(qubits) if bits&(1<<wire)]
        preparations.append((prefix,list(reversed(prefix))))
    preparations.append(([gate('H',wire) for wire in range(qubits)],[gate('H',wire) for wire in reversed(range(qubits))]))
    preparations.append(([gate('H',wire) for wire in range(qubits)]+[gate('S',0)],
                         [gate('Sdg',0)]+[gate('H',wire) for wire in reversed(range(qubits))]))
    for candidate in (model,restored):
        for prefix,undo in preparations:
            observed=copy.deepcopy(candidate)
            # Keep all existing classical storage and append a fresh observer.
            offset=sum(register['Size'] for register in observed['Registers'])
            observed['Registers'].append(dict(Name='dev08_audit',Size=qubits))
            observed['OutputBits']=[offset+wire for wire in reversed(range(qubits))]
            # Export spells out the model's initial zero state with leading resets.
            # Prepare each witness after that initialization, before its operator.
            start=0
            while start<len(observed['Steps']) and observed['Steps'][start]['Kind']=='Reset':start+=1
            observed['Steps']=observed['Steps'][:start]+prefix+observed['Steps'][start:]+inverse+undo
            observed['Steps'] += [dict(Kind='Measure',Wires=[wire],ClassicalBit=offset+wire) for wire in range(qubits)]
            try:run(bridge(observed),{'0'*qubits:1})
            except Exception as error:raise AssertionError((name,candidate is restored,prefix,undo)) from error
            checks+=1
    print('PASS:',name,flush=True)
print(f'PASS: {checks} pinned DEV-08 checks; operator witnesses use separate model copies.')
