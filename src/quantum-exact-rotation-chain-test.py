"""Exact rotation chains must simplify without recursive addition overflow."""
import json, math, os, struct, subprocess, sys
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
def nums(*values):return ''.join(str(v)+'\n' for v in values).encode()
def rotation(value,axis=0):return nums(16,0,axis,0,struct.unpack('>Q',struct.pack('>d',value))[0])
def gate(text):
 value=text.encode();return nums(0,1,0,len(value))+value
checks=0
for axis,name in [(0,'Rx'),(1,'Ry')]:
 for fixed_inverse in (True,False):
  steps=[rotation(i,axis) for i in (1,2,3,4)]
  steps.append(gate(name+'(-10)') if fixed_inverse else rotation(-10,axis))
  steps.append(nums(1,0,0))
  request=b'QEXACT10\n'+nums(1,1,0,1000,1,0,len(steps))+b''.join(steps)
  result=subprocess.run([str(worker),'--exact-circuit'],input=request,capture_output=True,timeout=20)
  assert result.returncode==0,(result.returncode,result.stderr)
  actual=json.loads(result.stdout)['probabilities'];assert '0' in actual,actual
  for key,expression in actual.items():
   value=subprocess.run([str(worker),'--json','--approx'],input=expression.encode(),capture_output=True,timeout=20)
   assert value.returncode==0,value.stderr
   number=float(json.loads(value.stdout)['text'].replace('−','-'))
   assert abs(number-(1 if key=='0' else 0))<1e-10,(key,number)
  checks+=1
print('PASS: %d exact rotation cancellation chains.'%checks)
