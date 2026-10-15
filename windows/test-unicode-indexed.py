"""Unicode large operators must evaluate identically to their TeX forms."""
import json,subprocess,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
('∑',r'\sum','_{k=0}^{3}{k^2}','14'),
('∏',r'\prod','_{k=1}^{4}{k}','24'),
('⨂',r'\bigotimes','_{k=0}^{2}{basis(k,3)}',None),
('⨁',r'\bigoplus','_{k=0}^{1}{X^k}',None),
]
checks=0
for symbol,command,body,expected in cases:
 for bounds in [body,body.replace('_{k=0}^{2}','^{2}_{k=0}').replace('_{k=0}^{1}','^{1}_{k=0}').replace('_{k=0}^{3}','^{3}_{k=0}').replace('_{k=1}^{4}','^{4}_{k=1}'),r'\limits'+body]:
  results=[]
  for operator in (symbol,command):
   for wrap in [False,True]:
    expression=operator+bounds
    if wrap:expression=r'\left('+expression+r'\right)'
    p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,capture_output=True,encoding='utf-8',env=env,timeout=30)
    assert p.returncode==0,(expression,p.stderr)
    results.append(json.loads(p.stdout))
  assert all(x==results[0] for x in results),results
  if expected is not None:assert results[0]['text']==expected,results[0]
  checks+=1
for symbol in ['∑','∏','⨂','⨁']:
 for suffix in ['', '_{k=0}{X}', '_{k=0}^{1}X', '_{k=0}_{j=1}{X}']:
  p=subprocess.run([str(worker),'--json'],input='quantum:'+symbol+suffix,capture_output=True,encoding='utf-8',env=env,timeout=30)
  assert p.returncode!=0,(symbol,suffix,p.stdout)
print(f'PASS: {checks} Unicode/TeX equivalence groups (48 calculations), plus 16 malformed bounds/operands.')
