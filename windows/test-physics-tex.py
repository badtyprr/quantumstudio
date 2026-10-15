"""Physics-package Dirac macros: aliases, conjugation, sizing, and scope."""
import subprocess,json
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
cases=[]
for name in ['expectationvalue','expval','ev']:
 for stars in ['','*','**']:
  for op,state,value in [('X','+','1'),('Y','i','1'),('Z','1','-1'),('X+Z','0','1'),('X@X','Phi+','1')]:
   cases.append((f'\\{name}{stars}{{{op}}}{{{state}}}',value))
for name in ['matrixelement','matrixel','mel']:
 for stars in ['','*','**']:
  for left,op,right,value in [('0','X','1','1'),('0','Y','1','-i'),('i','Y','i','1'),('1,1','CNOT','1,0','1')]:
   cases.append((f'\\{name}{stars}{{{left}}}{{{op}}}{{{right}}}',value))
for name in ['dyad','op','ketbra','outerproduct']:
 for stars in ['','*']:
  cases.append((f'norm(vec(\\{name}{stars}{{i}}-density(|i>)))','0'))
  cases.append((f'norm(vec(\\{name}{stars}{{0}}{{1}}^2))','0'))
  cases.append((f'norm(vec(\\{name}{stars}{{0}}{{1}}†-|1><0|))','0'))
for name in ['braket','Braket','innerproduct','ip']:
 for stars in ['','*']:
  cases.append((f'\\{name}{stars}{{i}}','1'))
  cases.append((f'\\{name}{stars}{{i}}{{-i}}','0'))
cases += [(r'\bra*{i}Y\ket*{i}','1'),(r'\mel{0}{X+Y}{1}-(1-i)','0'),(r'\expval{Z}{1}^2','1'),(r'\braket{0|X|1}','1')]
invalid=[r'\expval{X}',r'\ev{}{}',r'\matrixel{0}{X}',r'\mel{0}{}{1}',r'\ev***{X}{0}',r'\dyad**{0}',r'\ip{}',r'\ket**{0}',r'\expval{X}{0']
for e,want in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 got=json.loads(p.stdout)['text'].replace('−','-')
 assert got==want,(e,ascii(p.stdout))
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {len(cases)} physics-package Dirac macro checks and {len(invalid)} invalid inputs.')
