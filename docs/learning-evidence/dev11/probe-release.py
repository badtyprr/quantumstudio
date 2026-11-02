"""DEV-11 standalone source-derived audit. Python 3 standard library only.
Usage: python probe.py --worker PATH --output DIRECTORY --sources SNAPSHOT_DIRECTORY
Never builds, changes product code, or writes to the worker package.
"""
import ast, argparse, datetime, hashlib, itertools, json, math, os, re, subprocess
from pathlib import Path
BASE='214e686668672f2ab405300e88baa008eb40fcf4'
RELEASE='214e686668672f2ab405300e88baa008eb40fcf4'
HASH='42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d'
P={'I':[[1,0],[0,1]],'X':[[0,1],[1,0]],'Y':[[0,-1j],[1j,0]],'Z':[[1,0],[0,-1]]}
REJECTIONS={
 '060-negative-identity':'The generators contain -I in their group and have no common +1 eigenspace.',
 '060-noncommuting':'Stabilizer generators must commute.',
 '062-invalid-css':'CSS checks must satisfy Hx Hz^T = 0 over GF(2), so every X check commutes with every Z check.',
 '063-capacity-18':'Pauli labels require 1 to 9 letters I, X, Y, Z, with an optional sign, 1, and i/j phase prefix.',
 '067-capacity-14':'Pauli labels require 1 to 9 letters I, X, Y, Z, with an optional sign, 1, and i/j phase prefix.',
 '058-variadic-tensor':'Quantum function tensor requires exactly 2 arguments.',
}

def expected_rejection(fixture_id,returncode,stderr):
 return fixture_id in REJECTIONS and returncode==2 and stderr.strip()==REJECTIONS[fixture_id]
def apply(word,v):
 out=[0j]*len(v)
 for column,value in enumerate(v):
  row=column;phase=1
  for q,ch in enumerate(word):
   bit=1<<(len(word)-q-1);on=bool(column&bit)
   if ch in 'XY': row^=bit
   if ch=='Y': phase*= -1j if on else 1j
   if ch=='Z' and on:phase*=-1
  out[row]+=phase*value
 return out
def matrix(word):
 d=2**len(word);cols=[apply(word,[int(i==j) for i in range(d)]) for j in range(d)]
 return [list(r) for r in zip(*cols)]
