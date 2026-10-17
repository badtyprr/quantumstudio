"""Exercise both process protocols against classical and quantum expectations."""
import json,os,subprocess,sys
from fractions import Fraction
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks=0
def n(*v):return ''.join(str(x)+'\n' for x in v).encode()
def const(width,value):return n(0,width,value)
def read(*bits):return n(1,len(bits),*bits)
def binary(op,a,b):return n(3,op)+a+b
def assign(targets,value):return n(7,len(targets),*targets)+value
def branch(condition,yes,no=()):return n(8)+condition+n(len(yes))+b''.join(yes)+n(len(no))+b''.join(no)
def gate(text,*wires):
    encoded=text.encode();return n(0,len(wires),*wires,len(encoded))+encoded
def payload(exact,qubits,bits,output,steps,legacy=False):
    header=(b'QEXACT1\n' if legacy else b'QEXACT2\n') if exact else (b'QSAMPLE2\n' if legacy else b'QSAMPLE3\n')
    return header+n(qubits)+ (b'' if exact else n(10000,1731))+n(bits,len(output),*output,len(steps))+b''.join(steps)
def run(exact,data,expected=None):
    global checks
    result=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=data,capture_output=True,timeout=30)
    checks+=1
    if expected is None:
        assert result.returncode!=0 and result.stderr and not result.stdout,(data[:100],result.stdout)
        return
    assert result.returncode==0 and not result.stderr,(data[:100],result.stderr)
    value=json.loads(result.stdout)
    if exact:
        assert {k:Fraction(v) for k,v in value['probabilities'].items()}=={k:Fraction(v) for k,v in expected.items()},value
    else:
        counts=value['counts'];assert set(counts)==set(expected) and sum(counts.values())==10000,value
        for k,p in expected.items():
            if p==1:assert counts[k]==10000
            else:assert abs(counts[k]/10000-float(p))<.04,value

for exact in (True,False):
    def check(q,b,out,steps,expected):run(exact,payload(exact,q,b,out,steps),expected)
    check(0,3,[2,1,0],[assign([0],const(1,1)),assign([1,2],read(0,1))],{'011':1})
    check(1,2,[1,0],[gate('X',0),n(1,0,0),assign([1],read(0)),assign([0],const(1,0))],{'10':1})
    check(0,64,[63],[assign([63],const(1,1))],{'1':1})
    check(0,2,[1,0],[assign([0,1],read(0,0))],{'00':1})
    check(0,2,[1,0],[assign([0],const(1,1)),branch(read(0),[assign([0],const(1,0)),assign([1],const(1,1))])],{'10':1})
    check(0,1,[0],[branch(const(1,0),[],[assign([0],const(1,1))])],{'1':1})
    check(3,3,[2,1,0],[gate('H',0),gate('H',1),n(1,0,0),n(1,1,1),branch(binary(2,read(0),read(1)),[gate('X',2)]),n(1,2,2)],dict.fromkeys(['000','011','101','110'],Fraction(1,4)))
    check(2,2,[1,0],[gate('H',0),gate('CNOT',0,1),n(1,0,0),assign([0],const(1,0)),n(1,1,1)],{'00':Fraction(1,2),'10':Fraction(1,2)})
    # Explicit expected values avoid deriving expectations from wire codes.
    for op,value in enumerate([1,7,6,40,0,0,1,0,0,1,1]):
        width=4 if op<5 else 1
        check(0,width,list(reversed(range(width))),[assign(list(range(width)),binary(op,const(4,5),const(4,3)))],{format(value&((1<<width)-1),'0'+str(width)+'b'):1})
    check(0,4,[3,2,1,0],[assign([0,1,2,3],n(2)+const(4,5))],{'1010':1})
    check(0,1,[0],[assign([0],n(2)*31+const(1,0))],{'1':1})
    check(0,64,list(reversed(range(64))),[assign(list(range(64)),const(64,(1<<64)-1))],{'1'*64:1})
    check(0,1,[],[assign([0],const(1,1))],{'':1})
    for invalid in [const(0,0),const(65,0),const(1,2),read(),read(64),read(1),n(4),n(3,11),binary(2,const(1,0),const(2,0)),n(2)*32+const(1,0)]:
        run(exact,payload(exact,0,1,[0],[assign([0],invalid)]))
    broad=const(1,1)
    for _ in range(9):broad=binary(0,broad,broad)
    run(exact,payload(exact,0,1,[0],[assign([0],broad)]))
    for invalid in [assign([],const(1,0)),assign([0,0],const(2,0)),assign([1],const(1,0)),branch(const(2,0),[]),branch(const(1,0),[assign([1],const(1,0))])]:
        run(exact,payload(exact,0,1,[0],[invalid]))
    valid=payload(exact,0,1,[0],[assign([0],const(1,1))])
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'\n')
    run(exact,payload(exact,0,1,[0],[assign([0],const(1,1))],legacy=True))
print('PASS: '+str(checks)+' classical expression process checks.')
