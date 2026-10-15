"""Independent simulation of the exported phase-estimation preset."""
import sys,math,cmath
from pathlib import Path
from openqasm3 import parse,ast
base=sys.argv[1]
def angle(node):
    if isinstance(node,ast.Identifier):
        assert node.name=='pi';return math.pi
    if isinstance(node,(ast.IntegerLiteral,ast.FloatLiteral)):return node.value
    if isinstance(node,ast.UnaryExpression):
        assert node.op.name=='-';return -angle(node.expression)
    assert isinstance(node,ast.BinaryExpression)
    a,b=angle(node.lhs),angle(node.rhs)
    return {'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[node.op.name]()
for suffix,theta in [(str(k),k*math.pi/4) for k in range(8)]+[('-half',math.pi/8)]:
    program=parse(Path(base+'.qpe'+suffix+'.qasm').read_text(encoding='utf-8-sig'))
    gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
    assert len(gates)==14
    state=[complex(k==0) for k in range(16)]
    for gate in gates:
        name=gate.name.name;wires=[q.indices[0][0].value for q in gate.qubits]
        updated=[0j]*16
        for column,amplitude in enumerate(state):
            mask=1<<(3-wires[0])
            if name=='h':
                bit=int(bool(column&mask));updated[column&~mask]+=amplitude/math.sqrt(2);updated[column|mask]+=amplitude*((-1)**bit)/math.sqrt(2)
            elif name=='x':updated[column^mask]+=amplitude
            elif name=='cp':
                second=1<<(3-wires[1]);updated[column]+=amplitude*(cmath.exp(1j*angle(gate.arguments[0])) if column&mask and column&second else 1)
            elif name=='swap':
                second=1<<(3-wires[1]);target=column^(mask|second) if bool(column&mask)!=bool(column&second) else column;updated[target]+=amplitude
            else:raise AssertionError(name)
        state=updated
    expected=[0j]*16
    for k in range(8):expected[2*k+1]=sum(cmath.exp(1j*x*(theta-2*math.pi*k/8)) for x in range(8))/8
    assert max(abs(a-b) for a,b in zip(state,expected))<5e-14,(suffix,state,expected)
    assert abs(sum(abs(a)**2 for a in state)-1)<5e-14
print('PASS: 9 phase-estimation exports match the analytic Fourier sum, including all exact three-bit phases and an inexact phase, with complex phases preserved.')
