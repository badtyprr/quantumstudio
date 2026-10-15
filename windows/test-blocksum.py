"""Indexed block-diagonal operators, comparing full matrices independently."""
import json,os,subprocess
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(expression):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(expression,p.stderr)
 return json.loads(p.stdout)
cases=[
(r'norm(vec((\bigoplus_{k=0}^{1}{X^k})-CNOT))','0'),
(r'norm(vec(blocksum(P(k*pi/2),0,1,k)-controlled(S)))','0'),
(r'norm(vec(blocksum(k,-1,1,k)-[-1,0,0;0,0,0;0,0,1]))','0'),
(r'norm(vec(blocksum(blocksum(k,0,1,k),0,1,k)-[0,0,0,0;0,1,0,0;0,0,0,0;0,0,0,1]))','0'),
(r'tr(blocksum(X,5,5,k)*X)','2'),
(r'blocksum(3,0,0,k)','3'),
(r'tr(blocksum(identity(k),1,3,k))','6'),
(r'norm(vec(blocksum(tensorproduct(X,0,k,j),0,1,k)-(X # (X@X))))','0'),
]
for e,v in cases:
 assert evaluate(e)['text']==v,(e,evaluate(e))
for rows,cols in [(1,3),(3,1),(2,3),(2,2)]:
 literal='['+';'.join(','.join(f'({r+1}+({c+1})*i+k)' for c in range(cols)) for r in range(rows))+']'
 data=evaluate('blocksum('+literal+',0,2,k)')
 assert (data['rows'],data['columns'])==(3*rows,3*cols),data
 for r in range(3*rows):
  for c in range(3*cols):
   expected=complex(r%rows+1+r//rows,c%cols+1) if r//rows==c//cols else 0j
   actual=complex(data['cells'][r][c].replace('−','-').replace(' ','').replace('i','j'))
   assert actual==expected,(rows,cols,r,c,actual,expected)
for e in ['blocksum(X,1,0,k)','blocksum(X,0,32,k)','blocksum(X,0,1/2,k)','blocksum(X,0,infinity,k)','blocksum(X,0,1,pi)','blocksum(X,0,1,2)','blocksum(X,0,1,k+1)','blocksum(X,0,1000001,k)']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print('PASS: indexed block sums, controlled gates, scalar and rectangular complex blocks, nested scope, and invalid inputs.')

