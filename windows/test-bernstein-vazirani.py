"""Independently simulate exported BV circuits, preserving the ancilla phase."""
import sys, math
from pathlib import Path
from openqasm3 import parse, ast
for secret in range(8):
 program=parse(Path(sys.argv[1]+f'.bv{secret}.qasm').read_text(encoding='utf-8-sig'))
 gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
 assert len(gates)==8+secret.bit_count()
 state=[1+0j]+[0j]*15
 for gate in gates:
  wires=[q.indices[0][0].value for q in gate.qubits]
  mask=1<<(3-wires[0]);updated=[0j]*16;name=gate.name.name
  for column,amplitude in enumerate(state):
   if name=='h':
    updated[column&~mask]+=amplitude/math.sqrt(2)
    updated[column|mask]+=amplitude*(-1 if column&mask else 1)/math.sqrt(2)
   elif name=='x':updated[column^mask]+=amplitude
   elif name=='cx':updated[column^(1<<(3-wires[1])) if column&mask else column]+=amplitude
   else:raise AssertionError(name)
  state=updated
 expected=[(1 if k==2*secret else -1 if k==2*secret+1 else 0)/math.sqrt(2) for k in range(16)]
 assert max(abs(a-b) for a,b in zip(state,expected))<2e-14,(secret,state)
 probabilities=[abs(state[2*k])**2+abs(state[2*k+1])**2 for k in range(8)]
 assert abs(probabilities[secret]-1)<2e-14,(secret,probabilities)
print('PASS: all eight exported Bernstein-Vazirani circuits recover the hidden string and preserve the |-> ancilla phase.')
