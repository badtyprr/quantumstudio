"""Independent minimum-weight and recovery tests for stabilizer syndrome decoding."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np

worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),
   'Y':np.array([[0,-1j],[1j,0]]),'Z':np.diag([1,-1])}

def matrix(word):
    out=np.ones((1,1))
    for letter in word:
        out=np.kron(out,P[letter])
    return out

def syndrome(code,word):
    # Determine each tensor-factor commutator using its actual 2x2 matrices.
    return tuple(sum(not np.allclose(P[a]@P[b],P[b]@P[a])
                     for a,b in zip(g.lstrip('-'),word))%2 for g in code)

def packed(word):
    x=z=0
    for c in word:
        x=2*x+(c in 'XY');z=2*z+(c in 'YZ')
    return x+(z<<len(word))

def candidates(n,max_weight):
    for weight in range(max_weight+1):
        words=[]
        for positions in itertools.combinations(range(n),weight):
            for letters in itertools.product('XYZ',repeat=weight):
                word=['I']*n
                for position,letter in zip(positions,letters):
                    word[position]=letter
                words.append(''.join(word))
        yield from sorted(words,key=packed)

def run(expr):
    return subprocess.run([str(worker),'--json'],input='quantum:'+expr,
                          encoding='utf-8',capture_output=True,timeout=60)

def expect(expr,wanted):
    p=run(expr);assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']==wanted,(expr,p.stdout,wanted)

def correction(code,bits):
    return 'stabilizer_correction(<'+','.join(code)+'>,['+','.join(map(str,bits))+'])'

checks=0
# Exhaust every syndrome for representative small codes, including redundant and signed checks.
for code in [['II'],['XX'],['XX','ZZ'],['-XX','ZZ','YY'],['XX','XX'],
             ['XI','IZ'],['ZZI','IZZ'],['XXXX','ZZZZ'],
             ['XZZXI','IXZZX','XIXZZ','ZXIXZ']]:
    n=len(code[0].lstrip('-'));table={}
    for word in candidates(n,n):
        table.setdefault(syndrome(code,word),word)
    for bits in itertools.product([0,1],repeat=len(code)):
        expr=correction(code,bits)
        if bits in table:
            expect('norm(vec('+expr+'-pauli('+table[bits]+')))','0')
        else:
            assert run(expr).returncode!=0,(code,bits)
        checks+=1

# Every single-qubit Pauli error in the five-qubit, Steane, and Shor codes.
codes=[['XZZXI','IXZZX','XIXZZ','ZXIXZ'],
       ['ZZZZIII','ZZIIZZI','ZIZIZIZ','XXXXIII','XXIIXXI','XIXIXIX'],
       ['ZZIIIIIII','IZZIIIIII','IIIZZIIII','IIIIZZIII','IIIIIIZZI',
        'IIIIIIIZZ','XXXXXXIII','IIIXXXXXX']]
rng=np.random.default_rng(20261014)
for code in codes:
    n=len(code[0]);dimension=2**n;table={}
    for word in candidates(n,1):
        table.setdefault(syndrome(code,word),word)
    # Independently construct two complex encoded states by projector action.
    states=rng.normal(size=(dimension,2))+1j*rng.normal(size=(dimension,2))
    for g in code:
        states=(states+matrix(g)@states)/2
    states/=np.linalg.norm(states,axis=0)
    for error in candidates(n,1):
        bits=syndrome(code,error);chosen=table[bits]
        expr=correction(code,bits)
        expect(expr+'==pauli('+chosen+')','1')
        recovered=matrix(chosen)@(matrix(error)@states)
        overlap=np.sum(states.conj()*recovered,axis=0)
        assert np.allclose(np.abs(overlap),1),(code,error,chosen,overlap)
        assert np.allclose(overlap[0],overlap[1]),(code,error,'state-dependent phase')
        checks+=1

print(f'PASS: {checks} exhaustive syndrome and encoded-state recovery cases.',flush=True)
for expr,wanted in [
    ('norm(vec(stabilizer_correction(<Z>,1)-X))','0'),
    ('norm(vec(stabilizer_correction(<X>,1)-Z))','0'),
    ('norm(vec(stabilizer_correction(<X,Z@Z>,[0,0])))',None),
    ('norm(vec(stabilizer_correction(<Z,X>,[1,1])))',None),
    (r'norm(vec(stabilizer_correction(\langle XX,ZZ\rangle,[1,1])-pauli(IY)))','0'),
    ('norm(vec(stabilizer_correction(vector(Z@Z@I,I@Z@Z),[1,1])-pauli(IXI)))','0'),
    ('fidelity(stabilizer_correction(<ZZI,IZZ>,[1,1])pauli(IXI)(|000>+i|111>),|000>+i|111>)','1.00000000000'),
    ('stabilizer_correction(<IIIIIIIII>,0)==identity(512)','1'),
]:
    if wanted is None: assert run(expr).returncode!=0,expr
    else: expect(expr,wanted)
    checks+=1
invalid=['stabilizer_correction(<Z>,2)','stabilizer_correction(<Z>,-1)',
         'stabilizer_correction(<Z>,1/2)','stabilizer_correction(<Z>,i)',
         'stabilizer_correction(<Z>,interval(0,1))','stabilizer_correction(<Z>,x)',
         'stabilizer_correction(<XX,ZZ>,1)','stabilizer_correction(<XX,ZZ>,[1])',
         'stabilizer_correction(<XX,ZZ>,[1,0,1])','stabilizer_correction(<XX,ZZ>,[1;0])',
         'stabilizer_correction(<XX,ZZ>,[1,2])','stabilizer_correction(<I>,1)',
         'stabilizer_correction(<Z,Z>,[1,0])','stabilizer_correction(<-I>,0)',
         'stabilizer_correction(<Z>)','stabilizer_correction(<Z>,0,0)']
for expr in invalid:
    assert run(expr).returncode!=0,expr
print(f'PASS: {checks} minimum-weight, syndrome and recovery checks; {len(invalid)} malformed inputs rejected.')
