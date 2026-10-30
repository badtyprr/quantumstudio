"""Compile-time array compatibility and runtime allocation selection."""
import argparse,hashlib,importlib.util,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path);args=p.parse_args()
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('array_adapter',root/'qasm-import.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; qubit q; '
checks=0
def convert(source):
 global checks
 result=adapter.convert(source,classical=True);checks+=1
 if args.frozen:
  run=subprocess.run([str(args.frozen),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert run.returncode==0,run.stderr
  assert json.loads(run.stdout)==result;checks+=1
 return result
def reject(body,marker='compile-time array'):
 global checks
 source=header+body
 try:adapter.convert(source,classical=True)
 except Exception as error:
  assert marker in str(error).lower(),str(error)
 else:raise AssertionError('Accepted runtime or oversized array: '+body)
 checks+=1
 if args.frozen:
  run=subprocess.run([str(args.frozen),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert run.returncode and marker.encode() in run.stderr.lower(),run.stderr;checks+=1
for body in (
 'array[bool,1] a={true}; if(a[0]) x q;',
 'array[int[32],2] a={1,2}; if(a[0]+a[1]==3) x q;',
 'array[uint[8],2] a={1,2}; a[1]=a[1]+1; if(a[1]==3) x q;',
 'array[float[64],1] a={0.5}; if(a[0]==0.5) x q;',
 'array[bool,2,2] a={{false,true},{true,false}}; if(a[1,0]) x q;',
 'array[bool,2] a={false,false}; for int i in [0:1]{a[i]=true;} if(a[0] && a[1]) x q;',
 'array[bool,1] a={false}; if(true){a[0]=true;} if(a[0]) x q;',
):
 steps=convert(header+body)['Steps'];assert len(steps)==1 and steps[0]['Expression']=='X' and steps[0]['Wires']==[0],steps
reference=convert(header+'def set(mutable array[int[32], #dim=1] target){target[0]=1;} array[int[32],1] a={0}; set(a); if(a[0]==1) x q;')
assert reference['Version']==16 and any(step['Kind']=='CheckArrayReferences' for step in reference['Steps'])
assert convert(header+'array[bool,1] a={true};')['Steps']==[]
assert convert(header+'array[bool,65536] a;')['Steps']==[]
branch=convert(header+'bit c="1"; array[bool,1] a={true}; if(c==1){if(a[0]) x q;}')['Steps'][-1]
assert branch['Kind']=='Branch' and branch['WhenTrue'][0]['Expression']=='X'
for body in (
 'bit c="0"; array[bool,1] a={false}; if(c==1){a[0]=true;} if(a[0]) x q;',
 'bit c="0"; array[bool,1] a={false}; while(c==1){a[0]=true;}',
 'bit c="0"; array[bool,1] a={false}; if(c==1){if(true){a[0]=true;}}',
 'int n=1; array[bool,1] a={false}; for int i in [0:n]{a[0]=true;}',
 'int n=1; array[int[32],1] a={n};',
 'int n=1; array[int[32],1] a={0}; a[0]=n;',
):
 assert convert(header+body)['Version']==15
for body in (
 'array[bool,1000000000] a;',
 'array[bool,257,256] a;',
 'array[bool,40000] a; array[bool,40000] b;',
):reject(body)
assert convert(header+'def set(mutable array[int[32], #dim=1] target){target[0]=1;} bit c="0"; array[int[32],1] a={0}; if(c==1){set(a);}')['Version']==16
reject('bit c="0"; if(c==1){array[bool,1] a={true};}','arrays can only be declared globally')
# Unchanged QASM string extracted from qBraid notebook qasm_unroll.ipynb,
# revision86787e1ba372facc224f925189755e69c479828b; no gates/angles rewritten.
source=(root/'fixtures/qb-arrays/ripple-carry.qasm').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='503bda0e6df9ad1e0eb858606ef092c4eeab07be73cb1d29b0ee0ccbaa5d12ad'
doc=convert(source);assert doc['Qubits']==10 and doc['OutputBits']==[4,3,2,1,0]
# Independent Boolean simulation suffices for these reversible basis gates.
bits=[0]*10;record=[0]*5
for step in doc['Steps']:
 wires=step['Wires']
 if step['Kind']=='Reset':bits[wires[0]]=0
 elif step['Kind']=='Measure':record[step['ClassicalBit']]=bits[wires[0]]
 else:
  assert step['Kind']=='Gate' and step['Expression'] in ('X','CNOT','CCX')
  assert len(wires)=={'X':1,'CNOT':2,'CCX':3}[step['Expression']]
  if all(bits[i] for i in wires[:-1]):bits[wires[-1]]^=1
assert ''.join(str(record[i]) for i in doc['OutputBits'])=='10111',record
print('PASS: %d array import checks and unchanged ripple-carry result 10111.'%checks)
