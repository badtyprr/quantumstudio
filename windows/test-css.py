"""CSS checks and coset states versus independent matrix projectors."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),'Z':np.diag([1,-1])}
def tensor(bits,axis):
    result=np.ones((1,1))
    for bit in bits:result=np.kron(result,P[axis] if bit else P['I'])
    return result
def literal(a):return '['+';'.join(','.join(format(float(v),'.17g') for v in row) for row in a)+']'
def row(bits):return '['+','.join(map(str,bits))+']'
def run(expr,approx=False):return subprocess.run([str(worker),'--json']+(['--approx'] if approx else []),input='quantum:'+expr,encoding='utf-8',capture_output=True,timeout=60)
def expect(expr,wanted):
    p=run(expr);assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']==wanted,(expr,p.stdout,wanted)
def compare(expr,expected):
    p=run('norm(('+expr+')-('+literal(expected)+'))',True)
    assert p.returncode==0,(expr,p.stderr)
    value=float(json.loads(p.stdout)['text'].replace('−','-'))
    assert abs(value)<1e-12,(expr,value)
valid=invalid=0
for x,z in itertools.product(list(itertools.product([0,1],repeat=3)),repeat=2):
    xs,zs=row(x),row(z);gx,gz=tensor(x,'X'),tensor(z,'Z')
    if not np.allclose(gx@gz,gz@gx):
        assert run('css_generators('+xs+','+zs+')').returncode!=0,(x,z)
        invalid+=1;continue
    expect('css_generators('+xs+','+zs+")==vector("+literal(gx)+','+literal(gz)+')','1');valid+=1
    projector=(np.eye(8)+gx)@(np.eye(8)+gz)/4
    for u in range(8):
        expected=projector[:,u:u+1];norm=np.linalg.norm(expected)
        expr=f'css_state({xs},{zs},{u})'
        if norm<1e-12:
            assert run(expr).returncode!=0,(x,z,u);invalid+=1
        else:
            compare(expr,expected/norm);valid+=1
h='[1,1,1,1,0,0,0;1,1,0,0,1,1,0;1,0,1,0,1,0,1]'
expect(f'stabilizer_parameters(css_generators({h},{h}))','[7  1  3]');valid+=1
zero=['0000000','0011110','0101101','0110011','1001011','1010101','1100110','1111000']
one=['0000111','0011001','0101010','0110100','1001100','1010010','1100001','1111111']
for u,labels in [(0,zero),(7,one)]:
    expected='('+ '+'.join('|'+label+'>' for label in labels)+')/sqrt(8)'
    expect(f'norm(css_state({h},{h},{u})-({expected}))','0');valid+=1
for expr,wanted in [
    ('stabilizer_parameters(css_generators([1,1,1,1],[1,1,1,1]))','[4  2  2]'),
    ('stabilizer_parameters(css_generators([],[1,1,0;0,1,1]))','[3  1  1]'),
    ('norm(css_state([1,1],[],0)-(|00>+|11>)/sqrt(2))','0'),
    ('norm(css_state([],[1,1],3)-|11>)','0'),
    ('norm(css_state([1,1;1,1;0,0],[1,1],0)-(|00>+|11>)/sqrt(2))','0'),
    ('norm(css_state(1,[],1)-|+>)','0'),
    ('norm(css_state([],1,0)-|0>)','0'),
    ('stabilizer_dimension(css_generators(0,[]))','2'),
    ('stabilizer_syndrome(css_generators([1,1],[1,1]),pauli(XI))','[0  1]'),
    ('stabilizer_correction(css_generators([1,1],[1,1]),[1,1])==pauli(IY)','1'),
    ('norm(css_state([0,0,0,0,0,0,0,0,0],[],511)-|111111111>)','0'),
    ('stabilizer_dimension(css_generators(['+';'.join(['0']*32)+'],[]))','2'),
]:expect(expr,wanted);valid+=1
for expr in ['css_generators([],[])','css_generators([1,1],[1])','css_generators([1,0],[1,1])',
             'css_generators([1,2],[])','css_generators([1,i],[])','css_generators([1,x],[])',
             'css_generators([1,1/2],[])','css_generators([1,-1],[])',
             'css_generators([0,0,0,0,0,0,0,0,0,0],[])',
             'css_generators(['+';'.join(['0']*33)+'],[])',
             'css_state([1,1],[1,1],1)','css_state([1,1],[],-1)',
             'css_state([1,1],[],4)','css_state([1,1],[],1/2)',
             'css_state([1,1],[],i)','css_state([1,1],[],x)',
             'css_state([1,1],[],[0,0])','css_state([1,1],[])','css_generators([1,1])']:
    assert run(expr).returncode!=0,expr;invalid+=1
print(f'PASS: {valid} CSS generator/state checks and {invalid} rejected inputs.')
