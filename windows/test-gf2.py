"""GF(2) results checked by exhaustive spans and kernels, not row reduction."""
import json,subprocess,random,re,itertools
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def evaluate(expression):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+expression,encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode==0,(expression,p.stderr)
 return json.loads(p.stdout)['text']
def entries(text):return list(map(int,re.findall(r'-?\d+',text)))
def span(vectors):
 result={0}
 for v in vectors:result|={x^v for x in result}
 return result
def encoded(row):return sum(v<<i for i,v in enumerate(row))
def check(a):
 m,n=len(a),len(a[0]);expr='['+';'.join(','.join(map(str,row)) for row in a)+']'
 rows=[encoded(row) for row in a];space=span(rows);rank=(len(space)).bit_length()-1
 assert int(evaluate('gf2_rank('+expr+')'))==rank,a
 values=entries(evaluate('gf2_rref('+expr+')'));assert len(values)==m*n
 rref=[values[r*n:(r+1)*n] for r in range(m)]
 assert span([encoded(row) for row in rref])==space,a
 pivots=[next((i for i,v in enumerate(row) if v),n) for row in rref]
 assert pivots==sorted(pivots) and len(set(pivots[:rank]))==rank
 for r,p in enumerate(pivots[:rank]):assert all(rref[k][p]==int(r==k) for k in range(m)),a
 values=entries(evaluate('gf2_nullspace('+expr+')'));nullity=n-rank
 assert len(values)==n*nullity,(a,values)
 basis=[sum(values[r*nullity+c]<<r for r in range(n)) for c in range(nullity)]
 solutions={x for x in range(1<<n) if all((x&row).bit_count()%2==0 for row in rows)}
 assert span(basis)==solutions and len(solutions)==1<<nullity,(a,basis)

matrices=[[[int((mask>>(r*3+c))&1) for c in range(3)] for r in range(2)] for mask in range(64)]
rng=random.Random(442)
for m,n in [(1,1),(1,4),(4,1),(3,4),(4,3),(5,5)]:
 for _ in range(6):matrices.append([[rng.randrange(2) for c in range(n)] for r in range(m)])
for a in matrices:check(a)
for secret in range(1,8):
 equations=[[int((y>>(2-bit))&1) for bit in range(3)] for y in range(1,8) if (y&secret).bit_count()%2==0]
 expr='['+';'.join(','.join(map(str,row)) for row in equations)+']'
 assert entries(evaluate('gf2_nullspace('+expr+')'))==[int(v) for v in f'{secret:03b}']
assert evaluate('gf2_rank(identity(128))')=='128'
assert evaluate('gf2_rank(0*identity(128))')=='0'
assert evaluate('gf2_nullspace(identity(128))')=='[]'
invalid=['gf2_rank([])','gf2_rref([1,2])','gf2_nullspace([-1,0])','gf2_rank([1/2,0])','gf2_rank([i,0])','gf2_rank([x,0])','gf2_rank(identity(129))','gf2_rank([1,0;1])','gf2_nullspace()']
for e in invalid:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode!=0,(e,p.stdout)
print(f'PASS: {len(matrices)} independently enumerated GF(2) row spaces and kernels, all 7 nonzero Simon masks, 128-dimension bounds, {len(invalid)} invalid inputs.')
