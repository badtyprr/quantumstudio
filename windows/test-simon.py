"""Verify exported Simon circuits against an independent oracle/Fourier model."""
import sys,math
from pathlib import Path
from openqasm3 import parse,ast

def simulate(gates,state):
 for gate in gates:
  wires=[q.indices[0][0].value for q in gate.qubits]
  mask=1<<(5-wires[0]);updated=[0j]*64;name=gate.name.name
  for column,amplitude in enumerate(state):
   if name=='h':
    updated[column&~mask]+=amplitude/math.sqrt(2)
    updated[column|mask]+=amplitude*(-1 if column&mask else 1)/math.sqrt(2)
   elif name=='cx':updated[column^(1<<(5-wires[1])) if column&mask else column]+=amplitude
   else:raise AssertionError(name)
  state=updated
 return state

for secret in range(8):
 program=parse(Path(sys.argv[1]+f'.simon{secret}.qasm').read_text(encoding='utf-8-sig'))
 gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
 assert len(gates)==9+secret.bit_count()
 pivot=secret.bit_length()-1
 f=lambda x:x ^ (secret if secret and (x>>pivot)&1 else 0)
 # The promise is exact, including the one-to-one case s=0.
 for x in range(8):
  for y in range(8):assert (f(x)==f(y))==(x==y or (x^y)==secret)
 oracle=gates[3:-3]
 assert all(g.name.name=='cx' for g in oracle)
 for column in range(64):
  initial=[0j]*64;initial[column]=1
  result=simulate(oracle,initial)
  expected=column^f(column>>3)
  assert result[expected]==1 and sum(abs(a) for a in result)==1,(secret,column)
 state=simulate(gates,[1+0j]+[0j]*63)
 expected=[sum((-1)**((x&y).bit_count()%2) for x in range(8) if f(x)==z)/8 for y in range(8) for z in range(8)]
 assert max(abs(a-b) for a,b in zip(state,expected))<2e-14,secret
 probabilities=[sum(abs(state[8*y+z])**2 for z in range(8)) for y in range(8)]
 for y,probability in enumerate(probabilities):
  want=1/8 if secret==0 else 1/4 if (y&secret).bit_count()%2==0 else 0
  assert abs(probability-want)<2e-14,(secret,y,probability)
 support=[y for y,p in enumerate(probabilities) if p>1e-12]
 candidates=[s for s in range(8) if all((y&s).bit_count()%2==0 for y in support)]
 assert candidates==([0] if secret==0 else [0,secret]),(secret,candidates)
print('PASS: 8 Simon exports; 512 reversible basis mappings; exact oracle promises; 512 Fourier amplitudes; all marginals and hidden-string constraints.')
