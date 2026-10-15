"""Independent basis permutations and binary products for linear gates."""
import subprocess,json,re,random
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def run(e):return subprocess.run([str(worker),'--json'],input='quantum:'+e,encoding='utf-8',capture_output=True,timeout=30)
def evaluate(e):
 p=run(e);assert p.returncode==0,(e,p.stderr)
 return json.loads(p.stdout)['text']
def matrix(a):return '['+';'.join(','.join(map(str,row)) for row in a)+']'
def numbers(s):return list(map(int,re.findall(r'-?\d+',s)))
valid=[];rejected=0
for mask in range(512):
 a=[[(mask>>(3*r+c))&1 for c in range(3)] for r in range(3)]
 mapping=[sum((sum(a[r][c]*((x>>(2-c))&1) for c in range(3))%2)<<(2-r) for r in range(3)) for x in range(8)]
 p=run('linear_gate('+matrix(a)+')')
 if len(set(mapping))<8:
  assert p.returncode!=0,(a,p.stdout);rejected+=1;continue
 assert p.returncode==0,(a,p.stderr)
 entries=numbers(json.loads(p.stdout)['text'])
 assert entries==[int(r==mapping[c]) for r in range(8) for c in range(8)],a
 valid.append(a)
assert len(valid)==168 and rejected==344
rng=random.Random(927)
for _ in range(80):
 m,k,n=[rng.randrange(1,6) for _ in range(3)]
 a=[[rng.randrange(2) for _ in range(k)] for _ in range(m)]
 b=[[rng.randrange(2) for _ in range(n)] for _ in range(k)]
 expected=[sum(a[r][i]*b[i][c] for i in range(k))%2 for r in range(m) for c in range(n)]
 assert numbers(evaluate('gf2_mul('+matrix(a)+','+matrix(b)+')'))==expected
for _ in range(16):
 a,b=[matrix(rng.choice(valid)) for _ in range(2)]
 assert evaluate('norm(vec(linear_gate(gf2_mul('+a+','+b+'))-linear_gate('+a+')linear_gate('+b+')))')=='0'
 assert evaluate('norm(vec(linear_gate(gf2_inverse('+a+'))-linear_gate('+a+')†))')=='0'
for e,want in [('norm(vec(linear_gate([1,0;1,1])-CNOT))','0'),('norm(vec(linear_gate([0,1;1,0])-SWAP))','0'),('norm(linear_gate([1,0;1,1])|+0>-|Phi+>)','0'),('tr(linear_gate(identity(9)))','512'),('gf2_rank(gf2_mul(identity(128),identity(128)))','128'),('gf2_mul([1,1],[1;1])','0')]:
 assert evaluate(e)==want,e
for e in ['linear_gate(0)','linear_gate([1,0])','linear_gate(identity(10))','linear_gate([1,2;0,1])','linear_gate([])','gf2_mul([1,0],I@I)','gf2_mul(I,[1,-1;0,1])','gf2_mul([],I)','gf2_mul(identity(129),identity(129))']:
 p=run(e);assert p.returncode!=0,(e,p.stdout)
print('PASS: all 512 three-bit linear maps; 168 exact permutation gates, 344 rejections; 80 rectangular binary products; composition, inverse, entanglement and dimension checks.')
