"""Finite IBM-092 regularized-overlap composition; NumPy is an audit dependency."""
import argparse,ast,hashlib,json,os,re,subprocess
from pathlib import Path
import numpy as np
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--worker',type=Path,default=Path(os.environ.get('QUANTUM_WORKER','quantum-worker.exe' if os.name=='nt' else 'quantum-worker')))
ap.add_argument('--definitions',type=Path)
ap.add_argument('--source',type=Path,required=True,help='Pinned original IBM-092 notebook')
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args();w=args.worker.resolve();r=args.output;r.mkdir(parents=True,exist_ok=True)
if (r/'results.json').exists():raise SystemExit('Use a fresh evidence output directory')
source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
if source_hash!='524d48804ce536442b4329b818413ca7cda14304fcdf6a42c764b1b2dbdada8e':raise SystemExit('Pinned IBM-092 notebook hash mismatch')
cell=''.join(json.loads(args.source.read_bytes())['cells'][50]['source'])
cell_hash=hashlib.sha256(cell.encode()).hexdigest()
if cell_hash!='6627022329dcd5d84bcc48b479eeee7766cf6ce143e31b9017ab88bef48e08c8':raise SystemExit('Pinned cell50 hash mismatch')
(r/'original-cell50.py.txt').write_text(cell,encoding='utf-8')
definitions=(args.definitions or w.parent/'data').resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(definitions))
ref={'cases':[]}
def encode(a):return dict(real=a.real.tolist(),imag=a.imag.tolist())
def add(name,sd,hd,cutoff,expected,coupled=False,rotated=False):
 S=np.diag(sd).astype(complex);H=np.diag(hd).astype(complex)
 if coupled:H[0,2]=H[2,0]=1;H[1,2]=H[2,1]=2
 if rotated:
  Q=np.eye(len(sd),dtype=complex);Q[1:,1:]=np.array([[1,1j],[1j,1]])/np.sqrt(2)
  S=Q@S@Q.conj().T;H=Q@H@Q.conj().T
 ref['cases'].append(dict(name=name,H=encode(H),S=encode(S),cutoff=cutoff,expected=expected,retained_dimension=len(expected)))
# Authored analytic inputs, not the original sampled ten-spin experiment.
add('fullrank2',[2,1],[6,5],0,[3,5])
add('zero3',[2,1,0],[6,5,7],0,[3,5])
add('below3',[2,.125,0],[6,.5,7],.25,[3])
add('equal3',[2,.25,0],[6,1,7],.25,[3])
add('above3',[2,.5,0],[6,2,7],.25,[3,4])
add('coupled3',[2,1,0],[6,5,7],0,[3,5],coupled=True)
add('complex_rotated3',[2,1,0],[6,5,7],.25,[3,5],rotated=True)

def validate(h,s,t):
 # Authored audit preconditions, not a new native public validator.
 if h.ndim!=2 or s.ndim!=2 or h.shape!=s.shape or h.shape[0]!=h.shape[1] or not len(h):raise ValueError('matching nonempty square matrices required')
 if not np.isfinite(h).all() or not np.isfinite(s).all():raise ValueError('finite matrix entries required')
 if not np.isfinite(t) or t<0:raise ValueError('finite nonnegative cutoff required')
 if not np.allclose(h,h.conj().T,rtol=0,atol=1e-12) or not np.allclose(s,s.conj().T,rtol=0,atol=1e-12):raise ValueError('Hermitian matrices required')
 if np.linalg.eigvalsh(s).min() < -1e-12:raise ValueError('positive-semidefinite overlap required')
