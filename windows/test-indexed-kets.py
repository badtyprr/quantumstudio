"""Dimension-qualified computed basis labels in quantum algorithm formulas."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
(r"<1+1|mod(5,3)>_3","1"),
(r'norm(|1+1>_3-|2>_3)','0'),
(r'norm(\sum_{k=0}^{3}{\ket{k}_4}/2-H^{\otimes 2}|00>)','0'),
(r'norm(\bigotimes_{k=0}^{2}{\ket{k}_3}-(|0>_3@|1>_3@|2>_3))','0'),
(r'\sum_{k=0}^{3}{<k|k>_4}','4'),
(r'norm(vec(\sum_{k=0}^{2}{|k>_3<k|_3}-identity(3)))','0'),
(r'norm(\sum_{k=0}^{3}{exp(2*pi*i*k/4)|k>_4}/2-QFT(2)|01>)','0'),
(r'<1+1|_3|2>_3','1'),
(r'<mod(5,3)|_3|2>_3','1'),
(r'norm(|mod(5,3)>_3-|2>_3)','0'),
(r'norm(|001>-basis(1,8))','0'),
(r'norm(|001>_3-basis(1,3))','0'),
]
for e,v in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
for e in [r'|-1>_3',r'|3+1>_3',r'|1/2>_3',r'|i>_3',r'|H>_3',r'|k>_3',r'|1+>_3',r'|[0,1]>_3',r'|k+1>']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print('PASS: computed basis indices, superposition sums, resolution of identity, Fourier phases, bras, and preserved binary labels.')
