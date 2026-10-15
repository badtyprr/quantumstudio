"""Modulo notation in arithmetic and order-finding basis labels."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
(r'17 mod 5','2'),(r'17\bmod 5','2'),(r'17\mod 5','2'),(r'17\mathrm{mod}5','2'),
(r'-17 mod 5','3'),(r'2+7 mod 3','3'),(r'(2+7) mod 3','0'),(r'2*7 mod 5','4'),(r'17 mod 5 * 2','4'),
(r'norm(|2*7\bmod 15>_{15}-|14>_15)','0'),
(r'<2*7 mod 15|14>_15','1'),(r'<14|2*7 mod 15>_15','1'),
(r'norm(vec(\sum_{k=0}^{14}{|2*k\bmod 15>_16<k|_16}+|15>_16<15|_16-modmul(2,15)))','0'),
(r'norm(\sum_{k=0}^{3}{|2^k\bmod 15>_15}/2-(|1>_15+|2>_15+|4>_15+|8>_15)/2)','0'),
(r'17%5','2'),(r'mod(17,5)','2'),(r'2mod(17,5)','4'),
]
for e,v in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
for e in [r'17\bmod',r'\bmod 5',r'17\pmod{5}',r'|17 mod 0>_3',r'|17 mod 5>_2']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print('PASS: modular notation, precedence, negative dividends, computed ket/bra labels, and the full order-finding permutation matrix.')
