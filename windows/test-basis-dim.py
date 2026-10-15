"""Computed Hilbert-space dimensions and subscript scope."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
(r'norm(|7>_{2^3}-|111>)','0'),
(r'norm(|7>_(2^3)-basis(7,8))','0'),
(r'<7|_{2^3}|7>_{4+4}','1'),
(r'<7|_{2^3}7>_{4+4}','1'),
(r'\sum_{n=1}^{3}{<0|_{2^n}0>_{2^n}}','3'),
(r'norm(\sum_{k=0}^{7}{\ket{k}_{2^3}}/sqrt(8)-H^{\otimes 3}|000>)','0'),
(r'norm(\bigotimes_{k=2}^{4}{|k-1>_{k}}-(|1>_2@|2>_3@|3>_4))','0'),
(r'norm(vec(\sum_{k=0}^{3}{|k>_{2^2}<k|_{2^2}}-identity(4)))','0'),
(r'norm(|10>_{2^4}-basis(10,16))','0'),
(r'norm(|1>_{3+1}-|01>)','0'),
(r'<0|_{2^2}identity(4)|0>_{2+2}','1'),
]
for e,v in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
invalid=[r'|0>_{1}',r'|0>_{2^11}',r'|0>_{3/2}',r'|0>_{i}',r'|0>_{d}',r'|4>_{2^2}',r'<0|_3 0>_4',r'<0|_{2+1}0>_{2^2}',r'|0>_{}',r'|0>_{[2,3]}']
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print('PASS: computed dimensions, index-dependent dimensions, equivalent dimensions, subscript scope, and invalid/mismatched dimensions.')
