"""Expression-defined reversible oracles checked on every computational input."""
import os,subprocess,json
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(e):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=40)
 assert p.returncode==0,(e,p.stderr)
 return json.loads(p.stdout)
cases=[('norm(vec(oracle_function(x,1,1,x)-CNOT))', '0'), ('norm(vec(oracle_function(1-x,1,1,x)-oracle([1,0],1)))', '0'), ('norm(vec(oracle_function(mod(x*x+1,4),2,2,x)-oracle([1,2,1,2],2)))', '0'), ('norm((H @ H @ H @ I)oracle_function(bitdot("101",bits(x,3)),3,1,x)(H @ H @ H @ I)|000,->-|101,->)', '0'), ('norm(vec(blocksum(oracle_function(x,1,1,x),0,1,x)-(CNOT # CNOT)))', '0'), ('norm(vec(blocksum(oracle_function(mod(x+k,2),1,1,x),0,1,k)-(CNOT # oracle([1,0],1))))', '0'), ('tr(oracle_function(0,8,1,x))', '512'), ('norm(vec(oracle_function(mod(x+1,4),2,2,x)^2-identity(16)))', '0')]
invalid=['oracle_function(x,1,1,1)', 'oracle_function(x,1,1,pi)', 'oracle_function(x,1,1,x+1)', 'oracle_function(x,0,1,x)', 'oracle_function(x,1,0,x)', 'oracle_function(x,5,5,x)', 'oracle_function(x,1/2,1,x)', 'oracle_function(x,n,1,x)', 'oracle_function(x,2,1,x)', 'oracle_function(-1,1,1,x)', 'oracle_function(1/2,1,1,x)', 'oracle_function(i,1,1,x)', 'oracle_function(y,1,1,x)', 'oracle_function([0,1],1,1,x)', 'oracle_function(x,1,1)']

for e,want in cases:assert evaluate(e)['text']==want,(e,evaluate(e))
functions=[]
for n,m in [(1,1),(2,1),(2,2),(3,2),(4,1)]:
 functions.append((n,m,f'mod(x*x+3*x+1,{1<<m})',lambda x,m=m:(x*x+3*x+1)%(1<<m)))
for secret in range(8):functions.append((3,1,f'bitdot("{secret:03b}",bits(x,3))',lambda x,s=secret:(x&s).bit_count()%2))
checks=0
for n,m,body,f in functions:
 size=1<<(n+m)
 for column in range(size):
  data=evaluate(f'oracle_function({body},{n},{m},x)basis({column},{size})')
  expected=((column>>m)<<m)|((column&((1<<m)-1))^f(column>>m))
  assert data['rows']==size and data['columns']==1,data
  actual=[int(row[0]) for row in data['cells']]
  assert actual==[int(k==expected) for k in range(size)],(n,m,column,expected,actual)
  checks+=1
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {checks} oracle basis mappings, exact phase kickback, nested index scope, maximum dimension, and {len(invalid)} invalid expressions.')
