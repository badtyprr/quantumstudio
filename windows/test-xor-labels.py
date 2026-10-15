"""Literal XOR basis labels checked against integer XOR and oracle action."""
import json
import subprocess
from pathlib import Path

worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
checks=0
def run(expression):
    return subprocess.run([str(worker),'--json'],input='quantum:'+expression,
                          encoding='utf-8',capture_output=True,timeout=30)
def equal(a,b):
    global checks
    result=run('norm(vec(('+a+')-('+b+')))')
    assert result.returncode==0,(a,result.stderr)
    assert json.loads(result.stdout)['text']=='0',(a,b,result.stdout)
    checks+=1

for a in range(8):
    for b in range(8):
        x,y,z=(format(v,'03b') for v in (a,b,a^b))
        equal('|'+x+' ⊕ '+y+'⟩','|'+z+'>')
        equal('⟨'+x+' ⊕ '+y+'|','<'+z+'|')
for a,b in [
    (r'\ket{001\oplus 101}','|100>'),
    (r'\bra{001\oplus 101}','<100|'),
    ('|001⊕101⊕110>','|010>'),
    ('|01,001⊕101>','|01100>'),
    ('|0⊕1>|1⊕1>','|10>'),
    ('|0000000001⊕1000000000>','|1000000001>'),
    ('X⊕Z','directsum(X,Z)'),
    (r'X\oplus Z','directsum(X,Z)')]:
    equal(a,b)
for x in range(2):
    for y in range(8):
        equal(f'oracle([5,3],3)|{x},{y:03b}>',
              f'|{x},{y:03b}⊕{[5,3][x]:03b}>')
invalid=['1⊕1','|01⊕1>','|⊕1>','|1⊕>','|1⊕⊕0>','|2⊕1>',
         '|x⊕1>','|1⊕f(0)>','|+⊕1>','|11111111111⊕00000000000>']
for expr in invalid:
    result=run(expr)
    assert result.returncode!=0,(expr,result.stdout)
print(f'PASS: {checks} XOR label and direct-sum checks, {len(invalid)} invalid labels.')
