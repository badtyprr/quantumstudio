"""Boolean predicates: truth tables, precedence, De Morgan identities and oracles."""
import os,subprocess,json
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[('not 0', '1'), ('not 1', '0'), ('not not 2', '1'), ('1 or 0 and 0', '1'), ('(1 or 0) and 0', '0'), ('not 2=3', '1'), ('not 2=2 or 1=1 and 0=1', '0'), ('1+(not 0)', '2'), ('norm((2<3 and not 0)|0>-|0>)', '0'), ('norm(vec(phase_function(x=1 or x=3,2,x)-(I @ Z)))', '0'), ('norm(vec(phase_function(x>=1 and x<=2,2,x)-phaseoracle(2,[1,2])))', '0'), ('norm(vec(phase_function(not x=3,2,x)+CZ))', '0'), ('norm(vec(oracle_function(x<2 and not x=0,2,1,x)-oracle([0,1,0,0],1)))', '0'), ('norm(vec(phase_function(\\neg(x=1 \\lor x=3),2,x)+(I @ Z)))', '0')]
invalid=['not', '1 and', 'or 1', '1 and or 0', '1 or or 0', '1+not 0', 'not and 1', 'phase_function(x=1 or y=3,2,x)']

for left in [0,1]:
 for right in [0,1]:
  for token in ['and','∧',r'\land',r'\wedge']:cases.append((f'{left} {token} {right}',str(left&right)))
  for token in ['or','∨',r'\lor',r'\vee']:cases.append((f'{left} {token} {right}',str(left|right)))
  cases.append((f'(not ({left} and {right}))=(not {left} or not {right})','1'))
  cases.append((f'(not ({left} or {right}))=(not {left} and not {right})','1'))
for value in [0,1,2,-3]:
 for token in ['not','¬',r'\lnot',r'\neg']:cases.append((f'{token} ({value})',str(int(not value))))
for left in [0,1,2,-3]:
 for right in [0,1,2,-3]:
  for token in ['xor','⊻',r'\veebar']:
   cases.append((f'{left} {token} {right}',str(int(bool(left)!=bool(right)))))
for a in [0,1]:
 for b in [0,1]:
  for c in [0,1]:
   cases.append((f'{a} xor {b} and {c}',str(a ^ (b & c))))
   cases.append((f'{a} or {b} xor {c}',str(a | (b ^ c))))
   cases.append((f'{a} xor {b} xor {c}',str(a ^ b ^ c)))
cases += [('not 1 xor 1','1'),('1=1 xor 2=3','1'),('xor(5,6)','3'),('2*xor(5,6)','6'),('1 xor (0)','1'),('norm(vec(phase_function(x>=2 xor x mod 2,2,x)-(Z @ Z)))','0'),('norm(vec(oracle_function(x>=2 xor x mod 2,2,1,x)-oracle([0,1,1,0],1)))','0'),('norm((H@H)phase_function(x>=2 xor x mod 2,2,x)|++>-|11>)','0')]
invalid += ['xor','xor 1','1 xor','1 xor xor 0','1+ xor 0','phase_function(x=1 xor y=3,2,x)']
for e,want in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==want,(e,ascii(p.stdout))
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {len(cases)} Boolean truth/precedence checks, Unicode/TeX spellings, compound oracles, and {len(invalid)} invalid expressions.')
