"""Independent simulation of all four exported Bell preparation circuits."""
import sys,math
from pathlib import Path
from openqasm3 import parse,ast
for index in range(4):
    program=parse(Path(sys.argv[1]+f'.bell{index}.qasm').read_text(encoding='utf-8-sig'))
    gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
    assert len(gates)==2+(index>=2)+(index%2)
    state=[1+0j,0j,0j,0j]
    for gate in gates:
        name=gate.name.name;wires=[q.indices[0][0].value for q in gate.qubits]
        mask=1<<(1-wires[0]);updated=[0j]*4
        for column,amplitude in enumerate(state):
            if name=='h':
                updated[column&~mask]+=amplitude/math.sqrt(2)
                updated[column|mask]+=amplitude*(-1 if column&mask else 1)/math.sqrt(2)
            elif name=='x':updated[column^mask]+=amplitude
            elif name=='z':updated[column]+=amplitude*(-1 if column&mask else 1)
            elif name=='cx':updated[column^(1<<(1-wires[1])) if column&mask else column]+=amplitude
            else:raise AssertionError(name)
        state=updated
    expected=[0j]*4
    expected[0 if index<2 else 1]=1/math.sqrt(2)
    expected[3 if index<2 else 2]=(-1 if index%2 else 1)/math.sqrt(2)
    assert max(abs(a-b) for a,b in zip(state,expected))<1e-14,(index,state,expected)
print('PASS: all four exported Bell circuits preserve the exact relative and global phase conventions.')