def matmul(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def adj(a):return [[complex(x).conjugate() for x in row] for row in zip(*a)]
def scale(a,c):return [[x*c for x in row] for row in a]
def exprnum(z):
 z=complex(z)
 if abs(z.imag)<1e-15:return format(z.real,'.17g')
 return '('+format(z.real,'.17g')+'+('+format(z.imag,'.17g')+')*i)'
def literal(a):return '['+';'.join(','.join(exprnum(v) for v in row) for row in a)+']'
def pack(a):return [[[complex(x).real,complex(x).imag] for x in row] for row in a]
def anti(a,b):return sum(x!='I' and y!='I' and x!=y for x,y in zip(a,b))%2
def group(gs):return '<'+','.join(gs)+'>'
def pauli(w):return 'pauli("'+w+'")'
def columns(vs):return [list(row) for row in zip(*vs)]
def ket_terms(v):
 # Independently specified integer signed amplitudes, with common normalization.
 nonzero=[(j,int(round(complex(x).real))) for j,x in enumerate(v) if x]
 n=(len(v)-1).bit_length();norm=sum(k*k for j,k in nonzero)
 return '('+'+'.join(('' if k==1 else '-' if k==-1 else str(k)+'*')+'|'+format(j,f'0{n}b')+'>' for j,k in nonzero)+')/sqrt('+str(norm)+')'
def basis_expr(vs):
 # Columns via outer products retain exact sqrt normalization.
 return '('+'+'.join('('+ket_terms(v)+')*<'+str(j)+'|' for j,v in enumerate(vs))+')'
def normalize(v):
 n=math.sqrt(sum(abs(x)**2 for x in v));return [x/n for x in v]
def syndrome(gs,w):return [anti(g,w) for g in gs]
def errors(n):return ['I'*n]+['I'*q+p+'I'*(n-q-1) for p in 'XYZ' for q in range(n)]
def parse_complex(s):
 s=s.replace('−','-').replace('∕','/').replace('⋅','*').replace('×','*').replace('√','sqrt').replace('^','**')
 s=re.sub(r'(?<=\d)\s*i\b','*i',s)
 def val(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,(int,float,complex)):return n.value
  if isinstance(n,ast.Name) and n.id=='i':return 1j
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return val(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
  if isinstance(n,ast.BinOp):
   x,y=val(n.left),val(n.right)
   if isinstance(n.op,ast.Add):return x+y
   if isinstance(n.op,ast.Sub):return x-y
   if isinstance(n.op,ast.Mult):return x*y
   if isinstance(n.op,ast.Div):return x/y
   if isinstance(n.op,ast.Pow):return x**y
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sqrt' and len(n.args)==1:return math.sqrt(val(n.args[0]))
  raise ValueError('Unsupported numeric output: '+s)
 return complex(val(ast.parse(s.strip(),mode='eval').body))
def numeric_cells(d):
 if d['cells']:return [[parse_complex(x) for x in row] for row in d['cells']]
 m=re.fullmatch(r'matrix\((\d+),(\d+),\[(.*)\]\)',d['copy_text'],re.S)
 if not m:return []
 rows,cols=int(m[1]),int(m[2]);flat=[parse_complex(x) for x in m[3].split(',')]
 if len(flat)!=rows*cols:raise ValueError('Canonical matrix length mismatch')
 return [flat[r*cols:(r+1)*cols] for r in range(rows)]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--replay',type=Path);ap.add_argument('--worker',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sources',type=Path,required=True);a=ap.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 digest=hashlib.sha256(a.worker.read_bytes()).hexdigest()
 if digest!=HASH:raise SystemExit('Worker hash differs; update provenance explicitly before comparison')
 manifests=json.loads(Path(__file__).with_name('source-manifest.json').read_text());sources={r['id']:r for r in manifests}
 for row in manifests:
  assert hashlib.sha256((a.sources/(row['id']+'.ipynb')).read_bytes()).hexdigest()==row['notebook']['sha256'], 'Source snapshot hash mismatch: '+row['id']
 env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(a.worker.parent/'data'))
 cached_fixtures={f['id']:f for f in json.loads(a.replay.with_name('fixtures.json').read_text())} if a.replay else {}
 cases=[];results=[];cached={r['id']:r for r in json.loads(a.replay.read_text())['results']} if a.replay else {}
 def add(id,row,section,notation,expression,expected=None,kind='matrix',adaptation='ASCII Quantum notation; explicit finite matrices; leftmost qubit is most significant.',phase=False):
  nb=json.loads((a.sources/(row+'.ipynb')).read_text());cell=nb['cells'][0]
  cases.append(dict(id=id,source_row=row,source_url=sources[row]['url'],source_notebook=sources[row]['notebook'],section=section,cell_index=0,cell_id=cell.get('id'),original_notation=notation,adaptation=adaptation,expression='quantum:'+expression,expected=pack(expected) if kind=='matrix' else expected,comparison=kind,allow_common_global_phase=phase))
 # First executable group: IBM-058.
 for x,y in itertools.product('IXYZ',repeat=2):
  add('058-product-'+x+y,'IBM-058','Pauli operation basics / Properties of Pauli matrices','Pauli multiplication table',x+'*'+y,matmul(P[x],P[y]))
 add('058-group-phase','IBM-058','Pauli operations as generators','(X tensor X)(Z tensor Z) = -Y tensor Y','tensor(X,X)*tensor(Z,Z)',scale(matrix('YY'),-1))
 bell=[1,0,0,1];bellnorm=normalize(bell)
 add('058-degenerate-projector','IBM-058','Pauli observables','Pi_0=(I+Z tensor Z)/2; Pi_0 |phi+> = |phi+>','(qidentity(4)+tensor(Z,Z))/2*((|00>+|11>)/sqrt(2))',columns([bellnorm]),adaptation='Projector action only; not a measurement/instrument execution claim.')
 rep=['ZZI','IZZ'];vrep=[[1]+[0]*7,[0]*7+[1]]
 # Source table explicit, full four columns.
 for word,bits in zip(['III','XII','IXI','IIX'],[[0,0],[1,0],[1,1],[0,1]]):
  add('059-syndrome-'+word,'IBM-059','Error detection','rows ZZI, IZZ; +1 -> 0, -1 -> 1','stabilizer_syndrome('+group(rep)+','+pauli(word)+')',bits,'vector')
  add('059-recovery-'+word,'IBM-059','Error detection / Syndromes','apply matching X to restore alpha|000>+beta|111>','stabilizer_correction('+group(rep)+',['+','.join(map(str,bits))+'])*'+pauli(word)+'*'+basis_expr(vrep),columns(vrep))
 # Complete 64-Pauli syndrome partition explicitly described by IBM059.
 for w in map(''.join,itertools.product('IXYZ',repeat=3)):
  if w in ['III','XII','IXI','IIX']:continue
  add('059-partition-'+w,'IBM-059','Syndromes','64 Pauli operations partition into four equal syndrome classes','stabilizer_syndrome(<ZZI,IZZ>,'+pauli(w)+')',syndrome(rep,w),'vector',adaptation='Exhaustive finite expansion of source partition claim; no assertion that all errors are correctable.')
 for w,logical in [('XXX',P['X']),('ZII',P['Z'])]:
  add('059-logical-'+w,'IBM-059','Syndromes','XXX acts as logical X; commuting Paulis may act nontrivially on the logical qubit',pauli(w)+'*'+basis_expr(vrep),matmul(columns(vrep),logical),adaptation='XXX is the explicit source example; ZII is an independent phase-error witness.')
 codes={'repetition':rep,'phase-repetition':['XXI','IXX'],'five':['XZZXI','IXZZX','XIXZZ','ZXIXZ'],'steane':['ZZZZIII','ZZIIZZI','ZIZIZIZ','XXXXIII','XXIIXXI','XIXIXIX'],'shor':['ZZIIIIIII','IZZIIIIII','IIIZZIIII','IIIIZZIII','IIIIIIZZI','IIIIIIIZZ','XXXXXXIII','IIIXXXXXX']}
 # Project the computational zero state independently, then use XXXXX logical X.
 vf=[1]+[0]*31
 for g in codes['five']:vf=[x+y for x,y in zip(vf,apply(g,vf))]
 vf=[int(x.real) for x in vf];vf1=[int(x.real) for x in apply('XXXXX',vf)]
 span=[0,30,45,51,75,85,102,120]
 vs=[[int(j in span) for j in range(128)],[int((j^7) in span) for j in range(128)]]
 shor0=[int(all(((j>>k)&7) in (0,7) for k in (0,3,6))) for j in range(512)]
 shor1=[v*((-1)**sum(((j>>k)&7)==7 for k in (0,3,6))) for j,v in enumerate(shor0)]
 bases={'five':[vf,vf1],'steane':vs,'shor':[shor0,shor1]}
 for name,gs in codes.items():
  n=len(gs[0]);dist=1 if 'repetition' in name else 3
  add('060-parameters-'+name,'IBM-060','Examples / '+{'repetition':'3-bit repetition code','phase-repetition':'Modified 3-bit repetition code','five':'5-qubit code','steane':'7-qubit Steane code','shor':'9-qubit Shor code'}[name]+'; Distance of a stabilizer code','[[n,1,d]]','stabilizer_parameters('+group(gs)+')',[n,1,dist],'vector')
  if name not in bases:continue
  eb=basis_expr(bases[name]);expected=columns([normalize(v) for v in bases[name]])
  for w in errors(n):
   bits=syndrome(gs,w)
   add('060-syndrome-'+name+'-'+w,'IBM-060','Detecting errors / Correcting errors','anticommutation with ordered stabilizer generators','stabilizer_syndrome('+group(gs)+','+pauli(w)+')',bits,'vector',adaptation='Exhaustive weight <=1 Pauli extension of source correction claim; expected by per-site anticommutation, not product implementation.')
   add('060-recovery-'+name+'-'+w,'IBM-060','Correcting errors','C E |psi> = phase |psi>','stabilizer_correction('+group(gs)+',['+','.join(map(str,bits))+'])*'+pauli(w)+'*'+eb,expected,phase=True,adaptation='Both independent logical columns compared including leakage; ONE common global phase allowed across columns. Five-qubit basis chosen via source projector, not a source-specified encoding circuit.')
 add('060-bell-dimension','IBM-060','One-dimensional stabilizer codes','<ZZ,XX> fixes phi+','stabilizer_dimension(<ZZ,XX>)','1','scalar')
 add('060-negative-identity','IBM-060','Definition of stabilizer codes','-I excluded','stabilizer_dimension(<XX,ZZ,YY>)',None,'reject')
 add('060-noncommuting','IBM-060','Definition of stabilizer codes','generators must commute','stabilizer_dimension(<X,Z>)',None,'reject')
 for gate in ['H','S']:
  g=[[1/math.sqrt(2),1/math.sqrt(2)],[1/math.sqrt(2),-1/math.sqrt(2)]] if gate=='H' else [[1,0],[0,1j]]
  for w in 'XYZ':add('060-conjugate-'+gate+w,'IBM-060','Clifford operations','U P U dagger = signed Pauli',gate+'*'+w+'*adjoint('+gate+')',matmul(matmul(g,P[w]),adj(g)))
 cn=[[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]]
 for w in map(''.join,itertools.product('IXYZ',repeat=2)):
  add('060-CNOT-'+w,'IBM-060','Clifford operations','CNOT P CNOT dagger','CNOT*'+pauli(w)+'*CNOT',matmul(matmul(cn,matrix(w)),cn))
 # Expand beyond starter rows: original Steane states from IBM062.
 h='[1,1,1,1,0,0,0;1,1,0,0,1,1,0;1,0,1,0,1,0,1]'
 add('062-css-encoder','IBM-062','Code spaces of CSS codes','|0L>, |1L> listed eight-term cosets','css_encoder('+h+','+h+')',columns([normalize(v) for v in vs]))
 for j,u in enumerate([0,7]):add('062-css-state-'+str(j),'IBM-062','Code spaces of CSS codes','|u xor D_X>','css_state('+h+','+h+','+str(u)+')',columns([normalize(vs[j])]))
 add('062-invalid-css','IBM-062','Definition of CSS codes','Hx Hz transpose = 0 mod 2','css_generators([1,0],[1,0])',None,'reject')
 for name,w,logical in [('shor','ZIIZIIZII',P['X']),('shor','XXXIIIIII',P['Z']),('steane','XXXXXXX',P['X']),('steane','ZZZZZZZ',P['Z'])]:
  add('067-logical-'+name+'-'+w,'IBM-067','Examples of transversal gate implementations','physical Pauli acts as logical '+('X' if logical==P['X'] else 'Z'),pauli(w)+'*'+basis_expr(bases[name]),matmul(columns([normalize(v) for v in bases[name]]),logical))
 for gate,logical in [('H',[[1/math.sqrt(2),1/math.sqrt(2)],[1/math.sqrt(2),-1/math.sqrt(2)]]),('Sdg',[[1,0],[0,1j]])]:
  add('067-steane-'+gate,'IBM-067','Examples of transversal gate implementations','H tensor7 -> logical H; S dagger tensor7 -> logical S','tensorpow('+gate+',7)*'+basis_expr(vs),matmul(columns([normalize(v) for v in vs]),logical))
 # Actual capacity boundaries, not invented missing API spellings.
 add('063-capacity-18','IBM-063','Toric code description','3x3 torus has 18 edge qubits',pauli('X'+'I'*17),None,'capacity',adaptation='Finite size specialization of source family, 18-qubit Pauli construction; documented 9-qubit limit expected to reject.')
 add('067-capacity-14','IBM-067','Examples of transversal gate implementations','two Steane blocks require 14 qubits',pauli('X'+'I'*13),None,'capacity',adaptation='Capacity sentinel only; not a complete transversal CNOT execution.')
 add('059-original-tensor','IBM-059','Pauli observables for the repetition code','(Z tensor Z tensor I)|000>','(Z ⊗ Z ⊗ I)|000>',columns([vrep[0]]),adaptation='Unicode tensor notation with explicit basis substitution.')
 # Catch unsupported convenience syntax separately from supported binary nesting.
 add('058-variadic-tensor','IBM-058','Pauli operations on multiple qubits','X tensor Y tensor Z','tensor(X,Y,Z)',None,'syntax',adaptation='Diagnostic convenience spelling; NOT original IBM code; nested binary tensor is the supported adaptation.')
 add('058-nested-tensor','IBM-058','Pauli operations on multiple qubits','X tensor Y tensor Z','tensor(tensor(X,Y),Z)',matrix('XYZ'))
 # Additional independent lesson adaptations (no measurement/instrument assertions).
 encoder='tensor(I,SWAP)*tensor(CNOT,I)*tensor(I,SWAP)*tensor(CNOT,I)*tensor(I,|00>)'
 add('054-encoding','IBM-054','Encoding qubits','alpha|0>+beta|1> -> alpha|000>+beta|111>',encoder,columns(vrep),adaptation='Two control-first CNOTs synthesized with a wire swap; compares entire 8x2 isometry, not source circuit import.')
 phasebasis=[[1]*8,[(-1)**j.bit_count() for j in range(8)]]
 add('054-phase-encoding','IBM-054','Modified repetition code for phase-flip errors','|0> -> |+++>; |1> -> |--->','tensorpow(H,3)*('+encoder+')',columns([normalize(v) for v in phasebasis]))
 for w in ['III','ZII','IZI','IIZ']:
  bits=syndrome(codes['phase-repetition'],w)
  add('054-phase-recovery-'+w,'IBM-054','Modified repetition code for phase-flip errors','correct one Z error in plus/minus repetition basis','stabilizer_correction(<XXI,IXX>,['+','.join(map(str,bits))+'])*'+pauli(w)+'*'+basis_expr(phasebasis),columns([normalize(v) for v in phasebasis]))
 add('054-bit-noise','IBM-054','Noise reduction for the binary symmetric channel','3p^2(1-p)+p^3','3*(1/10)^2*(1-1/10)+(1/10)^3','0.028','scalar',adaptation='Independent parameter specialization p=1/10; expected 28/1000.')
 add('054-phase-noise','IBM-054','Phase-flip errors','3p(1-p)^2+p^3','3*(1/10)*(1-1/10)^2+(1/10)^3','0.244','scalar',adaptation='Independent parameter specialization p=1/10; expected 244/1000.')
 add('056-Pauli-expansion','IBM-056','Unitary qubit errors','U=alpha I+beta X+gamma Y+delta Z','(I+i*X)/sqrt(2)',[[1/math.sqrt(2),1j/math.sqrt(2)],[1j/math.sqrt(2),1/math.sqrt(2)]],adaptation='Chosen unitary U=exp(i*pi*X/4); coefficient expansion only; channel discretization untested.')
 # Equivalent small-output parenthesization for the 12 observed Shor timeouts.
 for w in errors(9):
  if w not in ['IIIIIIYII','IIIIIIIYI','IIIIIIIIY'] and 'Z' not in w:continue
  bits=syndrome(codes['shor'],w)
  add('060-associated-recovery-shor-'+w,'IBM-060','Correcting errors','C(E|psi>) = (CE)|psi>','stabilizer_correction('+group(codes['shor'])+',['+','.join(map(str,bits))+'])*('+pauli(w)+'*'+basis_expr(bases['shor'])+')',columns([normalize(v) for v in bases['shor']]),phase=True,adaptation='Performance follow-up: right-associated multiplication; compares BOTH encoded columns and full output, same mathematical recovery as timed-out left-associated fixture.')
 # Oracle self-checks: source literal syndrome table, normalization and phase-sensitive logical matrices.
 assert [syndrome(rep,w) for w in ['III','XII','IXI','IIX']]==[[0,0],[1,0],[1,1],[0,1]]
 for vs0 in bases.values():
  e=columns([normalize(v) for v in vs0]);gram=matmul(adj(e),e)
  assert max(abs(gram[r][c]-int(r==c)) for r in range(2) for c in range(2))<1e-12
 assert matmul(P['X'],P['Y'])==scale(P['Z'],1j)
 (a.output/'fixtures.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
 for c in cases:
  if c['id'] in cached:
   assert cached_fixtures[c['id']]['expression']==c['expression'], 'Cached expression differs'
   assert cached_fixtures[c['id']]['expected']==c['expected'], 'Cached oracle differs'
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=dict(id=c['id'],started_utc=start,execution_mode='packaged worker --json default exact evaluation',binary_revision=RELEASE,binary_sha256=digest,source_base=BASE)
  if c['id'] in cached and 'returncode' not in cached[c['id']]:
   r.update(cached[c['id']]);r['classification']='execution-timeout';results.append(r);print(c['id'],'preserved timeout',flush=True);continue
  try:
   if c['id'] in cached:
    old=cached[c['id']];p=subprocess.CompletedProcess([],old['returncode'],old['stdout'].encode(),old['stderr'].encode());r['execution_mode']='offline comparison of saved exact worker stdout';r['original_started_utc']=old['started_utc']
   else:p=subprocess.run([str(a.worker),'--json'],input=c['expression'].encode(),capture_output=True,env=env,timeout=90,cwd=a.output)
   r.update(returncode=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'))
   k=c['comparison'];success=False
   if k in ('reject','capacity','syntax'):
    success=expected_rejection(c['id'],p.returncode,r['stderr'])
    r['classification']=('validated-rejection' if k=='reject' else 'missing-operation-capacity' if k=='capacity' else 'unsupported-adaptation-syntax') if success else 'unexpected-rejection-result'
   elif p.returncode!=0:r['classification']='execution-error'
   else:
    d=json.loads(r['stdout']);r['approximate']=d['approximate']
    if k=='scalar':success=d['text']==c['expected']
    elif k=='vector':
     expected='vector('+','.join(map(str,c['expected']))+')';success=d['copy_text'].replace(' ','')==expected
    else:
     actual=numeric_cells(d);expected=[[complex(*x) for x in row] for row in c['expected']]
     same_shape=len(actual)==len(expected) and all(len(x)==len(y) for x,y in zip(actual,expected));phase=1
     if same_shape and c['allow_common_global_phase']:
      for ar,er in zip(actual,expected):
       pairs=[(x,y) for x,y in zip(ar,er) if abs(y)>1e-12]
       if pairs:phase=pairs[0][0]/pairs[0][1];break
     residual=max((abs(x-phase*y) for ar,er in zip(actual,expected) for x,y in zip(ar,er)),default=1e99) if same_shape else 1e99
     r.update(max_residual=residual,common_phase=[complex(phase).real,complex(phase).imag]);success=same_shape and residual<1e-12 and abs(abs(phase)-1)<1e-12
    r['classification']='already-supported-adaptation' if success else 'incorrect-or-unresolved-result'
   r['passed_expectation']=success
  except Exception as e:r.update(passed_expectation=False,classification='execution-timeout' if isinstance(e,subprocess.TimeoutExpired) else 'probe-error',error=str(e))
  results.append(r)
  (a.output/'results.json').write_text(json.dumps(dict(base=BASE,worker_revision=RELEASE,worker_sha256=digest,tolerance=1e-12,results=results),indent=2),encoding='utf-8')
  print(c['id'],r['classification'],r['passed_expectation'],flush=True)
 summary={k:sum(r['classification']==k for r in results) for k in sorted(set(r['classification'] for r in results))}
 summary.update(total=len(results),expectations_passed=sum(r['passed_expectation'] for r in results))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(summary)
 return 0 if all(r['passed_expectation'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
