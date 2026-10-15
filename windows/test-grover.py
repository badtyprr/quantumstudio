"""Check exported two-qubit Grover presets with an independent state simulator."""
import sys, math
from pathlib import Path
from openqasm3 import parse, ast
for target in range(4):
    program=parse(Path(sys.argv[1]+f'.grover{target}.qasm').read_text(encoding='utf-8-sig'))
    gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
    assert len(gates)==12+2*(2-target.bit_count())
    state=[1+0j,0j,0j,0j]
    for gate in gates:
        name=gate.name.name
        wires=[q.indices[0][0].value for q in gate.qubits]
        mask=1<<(1-wires[0]);updated=[0j]*4
        for column,amplitude in enumerate(state):
            if name=='h':
                updated[column&~mask]+=amplitude/math.sqrt(2)
                updated[column|mask]+=amplitude*(-1 if column&mask else 1)/math.sqrt(2)
            elif name=='x':updated[column^mask]+=amplitude
            elif name=='cz':
                second=1<<(1-wires[1])
                updated[column]+=amplitude*(-1 if column&mask and column&second else 1)
            else:raise AssertionError(name)
        state=updated
    expected=[-1 if k==target else 0 for k in range(4)]
    assert max(abs(a-b) for a,b in zip(state,expected))<2e-14,(target,state)
print('PASS: all four exported Grover circuits produce the marked state with the documented negative global phase.')
