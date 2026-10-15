"""Independent numerical checks for selected IBM Learning formulas.

This is a partial audit of discrimination/tomography, purifications and fidelity,
not certification of entire lessons or their Python/Qiskit programs.
Sources are recorded in docs/ibm-learning-sections.json.
"""
import json
import math
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / 'dist/QuantumStudio/quantum-worker.exe'
checks = 0

def run(expression):
    return subprocess.run([str(WORKER), '--json', '--approx'],
                          input='quantum:' + expression, encoding='utf-8',
                          capture_output=True, timeout=60)

def verify(expression, expected=0, tolerance=3e-9):
    global checks
    result = run(expression)
    assert result.returncode == 0, (expression, result.returncode, result.stderr)
    value = complex(json.loads(result.stdout)['text'].replace(' ', '').replace('−', '-').replace('i', 'j'))
    assert abs(value - expected) < tolerance, (expression, value, expected)
    checks += 1

def number(z):
    z = complex(z)
    return f'({z.real:.17g}+({z.imag:.17g})*i)'

def matrix(a):
    return '[' + ';'.join(','.join(number(z) for z in row) for row in a) + ']'

rng = np.random.default_rng(1913)
def state(n):
    a = rng.normal(size=(n,n)) + 1j*rng.normal(size=(n,n))
    rho = a @ a.conj().T + np.eye(n)/5
    return rho / np.trace(rho)

def square_root(a):
    values, vectors = np.linalg.eigh(a)
    return (vectors * np.sqrt(np.maximum(values,0))) @ vectors.conj().T

for n in (2,3,4):
    for trial in range(3):
        rho, sigma = state(n), state(n)
        r, s = matrix(rho), matrix(sigma)
        for p in (0, 1/7, .5, 1):
            difference = p*rho - (1-p)*sigma
            optimal = .5 + np.sum(np.abs(np.linalg.eigvalsh(difference)))/2
            verify(f'1/2+tracenorm({p}*{r}-(1-({p}))*{s})/2', optimal)
        sr = square_root(rho)
        root_fidelity = np.sum(np.sqrt(np.maximum(np.linalg.eigvalsh(sr@sigma@sr),0)))
        verify(f'root_fidelity({r},{s})', root_fidelity)
        verify(f'rootfidelity(3*{s},5*{r})', root_fidelity)
        verify(f'fidelity({r},{s})', root_fidelity**2)

verify(r'\frac{1}{2}+\frac{1}{2}\left\|\frac{|0\rangle\langle0|-|+\rangle\langle+|}{2}\right\|_1', .5+math.sqrt(2)/4)
verify('root_fidelity(|0>,|+>)', 1/math.sqrt(2))
verify('fidelity(|0>,|+>)', .5)
verify('root_fidelity(|i>,|-i>)', 0)
verify('root_fidelity(3i|+>,|+>)', 1)

paulis = [np.array([[0,1],[1,0]]),np.array([[0,-1j],[1j,0]]),np.diag([1,-1])]
tetra = [np.array([1,0]), np.array([1/math.sqrt(3),math.sqrt(2/3)]),
         np.array([1/math.sqrt(3),math.sqrt(2/3)*np.exp(2j*np.pi/3)]),
         np.array([1/math.sqrt(3),math.sqrt(2/3)*np.exp(-2j*np.pi/3)])]
projectors = [np.outer(v,v.conj()) for v in tetra]
for trial in range(5):
    rho = state(2)
    r = matrix(rho)
    coefficients = [np.trace(p@rho).real for p in paulis]
    reconstruction = '(I' + ''.join(f'+({x})*{name}' for x,name in zip(coefficients,['X','Y','Z'])) + ')/2'
    verify(f'norm(vec({reconstruction}-{r}))')
    # Probabilities are calculated independently; reconstruction uses native matrix arithmetic.
    probabilities = [np.trace(p@rho).real/2 for p in projectors]
    estimate = '+'.join(f'({3*p-.5})*{matrix(v)}' for p,v in zip(probabilities,projectors))
    verify(f'norm(vec(({estimate})-{r}))')
    for p,v in zip(probabilities,projectors):
        verify(f'born({matrix(v)}/2,{r})',p)

for system, environment in [(2,2),(2,3),(3,2),(3,3)]:
    for trial in range(3):
        a = rng.normal(size=(system,environment)) + 1j*rng.normal(size=(system,environment))
        a /= np.linalg.norm(a)
        expected = a@a.conj().T
        # The first tensor factor is the system. Row stacking of A gives this ordering.
        purification = f'vec({matrix(a)}^T)'
        verify(f'norm(vec(ptrace(density({purification}),1,[{system},{environment}])-{matrix(expected)}))')
        verify(f'norm({purification})',1)

invalid = ['root_fidelity(0|0>,|0>)','rootfidelity([1,2;0,0],I/2)',
           'root_fidelity([2,0;0,-1],I/2)','root_fidelity(I,identity(3))',
           'root_fidelity(|0>)','root_fidelity(|0>,|0>,|0>)']
for expression in invalid:
    result = run(expression)
    assert result.returncode != 0,(expression,result.stdout)
print(f'PASS: {checks} IBM discrimination, tomography, purification and fidelity checks; {len(invalid)} invalid inputs.')
