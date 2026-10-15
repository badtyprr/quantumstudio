"""Exhaust all 3x3 binary matrices; verify inverses by products and permutations."""
import subprocess,json,re
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def run(e):return subprocess.run([str(worker),'--json'],input='quantum:'+e,encoding='utf-8',capture_output=True,timeout=30)
def apply(a,x):return sum((sum(a[r][c]*((x>>c)&1) for c in range(3))%2)<<r for r in range(3))
invertible=singular=0
for mask in range(512):
 a=[[(mask>>(3*r+c))&1 for c in range(3)] for r in range(3)]
 expr='['+';'.join(','.join(map(str,row)) for row in a)+']'
 result=run('gf2_inverse('+expr+')')
 if len({apply(a,x) for x in range(8)})!=8:
  assert result.returncode!=0,(mask,result.stdout);singular+=1;continue
 assert result.returncode==0,(mask,result.stderr)
 values=list(map(int,re.findall(r'-?\d+',json.loads(result.stdout)['text'])))
 assert len(values)==9 and set(values)<={0,1}
 b=[values[3*r:3*r+3] for r in range(3)]
 for left,right in [(a,b),(b,a)]:
  assert [[sum(left[r][k]*right[k][c] for k in range(3))%2 for c in range(3)] for r in range(3)]==[[int(r==c) for c in range(3)] for r in range(3)]
 for x in range(8):assert apply(b,apply(a,x))==x
 invertible+=1
assert (invertible,singular)==(168,344)
for e,want in [('gf2_inverse(1)','1'),('gf2_rank(gf2_inverse(identity(128)))','128'),('norm(vec(gf2_inverse([1,1;0,1])-[1,1;0,1]))','0')]:
 result=run(e);assert result.returncode==0 and json.loads(result.stdout)['text']==want,(e,result.stdout,result.stderr)
invalid=['gf2_inverse(0)','gf2_inverse([1,0,1])','gf2_inverse([1;0])','gf2_inverse([])','gf2_inverse([1,2;0,1])','gf2_inverse([1,1,0;1,0,1;0,1,1])','gf2_inverse(identity(129))','gf2_inverse([1/2,0;0,1])']
for e in invalid:
 result=run(e);assert result.returncode!=0,(e,result.stdout)
print('PASS: all 512 binary 3x3 matrices: 168 two-sided inverses and 344 singular rejections; all 1344 reversible input mappings; scalar, dimension and invalid cases.')
