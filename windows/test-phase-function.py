"""Expression-defined phase oracles: independent signed basis mappings."""
import os,subprocess,json
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(e):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=40)
 assert p.returncode==0,(e,p.stderr)
 return json.loads(p.stdout)
cases=[('norm(vec(phase_function(x,1,x)-Z))', '0'), ('norm(vec(phase_function(0,3,x)-identity(8)))', '0'), ('norm(vec(phase_function(1,2,x)+identity(4)))', '0'), ('norm(vec(phase_function(floor(x/3),2,x)-CZ))', '0'), ('norm(diffusion(2)phase_function(floor(x/3),2,x)|++>-|11>)', '0'), ('norm((H @ H @ H)phase_function(bitdot("101",bits(x,3)),3,x)|+++>-|101>)', '0'), ('norm(vec(blocksum(phase_function(x,1,x),0,1,x)-(Z # Z)))', '0'), ('norm(vec(blocksum(phase_function(mod(x+k,2),1,x),0,1,k)-(Z # (-Z))))', '0'), ('norm(vec(oracle_function((tr(phase_function(x,1,x))+2)/2,1,1,x)-(I @ X)))', '0'), ('tr(phase_function(0,9,x))', '512')]
invalid=['phase_function(x,1,1)', 'phase_function(x,1,pi)', 'phase_function(x,1,x+1)', 'phase_function(x,0,x)', 'phase_function(x,10,x)', 'phase_function(x,1/2,x)', 'phase_function(x,n,x)', 'phase_function(x,2,x)', 'phase_function(-1,1,x)', 'phase_function(1/2,1,x)', 'phase_function(i,1,x)', 'phase_function(y,1,x)', 'phase_function([0,1],1,x)', 'phase_function(x,1)', 'phase_function(x,1,x,0)']

for e,want in cases:assert evaluate(e)['text']==want,(e,evaluate(e))
checks=0
for width in range(1,5):
 size=1<<width
 for secret in range(min(size,8)):
  body=f'bitdot("{secret:0{width}b}",bits(x,{width}))'
  for column in range(size):
   data=evaluate(f'phase_function({body},{width},x)basis({column},{size})')
   actual=[int(row[0].replace('−','-')) for row in data['cells']]
   sign=(-1)**((column&secret).bit_count()%2)
   assert actual==[sign if k==column else 0 for k in range(size)],(width,secret,column,actual)
   checks+=1
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {checks} independent signed basis mappings, Grover and Bernstein-Vazirani interference, bound indices, and {len(invalid)} invalid expressions.')
