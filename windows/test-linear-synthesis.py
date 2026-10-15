"""Verify compiler exports as permutations on all computational input states."""
import sys
from pathlib import Path
from openqasm3 import parse,ast
valid=0
for mask in range(512):
 a=[[(mask>>(3*r+c))&1 for c in range(3)] for r in range(3)]
 mapping=[sum((sum(a[r][c]*((x>>(2-c))&1) for c in range(3))%2)<<(2-r) for r in range(3)) for x in range(8)]
 path=Path(sys.argv[1]+f'.linear{mask}.qasm')
 if len(set(mapping))<8:
  assert not path.exists(),mask;continue
 program=parse(path.read_text(encoding='utf-8-sig'))
 gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
 for x,expected in enumerate(mapping):
  value=x
  for g in gates:
   wires=[q.indices[0][0].value for q in g.qubits];control=1<<(2-wires[0]);target=1<<(2-wires[1])
   if g.name.name=='cx':
    if value&control:value^=target
   elif g.name.name=='swap':
    if bool(value&control)!=bool(value&target):value^=control|target
   else:raise AssertionError(g.name.name)
  assert value==expected,(mask,x,value,expected)
 valid+=1
assert valid==168
print('PASS: all 168 reversible three-bit maps synthesize correctly; all 1344 basis mappings verified and all 344 singular maps rejected.')

longest=0
for case in range(8):
 base=sys.argv[1]+f'.wide{case}'
 a=[list(map(int,row.split(','))) for row in Path(base+'.matrix').read_text().split(';')]
 program=parse(Path(base+'.qasm').read_text(encoding='utf-8-sig'))
 gates=[s for s in program.statements if isinstance(s,ast.QuantumGate)]
 longest=max(longest,len(gates));assert len(gates)<=64
 for x in range(256):
  expected=sum((sum(a[r][c]*((x>>(7-c))&1) for c in range(8))%2)<<(7-r) for r in range(8))
  value=x
  for g in gates:
   wires=[q.indices[0][0].value for q in g.qubits];control=1<<(7-wires[0]);target=1<<(7-wires[1])
   if g.name.name=='cx':
    if value&control:value^=target
   elif g.name.name=='swap':
    if bool(value&control)!=bool(value&target):value^=control|target
   else:raise AssertionError(g.name.name)
  assert value==expected,(case,x)
assert longest>24
print(f'PASS: 8 eight-bit maps and 2048 input states; longest synthesized circuit has {longest} steps.')
