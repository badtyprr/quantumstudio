"""Adjacent Dirac factors: tensor grouping versus matrix contraction."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[
('<0|<1|CNOT|0>|1>','1'),
('<1|<1|CNOT|+>|0>-1/sqrt(2)','0'),
('<1|<0|CNOT|+>|0>','0'),
('<i|<-|i>|->','1'),
('<i|<-|I @ I|i>|->','1'),
('<0|<1|0>|1>','1'),
('<0|<1|01>','1'),
('<0|<1| |0>|1>','1'),
('<2|_3<1|identity(6)|2>_3|1>','1'),
('<2|_3<1|2>_3|1>','1'),
('<0|<1|1>|0>','0'),
('<0|<1|<0|010>','1'),
('norm((<0|<1|)†-|01>)','0'),
('<0|<1|†','0'),
('<i|<i|†','1'),
('<0|0>|1>-|1>','[0; 0]'),
('\\bra{1}\\bra{1}CNOT\\ket{+}\\ket{0}-1/sqrt(2)','0'),

('<00|CNOT|+>|0>-1/sqrt(2)','0'),
('<11|CNOT|+>|0>-1/sqrt(2)','0'),
('<01|CNOT|1>|0>','0'),
('<11|CNOT|1>|0>','1'),
('<00|CNOT|+>|0>^2','0.5'),
('<00|CNOT|+>|0>+<11|CNOT|+>|0>-sqrt(2)','0'),
('<11|I @ Y|1>|0>-i','0'),
('<101|identity(8)|1>|0>|1>','1'),
('<5|_6 identity(6)|2>_3|1>','1'),
('\\bra{11}CNOT\\ket{+}\\ket{0}-1/sqrt(2)','0'),
('<00|CNOT+identity(4)|+>|0>-sqrt(2)','0'),

(r'norm(|0>|1>-|01>)','0'),(r'norm(|0>|1>|0>-|010>)','0'),
(r'norm(CNOT|0>|1>-|01>)','0'),(r'norm(CNOT|1>|0>-|11>)','0'),
(r'norm(CNOT|+>|0>-|Φ+>)','0'),(r'norm(-|0>|1>+|01>)','0'),
(r'norm(|i>|->-(|i>@|->))','0'),(r'norm(|2>_3|1>-basis(5,6))','0'),
(r'norm(\ket{0}\ket{1}-|01>)','0'),(r'norm(|Φ+>|1>-(|001>+|111>)/sqrt(2))','0'),
(r'(<0|<1|)(|0>|1>)','1'),(r'(<i|<-|)(|i>|->)','1'),
(r'norm(vec(|0>|1><0|<1|-density(|01>)))','0'),
(r'<0|1>','0'),(r'<i|i>','1'),(r'norm(vec(|0><1|-[0,1;0,0]))','0'),
(r'|0>†|0>','1'),(r'(<0|†)†|0>','1'),
(r'norm(vec(X Y-iZ))','0'),(r'norm(vec([1,0;0,1][0,1;1,0]-X))','0'),
]
for e,v in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
for e in [r'|0>*|1>',r'[1;0][0;1]',r'CNOT|0>',r'(<0|<1|)|0>']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print('PASS: adjacent registers, gate scope, complex and mixed-dimensional states, grouped bras, outer products, and unchanged matrix arithmetic.')
