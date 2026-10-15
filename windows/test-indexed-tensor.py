"""Exact indexed tensor products, order, lexical scope, and rejected bounds."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
(r'norm((\bigotimes_{k=0}^{2}{basis(k,3)})-(|0>_3@|1>_3@|2>_3))','0'),
(r'tr((\bigotimes_{k=1}^{2}{Rz(k*pi)})-(Rz(pi)@Rz(2*pi)))','0'),
(r'norm(tensorproduct(Ry(k*pi),0,2,k)|000>+|010>)','0'),
(r'(\bigotimes_{k=1}^{2}{<i|})|11>','−0.5'),
(r'norm(tensorproduct(basis(k+1,3),-1,1,k)-(|0>_3@|1>_3@|2>_3))','0'),
(r'tensorproduct(<0|,0,2,k)|000>','1'),
(r'tr(tensorproduct(X,3,3,k)X)','2'),
(r'norm(tensorproduct(tensorproduct(basis(k,2),0,1,k),0,1,k)-|0101>)','0'),
(r'norm(tensorproduct(tensorproduct(basis(j,2),0,k,j),0,1,k)-|001>)','0'),
]
for e,expected in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==expected,(e,ascii(p.stdout))
for e in ['tensorproduct(X,2,1,k)','tensorproduct(X,0,32,k)','tensorproduct(X,0,1/2,k)','tensorproduct(X,0,infinity,k)','tensorproduct(X,0,1,2)','tensorproduct(X,0,1,k+1)','tensorproduct(X,-1000001,0,k)','tensorproduct(2,0,1,k)']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print('PASS: indexed tensor products, complex bras, wire ordering, nested scope, and invalid inputs.')

