#!/usr/bin/env python3
"""Finite manual IBM adaptations; see learning-evidence/DEV-12.md.

Independent trigonometric and state-vector oracles; no SDK execution claim.
Optional DEV12_RESULTS saves every request/response and binary provenance.
"""
import cmath
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else
              'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()
records = []


def evaluate(expression, approximate=False):
    process = subprocess.run([str(worker), '--json'] + (['--approx'] if approximate else []),
                             input=('quantum:' + expression).encode(), capture_output=True, timeout=30)
    record = dict(expression=expression, approximate=approximate, returncode=process.returncode,
                  stdout=process.stdout.decode(), stderr=process.stderr.decode())
    records.append(record)
    assert process.returncode == 0 and not process.stderr, record
    return json.loads(process.stdout)


def exact(expression):
    result = evaluate(expression)
    assert result['text'] == '0' and not result['approximate'], (expression, result)


def number(z):
    z = complex(z)
    return '(' + format(z.real, '.17g') + '+(' + format(z.imag, '.17g') + ')*i)'


def close(expression, expected, tolerance=2e-12):
    result = evaluate(expression, True)
    error = abs(complex(result['text'].replace('−', '-').replace(' ', '').replace('i', 'j')) - expected)
    assert error <= tolerance, (expression, expected, error)


def vector_close(expression, expected):
    literal = '[' + ';'.join(number(x) for x in expected) + ']'
    close('norm(vec((' + expression + ')-' + literal + '))', 0)


def rotation(axis, angle):
    c, s = math.cos(angle / 2), math.sin(angle / 2)
    if axis == 'y':
        return [[c, -s], [s, c]]
    if axis == 'x':
        return [[c, -1j*s], [-1j*s, c]]
    return [[cmath.exp(-0.5j*angle), 0], [0, cmath.exp(0.5j*angle)]]


def local(state, matrix, wire):
    # This oracle numbers wire 0 as the least significant bit, like Qiskit.
    result = [0j] * len(state)
    for column, amplitude in enumerate(state):
        bit = (column >> wire) & 1
        for row in range(2):
            result[(column & ~(1 << wire)) | (row << wire)] += matrix[row][bit] * amplitude
    return result


def cx(state):
    result = [0j] * 4
    for index, value in enumerate(state):
        result[index ^ (2 if index & 1 else 0)] = value
    return result


def two_local(parameters, derivative=None):
    state = [0j, 1+0j, 0j, 0j]  # Source X on Qiskit qubit 0.
    tangent = [0j] * 4
    for layer in range(2):
        for axis, offset in [('z', 0), ('y', 2)]:
            for wire in range(2):
                index = 4*layer+offset+wire
                matrix = rotation(axis, parameters[index])
                tangent = local(tangent, matrix, wire)
                state = local(state, matrix, wire)
                if index == derivative:
                    # dR/dtheta = (-i/2) P R; product rule through all later gates.
                    pauli = [[1,0],[0,-1]] if axis == 'z' else [[0,-1j],[1j,0]]
                    addition = local(state, pauli, wire)
                    tangent = [v-0.5j*d for v,d in zip(tangent, addition)]
        if layer == 0:
            state = cx(state)
            tangent = cx(tangent)
    return tangent if derivative is not None else state


def two_local_expression(parameters):
    state = '|01>'
    for layer in range(2):
        for axis, offset in [('z', 0), ('y', 2)]:
            for wire in range(2):
                parameter = parameters[4*layer+offset+wire]
                gate = 'R' + axis + '(' + (parameter if isinstance(parameter, str) else format(parameter, '.17g')) + ')'
                state = 'apply(' + gate + ',' + state + ',[' + str(1-wire) + '])'
        if layer == 0:
            state = 'apply(CX,' + state + ',[1,0])'
    return state


