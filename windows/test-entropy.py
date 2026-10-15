"""Independent known-spectrum checks for the numerical entropy implementation."""
import cmath
import json
import math
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
worker = root / 'dist/QuantumStudio/quantum-worker.exe'
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / 'data'))
for n in (2, 3, 5, 8, 16):
    probabilities = [(k+1)/(n*(n+1)/2) for k in range(n)]
    # DFT eigenvectors with independent row phases produce dense complex
    # Hermitian matrices; eigenvalues are specified before constructing rho.
    unitary = [[cmath.exp(1j*(2*math.pi*r*k/n + math.sin(r+1)))/math.sqrt(n)
                for k in range(n)] for r in range(n)]
    matrix = [[sum(unitary[r][k]*probabilities[k]*unitary[c][k].conjugate()
                   for k in range(n)) for c in range(n)] for r in range(n)]
    # Larger literal matrices exceed the quantum notation node budget. Invoke
    # the registered core function directly to test its numerical matrix path.
    prefix = 'quantum:entropy([' if n <= 8 else 'qentropy(['
    expression = prefix + ';'.join(','.join(
        f'({z.real:.17g}+({z.imag:.17g})*i)' for z in row) for row in matrix) + '])'
    assert len(expression.encode()) <= 32768
    result = subprocess.run([str(worker),'--json'], input=expression,
                            encoding='utf-8', capture_output=True, env=env, timeout=20)
    assert result.returncode == 0, (n,result.stderr)
    data = json.loads(result.stdout)
    expected = -sum(p*math.log2(p) for p in probabilities)
    assert data['approximate'] and abs(float(data['text'])-expected)<2e-10, (n,data,expected)
    print(f'PASS: dense complex {n}x{n} entropy matches known spectrum')
    other_probabilities = probabilities[::-1]
    other = [[sum(unitary[r][k]*other_probabilities[k]*unitary[c][k].conjugate()
                  for k in range(n)) for c in range(n)] for r in range(n)]
    def literal(matrix):
        return '[' + ';'.join(','.join(f'({z.real:.17g}+({z.imag:.17g})*i)' for z in row) for row in matrix) + ']'
    prefix = 'quantum:tracedistance(' if n < 8 else 'qtracedistance('
    expression = prefix + literal(matrix) + ',' + literal(other) + ')'
    assert len(expression.encode()) <= 32768
    result = subprocess.run([str(worker),'--json'], input=expression,
                            encoding='utf-8', capture_output=True, env=env, timeout=20)
    assert result.returncode == 0, (n,result.stderr)
    data = json.loads(result.stdout)
    expected = sum(abs(p-q) for p,q in zip(probabilities,other_probabilities))/2
    assert data['approximate'] and abs(float(data['text'])-expected)<2e-10, (n,data,expected)
    print(f'PASS: dense complex {n}x{n} trace distance matches known spectrum')
    prefix = 'quantum:fidelity(' if n < 8 else 'qfidelity('
    expression = prefix + literal(matrix) + ',' + literal(other) + ')'
    result = subprocess.run([str(worker),'--json'], input=expression,
                            encoding='utf-8', capture_output=True, env=env, timeout=20)
    assert result.returncode == 0, (n,result.stderr)
    data = json.loads(result.stdout)
    expected = sum(math.sqrt(p*q) for p,q in zip(probabilities,other_probabilities))**2
    assert data['approximate'] and abs(float(data['text'])-expected)<2e-10, (n,data,expected)
    print(f'PASS: dense complex {n}x{n} squared fidelity matches known spectrum')
