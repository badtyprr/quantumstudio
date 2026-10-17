"""Exact worker protocol; rational expectations from an independent density oracle."""
import json
import os
from fractions import Fraction
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks = 0
def numbers(*values):
    return ''.join(str(v)+'\n' for v in values).encode()
def expression(kind, targets, text):
    encoded=text.encode()
    return numbers(kind,len(targets),*targets,len(encoded))+encoded
def operations(steps):
    result=b''
    for kind,*args in steps:
        if kind=='branch':
            mask,value,yes,no=args
            result+=numbers(6,mask,value,len(yes))+operations(yes)+numbers(len(no))+operations(no)
        elif kind=='measure': result+=numbers(1,*args)
        elif kind=='reset': result+=numbers(2,*args)
        elif kind=='readout':
            bit,p01,p10=args;p01,p10=Fraction(p01),Fraction(p10)
            result+=expression(5,[bit],f'[{1-p01},{p01};{p10},{1-p10}]')
        else: result+=expression(0,args,kind)
    return result
def request(qubits=1,bits=1,output=(0,),steps=()):
    return b'QEXACT1\n'+numbers(qubits,bits,len(output),*output,len(steps))+b''.join(steps)
def run(payload,success=True,flags=('--exact-circuit',)):
    global checks
    p=subprocess.run([str(worker),*flags],input=payload,capture_output=True,timeout=30)
    assert (p.returncode==0)==success,(payload[:150],p.stderr)
    checks+=1
    if not success:
        assert not p.stdout and p.stderr
        return
    assert not p.stderr,p.stderr
    value=json.loads(p.stdout)
    assert set(value)=={'qubits','classical_bits','bits','probabilities'}
    assert all(isinstance(p,str) and len(k)==len(value['bits']) and set(k)<={'0','1'} for k,p in value['probabilities'].items())
    return value

fixtures=json.loads(Path(__file__).with_name('quantum-exact-fixtures.json').read_text())
for f in fixtures:
    payload=b'QEXACT1\n'+numbers(f['qubits'],64,len(f['output_bits']),*f['output_bits'],len(f['steps']))+operations(f['steps'])
    result=run(payload)
    assert result['bits']==f['output_bits'] and result['qubits']==f['qubits'] and result['classical_bits']==64
    assert {k:Fraction(v) for k,v in result['probabilities'].items()}=={k:Fraction(v) for k,v in f['probabilities'].items()},(f['name'],result)
assert run(request(0,0,()))['probabilities']=={'':'1'}
thirds=run(request(steps=[expression(5,[0],'[1/3,2/3;0,1]')]))['probabilities']
assert {k:Fraction(v) for k,v in thirds.items()}=={'0':Fraction(1,3),'1':Fraction(2,3)},thirds
symbolic=run(request(steps=[expression(0,[0],'Ry(x)'),numbers(1,0,0)]))['probabilities']
assert 'cos' in symbolic['0'] and 'sin' in symbolic['1'],symbolic
assert run(request(steps=[expression(0,[0],'X'),expression(4,[0],'vector([1,0;0,sqrt(3)/2],[0,1/2;0,0])'),numbers(1,0,0)]))['probabilities']=={'0':'0.25','1':'0.75'}
assert run(request(steps=[numbers(3,0,0)+expression(0,[0],'X')[2:],numbers(1,0,0)]))['probabilities']=={'1':'1'}
for gate in ('2*I','[x,0;0,1]','[1,0,0;0,1,0;0,0,1]','[1,0;0,inf]'):
    run(request(steps=[expression(0,[0],gate)]),False)
for table in ('[1,1;0,1]','[2,-1;0,1]','[x,1-x;0,1]'):
    run(request(steps=[expression(5,[0],table)]),False)
valid=request(steps=[expression(0,[0],'H'),numbers(1,0,0)])
for n in range(len(valid)):
    run(valid[:n],False)
for payload in (valid+b'\n',request(11),request(1,65),request(output=(0,0)),request(steps=[numbers(7)]),
                request(steps=[numbers(6,1,1,1,2,1,0)]),b'QEXACT1\n'+b'9'*21+b'\n',
                request(steps=[expression(0,[0],'H\0')]),b'x'*1100001):
    run(payload,False)
for flag in ('--json','--approx','--sample','--states'):
    run(valid,False,('--exact-circuit',flag))
print(f'PASS: {checks} exact circuit worker checks.')
