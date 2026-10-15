"""Exact finite binary numeral tests motivated by qBraid's QPE lesson."""
import json
import random
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
worker=root/'dist/QuantumStudio/quantum-worker.exe'
checks=0
def run(expression):
    return subprocess.run([str(worker),'--json'],input='quantum:'+expression,
                          encoding='utf-8',capture_output=True,timeout=30)
def equal(source,expected):
    global checks
    result=run('('+source+')==('+expected+')')
    assert result.returncode==0,(source,result.stderr)
    data=json.loads(result.stdout)
    assert data['text']=='1' and not data['approximate'],(source,expected,result.stdout)
    checks+=1
rng=random.Random(991)
for width in (1,2,3,5,8,16,64):
    for trial in range(5):
        bits=''.join(str(rng.randrange(2)) for _ in range(width))
        split=rng.randrange(width+1)
        numeral=bits[:split]+'.'+bits[split:]
        expected=str(int(bits,2))+'/2^'+str(width-split)
        for suffix in ('_2','₂','_{2}'):
            equal(numeral+suffix,expected)
for source,expected in [('0.100₂','1/2'),('101_2','5'),('-1.01_2','-5/4'),
                        ('0.1_2^2','1/4'),('-0.1_2^2','-1/4'),
                        ('0.1₂+0.01₂','3/4'),('0.100','1/10'),('1e-3','1/1000'),
                        ('norm(0.1_2|0>)','1/2'),('norm(|1>_3)','1'),
                        ('norm(vec(Rz(2*pi*0.100_2)-Rz(pi)))','0'),
                        ('norm(vec(H[0.1_2;0.1_2]-H[1/2;1/2]))','0')]:
    equal(source,expected)
equal('1'*1024+'_2','2^1024-1')
equal('0.'+'0'*1022+'1₂','1/2^1023')
invalid=['0.102_2','2_2','0..1_2','._2','0.1_3','0.1_20',
         '1e2_2','0.1_{x}','0.1_2_2','1'*1025+'_2']
for source in invalid:
    result=run(source)
    assert result.returncode!=0,(source,result.stdout)
print(f'PASS: {checks} exact binary numeral identities and {len(invalid)} malformed numerals.')
