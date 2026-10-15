"""Compare adjacent-register matrix elements with independent complex gates."""
import itertools, json, math, os, subprocess, sys
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
  for u,v in [('0','0'),('0','1'),('1','0'),('1','1'),('i','+'),('-i','i'),('+','-'),('-','i')]:
   output=[complex(x*y) for x in states[u] for y in states[v]]
   want=sum(x.conjugate()*y for x,y in zip(output,expected))
   expression=(f'<{u},{v}|{gate}|{left},{right}>' if '--commas' in sys.argv else f'<{u}|<{v}|{gate}|{left}>|{right}>') 
   p=subprocess.run([str(worker),'--json','--approx'],input='quantum:'+expression,
                    capture_output=True,encoding='utf-8',env=env,timeout=30)
   assert p.returncode==0,(expression,p.stderr)
   text=json.loads(p.stdout)['text']
   actual=complex(text.replace('−','-').replace(' ','').replace('i','j'))
   assert abs(actual-want)<2e-14,(expression,actual,want)
   checks+=1
print(f'PASS: {checks} multi-bra amplitudes match independent complex contractions for CNOT, CZ, and SWAP.')

invalid=['<0|<1|CNOT|0>', '<0|<1|0>', '<0|<2|00>',
         '<2|_3<1|identity(4)|2>_3|1>', '<0|<1',
         '<0|<1|0>|', '<0|<1|CNOT|0>|', '<0|'*514]
for expression in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,
                  capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(expression,p.stdout)
print('PASS: malformed output registers, incompatible dimensions, and excessive factor counts are rejected.')
