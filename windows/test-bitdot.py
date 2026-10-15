"""Binary inner products: exact parity, vector shapes, and strict validation."""
import os,subprocess,json
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[('bitdot("101","110")', '1'), ('bitdot("111","110")', '0'), ('binarydot([1,0,1],[1,1,0])', '1'), ('bitdot([1;0;1],[1,1,0])', '1'), ('bitdot("001",[0;0;1])', '1'), ('bitdot("0","1")', '0'), ('bitdot(1,1)', '1'), ('(-1)^bitdot("101","100")', '-1'), ('sum((-1)^bitdot([1,0,1],[k,0,0]),0,1,k)', '0'), ('bitdot([1-1,2/2],[0,1])', '1')]
invalid=['bitdot("","0")', 'bitdot("10","1")', 'bitdot("1 0","10")', 'bitdot("102","101")', 'bitdot([1,2],[0,1])', 'bitdot([1/2,0],[0,1])', 'bitdot([i,0],[0,1])', 'bitdot([x,0],[0,1])', 'bitdot(I,I)', 'bitdot(2,1)', 'bitdot("1")', 'bitdot("1","1","1")', 'bitdot("1,1)']

for left in range(16):
 for right in range(16):
  cases.append((f'bitdot("{left:04b}","{right:04b}")',str((left&right).bit_count()%2)))
cases += [(f'bitdot("{"1"*1024}","{"1"*1024}")','0'),(f'bitdot("{"1"*1023}","{"1"*1023}")','1')]
invalid += [f'bitdot("{"1"*1025}","{"1"*1025}")',f'bitdot("{"0"*1024}","{"0"*1023}")']
for e,want in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text'].replace('−','-')==want,(e,ascii(p.stdout))
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print(f'PASS: {len(cases)} binary inner products and {len(invalid)} invalid expressions.')
