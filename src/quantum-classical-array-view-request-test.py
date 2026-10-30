"""Array references through both engines, with explicit preflight and bounded decoding."""
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

def request(steps, exact, declarations=None, copies=False):
    header = b'QEXACT15\n' + nums(1, 2) if exact else b'QSAMPLE16\n' + nums(1, 4000, 731, 2)
    if copies:header=header.replace(b'QEXACT15',b'QEXACT16').replace(b'QSAMPLE16',b'QSAMPLE17')
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

def scalar(value):return nums(0)+value
def span(start=None,stop=None,step=None):
    return nums(1,(1 if start is not None else 0)|(2 if stop is not None else 0)|(4 if step is not None else 0))+b''.join(v for v in (start,stop,step) if v is not None)
def view(axes,writable=False,array=0,parent=None):
    return nums(int(writable),int(parent is not None))+(parent if parent is not None else nums(array))+nums(len(axes))+b''.join(axes)
def selected(reference,indices):
    label=b'view.qasm:8:3'
    return nums(4096)+reference+nums(len(indices))+b''.join(indices)+nums(len(label),*label)
def load(reference,indices):return nums(10,0,0)+selected(reference,indices)
def save(reference,indices,value):return nums(21)+selected(reference,indices)+value
def extent(reference,axis=0):return nums(12)+reference+nums(axis)
def check(*references):
    return nums(23,len(references))+b''.join(reference+nums(len(shape),*shape) for reference,shape in references)

for exact in (True,False):
    full=view([span(),span()],True)
    readonly=view([span(),span()])
    row=view([scalar(integer(1)),span()],True)
    reversed_row=view([span(step=integer(-1))],parent=row)
    payload=request([check((full,[2,3])),save(row,[integer(-1)],integer(7)),output(load(reversed_row,[integer(0)]),7)],exact)
    run(payload,exact,{'1':1})
    run(request([check((readonly,[]),(readonly,[])),output(extent(row),3)],exact),exact,{'1':1})
    run(request([check((readonly,[]),(full,[]))],exact),exact,{'0':1})
    run(request([check((full,[]),(full,[]))],exact),exact,error='must not overlap')
    even=view([scalar(integer(0)),span(integer(0),integer(2),integer(2))],True)
    odd=view([scalar(integer(0)),span(integer(1),integer(2),integer(2))],True)
    run(request([check((even,[2]),(odd,[1]))],exact),exact,{'0':1})
    run(request([check((full,[3,2])),output(read([integer(0),integer(0)]),0)],exact),exact,error='shape')
    run(request([save(readonly,[integer(0),integer(0)],integer(1))],exact),exact,error='readonly')
    illegal=view([span(),span()],True,parent=readonly)
    run(request([check((illegal,[]))],exact),exact,error='Readonly')
    undefined=view([scalar(nums(4,0,0,0)),span()])
    run(request([check((undefined,[]))],exact),exact,error='before initialization')
    invalid=view([scalar(integer(2)),span()])
    run(request([check((invalid,[]))],exact),exact,error='outside')
    zero_step=view([span(step=integer(0)),span()])
    run(request([check((zero_step,[]))],exact),exact,error='step must not be zero')
    bit=nums(1,1,1,0)
    dynamic=view([scalar(bit),span()],True)
    gate_h=nums(0,1,0,1)+b'H'
    run(request([gate_h,nums(1,0,0),check((dynamic,[3])),save(dynamic,[integer(2)],integer(7)),output(load(dynamic,[integer(2)]),7)],exact),exact,{'1':1})
    empty_declaration=nums(1,0,0,0,6,1,0)
    empty=view([span()])
    run(request([check((empty,[0])),output(extent(empty),0)],exact,empty_declaration),exact,{'1':1})
    run(request([output(load(empty,[integer(0)]),0)],exact,empty_declaration),exact,error='outside')
    run(request([check()],exact),exact,error='one to 64')
    run(request([check((full,[6]))],exact),exact,error='rank')
    run(request([output(extent(row,1),0)],exact),exact,error='rank')
    run(payload.replace(b'QEXACT15\n',b'QEXACT14\n').replace(b'QSAMPLE16\n',b'QSAMPLE15\n'),exact,error='')
    selection_only=request([save(row,[integer(0)],integer(1))],exact)
    run(selection_only.replace(b'QEXACT15\n',b'QEXACT14\n').replace(b'QSAMPLE16\n',b'QSAMPLE15\n'),exact,error='')
    deep=full
    for _ in range(32):deep=view([span(),span()],parent=deep)
    run(request([check((deep,[]))],exact),exact,error='32 levels')
    run(request([check((view([]),[]))],exact),exact,error='one to seven')
    run(request([nums(23,65)],exact),exact,error='')
    run(request([check((full,[4097,3]))],exact),exact,error='')
    for length in range(len(payload)):run(payload[:length],exact,error='')
    run(payload+b'0\n',exact,error='')
for exact in (True,False):
    row0=view([scalar(integer(0)),span()],True)
    row1=view([scalar(integer(1)),span()],True)
    def copy_values(destination,*sources):return nums(24)+destination+nums(len(sources))+b''.join(sources)
    initial=[save(row0,[integer(k)],integer(k+1)) for k in range(3)]
    copied=copy_values(row1,row0)
    run(request(initial+[copied,output(load(row1,[integer(2)]),3)],exact,copies=True),exact,{'1':1})
    first_two=view([span(integer(0),integer(1))],parent=row0)
    last_two=view([span(integer(1),integer(2))],True,parent=row0)
    first=view([span(integer(0),integer(0))],parent=row0)
    run(request(initial+[copy_values(last_two,first_two),output(load(row0,[integer(2)]),2)],exact,copies=True),exact,{'1':1})
    run(request(initial+[copy_values(row0,last_two,first),output(load(row0,[integer(2)]),1)],exact,copies=True),exact,{'1':1})
    run(request([copied],exact,copies=True),exact,error='initialization')
    run(request([copy_values(row1,first_two)],exact,copies=True),exact,error='shape')
    run(request([copy_values(row1,view([span()],array=1))],exact,copies=True),exact,error='type')
    run(request([copy_values(view([scalar(integer(1)),span()]),row0)],exact,copies=True),exact,error='readonly')
    run(request([copy_values(row1)],exact,copies=True),exact,error='sources')
    run(request([nums(24)+row1+nums(65)],exact,copies=True),exact,error='')
    run(request([copied],exact),exact,error='')
    for cut in (1,2,4,8,len(copied)//2):run(request([copied[:-cut]],exact,copies=True),exact,error='')

print(f'PASS: {checks} array view protocol checks.')
