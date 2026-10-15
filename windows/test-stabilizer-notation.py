"""Context-sensitive Pauli-group brackets, including Unicode and pasted TeX."""
import json
import subprocess
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def run(expr):
    return subprocess.run([str(worker),'--json'],input='quantum:'+expr,encoding='utf-8',capture_output=True,timeout=30)
def expect(expr,wanted):
    p=run(expr)
    assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']==wanted,(expr,p.stdout,wanted)

groups=[
    '<XX,ZZ>', '⟨XX,ZZ⟩', '<X X, Z Z>', '⟨X⊗X, Z⊗Z⟩',
    r'\langle XX,ZZ\rangle', r'\left\langle X\otimes X,Z\otimes Z\right\rangle',
    r'\bigl\langle \mathbf{X}\otimes\mathbf{X}, \mathbf{Z}\otimes\mathbf{Z}\bigr\rangle',
    '<+XX,+ZZ,-YY>', '⟨XX,ZZ,−YY⟩', '<XX,ZZ,II>',
]
checks=0
for group in groups:
    expect('stabilizer_dimension('+group+')','1')
    expect('norm(vec(stabilizer_projector('+group+')-density(|Phi+>)))','0')
    # Error syndrome retains the original generator order, including redundancy.
    wanted='[0  1  1]' if 'YY' in group else '[0  1  0]' if 'II' in group else '[0  1]'
    expect('stabilizer_syndrome('+group+',X@I)',wanted)
    checks+=3
for group in ['<ZZI,IZZ>', '⟨Z Z I,I Z Z⟩', r'\langle ZZ\mathbb{I},\mathbb{I}ZZ\rangle']:
    expect('stabilizer_dimension('+group+')','2')
    expect('stabilizer_syndrome('+group+',pauli(IXI))','[1  1]')
    checks+=2
for expr,wanted in [
    ('stabilizer_dimension(<I>)','2'),('stabilizer_dimension(<X,X>)','1'),
    ('stabilizer_syndrome(<Z>,iX)','1'),
    ('stabilizer_dimension(<'+','.join(['I']*32)+'>)','2'),
    ('<0|X|1>','1'), ('norm(vec(X X-I))','0'),
    ('stabilizer_dimension(vector(X@X,Z@Z))','1'),
    ('norm(vec(stabilizer_projector(<-Z>)-density(|1>)))','0'),
    ('stabilizer_dimension(<ZZ>)>1','1'),
    ('stabilizer_dimension(<ZZ>)<3','1'),
    ('stabilizer_dimension(<XIIIIIIII>)','256'),
    ('stabilizer_dimension(⟨ZZZZIII,ZZIIZZI,ZIZIZIZ,XXXXIII,XXIIXXI,XIXIXIX⟩)','2'),
    ('stabilizer_syndrome(⟨ZZZZIII,ZZIIZZI,ZIZIZIZ,XXXXIII,XXIIXXI,XIXIXIX⟩,pauli(IIIXIII))','[1  0  0  0  0  0]'),
    ('norm(vec(stabilizer_projector(<XX,ZZ>)^2-stabilizer_projector(<XX,ZZ>)))','0'),
]:
    expect(expr,wanted);checks+=1
invalid=['<>','<,X>','<X,>','<X,,Z>','<X','<X@>','<@X>','<X@@X>',
         '<X*X>','<2X>','<H>','<X,Z>','<iX>','<XX,ZZ,YY>',
         '<'+','.join(['I']*33)+'>', '<XXXXXXXXXX>', '<X@-X>']
for group in invalid:
    p=run('stabilizer_projector('+group+')')
    assert p.returncode!=0,(group,p.stdout)
for expr in ['stabilizer_syndrome(<Z>)','stabilizer_dimension(<X>,Z)','stabilizer_projector(<X>>)',
             'stabilizer_projector(<X>)>','stabilizer_syndrome(<ZZ>,pauli(X))']:
    assert run(expr).returncode!=0,expr
print(f'PASS: {checks} group-notation/Dirac regression checks and {len(invalid)+5} rejected inputs.')
