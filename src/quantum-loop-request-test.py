"""Exercise versioned runtime loops through the real worker process."""
import json
import os
from pathlib import Path
import subprocess
import sys
from fractions import Fraction

worker = Path(sys.argv[1] if len(sys.argv) > 1 else 'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()
checks = 0
def fields(*items):
    return ('\n'.join(map(str, items)) + '\n').encode()
def constant(value, width=1):
    return fields(0, width, value)
def read(index):
    return fields(1, 1, index)
def assign(index, value):
    return fields(7, 1, index) + value
def loop(condition, *body):
    return fields(11) + condition + fields(len(body)) + b''.join(body)
def gate(expression):
    value = expression.encode()
    return fields(0, 1, 0, len(value)) + value
def request(exact, body=(), budget=100, qubits=0, bits=1, output=(0,), types=(), old=False):
    header = ('QEXACT5' if old else 'QEXACT6') if exact else ('QSAMPLE6' if old else 'QSAMPLE7')
    result = fields(header, qubits, bits) if exact else fields(header, qubits, 100, 7, bits)
    result += fields(len(types)) + b''.join(fields(*t) for t in types)
    if not old:
        result += fields(budget)
    return result + fields(len(output), *output, len(body)) + b''.join(body)
def run(exact, value, expected=None, error=None):
    global checks
    result = subprocess.run([str(worker), '--exact-circuit' if exact else '--sample'], input=value, capture_output=True, timeout=20)
    checks += 1
    if error is not None:
        assert result.returncode != 0 and not result.stdout and result.stderr, (value, result)
        assert error in result.stderr.decode(errors='replace'), result.stderr
        return
    assert result.returncode == 0 and not result.stderr, (value, result.stderr)
    data = json.loads(result.stdout)
    values = data['probabilities' if exact else 'counts']
    if exact:
        assert {k: Fraction(v) for k, v in values.items()} == {k: Fraction(v) for k, v in expected.items()}, data
    else:
        assert set(values) == set(expected) and sum(values.values()) == 100, data
        for k, probability in expected.items():
            assert abs(values[k] / 100 - float(Fraction(probability))) < .2, data

yes, no = constant(1), constant(0)
variable = fields(4, 0, 8, 0)
def integer(value):
    return fields(0, 0, 0, value)
condition = fields(6, 4) + variable + integer(0)
decrement = fields(9, 0, 3, 1) + variable + integer(1)
for exact in (False, True):
    run(exact, request(exact), {'0': 1})
    run(exact, request(exact, old=True), {'0': 1})
    program = [assign(0, yes), loop(read(0), assign(0, no))]
    run(exact, request(exact, program, budget=2), {'0': 1})
    run(exact, request(exact, program, budget=1), error='loop condition budget')
    run(exact, request(exact, [loop(no)], budget=1), {'0': 1})
    run(exact, request(exact, [loop(no)], budget=0), error='loop condition budget')
    run(exact, request(exact, [loop(yes)], budget=3), error='loop condition budget')
    run(exact, request(exact, budget=0), {'0': 1})
    nested = [assign(0, yes), loop(read(0), loop(no), assign(0, no))]
    run(exact, request(exact, nested, budget=3), {'0': 1})
    run(exact, request(exact, nested, budget=2), error='loop condition budget')
    countdown = [fields(9, 0) + integer(3), loop(condition, decrement, assign(0, yes))]
    run(exact, request(exact, countdown, budget=4, types=[(0, 8)]), {'1': 1})
    run(exact, request(exact, [loop(condition)], types=[(0, 8)]), error='')
    run(exact, request(exact, [loop(constant(0, 2))]), error='one bit')
    run(exact, request(exact, [loop(no, assign(1, yes))]), error='')
    run(exact, request(exact, [loop(no)], old=True), error='')
    run(exact, request(exact, budget=1000001), error='')
    run(exact, request(exact, [loop(no)], bits=0, output=()), {'': 1})
    measured = [assign(1, yes), loop(read(1), gate('H'), fields(1, 0, 0), assign(1, no))]
    run(exact, request(exact, measured, qubits=1, bits=2, budget=3), {'0': '1/2', '1': '1/2'})
    # Almost-sure termination is not a finite exact distribution computation.
    repeat = [loop(fields(2) + read(0), gate('H'), fields(1, 0, 0))]
    if exact:
        run(exact, request(exact, repeat, qubits=1, budget=8), error='loop condition budget')
    else:
        run(exact, request(exact, repeat, qubits=1, budget=100), {'1': 1})
    payload = request(exact, [loop(no)])
    for cut in range(len(payload)):
        run(exact, payload[:cut], error='')
    run(exact, payload + b'0\n', error='')
    depth = loop(no)
    for _ in range(31):
        depth = loop(no, depth)
    run(exact, request(exact, [depth]), {'0': 1})
    run(exact, request(exact, [loop(no, depth)]), error='32')
print(f'PASS: {checks} runtime loop process checks.')
