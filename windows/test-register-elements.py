"""Compare adjacent-register matrix elements with independent complex gates."""
import itertools, json, math, os, subprocess
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
h=1/math.sqrt(2)
states={'0':[1,0],'1':[0,1],'+':[h,h],'-':[h,-h],'i':[h,1j*h],'-i':[h,-1j*h]}
checks=0
for gate in ['CNOT','CZ','SWAP']:
 for (left,a),(right,b) in itertools.product(states.items(),repeat=2):
  state=[x*y for x in a for y in b]
  expected=([state[0],state[1],state[3],state[2]] if gate=='CNOT' else
            [state[0],state[1],state[2],-state[3]] if gate=='CZ' else
            [state[0],state[2],state[1],state[3]])
  for k,want in enumerate(expected):
   expression=f'<{k:02b}|{gate}|{left}>|{right}>'
   p=subprocess.run([str(worker),'--json','--approx'],input='quantum:'+expression,
                    capture_output=True,encoding='utf-8',env=env,timeout=30)
   assert p.returncode==0,(expression,p.stderr)
   text=json.loads(p.stdout)['text']
   actual=complex(text.replace('−','-').replace(' ','').replace('i','j'))
   assert abs(actual-want)<2e-14,(expression,actual,want)
   checks+=1
print(f'PASS: {checks} amplitudes match independent CNOT, CZ, and SWAP calculations over six single-qubit states.')
