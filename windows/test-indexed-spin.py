"""Independent indexed-spin matrix checks, including CUDA-Q's example."""
import itertools
import json
import math
import random
import subprocess
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent.parent
worker=root/'dist/QuantumStudio/quantum-worker.exe'
checks=0
pauli={'i':np.eye(2,dtype=complex),'x':np.array([[0,1],[1,0]],complex),
       'y':np.array([[0,-1j],[1j,0]],complex),'z':np.diag([1,-1]).astype(complex)}
def factor(n,axis,index):
    result=np.ones((1,1),complex)
    for wire in reversed(range(n)):
        result=np.kron(result,pauli[axis] if wire==index else pauli['i'])
    return result
def literal(matrix):
    return '['+';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)' for z in row) for row in matrix)+']'
def run(source):
    return subprocess.run([str(worker),'--json','--approx'],input='quantum:'+source,
                          encoding='utf-8',capture_output=True,timeout=60)
def scalar(source,expected):
    global checks
    result=run(source)
    assert result.returncode==0,(source,result.stderr)
    value=complex(json.loads(result.stdout)['text'].replace(' ','').replace('\u2212','-').replace('i','j'))
    assert abs(value-expected)<1e-12,(source,value,expected)
    checks+=1
def verify(source,expected):scalar('norm(vec(('+source+')-('+literal(expected)+')))',0)

for n in range(1,4):
    for axis in 'ixyz':
        for index in range(n):
            source=f'spin.{axis}({index})*spin.i({n-1})'
            verify(source,factor(n,axis,index))
            verify('3+'+source,3*np.eye(2**n)+factor(n,axis,index))
for left,right in itertools.product('xyz',repeat=2):
    verify(f'spin.{left}(0)*spin.{right}(0)',pauli[left]@pauli[right])
rng=random.Random(171)
for n in range(1,4):
    for trial in range(5):
        offset=rng.randrange(-4,5);source=str(offset);expected=offset*np.eye(2**n,dtype=complex)
        for term in range(3):
            coefficient=rng.choice([-3,-1,1,2]);word=np.eye(2**n,dtype=complex)
            expr=str(coefficient)
            for _ in range(3):
                axis=rng.choice('xyz');index=rng.randrange(n)
                expr+=f'*spin.{axis}({index})';word=word@factor(n,axis,index)
            source+='+'+expr;expected+=coefficient*word
        source+=f'+0*spin.i({n-1})'
        verify(source,expected)

hamiltonian='5.907-2.1433*spin.x(0)*spin.x(1)-2.1433*spin.y(0)*spin.y(1)+0.21829*spin.z(0)-6.125*spin.z(1)'
expected=5.907*np.eye(4)-2.1433*np.kron(pauli['x'],pauli['x'])-2.1433*np.kron(pauli['y'],pauli['y'])+0.21829*np.kron(pauli['i'],pauli['z'])-6.125*np.kron(pauli['z'],pauli['i'])
for prefix in ('spin.','cudaq.spin.','cudaq::spin::','cudaq::spin_op::'):
    verify(hamiltonian.replace('spin.',prefix),expected)
# CUDA-Q ansatz: X on q0, Ry(theta) on q1, controlled-X q1 -> q0.
# In the app's tensor order this is c|01>+s|10>.
for theta in (0,.59,math.pi/2,math.pi):
    state=f'cos(({theta})/2)|01>+sin(({theta})/2)|10>'
    scalar(f'expect({hamiltonian},{state})',5.907-4.2866*math.sin(theta)-6.34329*math.cos(theta))
verify('spin.x(2)',np.kron(pauli['x'],np.eye(4)))
scalar('tr(spin.i(8))',512)
scalar('norm(spin.x(0)|0>-|1>)',0)
scalar('norm(vec(controlled(spin.x(0))-CNOT))',0)
scalar('norm(vec((1+spin.z(0))/2-density(|0>)))',0)
scalar('tr((spin.x(0)+2)^2)',10)
scalar('tr(spin.x(0)+sin(pi/2+0))',2)
invalid=['spin.x(-1)','spin.x(9)','spin.x(0.5)','spin.x(a)','spin.x(1+1)',
         'spin.x()','spin.x(0,1)','spin.h(0)','spin.x','spin.x(0)+|0>',
         'spin.x(0)+1+spin.z(9)']
for source in invalid:
    result=run(source)
    assert result.returncode!=0,(source,result.stdout)
print(f'PASS: {checks} indexed-spin matrix/order/offset checks and {len(invalid)} invalid expressions.')