def sample(gates, expected_zero):
    # Separate stochastic witness, not an exact expectation/gradient oracle.
    shots, seed = 20000, 120105
    payload = ('QSAMPLE1\n1\n' + str(shots) + '\n' + str(seed) + '\n1\n0\n' + str(len(gates)) + '\n').encode()
    for gate in gates:
        encoded = gate.encode()
        payload += ('1\n0\n' + str(len(encoded)) + '\n').encode() + encoded
    process = subprocess.run([str(worker), '--sample'], input=payload, capture_output=True, timeout=30)
    record = dict(route='numerical sampling', payload=payload.decode(), returncode=process.returncode,
                  stdout=process.stdout.decode(), stderr=process.stderr.decode(),
                  expected_zero=expected_zero, absolute_frequency_tolerance=0.025)
    records.append(record)
    assert process.returncode == 0 and not process.stderr, record
    result = json.loads(process.stdout)
    assert sum(result['counts'].values()) == shots and set(result['counts']) <= {'0', '1'}, result
    assert abs(result['counts'].get('0', 0)/shots - expected_zero) < 0.025, record


def run():
    # IBM-102 cells 3,5; IBM-103 cells 2,3. Relative phases are compared directly.
    exact('norm(vec(apply(X,|000>,[2])-|001>))')
    exact('norm(vec(apply(X,apply(CX,apply(H,|000>,[2]),[2,1]),[0])-(|100>+|111>)/sqrt(2)))')
    for angle in (math.pi/3, math.pi/2, -0.7):
        state = 'apply(X,apply(CX,apply(Rx(' + repr(angle) + '),|000>,[2]),[2,1]),[0])'
        expected = [0j]*8
        expected[4], expected[7] = math.cos(angle/2), -1j*math.sin(angle/2)
        vector_close(state, expected)
        close('norm(vec(' + state + '))', 1)

    # IBM-104 cells 7,11: exact expectation, separate from finite-shot estimates.
    exact('expect(2*X-Z,H*|0>)-2')
    exact('expect(X,H*|0>)-1')
    exact('expect(Z,H*|0>)')
    # Added Y witness makes relative-phase/basis-sign errors observable.
    exact('expect(Y,(|0>+i*|1>)/sqrt(2))-1')
    # MOD-012 cell15 Rx then Rz: Bloch vector (sin(theta)sin(phi),
    # -sin(theta)cos(phi), cos(theta)); H and Sdg/H select X and Y.
    theta, phi = 0.7, -0.4
    gates = ['Rx(0.7)', 'Rz(-0.4)']
    for basis, mean in [([], math.cos(theta)), (['H'], math.sin(theta)*math.sin(phi)),
                        (['Sdg', 'H'], -math.sin(theta)*math.cos(phi))]:
        sample(gates+basis, (1+mean)/2)

    # IBM-104 cell18 / IBM-105 cell2: manual two-layer decomposition.
    for params in ([0]*8, [1]*8, [0.2,-0.4,0.7,-0.9,1.2,0.3,-0.8,0.6]):
        expected = two_local(params)
        expression = two_local_expression(params)
        vector_close(expression, expected)
        close('norm(vec(' + expression + '))', 1)
        # XX-3YY has off-diagonal weights 4 on 00<->11 and -2 on 01<->10.
        energy = 8*(expected[0].conjugate()*expected[3]).real - 4*(expected[1].conjugate()*expected[2]).real
        close('expect(tensor(X,X)-3*tensor(Y,Y),' + expression + ')', energy)
    params = [0.2,-0.4,0.7,-0.9,1.2,0.3,-0.8,0.6]
    state = two_local(params)
    hstate = [4*state[3], -2*state[2], -2*state[1], 4*state[0]]
    for index in range(8):
        tangent = two_local(params, index)
        derivative = 2*sum(d.conjugate()*h for d,h in zip(tangent, hstate)).real
        symbolic = list(params)
        symbolic[index] = 'x'
        cost = 'expect(tensor(X,X)-3*tensor(Y,Y),' + two_local_expression(symbolic) + ')'
        close('diff(' + cost + ',x,1,' + repr(params[index]) + ')', derivative)

    # MOD-012 cells13,15: C(x)=0.2355(cos(x)-1); analytic derivatives.
    observable = '(-471/2000*I+471/2000*Z)'
    objective = 'expect(' + observable + ',Rx(x)*|0>)'
    exact('diff(' + objective + ',x,1,pi/2)+471/2000')
    exact('diff(' + objective + ',x,2,0)+471/2000')
    for x in (-1.1, 0, 0.4, 1.7):
        close('diff(' + objective + ',x,1,' + repr(x) + ')', -0.2355*math.sin(x))
        # Parameter shift is checked against analytic differentiation, not finite differences.
        shifted = '(expect(' + observable + ',Rx(' + repr(x+math.pi/2) + ')*|0>)-expect(' + observable + ',Rx(' + repr(x-math.pi/2) + ')*|0>))/2'
        close(shifted, -0.2355*math.sin(x))
    # Repeated occurrence needs the chain rule; a naive pi/2 shift in x would give zero.
    exact('diff(expect(Z,Rx(2*x)*|0>),x,1,pi/4)+2')
    # IBM-105 cell9 update rule; finite deterministic steps, no convergence claim.
    x = 1.0
    for _ in range(5):
        gradient = -0.2355*math.sin(x)
        close('diff(' + objective + ',x,1,' + repr(x) + ')', gradient)
        next_x = x - 0.2*gradient
        close('expect(' + observable + ',Rx(' + repr(next_x) + ')*|0>)', 0.2355*(math.cos(next_x)-1))
        assert 0.2355*(math.cos(next_x)-1) < 0.2355*(math.cos(x)-1)
        x = next_x
    # Copy/re-entry of symbolic cost and derivative, then independent point evaluation.
    for original, expected in [(objective, 0.2355*(math.cos(0.7)-1)),
                               ('diff(' + objective + ',x)', -0.2355*math.sin(0.7))]:
        copied = evaluate(original)['copy_text']
        copied_twice = evaluate(copied)['copy_text']
        for text in (copied, copied_twice):
            close('replace((' + text + '),x,0.7)', expected)

    # IBM-106 cell4 / IBM-107 cell2: independent Bell eigenstates of aI+bXX+cYY+dZZ.
    hamiltonian = '2*tensor(I,I)-2*tensor(X,X)+3*tensor(Y,Y)-3*tensor(Z,Z)'
    bells = [('(|00>+|11>)/sqrt(2)', -6), ('(|00>-|11>)/sqrt(2)', 4),
             ('(|01>+|10>)/sqrt(2)', 6), ('(|01>-|10>)/sqrt(2)', 4)]
    for state, energy in bells:
        exact('expect(' + hamiltonian + ',' + state + ')-(' + str(energy) + ')')
        exact('norm(vec((' + hamiltonian + ')*(' + state + ')-(' + str(energy) + ')*(' + state + ')))')
    # IBM-106 cells17,28: finite weighted energy and overlap penalty adaptations.
    exact('2*expect(' + hamiltonian + ',' + bells[0][0] + ')+expect(' + hamiltonian + ',' + bells[1][0] + ')+8')
    exact('expect(' + hamiltonian + ',' + bells[0][0] + ')+33*abs(adjoint(' + bells[0][0] + ')*(' + bells[0][0] + '))^2-27')
    exact('abs(adjoint(' + bells[0][0] + ')*(' + bells[1][0] + '))^2')
    # MOD-012 cell43: given coefficients, not an independent chemistry derivation.
    a, b, c = -1.04886087, -0.7967368, 0.18121804
    for x in (0.0, 0.6, 2.0):
        h = '(' + repr(a) + '*I+' + repr(b) + '*Z+' + repr(c) + '*X)'
        close('expect(' + h + ',Ry(' + repr(x) + ')*|0>)', a+b*math.cos(x)+c*math.sin(x))
        close('diff(expect(' + h + ',Ry(x)*|0>),x,1,' + repr(x) + ')', -b*math.sin(x)+c*math.cos(x))


try:
    run()
    print('Variational finite adaptations:', len(records), 'worker checks passed')
finally:
    if os.environ.get('DEV12_RESULTS'):
        Path(os.environ['DEV12_RESULTS']).write_text(json.dumps(dict(
            worker=str(worker), worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
            records=records), indent=2) + '\n', encoding='utf-8')
