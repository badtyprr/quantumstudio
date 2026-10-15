"""Repeated all-zero/all-one registers with preserved basis-index semantics."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
(r'norm(|0^3>-|000>)','0'),(r'norm(|1^3>-|111>)','0'),
(r'norm(\ket{0^{3}}-|000>)','0'),(r'norm(|1³⟩-|111>)','0'),
(r'<0^3|0^3>','1'),(r'<0^3|1^3>','0'),(r'<1^{3}|X^{\otimes 3}|0^{3}>','1'),
(r'\sum_{n=1}^{4}{<0^n|0^n>}','4'),
(r'norm(|0^(1+2)>-|000>)','0'),(r'norm(| 1 ^ (2+1) >-|111>)','0'),
(r'|0^0>','1'),(r'|1^0>','1'),
(r'norm(|1^3>_8-basis(1,8))','0'),
(r'norm(|0^3>_8-basis(0,8))','0'),
(r'norm(|1^10>-basis(1023,1024))','0'),
(r'norm(\bigotimes_{k=1}^{3}{|0^k>}-|000000>)','0'),
]
for e,v in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
invalid=[r'|0^-1>',r'|0^11>',r'|0^(1/2)>',r'|0^n>',r'|0^i>',r'|0^H>',r'|0^>',r'|0^2+1>',r'<0^2|0^3>']
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print('PASS: repeated registers, TeX/Unicode powers, bras, indexed counts, zero/ten-qubit cases, and dimension-qualified arithmetic labels.')
