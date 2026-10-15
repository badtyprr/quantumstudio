"""Comma-separated register labels and unambiguous function arguments."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
cases=[('norm(|0,1>-|01>)', '0'), ('norm(|00,1>-|001>)', '0'), ('norm(|+,i>-(|+>@|i>))', '0'), ('norm(|Phi+,1>-(|Phi+>@|1>))', '0'), ('norm(|0^2,1>-|001>)', '0'), ('<0,1|0,1>', '1'), ('<i,-|i,->', '1'), ('<i,-|-i,->', '0'), ('<1,1|CNOT|+,0>-1/sqrt(2)', '0'), ('norm(CNOT|+,0>-|Phi+>)', '0'), ('norm(vec(|0,1><1,0|-|01><10|))', '0'), ('norm(<i,-|†-|i,->)', '0'), ('norm(\\ket{0,1}-|01>)', '0'), ('\\braket{i,-|i,-}', '1'), ('norm(|mod(5,3)>_3-|2>_3)', '0'), ('<mod(5,3)|_3 mod(8,3)>_3', '1'), ('norm(|0,1>|1>-|011>)', '0'), ('<0,1|<1|011>', '1'), ('norm(| 0 , 1 , 0 >-|010>)', '0')]
invalid=['|0,>', '|,1>', '|0,,1>', '|0,2>', '|0,1>_4', '<0,1|_4 1>_4', '|0;1>', '|0,(1,0)>', '<0,1|0>', '|0,1,0,1,0,1,0,1,0,1,0>']

cases += [('norm((tensor(<0|,<1|)-<01|)†)','0'),('norm(tensor(|0,1>,|0>)-|010>)','0'),('tensor(<0|,<1|)|01>','1'),('norm(vec([<0|;<1|]-I))','0')]
for e,want in cases:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==want,(e,ascii(p.stdout))
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print(f'PASS: {len(cases)} exact comma-register checks and {len(invalid)} invalid expressions.')
