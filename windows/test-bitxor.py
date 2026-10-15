"""Width-preserving binary XOR and its composition with binary inner products."""
import os,subprocess,json,re
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def evaluate(expression):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(expression,p.stderr)
 return json.loads(p.stdout)['text']
checks=0
for left in range(16):
 for right in range(16):
  expression=f'bitxor("{left:04b}","{right:04b}")'
  actual=[int(x) for x in re.findall('[01]',evaluate(expression))]
  assert actual==[int(x) for x in f'{left^right:04b}'],(expression,actual)
  checks+=1
cases=[('bitdot(bitxor("101","110"),"011")','0'),
       ('bitdot(bitxor("001","101"),"100")','1'),
       ('bitdot(binaryxor([0;0;1],[1,0,1]),[1,0,0])','1'),
       ('xor(5,6)','3')]
for expression,want in cases:assert evaluate(expression)==want,(expression,evaluate(expression))
for s in range(8):
 for t in range(8):
  x=(s*3+t*5)%8
  expression=f'bitdot(bitxor("{s:03b}","{t:03b}"),"{x:03b}")-xor(bitdot("{s:03b}","{x:03b}"),bitdot("{t:03b}","{x:03b}"))'
  assert evaluate(expression)=='0',expression
  checks+=1
invalid=['bitxor("","0")','bitxor("01","1")','bitxor("0 1","101")','bitxor("102","101")','bitxor([2,0],[0,1])','bitxor([i,0],[0,1])','bitxor([x,0],[0,1])','bitxor(I,I)','bitxor(2,1)','bitxor("1")','bitxor("1","1","1")']
for expression in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(expression,p.stdout)
for size in [1,1024]:
 actual=[int(x) for x in re.findall('[01]',evaluate(f'bitxor("{"0"*size}","{"1"*size}")'))]
 assert actual==[1]*size,(size,len(actual))
print(f'PASS: {checks} XOR/linearity comparisons, nested composition, invalid inputs, and 1/1024-bit boundaries.')
