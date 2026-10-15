"""Verify CSS isometries against independently projected computational bases."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),'Z':np.diag([1,-1])}
def tensor(bits,axis):
    out=np.ones((1,1))
    for b in bits:out=np.kron(out,P[axis] if b else P['I'])
    return out
def literal(rows):return '['+';'.join(','.join(map(str,r)) for r in rows)+']'
def run(expr,approx=False):return subprocess.run([str(worker),'--json']+(['--approx'] if approx else []),input='quantum:'+expr,encoding='utf-8',capture_output=True,timeout=60)
def expect(expr,wanted='0'):
    p=run(expr);assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']==wanted,(expr,p.stdout,wanted)
def verify(hx,hz,n):
    expr='css_encoder('+literal(hx)+','+literal(hz)+')'
    projector=np.eye(2**n)
    for rows,axis in [(hx,'X'),(hz,'Z')]:
        for row in rows:projector=projector@(np.eye(2**n)+tensor(row,axis))/2
    basis=[]
    for u in range(2**n):
        v=projector[:,u].copy()
        for previous in basis:v-=np.vdot(previous,v)*previous
        norm=np.linalg.norm(v)
        if norm>1e-10:basis.append(v/norm)
    expected=np.stack(basis,axis=1)
    p=run(expr,True);assert p.returncode==0,(expr,p.stderr)
    data=json.loads(p.stdout)
    if expected.size<=128:
        actual=np.array([[float(c.replace('−','-')) for c in row] for row in data['cells']])
        assert np.allclose(actual,expected,atol=1e-12),(expr,actual,expected)
    else:
        for c in range(expected.shape[1]):
            p=run('norm(('+expr+')basis('+str(c)+','+str(expected.shape[1])+')-('+literal(expected[:,c:c+1])+'))',True)
            assert p.returncode==0,(expr,p.stderr)
            assert abs(float(json.loads(p.stdout)['text'].replace('−','-')))<1e-12,(expr,c,p.stdout)
    assert np.allclose(expected.T@expected,np.eye(expected.shape[1]))
    assert np.allclose(expected@expected.T,projector)
    # Exact native identities test arbitrary complex amplitudes by linearity.
    expect('('+expr+')†('+expr+')==identity('+str(expected.shape[1])+')','1')

valid=invalid=0
for x,z in itertools.product(list(itertools.product([0,1],repeat=3)),repeat=2):
    if sum(a*b for a,b in zip(x,z))%2:
        assert run('css_encoder('+literal([x])+','+literal([z])+')').returncode!=0;invalid+=1
    else:verify([x],[z],3);valid+=1
# Multiple and dependent rows, missing check types, and k=0 codes.
for hx,hz,n in [([[1,1],[1,1],[0,0]],[[1,1]],2),
                ([],[[1,1,0],[0,1,1]],3),
                ([[1,0,0],[0,1,0],[0,0,1]],[],3),
                ([],[[1,0],[0,1]],2),
                ([[1,1,1,1]],[[1,1,1,1]],4),
                ([[0,0,0,0]],[],4)]:
    verify(hx,hz,n);valid+=1
h='[1,1,1,1,0,0,0;1,1,0,0,1,1,0;1,0,1,0,1,0,1]'
v='css_encoder('+h+','+h+')'
for u,state in [(0,'|0>'),(7,'|1>')]:
    expect('norm(('+v+')'+state+'-css_state('+h+','+h+','+str(u)+'))');valid+=1
expect('norm(('+v+')|i>-(css_state('+h+','+h+',0)+i*css_state('+h+','+h+',7))/sqrt(2))');valid+=1
expect('norm(('+v+')†('+v+')(3|0>+4i|1>)-(3|0>+4i|1>))');valid+=1
expect('css_encoder([0,0,0,0,0,0,0,0,0],[])==identity(512)','1');valid+=1
expect('norm(css_encoder([1,0;0,1],[])-|++>)');valid+=1
expect('css_encoder([1,1;1,1],[1,1])==css_encoder([1,1],[1,1])','1');valid+=1
expect('css_encoder([],[1,1,0;0,1,1])==css_encoder([],[1,0,1;1,1,0])','1');valid+=1
v='css_encoder([],[1,1,0;0,1,1])'
expect('('+v+')(I/2)('+v+')†==stabilizer_projector(<ZZI,IZZ>)/2','1');valid+=1
expect('norm(('+v+')†stabilizer_correction(<ZZI,IZZ>,[1,1])pauli(IXI)('+v+')|i>-|i>)');valid+=1
for expr in ['css_encoder([],[])','css_encoder([1,1],[1])','css_encoder([1,0],[1,0])',
             'css_encoder([1,2],[])','css_encoder([1,i],[])','css_encoder([1,1/2],[])',
             'css_encoder([0,0,0,0,0,0,0,0,0,0],[])','css_encoder([1,1])',
             'css_encoder([1,1],[],0)','css_encoder(['+';'.join(['0']*33)+'],[])']:
    assert run(expr).returncode!=0,expr;invalid+=1
print(f'PASS: {valid} CSS encoder families and exact identities; {invalid} invalid inputs rejected.')
