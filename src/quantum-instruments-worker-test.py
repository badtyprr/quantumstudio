"""DEV-09 worker contract and independently expected measurement regressions."""
import cmath, json, math, os, subprocess, sys
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else "quantum-worker"+(".exe" if os.name=="nt" else "")).resolve()
checks=0

def data(expression, approximate=False, reject=False):
    global checks
    args=[str(worker),'--json']+(['--approx'] if approximate else [])
    result=subprocess.run(args,input=('quantum:'+expression).encode(),capture_output=True,timeout=60)
    assert (result.returncode!=0)==reject,(expression,result.returncode,result.stdout.decode(errors='replace'),result.stderr.decode(errors='replace'))
    checks+=1
    return None if reject else json.loads(result.stdout)

def equal(expression,expected,approximate=False):
    value=data('('+expression+')==('+expected+')',approximate)
    assert value['text']=='1',(expression,expected,value)

def copy(expression,approximate=False):
    original=data(expression,approximate)
    restored=data(original['copy_text'],approximate)
    # Matrix literals may canonicalize to qmatrix on the first re-entry.
    # Require a stable canonical result, then test substitutions below.
    again=data(restored['copy_text'],approximate)
    assert again['copy_text']==restored['copy_text'],(expression,restored,again)
    return restored['copy_text']

p='povm(vector("red","blue"),vector([2,1;1,1]/3,[1,-1;-1,2]/3))'
z='instrument(vector("red","blue"),vector(vector([1,0;0,0]),vector([0,0;0,1])))'
e='ensemble(vector("red","blue"),vector(1/3,2/3),vector(|0>,|+>))'
for approximate in (False,True):
    equal('measurementvalid('+p+')','1',approximate)
    equal('probabilities('+p+',|+>)','vector(5/6,1/6)',approximate)
    equal('poststate('+z+',|+>,"blue")','density(|1>)',approximate)
    equal('ensembleaverage('+e+')','[2/3,1/3;1/3,1/3]',approximate)
    for expression in (p,z,e,'branches('+z+',|0>)'):
        copy(expression,approximate)
    for expression in (
        'measurementvalid(povm(vector(0,1),vector([x,0;0,1],[1-x,0;0,0])))',
        'measurementvalid(povm(vector(x,y),vector([1,0;0,0],[0,0;0,1])))',
        'measurementvalid(povm(vector(0,1),vector(matrixparam(A,2,2),matrixparam(B,2,2))))',
        'naimark('+p+',n)'):
        restored=copy(expression,approximate)
        assert 'q' in restored and restored!='1'
    symbolic=copy('measurementvalid(povm(vector(0,1),vector([x,0;0,1],[1-x,0;0,0])))',approximate)
    equal('replace('+symbolic+',x,1/2)','1',approximate)
    data('replace('+symbolic+',x,2)',approximate,reject=True)
    symbolic=copy('measurementvalid(povm(vector(x,y),vector([1,0;0,0],[0,0;0,1])))',approximate)
    data('replace('+symbolic+',y,x)',approximate,reject=True)
    data('poststate('+z+',|0>,"blue")',approximate,reject=True)
    data('probabilities('+p+',|00>)',approximate,reject=True)
    data('naimark('+p+',1)',approximate,reject=True)
    comparison=copy('probabilities(povm(vector(0,1),vector([x,0;0,1],[1-x,0;0,0])),|0>)==vector(1/2,1/2)',approximate)
    equal('replace(('+comparison+'),x,1/2)','1',approximate)
    comparison=copy('poststate('+z+',|+>,x)==[1,0;0,0]',approximate)
    equal('replace(('+comparison+'),x,"red")','1',approximate)
    selection=copy('poststate('+z+',|+>,x)',approximate)
    equal('replace('+selection+',x,"red")','density(|0>)',approximate)
    data('replace('+selection+',x,2)',approximate,reject=True)
    data('measurementvalid(instrument(vector(0),vector(vector(matrixparam(A,2,2),[infinity,infinity;infinity,infinity]))))',approximate,reject=True)
    equal('measurementvalid(povm(vector(0,"red"),vector(density(|0>),density(|1>))))','1',approximate)
    singleton='povm(vector("only"),vector(matrix(1,1,[1])))'
    equal('measurementvalid('+singleton+')','1',approximate)
    copy(singleton,approximate)
    rectangular='instrument(vector(0,1),vector(vector(matrix(1,2,[1,0])),vector(matrix(1,2,[0,1]))))'
    equal('measurementvalid('+rectangular+')','1',approximate)
    equal('poststate('+rectangular+',|+>,0)','matrix(1,1,[1])',approximate)
    entangled='instrument(vector(0,1),vector(vector(density(|0>)@I),vector(density(|1>)@I)))'
    equal('ptrace(poststate('+entangled+',( |00>+|11>)/sqrt(2),1),0)','density(|1>)',approximate)

# IBM tetrahedral POVM, retaining all four original source states.
states=['|0>','(|0>+sqrt(2)*|1>)/sqrt(3)','(|0>+sqrt(2)*exp(2*pi*i/3)*|1>)/sqrt(3)','(|0>+sqrt(2)*exp(-2*pi*i/3)*|1>)/sqrt(3)']
effects=['density('+state+')/2' for state in states]
tetra='povm(vector(0,1,2,3),vector('+','.join(effects)+'))'
equal('probabilities('+tetra+',|0>)','vector(1/2,1/6,1/6,1/6)')
u=data('naimark('+tetra+',4)')
assert u['rows']==u['columns']==8,u
# Independent complex arithmetic checks every compressed effect, not only one
# input state's distribution. The ancilla block order must preserve all labels.
un=data('naimark('+tetra+',4)',True)
def number(text):
    return complex(text.replace(' ','').replace('−','-').replace('i','j'))
mat=[[number(cell) for cell in row] for row in un['cells']]
assert len(mat)==8 and all(len(row)==8 for row in mat)
for a in range(8):
    for b in range(8):
        assert abs(sum(mat[r][a].conjugate()*mat[r][b] for r in range(8))-(a==b))<1e-9
        checks+=1
reference=[[1,0]]+[[1/math.sqrt(3),math.sqrt(2/3)*cmath.exp(phase*1j)] for phase in (0,2*math.pi/3,-2*math.pi/3)]
for outcome,state in enumerate(reference):
    for a in range(2):
        for b in range(2):
            compressed=sum(mat[2*outcome+r][a].conjugate()*mat[2*outcome+r][b] for r in range(2))
            assert abs(compressed-state[a]*state[b].conjugate()/2)<1e-9
            checks+=1
# For rank-one projectors sqrt(P/2)=P/sqrt(2), independently of
# the general symbolic matrix-root simplifier.
instrument='instrument(vector(0,1,2,3),vector('+','.join('vector(density('+state+')/sqrt(2))' for state in states)+'))'
for outcome,state in enumerate(states):
    equal('poststate('+instrument+',|0>,'+str(outcome)+')','density('+state+')')
# The exact sign of the fourth |i> probability is not currently proved by
# the scalar simplifier. Retain the obligation instead of claiming a poststate.
pending=copy('poststate('+instrument+',|i>,3)')
assert pending.startswith('qpoststate('),pending
print('PASS:',checks,'DEV-09 worker checks')
