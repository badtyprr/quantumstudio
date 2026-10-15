"""Check logical distance independently using matrix action on the code space."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np

worker = Path(__file__).resolve().parent.parent / 'dist/QuantumStudio/quantum-worker.exe'
paulis = dict(I=np.eye(2), X=np.array([[0,1],[1,0]]),
              Y=np.array([[0,-1j],[1j,0]]), Z=np.diag([1,-1]))

def matrix(word):
    out = np.ones((1,1))
    for letter in word:
        out = np.kron(out, paulis[letter])
    return out

def run(expr):
    return subprocess.run([str(worker), '--json'], input='quantum:'+expr,
                          encoding='utf-8', capture_output=True, timeout=60)

def expect(expr, expected):
    p = run(expr)
    assert p.returncode == 0, (expr, p.stderr)
    assert json.loads(p.stdout)['text'] == expected, (expr, p.stdout, expected)

checks = 0
# Every signed, nonidentity single generator on two qubits has a two-dimensional code.
for letters in itertools.product('IXYZ', repeat=2):
    word = ''.join(letters)
    if word == 'II':
        continue
    for sign in [1, -1]:
        projector = (np.eye(4) + sign*matrix(word))/2
        distance = 3
        for error_letters in itertools.product('IXYZ', repeat=2):
            error_word = ''.join(error_letters)
            error = matrix(error_word)
            if not np.allclose(error@projector, projector@error):
                continue
            restricted = projector@error@projector
            scalar = np.trace(restricted)/np.trace(projector)
            if not np.allclose(restricted, scalar*projector):
                distance = min(distance, sum(c != 'I' for c in error_word))
        label = ('-' if sign < 0 else '')+word
        expect(f'stabilizer_parameters(<{label}>)', f'[2  1  {distance}]')
        checks += 1

cases = [
    ('I', 1, 1, 1), ('IIIIIIIII', 9, 9, 1),
    ('ZZI,IZZ', 3, 1, 1), # protects bit flips, but a weight-one Z is logical
    ('XXXX,ZZZZ', 4, 2, 2),
    ('XZZXI,IXZZX,XIXZZ,ZXIXZ', 5, 1, 3),
    ('ZZZZIII,ZZIIZZI,ZIZIZIZ,XXXXIII,XXIIXXI,XIXIXIX', 7, 1, 3),
    ('ZZIIIIIII,IZZIIIIII,IIIZZIIII,IIIIZZIII,IIIIIIZZI,IIIIIIIZZ,XXXXXXIII,IIIXXXXXX', 9, 1, 3),
    # Add a frozen ancilla: low-weight stabilizers must not lower logical distance.
    ('XZZXII,IXZZXI,XIXZZI,ZXIXZI,IIIIIZ', 6, 1, 3),
    ('-XXXX,ZZZZ,-YYYY,IIII,-XXXX', 4, 2, 2),
]
for group,n,k,d in cases:
    expect(f'stabilizer_parameters(<{group}>)', f'[{n}  {k}  {d}]')
    expect(f'stabilizer_distance(<{group}>)', str(d))
    checks += 2
expect(r'stabilizer_parameters(\left\langle XXXX,ZZZZ\right\rangle)', '[4  2  2]')
expect('stabilizer_parameters(vector(X@X@X@X,Z@Z@Z@Z))', '[4  2  2]')
checks += 2
invalid = ['<Z>', '<XX,ZZ>', '<X,Z>', '<XX,ZZ,YY>', '<-I>', '<iX>',
           '<X,ZZ>', '<H>', '<>', '<XXXXXXXXXX>']
for group in invalid:
    for name in ['stabilizer_distance', 'stabilizer_parameters']:
        p = run(name+'('+group+')')
        assert p.returncode != 0, (group,p.stdout)
print(f'PASS: {checks} distance/parameter checks; {2*len(invalid)} invalid or k=0 inputs rejected.')
