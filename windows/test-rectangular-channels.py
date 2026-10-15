"""Dimension-changing Kraus maps, independently checked with NumPy.

IBM general-measurement formulas motivate these tests; random maps are
generated independently, including trace-decreasing branches and discards.
"""
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / 'dist/QuantumStudio/quantum-worker.exe'
checks = 0

def run(expression, approximate=True):
    return subprocess.run([str(WORKER), '--json'] + (['--approx'] if approximate else []),
                          input='quantum:' + expression, encoding='utf-8',
                          capture_output=True, timeout=60)

def scalar(expression, expected=0):
    global checks
    result = run(expression)
    assert result.returncode == 0, (expression, result.returncode, result.stderr)
    text = json.loads(result.stdout)['text'].replace(' ', '').replace('−', '-').replace('i', 'j')
    value = complex(text)
    assert abs(value - expected) < 2e-11, (expression, value, expected)
    checks += 1

def number(z):
    z = complex(z)
    return f'({z.real:.17g}+({z.imag:.17g})*i)'

def matrix(a):
    return '[' + ';'.join(','.join(number(z) for z in row) for row in a) + ']'

def operators(ks):
    return 'vector(' + ','.join(matrix(k) for k in ks) + ')'

rng = np.random.default_rng(1741)
for source, target, count in [(1,1,2),(1,2,2),(1,3,1),(2,3,2),(3,2,2),(2,4,1),(4,2,3),(2,1,2),(3,1,3),(3,5,2)]:
    for trial in range(3):
        raw = rng.normal(size=(target*count,source)) + 1j*rng.normal(size=(target*count,source))
        isometry = np.linalg.qr(raw)[0]
        ks = list(isometry.reshape(count,target,source))
        x = rng.normal(size=(source,source)) + 1j*rng.normal(size=(source,source))
        rho = x @ x.conj().T
        rho /= np.trace(rho)
        result = sum(k @ rho @ k.conj().T for k in ks)
        expr = f'channel({matrix(rho)},{operators(ks)})'
        if target == 1:
            scalar(expr, result[0,0])
        else:
            scalar(f'norm(vec({expr}-{matrix(result)}))')
        scalar(expr if target == 1 else f'tr({expr})', 1)
        # A single branch is not silently renormalized to trace one.
        branch = ks[0] @ rho @ ks[0].conj().T
        branch_expression = f'channel({matrix(rho)},vector({matrix(ks[0])}))'
        scalar(branch_expression if target == 1 else f'tr({branch_expression})', np.trace(branch))
        if target > 1:
            input_vector = number(rho[0,0]) if source == 1 else f'vec({matrix(rho)})'
            scalar(f'norm(superop({operators(ks)})*{input_vector}-vec({expr}))')
            # Choi is ordered input tensor output, with column-stacked Kraus vectors.
            choi = sum(np.outer(k.flatten(order='F'),k.flatten(order='F').conj()) for k in ks)
            if choi.size <= 128:
                scalar(f'norm(vec(choi({operators(ks)})-{matrix(choi)}))')
            else:
                # Keep each pasted expression below the parser's complexity limit.
                for column in range(len(choi)):
                    scalar(f'norm(choi({operators(ks)})basis({column},{len(choi)})-{matrix(choi[:,column:column+1])})')

# Three-outcome trine POVM, represented as a qubit-to-classical-qutrit channel.
trine = 'vector([sqrt(2/3),0;0,0;0,0],[0,0;-1/sqrt(6),1/sqrt(2);0,0],[0,0;0,0;-1/sqrt(6),-1/sqrt(2)])'
scalar(f'norm(vec(channel(density(|0>),{trine})-[2/3,0,0;0,1/6,0;0,0,1/6]))')
scalar(f'norm(vec(channel(density(|i>),{trine})-identity(3)/3))')
scalar('channel(density(|i>),vector(<0|,<1|))', 1)
scalar('channel(density(|i>),vector(<0|))', .5)
scalar('norm(vec(channel(density(|1>_3),vector([1,0,0;0,1,0],[0,0,1;0,0,0]))-density(|1>)))')
# IBM's non-projective two-outcome example: positive effects are not Kraus operators.
scalar('born([2/3,1/3;1/3,1/3],|+>)', 5/6)
scalar('born([1/3,-1/3;-1/3,2/3],|+>)', 1/6)
scalar('tr(channel(density(2|0>),vector([1,0;0,1;0,0])))', 4)
scalar('norm(vec(channel(1,vector(|i>))-density(|i>)))')
scalar('norm(vec(channel([1],vector([1;0]))-density(|0>)))')
scalar('channel(3,vector(1/2,i/2))', 1.5)
scalar('channel(0,vector(1))', 0)
scalar('norm(vec(channel(channel(density(|i>),vector(<0|)),vector(|+>))-density(|+>)/2))')
scalar('norm(superop(vector([1;2]))-[1;2;2;4])')
scalar('norm(vec(choi(vector([1;2]))-[1,2;2,4]))')

invalid = ['channel(I/2,vector([1,0;0,1;0,0],I))',
           'channel(I/2,vector(identity(3)))', 'channel(|0>,vector(I))',
           'channel(I/2,vector(2))', 'channel(I/2,[])',
           'channel(I/2,vector([1,0;0,1;0,0]),0)']
for expression in invalid:
    result = run(expression)
    assert result.returncode != 0, (expression, result.stdout)
print(f'PASS: {checks} rectangular-channel, branch, POVM and superoperator checks; {len(invalid)} invalid inputs.')
