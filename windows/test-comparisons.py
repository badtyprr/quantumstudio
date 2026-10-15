"""Comparison predicates without disturbing Dirac delimiters."""
import os,subprocess,json,operator
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[('2=2', '1'), ('2==3', '0'), ('2!=3', '1'), ('1<2', '1'), ('1>2', '0'), ('2<=2', '1'), ('3>=2', '1'), ('1≤2', '1'), ('3≥4', '0'), ('2≠3', '1'), ('2\\leq3', '1'), ('3\\geq3', '1'), ('2\\neq2', '0'), ('0<=2<3', '1'), ('0<=3<3', '0'), ('3>2>=1', '1'), ('1+2=3', '1'), ('1=2+1', '0'), ('norm(vec(phase_function(x=3,2,x)-CZ))', '0'), ('norm(vec(phase_function(1<=x<3,2,x)-phaseoracle(2,[1,2])))', '0'), ('norm(vec(oracle_function(x>1,2,1,x)-oracle([0,0,1,1],1)))', '0'), ('norm(diffusion(2)phase_function(x==3,2,x)|++>-|11>)', '0'), ('<0|X|1>', '1'), ('<0|<1|01>', '1'), ('norm(vec(|0><0|+|1><1|-I))', '0'), ('sum(k=2,0,3,k)', '1')]
cases += [('vector(1<2,|0>)','(1, [1; 0])'), ('vector(2<1,|0>)','(0, [1; 0])'), ('vector(1<2,3<4,|0>)','(1, 1, [1; 0])'), ('vector(1<2,<0|)','(1, [1  0])'), ('norm(vec(2<0,1|-2*<01|))','0')]
invalid=['1<', '1>=', '1===2', '1><2', 'phase_function(x<y,2,x)']

for token,operation in [('=',operator.eq),('==',operator.eq),('!=',operator.ne),('<',operator.lt),('>',operator.gt),('<=',operator.le),('>=',operator.ge)]:
 for left in range(-2,3):
  for right in range(-2,3):cases.append((f'{left}{token}{right}',str(int(operation(left,right)))))
ops=[('=',operator.eq),('==',operator.eq),('!=',operator.ne),('<',operator.lt),('>',operator.gt),('<=',operator.le),('>=',operator.ge)]
for outer,compare in ops:
 for inner,test in ops:
  for left in [0,1]:
   for right in [0,1]:
    cases.append((f'(0{inner}{left}){outer}(1{inner}{right})',str(int(compare(int(test(0,left)),int(test(1,right)))))))
 for left in [0,1]:
  for right in [0,1]:
   cases.append((f'(0={left}){outer}(1!={right})',str(int(compare(int(0==left),int(1!=right))))))
cases += [('norm(vec(phase_function((x=1)!=(x=2),2,x)-(Z@Z)))','0'),('norm(vec(oracle_function((x=1)=(x=2),2,1,x)-oracle([1,0,0,1],1)))','0'),('0<=(2>1)<2','1'),('(2>1)=(3>2)=(4>3)','1'),('((1=1)=(2=2))!=0','1')]
for e,want in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==want,(e,ascii(p.stdout))
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {len(cases)} predicates, chained relations, Unicode/TeX comparisons, oracles and Dirac regressions; {len(invalid)} invalid expressions.')