records=[];cases=[]
def parse(text):
 text=text.replace('−','-').replace('∕','/').replace('⋅','*').replace('^','**');text=re.sub(r'(?<=[\d)])\s*i\b','*i',text)
 def v(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,(float,int,complex)):return n.value
  if isinstance(n,ast.Name) and n.id=='i':return 1j
  if isinstance(n,ast.UnaryOp):return -v(n.operand) if isinstance(n.op,ast.USub) else v(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=v(n.left),v(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
   if isinstance(n.op,ast.Pow):return a**b
  raise ValueError(text)
 return complex(v(ast.parse(text,mode='eval').body))
def numeric(a):
 if a['cells']:return np.array([[parse(x) for x in row] for row in a['cells']])
 if a['copy_text'].startswith('vector('):return np.array([[parse(x) for x in a['copy_text'][7:-1].split(',') if x]])
 return np.array([[parse(a['text'])]])
def run(label,e):
 p=subprocess.run([str(w),'--json','--approx'],input=e.encode(),capture_output=True,env=env,timeout=20)
 d=dict(case=case['name'],stage=label,input=e,exit=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode());records.append(d)
 if p.returncode:raise ValueError(d['stderr'])
 a=json.loads(p.stdout);d['actual']=a
 # Actual canonical output is re-entered via ordinary evaluation.
 q=subprocess.run([str(w),'--json','--approx'],input=a['copy_text'].encode(),capture_output=True,env=env,timeout=20)
 b=json.loads(q.stdout) if not q.returncode else {}
 d['copy_reentry']=dict(exit=q.returncode,stdout=q.stdout.decode(),stderr=q.stderr.decode())
 if q.returncode:raise ValueError('Copy re-entry failed')
 if (a['rows'],a['columns'])!=(b['rows'],b['columns']):raise ValueError('Copy shape mismatch')
 if numeric(a).shape!=numeric(b).shape or not np.allclose(numeric(a),numeric(b),rtol=0,atol=2e-8):raise ValueError('Copy numeric mismatch')
 return a['copy_text'],a

def decode(x):return np.array(x['real'])+1j*np.array(x['imag'])
def lit(a):
 def num(z):return format(z.real,'.17g') if z.imag==0 else f'({z.real:.17g}+({z.imag:.17g})*i)'
 return f'matrix({a.shape[0]},{a.shape[1]},['+','.join(num(z) for z in a.flat)+'])'
for case in ref['cases']:
 result=dict(name=case['name'],passed=False)
 try:
  h,s=decode(case['H']),decode(case['S']);n=len(h);t=case['cutoff']
  validate(h,s,t)
  H,S=lit(h),lit(s)
  L,_=run('L',f'qheigenvalues({S})');V,_=run('V',f'qheigenvectors({S})')
  J,_=run('J',f'select(genvector(j,1,{n},1,j,1),element({L},j,1)>{t},j)')
  rank,_=run('rank',f'elements({J})');rank=int(rank)
  if rank==0:raise ValueError('no overlap eigenvalues exceed cutoff')
  U,ua=run('U',f'processm(element({V},p,element({J},q)),z,matrix({n},{rank},vector()),p,q)')
  Sr,_=run('Sr',f'qdag({U})*{S}*{U}');Hr,_=run('Hr',f'qdag({U})*{H}*{U}')
  W,_=run('W',f'qpower({Sr},-1/2)');A,_=run('A',f'{W}*{Hr}*{W}')
  if rank==1:
   # Preserve the native scalar result as an explicit quantum 1x1 matrix.
   A=f'qmul(({A}),qbasis(0,1))'
   result['singleton_shape_adaptation']='existing qmul/qbasis 1x1 constructor; native eigensolver still used'
  D,da=run('D',f'qheigenvalues({A})');Z,_=run('Z',f'qheigenvectors({A})')
  X,xa=run('X',f'{U}*{W}*{Z}')
  u,x,d=numeric(ua),numeric(xa),numeric(da).reshape(-1)
  residual=h@x-(s@x)*d;projected=u.conj().T@residual;orth=x.conj().T@s@x-np.eye(rank)
  result.update(rank=rank,spectrum=d.real.tolist(),max_projected_residual=float(np.max(np.abs(projected))),max_full_residual=float(np.max(np.abs(residual))),max_S_orthonormality_error=float(np.max(np.abs(orth))))
  assert rank==case['retained_dimension'] and u.shape==(n,rank) and x.shape==(n,rank)
  assert np.allclose(d,case['expected'],rtol=0,atol=2e-8)
  assert np.max(np.abs(projected))<=2e-8 and np.max(np.abs(orth))<=2e-9
  result['passed']=True
 except Exception as e:result['error']=str(e)
 cases.append(result)
policies=[]
for name,h,s,t,expected in [
 ('shape',np.eye(2),np.eye(3),0,'matching nonempty square matrices required'),
 ('nonfinite',np.diag([float('nan'),1]),np.eye(2),0,'finite matrix entries required'),
 ('nonHermitian_H',np.array([[3,9],[0,5]]),np.eye(2),0,'Hermitian matrices required'),
 ('nonHermitian_S',np.eye(2),np.array([[1,9],[0,1]]),0,'Hermitian matrices required'),
 ('indefinite',np.diag([6,5]),np.diag([2,-1]),0,'positive-semidefinite overlap required'),
 ('negative_cutoff',np.eye(2),np.eye(2),-1,'finite nonnegative cutoff required'),
 ('infinite_cutoff',np.eye(2),np.eye(2),float('inf'),'finite nonnegative cutoff required'),
 ('empty_zero',np.eye(2),np.zeros((2,2)),0,'no overlap eigenvalues exceed cutoff'),
 ('empty_equal',np.eye(2),np.eye(2),1,'no overlap eigenvalues exceed cutoff')]:
 case={'name':name};p=dict(name=name,inputs=dict(H=repr(h.tolist()),S=repr(s.tolist()),cutoff=repr(t)),expected=expected,passed=False,policy_owner='authored audit prevalidation; empty selection is computed natively')
 try:
  validate(h,s,t)
  L,_=run('policy-L',f'qheigenvalues({lit(s)})')
  J,_=run('policy-J',f'select(vector(1,2),element({L},j,1)>{t},j)')
  rank,_=run('policy-rank',f'elements({J})')
  if int(rank)==0:raise ValueError('no overlap eigenvalues exceed cutoff')
 except ValueError as e:p.update(actual=str(e),passed=str(e)==expected)
 policies.append(p)
summary=dict(cases=len(cases),passed=sum(c['passed'] for c in cases),policy_checks=len(policies),policies_passed=sum(p['passed'] for p in policies),native_stages=len(records),copies=sum('copy_reentry' in x for x in records))
result=dict(summary=summary,source_sha256=source_hash,source_cell_sha256=cell_hash,worker_sha256=hashlib.sha256(w.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),definitions_sha256={str(p.relative_to(definitions)):hashlib.sha256(p.read_bytes()).hexdigest() for p in definitions.rglob('*') if p.is_file()},route='ordinary existing native composition, all stages --approx; ordinary canonical copy re-entry',tolerances=dict(spectrum=2e-8,projected_residual=2e-8,copy=2e-8,S_orthonormality=2e-9,authored_precondition=1e-12),authored_inputs=ref['cases'],cases=cases,policies=policies,records=records)
(r/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(summary));raise SystemExit(int(not all(c['passed'] for c in cases) or not all(p['passed'] for p in policies)))
