"""Compare compact Pauli construction with independently generated tensor matrices."""
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np

worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),
   'Y':np.array([[0,-1j],[1j,0]]),'Z':np.diag([1,-1])}

def run(expr):
    return subprocess.run([str(worker),'--json'],input='quantum:'+expr,
                          encoding='utf-8',capture_output=True,timeout=60)

def expect(expr,value='1'):
    p=run(expr);assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']==value,(expr,p.stdout,value)

def literal(matrix):
    def entry(value):
        value=complex(value)
        if value.imag: return 'i' if value.imag==1 else '-i'
        return str(int(value.real))
    return '['+';'.join(','.join(entry(v) for v in row) for row in matrix)+']'

checks=0
for n in range(1,4):
    for letters in itertools.product('IXYZ',repeat=n):
        label=''.join(letters);a=np.ones((1,1))
        for letter in letters:a=np.kron(a,P[letter])
        for prefix,phase in [('',1),('-',-1),('i',1j),('-i',-1j)]:
            expect('pauli("'+prefix+label+'") == '+literal(phase*a));checks+=1

for sign,sgn in [('',1),('+',1),('-',-1)]:
    for one in ['', '1']:
        for unit,phase in [('',1),('i',1j),('j',1j)]:
            prefix=sign+one+unit
            expected=literal(sgn*phase*np.kron(P['Y'],P['Z']))
            for quote in ['', '"', "'"]:
                expect('Pauli('+quote+prefix+'YZ'+quote+')=='+expected);checks+=1

# Upper width boundary and nontrivial tensor phases at larger widths.
for label in ['IIIIIIIII','XXXXXXXXX','YYYYYYYYY','ZZZZZZZZZ','XYZIYXZYI']:
    for prefix,phase in [('', '1'),('-','-1'),('j','i'),('-1j','-i')]:
        expect('pauli("'+prefix+label+'") == ('+phase+')*('+'@'.join(label)+')');checks+=1

for expr,wanted in [
    ("stabilizer_dimension(<-1XX,ZZ,1YY>)",'1'),
    ("stabilizer_syndrome(<ZZ>,Pauli('-1jXI'))",'1'),
    ("norm(vec(stabilizer_projector(<-1Z>)-density(|1>)))",'0'),
]:expect(expr,wanted);checks+=1

invalid=['pauli(2X)','pauli(11X)','pauli(iiX)','pauli(ijX)','pauli(--X)',
         'pauli(j)','pauli(1)','pauli(IXYZIXYZIX)',"Pauli('X\")",'pauli("X\')',
         'qpauliword(0,0,0,0)','qpauliword(10,0,0,0)','qpauliword(1,2,0,0)',
         'qpauliword(1,0,2,0)','qpauliword(1,0,0,4)','qpauliword(1,-1,0,0)',
         'qpauliword(1,0,0,1/2)','qpauliword(1,0,0,i)','qpauliword(1,0,0,x)',
         'qpauliword(100000000000000000000000000000,0,0,0)',
         'stabilizer_dimension(<jX>)']
for expr in invalid:assert run(expr).returncode!=0,expr
print(f'PASS: {checks} Pauli tensor/phase/label checks; {len(invalid)} malformed inputs rejected.')
