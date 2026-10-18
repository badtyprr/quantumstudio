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
def request(exact, body=(), budget=100, qubits=0, bits=1, output=(0,), types=(), old=False, transfers=False, termination=False, ranges=False):
    header = ('QEXACT5' if old else 'QEXACT6') if exact else ('QSAMPLE6' if old else 'QSAMPLE7')
    if transfers:
        assert not old
        header='QEXACT7' if exact else 'QSAMPLE8'
    if termination:
        assert not old
        header='QEXACT8' if exact else 'QSAMPLE9'
    if ranges:
        assert not old
        header='QEXACT9' if exact else 'QSAMPLE10'
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
def branch(condition, yes_body, no_body=()):
    return fields(8)+condition+fields(len(yes_body))+b''.join(yes_body)+fields(len(no_body))+b''.join(no_body)
for exact in (False, True):
    def new(body=(), **options):
        return request(exact, body, transfers=True, **options)
    stop, again = fields(12), fields(13)
    run(exact,new(),{'0':1})
    run(exact,new([loop(yes,stop,assign(0,yes))],budget=1),{'0':1})
    run(exact,new([loop(yes,stop),assign(0,yes)],budget=1),{'1':1})
    run(exact,new([loop(yes,stop)],budget=0),error='loop condition budget')
    run(exact,new([loop(yes,branch(yes,[stop]),loop(yes))],budget=1),{'0':1})
    once=loop(fields(2)+read(0),assign(0,yes),again,assign(0,no))
    run(exact,new([once],budget=2),{'1':1})
    run(exact,new([once],budget=1),error='loop condition budget')
    run(exact,new([loop(yes,again)],budget=3),error='loop condition budget')
    run(exact,new([fields(9,0)+integer(2),loop(condition,loop(yes,stop),decrement),assign(0,yes)],budget=5,types=[(0,8)]),{'1':1})
    for transfer in [stop,again]:
        run(exact,new([transfer]),error='enclosing loop')
        run(exact,new([branch(no,[transfer])]),error='enclosing loop')
        run(exact,request(exact,[loop(no,transfer)]),error='')
        run(exact,request(exact,[transfer],old=True),error='')
        run(exact,new([loop(no,transfer,assign(1,yes))]),error='')
        payload=new([loop(yes,transfer)])
        for cut in range(len(payload)):
            run(exact,payload[:cut],error='')
        run(exact,payload+b'0\n',error='')
    run(exact,new([loop(no,fields(14))]),error='')
    # Equal classical records retain different pending transfers after measurement.
    measured=[gate('H'),fields(1,0,0),loop(yes,branch(read(0),[assign(0,no),stop],[assign(0,no)]),gate('X'),fields(1,0,0),stop)]
    run(exact,new(measured,qubits=1),{'0':'1/2','1':'1/2'})
for exact in (False, True):
    def ended(body=(), **kwargs):
        return request(exact, body, termination=True, **kwargs)
    end=fields(14)
    run(exact,ended([end,assign(0,yes)],budget=0),{'0':1})
    run(exact,ended([assign(0,yes),end,assign(0,no)],budget=0),{'1':1})
    run(exact,ended([branch(yes,[end]),assign(0,yes)],budget=0),{'0':1})
    run(exact,ended([branch(no,[end]),assign(0,yes)],budget=0),{'1':1})
    run(exact,ended([loop(yes,loop(yes,assign(0,yes),end)),assign(0,no)],budget=2),{'1':1})
    run(exact,ended([end,loop(condition)],types=[(0,8)],budget=0),{'0':1})
    run(exact,ended([loop(yes,end)],budget=0),error='loop condition budget')
    run(exact,ended([end,assign(1,yes)]),error='')
    run(exact,ended([end,fields(12)]),error='enclosing loop')
    run(exact,ended([fields(15)]),error='')
    # Termination preserves probability mass with matching classical records.
    measured=[gate('H'),fields(1,0,0),branch(read(0),[assign(0,no),end],[assign(0,no)]),assign(0,yes)]
    run(exact,ended(measured,qubits=1),{'0':'1/2','1':'1/2'})
    payload=ended([end],budget=0)
    for cut in range(len(payload)):
        run(exact,payload[:cut],error='')
    run(exact,payload+b'0\n',error='')
    # Every earlier header rejects the new opcode instead of interpreting it.
    for version in range(1,8 if exact else 9):
        header=fields(('QEXACT' if exact else 'QSAMPLE')+str(version))
        run(exact,header+payload.split(b'\n',1)[1],error='')
