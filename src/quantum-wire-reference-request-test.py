"""Runtime wire resolution through both worker engines, including malformed input."""
import json, os, subprocess, sys
from pathlib import Path

worker = Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks = 0
def nums(*values): return ''.join(str(v)+'\n' for v in values).encode()
def integer(value): return nums(0,0,0,value & ((1<<64)-1))
def variable(slot=0): return nums(4,0,0,slot)
def measured(bit): return nums(1,1,1,bit)
def store(value,slot=0): return nums(9,slot)+value
def gate(name,wires):
    value=name.encode();return nums(0,len(wires),*wires,len(value))+value
def select(targets,operation,source='fixture.qasm:7:3'):
    label=source.encode()
    return nums(20,len(label))+label+nums(len(targets))+b''.join(nums(len(mapping),*mapping)+index for mapping,index in targets)+operation
def branch(value,steps): return nums(8,0,1,value,len(steps))+b''.join(steps)+nums(0)
def request(steps,exact,qubits=3,bits=3,slots=1):
    header=b'QEXACT17\n'+nums(qubits,bits) if exact else b'QSAMPLE18\n'+nums(qubits,4000,731,bits)
    return header+nums(slots)+nums(0,0)*slots+nums(0,0,1000,bits,*range(bits),len(steps))+b''.join(steps)
def run(payload,exact,error=None):
    global checks
    p=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=45)
    checks+=1
    if error is not None:
        assert p.returncode and not p.stdout and error.encode() in p.stderr,(error,p.stdout,p.stderr)
        return
    assert p.returncode==0 and not p.stderr,p.stderr
    result=json.loads(p.stdout)
    if not exact:return {k:v/4000 for k,v in result['counts'].items()}
    values={}
    for k,v in result['probabilities'].items():
        p=subprocess.run([str(worker),'--json','--approx'],input=v.encode(),capture_output=True,timeout=30)
        assert p.returncode==0,p.stderr
        values[k]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
    return values
def expect(steps,expected,exact,**kw):
    global checks
    values=run(request(steps,exact,**kw),exact)
    assert set(values)==set(expected),(values,expected)
    assert all(abs(values[k]-v)<(1e-12 if exact else .035) for k,v in expected.items()),(values,expected)
    checks+=1

def preflight(targets,source='call.qasm:4:2'):
    label=source.encode()
    return nums(25,len(label))+label+nums(len(targets))+b''.join(nums(len(mapping),*mapping)+index for mapping,index in targets)
for exact in (True,False):
    valid=preflight([([2,0],variable()),([1,2],integer(0))])
    expect([store(integer(1)),valid],{'000':1},exact)
    expect([store(integer(1)),valid,gate('X',[0]),nums(1,0,0)],{'100':1},exact)
    run(request([valid],exact),exact,'before initialization')
    run(request([store(integer(2)),valid],exact),exact,'Wire index is outside')
    run(request([preflight([([0,2],integer(1)),([2,1],integer(0))])],exact),exact,'must be distinct')
    for index in [integer(-1),nums(0,1,0,(1<<64)-1)]:
        run(request([preflight([([0,1],index)])],exact),exact,'Wire index is outside')
    expect([branch(0,[valid])],{'000':1},exact)
    for bad in [preflight([]),preflight([([],integer(0))]),preflight([([3],integer(0))]),
                preflight([([0],variable(2))]),preflight([([0],integer(0))]*26),preflight([([0],integer(0))],'x'*513)]:
        run(request([branch(0,[bad])],exact),exact,'')
    # Larger than gate arity, with distinct selected identities and explicit order.
    expect([preflight([([wire],integer(0)) for wire in range(5)])],{'000':1},exact,qubits=5)
    deep=integer(0)
    for _ in range(30):deep=nums(2,0,0)+deep
    run(request([preflight([([0],deep)]*17)],exact),exact,'512')
    too_deep=nums(2,0,0)+nums(2,0,0)+deep
    run(request([preflight([([0],too_deep)])],exact),exact,'32 levels')
    run(request([select([([0],integer(0))],valid)],exact),exact,'Only quantum operations')
    payload=request([store(integer(1)),valid],exact)
    for length in range(len(payload)):run(payload[:length],exact,'')
    run(payload+b'0\n',exact,'')
    run(payload.replace(b'QEXACT17',b'QEXACT16').replace(b'QSAMPLE18',b'QSAMPLE17'),exact,'')
print(f'PASS: {checks} wire reference preflight protocol checks.')
