"""Fixed-width bits and integer decoding, checked with Python integer arithmetic."""
import os,subprocess,json,re
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(e):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 return json.loads(p.stdout)['text']
cases=[('bits(5,4)', '[0  1  0  1]'), ('bitvalue("00101")', '5'), ('bitvalue([0;1;0;1])', '5'), ('bitvalue(bits(2^100+13,128))-(2^100+13)', '0'), ('bitvalue(bits(2^1024-1,1024))-(2^1024-1)', '0'), ('bitvalue(bitxor(bits(5,4),bits(6,4)))', '3'), ('norm(|bitvalue("101")>_8-|101>)', '0'), ('bits(0,1)', '0'), ('bitvalue(1)', '1'), ('<101|H @ H @ H|011>-(-1)^bitdot(bits(5,3),bits(3,3))/sqrt(8)', '0')]
invalid=['bits(-1,3)', 'bits(8,3)', 'bits(1/2,3)', 'bits(i,3)', 'bits(x,3)', 'bits(0,0)', 'bits(0,1025)', 'bits(0,3/2)', 'bits(0,n)', 'bits(2^1024,1024)', 'bits(1)', 'bits(1,2,3)', 'bitvalue("")', 'bitvalue("102")', 'bitvalue([0,2])', 'bitvalue(I)', 'bitvalue([0,x])', 'bitvalue("1","0")']

for e,want in cases:assert evaluate(e)==want,(e,evaluate(e))
checks=0
for width in range(1,9):
 for value in range(min(1<<width,32)):
  bits=f'{value:0{width}b}'
  assert ''.join(re.findall('[01]',evaluate(f'bits({value},{width})')))==bits,(value,width)
  assert evaluate(f'bitvalue("{bits}")')==str(value),(value,width)
  checks+=2
for x in range(8):
 for y in range(8):
  e=f'<{y:03b}|H @ H @ H|{x:03b}>-(-1)^bitdot(bits({x},3),bits({y},3))/sqrt(8)'
  assert evaluate(e)=='0',e
  checks+=1
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {checks} independent conversions and Walsh-Hadamard coefficients, exact large integers, and {len(invalid)} invalid inputs.')
