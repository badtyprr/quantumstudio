"""Typed numeric protocol tests with independent IEEE and modular references."""
import json, math, os, struct, subprocess, sys
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks=0
def n(*values):return ''.join(str(v)+'\n' for v in values).encode()
def floating(x,width=64):return n(3,0,width,struct.unpack('>I' if width==32 else '>Q',struct.pack('>f' if width==32 else '>d',x))[0])
def angle(x,width=8):return n(3,1,width,x)
def variable(kind,width,slot=0):return n(4,kind,width,slot)
def integer(x,width=64):return n(0,1,width,x)
def binary(op,a,b):return n(2,op)+a+b
def function(op,a):return n(6,op)+a
def cast(kind,width,a):return n(5,kind,width)+a
def store(a,slot=0):return n(18,slot)+a
def readout(a,width=8):return n(7,width,*range(width),8)+n(6,1,width)+a
def angleout(a,width=8):return n(7,width,*range(width),8,8)+a
def request(steps,exact,types=((0,64),),bits=8,qubits=0):
    header=b'QEXACT12\n'+n(qubits,bits) if exact else b'QSAMPLE13\n'+n(qubits,1000,731,bits)
    return header+n(0,len(types))+b''.join(n(*t) for t in types)+n(1000,bits,*reversed(range(bits)),len(steps))+b''.join(steps)
def run(payload,exact,success=True):
    global checks
    p=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=45)
    assert (p.returncode==0)==success,(p.stderr,payload[:160]);checks+=1
    if not success:assert not p.stdout and p.stderr;return
    assert not p.stderr,p.stderr
    return json.loads(p.stdout)
def expect(steps,expected,exact,types=((0,64),),bits=8):
    r=run(request(steps,exact,types,bits),exact)
    values=r['probabilities' if exact else 'counts']
    assert list(values)==[format(expected,'0'+str(bits)+'b')],values
for exact in (True,False):
    # A binary32 operation rounds before a later binary64 conversion.
    f=variable(0,32)
    expect([store(floating(16777216,32)),readout(binary(1,binary(0,f,floating(1,32)),f))],0,exact,((0,32),))
    expect([store(floating(16777216)),readout(binary(1,binary(0,variable(0,64),floating(1)),variable(0,64)))],1,exact)
    for code,value,expected in [(1,0,0),(2,0,1),(3,0,0),(4,0,0),(5,1,0),(6,0,0),(7,0,1),(8,1,0),(9,9,3),(10,3.9,3),(11,3.1,4)]:
        expect([readout(function(code,floating(value)))],expected,exact)
    expect([readout(binary(4,floating(2),floating(7)))],128,exact)
    expect([readout(binary(5,floating(17),floating(5)))],2,exact)
    a=variable(1,8)
    for op,x,y,result in [(0,250,10,4),(1,2,3,255),(6,170,15,10),(7,160,15,175),(8,170,15,165)]:
        expect([store(angle(x)),angleout(binary(op,a,angle(y)))],result,exact,((1,8),))
    for op,x,y,result in [(0,200,2,144),(1,200,3,66),(2,1,7,128),(3,128,7,1),(2,1,64,0)]:
        expect([angleout(n(7,op)+angle(x)+integer(y,8))],result,exact)
    expect([angleout(function(0,angle(1)))],255,exact)
    expect([angleout(function(12,angle(170)))],85,exact)
    expect([angleout(cast(1,8,floating(2*math.pi*127/512)))],64,exact)
    expect([angleout(cast(1,8,angle(65535,16)))],255,exact)
    expect([angleout(n(8,8,0,8,173))],173,exact)
    # Cross-domain nodes: ratio and comparison retain integer widths/signs.
    expect([n(7,8,*range(8),8,7)+angle(200)+angle(3)],66,exact)
    expect([n(7,1,0,6,2,9)+floating(-1)+floating(0)+n(0,0,0,0)],1,exact,bits=1)
    for expression in [binary(3,floating(1),floating(0)),function(9,floating(-1)),function(8,floating(0)),function(4,floating(2)),binary(4,floating(-1),floating(.5)),floating(float('inf')),n(3,0,32,1<<32),cast(0,64,angle(1)),cast(1,0,floating(0)),n(6,13)+floating(0),variable(0,32),variable(0,64,1)]:
        run(request([readout(expression)],exact),exact,False)
    run(request([readout(variable(0,64))],exact),exact,False)
    run(request([store(floating(1)),n(19,0),readout(variable(0,64))],exact),exact,False)
    # Lazy condition: a failing expression in an untaken body stays unevaluated.
    expect([n(8,0,1,0,1)+readout(function(9,floating(-1)))+n(0)],0,exact)
    valid=request([store(floating(3)),readout(variable(0,64))],exact)
    for length in range(len(valid)):run(valid[:length],exact,False)
    run(valid+b'0\n',exact,False)
    run(valid.replace(b'QEXACT12\n',b'QEXACT11\n').replace(b'QSAMPLE13\n',b'QSAMPLE12\n'),exact,False)
print(f'PASS: {checks} runtime numeric protocol checks.')
