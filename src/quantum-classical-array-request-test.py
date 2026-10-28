"""Typed runtime arrays through both worker engines and bounded request decoding."""
import json
import os
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

worker = Path(sys.argv[1] if len(sys.argv) > 1 else 'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()
checks = 0

def nums(*values):
    return ''.join(str(v) + '\n' for v in values).encode()

def integer(value):
    return nums(0, 0, 0, value & ((1 << 64) - 1))

def selection(indices, array=0, source='array.qasm:7:3'):
    label = source.encode()
    return nums(array, len(indices)) + b''.join(indices) + nums(len(label), *label)

def store(indices, value, array=0, numeric=False):
    return nums(22 if numeric else 21) + selection(indices, array) + value

def read(indices, array=0, numeric=False):
    return nums(10, 0, 32 if numeric else 0) + selection(indices, array)

def output(value, expected):
    return nums(7, 1, 1, 6, 0) + value + integer(expected)

def floating(value):
    return nums(3, 0, 64, struct.unpack('<Q', struct.pack('<d', value))[0])

def request(steps, exact, declarations=None):
    header = b'QEXACT14\n' + nums(1, 2) if exact else b'QSAMPLE15\n' + nums(1, 4000, 731, 2)
    # Six machine integers in a 2x3 array, and one float32 in a rank-one array.
    if declarations is None:
        declarations = nums(2, 0, 0, 0, 0, 2, 2, 3, 1, 0, 32, 0, 1, 1)
    return header + nums(6) + nums(0, 0) * 6 + nums(1, 0, 32) + declarations + nums(1000, 1, 1, len(steps)) + b''.join(steps)

def run(payload, exact, expected=None, error=None):
    global checks
    result = subprocess.run([str(worker), '--exact-circuit' if exact else '--sample'], input=payload, capture_output=True, timeout=45)
    checks += 1
    if error is not None:
        assert result.returncode and not result.stdout and error.encode() in result.stderr, (error, result.stdout, result.stderr)
        return
    assert result.returncode == 0 and not result.stderr, result.stderr
    value = json.loads(result.stdout)
    actual = {k: float(Fraction(v)) for k, v in value['probabilities'].items()} if exact else {k: v / 4000 for k, v in value['counts'].items()}
    assert set(actual) == set(expected), (actual, expected)
    assert all(abs(actual[k] - v) < (1e-12 if exact else .035) for k, v in expected.items()), (actual, expected)

for exact in (True, False):
    first = [integer(0), integer(0)]
    last = [integer(-1), integer(-1)]
    valid = request([store(last, integer(7)), output(read([integer(1), integer(2)]), 7)], exact)
    run(valid, exact, {'1': 1})
    # Nested array reads can supply an index, with each axis checked separately.
    run(request([store(first, integer(2)), store([integer(1), read(first)], integer(7)), output(read(last), 7)], exact), exact, {'1': 1})
    # Measurement-indexed writes retain independent state per history and shot.
    bit = nums(1, 1, 1, 0)
    gate_h = nums(0, 1, 0, 1) + b'H'
    run(request([gate_h, nums(1, 0, 0), store([bit, integer(0)], integer(7)), output(read([bit, integer(0)]), 7)], exact), exact, {'1': 1})
    # Read/write conversion to float32 happens at the array element boundary.
    numeric = read([integer(0)], 1, True)
    converted = nums(6, 0, 0) + numeric
    run(request([store([integer(0)], floating(16777217), 1, True), output(converted, 16777216)], exact), exact, {'1': 1})
    run(request([output(read(first), 0)], exact), exact, error='read before initialization')
    for indices in ([integer(2), integer(0)], [integer(-3), integer(0)], [integer(0), integer(3)], [integer(0), integer(-4)]):
        run(request([store(indices, integer(1))], exact), exact, error='array.qasm:7:3: Array index is outside')
    run(request([store([integer(0)], integer(1))], exact), exact, error='rank')
    run(request([store(first, integer(1), 2)], exact), exact, error='')
    run(request([store([integer(0)], integer(1), 1)], exact), exact, error='Expected an integer array')
    run(request([store(first, floating(1), numeric=True)], exact), exact, error='Expected a numeric array')
    # Reject malformed declarations, overlapping allocations and zero axes on access.
    for declaration in (nums(1, 0, 0, 0, 0, 0), nums(1, 0, 0, 0, 0, 8),
                        nums(1, 0, 0, 0, 0, 1, 4097), nums(1, 0, 0, 0, 0, 1, 7),
                        nums(1, 0, 0, 8, 0, 1, 1),
                        nums(2, 0, 0, 0, 0, 1, 4, 0, 0, 0, 3, 1, 3)):
        run(request([], exact, declaration), exact, error='')
    empty = nums(1, 0, 0, 0, 6, 1, 0)
    run(request([], exact, empty), exact, {'0': 1})
    run(request([store([integer(0)], integer(1))], exact, empty), exact, error='outside dimension')
    # Every truncation fails without partial output; previous versions reject the new format.
    for length in range(len(valid)):
        run(valid[:length], exact, error='')
    run(valid + b'0\n', exact, error='Trailing' if exact else 'trailing')
    run(valid.replace(b'QEXACT14\n', b'QEXACT13\n').replace(b'QSAMPLE15\n', b'QSAMPLE14\n'), exact, error='')

print(f'PASS: {checks} runtime array protocol checks.')
