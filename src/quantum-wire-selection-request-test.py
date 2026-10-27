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
    header=b'QEXACT13\n'+nums(qubits,bits) if exact else b'QSAMPLE14\n'+nums(qubits,4000,731,bits)
    return header+nums(slots)+nums(0,0)*slots+nums(0,1000,bits,*range(bits),len(steps))+b''.join(steps)
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

readout=[nums(1,k,k) for k in range(3)]
for exact in (True,False):
    # Re-evaluate after mutation, preserving the alias's noncontiguous order.
    dynamic_x=select([([2,0],variable())],gate('X',[0]))
    expect([store(integer(0)),dynamic_x,store(integer(1)),dynamic_x]+readout,{'101':1},exact)
    # Measurement selects different wires per trajectory/history.
    dynamic_x=select([([1,2],measured(0))],gate('X',[0]))
    expect([gate('H',[0]),nums(1,0,0),dynamic_x]+readout,{'010':.5,'101':.5},exact)
    # Measurement resolves its source before overwriting a selector bit.
    dynamic_measure=select([([1,2],measured(0))],nums(1,0,0))
    expect([gate('X',[2]),nums(7,1,0,0,1,1),dynamic_measure]+readout[1:],{'101':1},exact)
    # Dynamic reset of an entangled subsystem is a channel, not a unitary.
    reset=select([([1,2],integer(0))],nums(2,0))
    expect([gate('H',[0]),gate('CNOT',[0,1]),reset]+readout,{'000':.5,'100':.5},exact)
    # Resolved roles are ordered, including controls and targets.
    cx=select([([0,2],integer(1)),([0,1],integer(1))],gate('CNOT',[0,1]))
    expect([gate('X',[2]),cx]+readout,{'011':1},exact)
    # Runtime gate parameters and a selected target share the pre-operation record.
    parameter=nums(17,1,0,3,0,0,1,0,0)+integer(1)  # P(0), one target
    expect([select([([0,2],integer(1))],parameter)]+readout,{'000':1},exact)
    division=nums(3,3)+integer(1)+integer(0)
    run(request([select([([0,1],division)],gate('X',[0]))],exact),exact,'fixture.qasm:7:3: Wire index')
    unsigned=nums(0,1,0,(1<<64)-1)
    run(request([select([([0,1],unsigned)],gate('X',[0]))],exact),exact,'Wire index is outside')
    # Invalid indices are lazy; declaration/map validation is not.
    bad=select([([0,1],variable())],gate('X',[0]))
    expect([branch(0,[bad])]+readout,{'000':1},exact)
    expect([store(integer(1)),branch(1,[bad])]+readout,{'010':1},exact)
    for value in (-1,2,(1<<63)-1):
        run(request([store(integer(value)),bad],exact),exact,'fixture.qasm:7:3: Wire index')
    run(request([bad],exact),exact,'fixture.qasm:7:3: Wire index')
    collision=select([([2,0],integer(0)),([1,2],integer(1))],gate('CNOT',[0,1]))
    run(request([collision],exact),exact,'wires must be distinct')
    for bad_step in [select([],gate('X',[0])),select([([],integer(0))],gate('X',[0])),
                     select([([3],integer(0))],gate('X',[0])),
                     select([([1],integer(0))],store(integer(0))),
                     select([([1],integer(0))],nums(3,1,1)+gate("X",[0])[2:]),
                     select([([1],integer(0))],gate('X',[1])),
                     select([([1],integer(0))],bad),
                     select([([1],integer(0))],gate('CNOT',[0,1])),
                     select([([1],integer(0))],gate('X',[0]),'x'*513)]:
        run(request([branch(0,[bad_step])],exact),exact,'')
    valid=request([select([([0,2],integer(1))],gate('X',[0]))]+readout,exact)
    for length in range(len(valid)):run(valid[:length],exact,'')
    run(valid+b'0\n',exact,'')
    run(valid.replace(b'QEXACT13\n',b'QEXACT12\n').replace(b'QSAMPLE14\n',b'QSAMPLE13\n'),exact,'')
print(f'PASS: {checks} runtime wire selection protocol checks.')