def span(slot, start, stop, stride, *body):
    return fields(15, slot)+start+stop+stride+fields(len(body))+b''.join(body)

def ivar(slot):
    return fields(4,0,0,slot)

for exact in (False,True):
    def ranged(body=(), **options):
        options.setdefault('types',[(0,0),(0,0)])
        return request(exact,body,ranges=True,**options)
    binding,total=ivar(0),ivar(1)
    add=fields(9,1,3,0)+total+binding
    def equals(n):
        return assign(0,fields(6,0)+total+integer(n))
    def sum_range(start,stop,stride,body=(add,)):
        return [fields(9,1)+integer(0),span(0,integer(start),integer(stop),integer(stride),*body)]
    run(exact,ranged(),{'0':1})
    for start,stop,stride,expected in [(0,3,1,6),(0,5,2,6),(5,0,2**64-2,9),(3,0,1,0)]:
        run(exact,ranged(sum_range(start,stop,stride)+[equals(expected)]),{'1':1})
    run(exact,ranged(sum_range(0,3,1,(add,fields(9,0)+integer(99)))+[equals(6)]),{'1':1})
    captured=[fields(9,1)+integer(0),fields(9,2)+integer(3),
              span(0,integer(0),ivar(2),integer(1),add,fields(9,2)+integer(0)),equals(6)]
    run(exact,ranged(captured,types=[(0,0)]*3),{'1':1})
    negative=[fields(9,1)+integer(0),fields(9,2)+integer(2**64-2),
              span(0,integer(5),integer(0),ivar(2),add,fields(9,2)+integer(1)),equals(9)]
    run(exact,ranged(negative,types=[(0,0)]*3),{'1':1})
    measured=span(0,integer(0),integer(2),integer(1),gate('H'),fields(1,0,0),branch(read(0),[fields(12)]))
    run(exact,ranged([measured],qubits=1),{'0':'1/8','1':'7/8'})
    skip=branch(fields(6,0)+binding+integer(1),[fields(13)])
    run(exact,ranged(sum_range(0,3,1,(skip,add))+[equals(5)]),{'1':1})
    run(exact,ranged(sum_range(0,3,1,(add,fields(12)))+[equals(0)],budget=1),{'1':1})
    run(exact,ranged([span(0,integer(0),integer(3),integer(1),assign(0,yes),fields(14)),assign(0,no)],budget=1),{'1':1})
    payload=ranged([span(0,integer(0),integer(2),integer(1))],budget=4)
    run(exact,payload,{'0':1})
    run(exact,ranged([span(0,integer(0),integer(2),integer(1))],budget=3),error='loop condition budget')
    run(exact,ranged([span(0,integer(1),integer(0),integer(1))],budget=0),error='loop condition budget')
    run(exact,ranged([span(0,integer(0),integer(1),integer(0))]),error='step must not be zero')
    run(exact,ranged([branch(no,[span(0,integer(0),integer(1),integer(0))])],budget=0),{'0':1})
    run(exact,ranged([span(2,integer(0),integer(1),integer(1))]),error='')
    run(exact,ranged([span(0,ivar(5),integer(1),integer(1))]),error='')
    run(exact,ranged([span(0,ivar(1),integer(1),integer(1))]),error='initialization')
    run(exact,ranged([span(0,integer(0),integer(0),integer(1)),fields(9,1)+binding]),error='initialization')
    run(exact,ranged([fields(16)]),error='')
    for cut in range(len(payload)):
        run(exact,payload[:cut],error='')
    run(exact,payload+b'0\n',error='')
    for version in range(1,9 if exact else 10):
        old_header=fields(('QEXACT' if exact else 'QSAMPLE')+str(version))
        run(exact,old_header+payload.split(b'\n',1)[1],error='')
    depth=span(0,integer(1),integer(0),integer(1))
    for _ in range(31):depth=span(0,integer(1),integer(0),integer(1),depth)
    run(exact,ranged([depth]),{'0':1})
    run(exact,ranged([span(0,integer(1),integer(0),integer(1),depth)]),error='32')
print(f'PASS: {checks} runtime loop process checks.')
