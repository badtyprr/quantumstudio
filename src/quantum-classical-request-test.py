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
def payload(exact,qubits,bits,output,steps,legacy=False,typed=False):
    header=(b'QEXACT1\n' if legacy else b'QEXACT2\n') if exact else (b'QSAMPLE2\n' if legacy else b'QSAMPLE3\n')
    if typed:header=b'QEXACT3\n' if exact else b'QSAMPLE4\n'
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
    # Population counts retain full values through 64, including saved measurement reads.
    for value,count in [(0,0),(1,1),((1<<64)-1,64),(1<<63,1)]:
        check(0,64,list(reversed(range(64))),[assign(list(range(64)),n(4)+const(64,value))],{format(count,'064b'):1})
    check(1,64,[1,0],[gate('H',0),n(1,0,63),assign(list(range(64)),n(4)+read(63))],{'00':Fraction(1,2),'01':Fraction(1,2)})
    for direction,signed,distance,expected in [(0,0,1,'0011'),(1,0,1,'1100'),(0,1,255,'1100'),(1,1,255,'0011'),(0,0,255,'1100'),(0,0,0,'1001'),(1,1,128,'1001')]:
        check(0,4,[3,2,1,0],[assign([0,1,2,3],n(5,direction,signed)+const(4,9)+const(8,distance))],{expected:1})
    check(0,64,[63,0],[assign(list(range(64)),n(5,0,1)+const(64,1)+const(64,1<<63))],{'01':1})
    # Validate new nodes even in an untaken branch, and reject malformed flags.
    for invalid in [n(6),n(5,2),n(5,0,2),n(4)+read(1),n(5,0,0)+const(64,1)+read(1),n(4)*32+const(1,0)]:
        run(exact,payload(exact,0,1,[0],[branch(const(1,0),[branch(binary(5,invalid,const(64,0)),[])])]))
    rotated=payload(exact,0,4,[3,2,1,0],[assign([0,1,2,3],n(5,0,1)+const(4,9)+const(8,255))])
    for end in range(len(rotated)-12,len(rotated)):run(exact,rotated[:end])
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
# Typed integer nodes are available only in the new protocol versions.
def integer_constant(sign,width,value):return n(0,sign,width,value)
def integer_read(sign,width,*indices):return n(1,sign,width,*indices)
def integer_binary(op,left,right):return n(3,op)+left+right
def integer_cast(sign,width,value):return n(2,sign,width)+value
def compare(op,left,right):return n(6,op)+left+right
for exact in (True,False):
    def typed(steps,bits=9,out=[8],expected=None):
        run(exact,payload(exact,0,bits,out,steps,typed=True),expected)
    signed=integer_read(0,8,*range(8));unsigned=integer_read(1,8,*range(8))
    zero=integer_constant(0,0,0);one=integer_constant(0,0,1)
    initialize=assign(list(range(8)),const(8,255));set_output=assign([8],const(1,1))
    for op,value in enumerate([0,1,1,1,0,0]):
        typed([initialize,assign([8],compare(op,signed,unsigned))],expected={str(value):1})
    negative=compare(2,signed,zero)
    typed([initialize,branch(negative,[set_output])],expected={'1':1})
    typed([initialize,assign([8],compare(2,integer_cast(0,0,signed),zero))],expected={'1':1})
    typed([initialize,assign([8],compare(4,integer_cast(1,8,signed),zero))],expected={'1':1})
    quotient=integer_binary(3,integer_constant(0,0,6),signed)
    condition=compare(0,quotient,integer_constant(0,0,3))
    typed([assign(list(range(8)),const(8,2)),branch(condition,[set_output])],expected={'1':1})
    typed([branch(const(1,0),[branch(condition,[set_output])])],expected={'0':1})
    typed([branch(condition,[set_output])]) # Runtime division by zero.
    typed([branch(const(1,0),[branch(negative,[])])],bits=7,out=[])
    for op,want in enumerate([8,4,12,3,0]):
        expr=integer_binary(op,integer_constant(0,0,6),integer_constant(0,0,2))
        typed([assign([8],compare(0,expr,integer_constant(0,0,want)))],expected={'1':1})
    for malformed in [n(4),n(0,2,8,0),n(0,0,65,0),n(0,0,8,256),n(1,0,1,64),n(3,5),n(2,2,8)+one]:
        typed([assign([8],compare(0,malformed,zero))])
    typed([assign([8],n(6,6)+zero+zero)])
    typed([assign([8],compare(0,n(2,0,0)*32+zero,zero))])
    broad=zero
    for _ in range(8):broad=integer_binary(0,broad,broad)
    typed([assign([8],compare(0,broad,zero))]) # 513 expanded nodes.
    overflow=integer_binary(0,integer_constant(0,0,(1<<63)-1),one)
    typed([assign([8],compare(0,overflow,zero))])
    typed([assign(list(range(64)),const(64,1<<63)),assign([0],compare(2,integer_read(0,0,*range(64)),zero))],bits=64,out=[0],expected={'1':1})
    typed([assign([8],compare(0,n(2,0,0)*30+zero,zero))],expected={'1':1})
    typed([assign([8],compare(0,n(2,0,0)*31+zero,zero))])
    half=zero
    for _ in range(7):half=integer_binary(0,half,half) # 255 nodes each.
    at_limit=n(2)+compare(0,half,half) # 512 nodes including bit complement.
    typed([assign([8],at_limit)],expected={'0':1})
    typed([assign([8],n(2)+at_limit)])
    # Old headers must reject the typed node, not silently reinterpret it.
    run(exact,payload(exact,0,9,[8],[initialize,branch(negative,[set_output])]))
    valid=payload(exact,0,9,[8],[initialize,branch(negative,[set_output])],typed=True)
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'\n')
print('PASS: '+str(checks)+' classical expression process checks.')
