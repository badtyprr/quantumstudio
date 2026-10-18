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
def payload(exact,qubits,bits,output,steps,legacy=False,typed=False,variables=None):
    header=(b'QEXACT1\n' if legacy else b'QEXACT2\n') if exact else (b'QSAMPLE2\n' if legacy else b'QSAMPLE3\n')
    if typed:header=b'QEXACT3\n' if exact else b'QSAMPLE4\n'
    declarations=b''
    if variables is not None:
        header=b'QEXACT4\n' if exact else b'QSAMPLE5\n'
        declarations=n(len(variables))+b''.join(n(*t) for t in variables)
    return header+n(qubits)+ (b'' if exact else n(10000,1731))+n(bits)+declarations+n(len(output),*output,len(steps))+b''.join(steps)
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
def logical(op,left,right):return n(7,op)+left+right
def integer_bits(value):return n(8)+value
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
    # Logical guards skip runtime arithmetic, but never structural validation.
    for op,left,want in [(0,0,0),(1,1,1)]:
        typed([assign([8],logical(op,const(1,left),condition))],expected={str(want):1})
        typed([branch(logical(op,const(1,left),condition),[set_output])],expected={str(want):1})
        typed([assign([8],binary(op,const(1,left),condition))]) # Bitwise remains eager.
    for op,left in [(0,1),(1,0)]:
        typed([assign([8],logical(op,const(1,left),condition))])
    guarded=logical(0,compare(1,signed,zero),condition)
    for value,want in [(0,0),(2,1),(3,0)]:
        typed([assign(list(range(8)),const(8,value)),assign([8],guarded)],expected={str(want):1})
    for op in (0,1):
        for a in (0,1):
            for b in (0,1):
                want=(a and b) if op==0 else (a or b)
                typed([assign([8],logical(op,const(1,a),const(1,b)))],expected={str(want):1})
    for bad in [n(7,2),n(9),logical(0,const(2,0),const(1,1)),logical(1,const(1,1),const(2,0)),logical(0,const(1,0),read(9))]:
        typed([branch(const(1,0),[assign([8],bad)])])
    valid_logical=payload(exact,0,9,[8],[assign([8],guarded)],typed=True)
    for end in range(len(valid_logical)):run(exact,valid_logical[:end])
    run(exact,valid_logical+b'\n')
    for legacy in (False,True):
        run(exact,payload(exact,0,9,[8],[assign([8],logical(0,const(1,0),const(1,1)))],legacy=legacy))
    deep=const(1,0)
    for _ in range(31):deep=logical(0,const(1,0),deep)
    typed([assign([8],deep)],expected={'0':1})
    typed([assign([8],logical(0,const(1,0),deep))])
    broad=const(1,1)
    for _ in range(8):broad=logical(1,broad,broad)
    typed([assign([8],broad)],expected={'1':1})
    typed([assign([8],n(2)+broad)],expected={'0':1}) # Exactly 512 nodes.
    typed([assign([8],n(2,2)+broad)])

    typed([branch(const(1,0),[branch(negative,[])])],bits=7,out=[])
    for op,want in enumerate([8,4,12,3,0,36]):
        expr=integer_binary(op,integer_constant(0,0,6),integer_constant(0,0,2))
        typed([assign([8],compare(0,expr,integer_constant(0,0,want)))],expected={'1':1})
    for malformed in [n(4),n(0,2,8,0),n(0,0,65,0),n(0,0,8,256),n(1,0,1,64),n(3,6),n(2,2,8)+one]:
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
for exact in (True,False):
    def typed(steps,bits=8,out=list(range(8)),expected=None):
        run(exact,payload(exact,0,bits,out,steps,typed=True),expected)
    for sign in (0,1):
        for width in (1,3,8,63,64):
            targets=list(range(width));value=(1<<width)-1
            typed([assign(targets,integer_bits(integer_constant(sign,width,value)))],bits=width,out=targets,expected={'1'*width:1})
            typed([assign(targets,const(width,value)),assign(targets,integer_bits(integer_read(sign,width,*reversed(targets))))],bits=width,out=targets,expected={'1'*width:1})
            # Output strings follow requested bit order, unlike integer display.
            typed([assign(targets,const(width,1)),assign(targets,integer_bits(integer_read(sign,width,*reversed(targets))))],bits=width,out=targets,expected={'0'*(width-1)+'1':1})
    one=integer_constant(0,0,1)
    source=integer_read(0,3,0,1,2)
    increment=integer_bits(integer_cast(0,3,integer_binary(0,source,one)))
    typed([assign([0,1,2],const(3,3)),assign([1,2,3],increment)],bits=4,out=list(range(4)),expected={'1001':1})
    quotient=integer_bits(integer_cast(0,8,integer_binary(3,one,integer_read(0,8,*range(8)))))
    typed([branch(const(1,0),[assign(list(range(8)),quotient)])],expected={'00000000':1})
    typed([assign(list(range(8)),quotient)])
    for malformed in [integer_bits(one),integer_bits(n(4)),integer_bits(integer_read(0,8,*range(1,9))),integer_bits(integer_constant(0,3,8))]:
        typed([branch(const(1,0),[assign(list(range(8)),malformed)])])
    typed([assign([0],integer_bits(integer_constant(0,8,0)))])
    valid=payload(exact,0,8,list(range(8)),[assign(list(range(8)),integer_bits(integer_constant(0,8,255)))],typed=True)
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'\n')
    for legacy in (False,True):run(exact,payload(exact,0,8,list(range(8)),[assign(list(range(8)),integer_bits(integer_constant(0,8,0)))],legacy=legacy))
    deep=integer_constant(0,8,0)
    for _ in range(30):deep=integer_cast(0,8,deep)
    typed([assign(list(range(8)),integer_bits(deep))],expected={'00000000':1})
    typed([assign(list(range(8)),integer_bits(integer_cast(0,8,deep)))])
    broad=integer_constant(0,8,0)
    for _ in range(8):broad=integer_binary(0,broad,broad)
    typed([assign(list(range(8)),integer_bits(integer_cast(0,8,broad)))])
for exact in (True,False):
    def typed(steps,expected=None):
        run(exact,payload(exact,0,9,[8],steps,typed=True),expected)
    def ic(value):return integer_constant(0,0,value & ((1<<64)-1))
    base=integer_read(0,8,*range(8))
    power=integer_binary(5,base,ic(3))
    for raw,want in [(0,0),(2,8),(127,2048383),(254,-8),(255,-1)]:
        typed([assign(list(range(8)),const(8,raw)),assign([8],compare(0,power,ic(want)))],{'1':1})
    runtime_exponent=integer_binary(5,ic(2),base)
    for raw,want in [(0,1),(3,8),(62,1<<62)]:
        typed([assign(list(range(8)),const(8,raw)),assign([8],compare(0,runtime_exponent,ic(want)))],{'1':1})
    for raw in (63,255):
        steps=[assign(list(range(8)),const(8,raw))]
        failure=compare(0,runtime_exponent,ic(0))
        typed(steps+[assign([8],failure)])
        typed(steps+[branch(const(1,0),[assign([8],failure)])],{'0':1})
        typed(steps+[assign([8],logical(0,const(1,0),failure))],{'0':1})
    nested=integer_binary(5,ic(2),integer_binary(5,ic(3),ic(2)))
    typed([assign([8],compare(0,nested,ic(512)))],{'1':1})
    wrapped=integer_binary(5,integer_constant(1,0,2),ic(64))
    typed([assign([8],compare(0,wrapped,ic(0)))],{'1':1})
    malformed=integer_binary(5,ic(2),integer_read(0,1,9))
    typed([branch(const(1,0),[assign([8],compare(0,malformed,ic(0)))])])
    valid=payload(exact,0,9,[8],[assign([8],compare(0,nested,ic(512)))],typed=True)
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'\n')
    for legacy in (False,True):
        run(exact,payload(exact,0,9,[8],[assign([8],compare(0,nested,ic(512)))],legacy=legacy))
def variable(sign,width,slot):return n(4,sign,width,slot)
def store(slot,value):return n(9,slot)+value
for exact in (True,False):
    def checkvars(q,b,out,steps,expected,types=((0,8),)):
        run(exact,payload(exact,q,b,out,steps,variables=types),expected)
    v=variable(0,8,0);one=integer_constant(0,0,1);zero=integer_constant(0,0,0)
    positive=compare(4,v,zero);emit=assign([0],const(1,1))
    checkvars(0,1,[0],[store(0,integer_constant(0,0,3)),branch(positive,[emit])],{'1':1})
    checkvars(0,1,[0],[store(0,integer_constant(0,0,255)),branch(positive,[emit])],{'0':1})
    checkvars(0,8,list(reversed(range(8))),[store(0,integer_constant(0,0,3)),store(0,integer_binary(5,v,integer_constant(0,0,2))),assign(list(range(8)),integer_bits(v))],{'00001001':1})
    checkvars(1,1,[0],[gate('H',0),n(1,0,0),store(0,integer_read(1,1,0)),assign([0],const(1,0)),n(2,0),branch(positive,[gate('X',0)]),n(1,0,0)],{'0':Fraction(1,2),'1':Fraction(1,2)})
    checkvars(0,1,[0],[branch(const(1,0),[store(0,v)])],{'0':1})
    checkvars(0,1,[0],[branch(logical(0,const(1,0),positive),[emit])],{'0':1})
    checkvars(0,1,[0],[store(4095,one),branch(compare(0,variable(0,8,4095),one),[emit])],{'1':1},[(0,8)]*4096)
    checkvars(0,1,[0],[emit],{'1':1},[])
    for steps in [[branch(positive,[emit])],[store(0,one),n(10,0),branch(positive,[emit])],
                  [store(1,one)],[n(10,1)],[store(0,variable(1,8,0))],
                  [branch(const(1,0),[store(1,one)])],[store(0,integer_binary(3,one,zero))],
                  [store(0,variable(0,8,4096))],[n(11)]]:
        checkvars(0,1,[0],steps,None)
    for types in [[(2,8)],[(0,65)],[(0,8)]*4097]:checkvars(0,0,[],[],None,types)
    valid=payload(exact,0,1,[0],[store(0,one),branch(positive,[emit])],variables=[(0,8)])
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'0\n')
    # New nodes are unavailable in the preceding protocol, even if untaken.
    run(exact,payload(exact,0,1,[0],[branch(const(1,0),[branch(positive,[])])],typed=True))
    run(exact,payload(exact,0,1,[0],[store(0,one)],typed=True))
def from_bits(sign,width,value):return n(5,sign,width)+value
for exact in (True,False):
    def computed(steps,bits=1,expected=None,types=((1,1),),q=0):
        data=payload(exact,q,bits,list(reversed(range(bits))),steps,variables=types)
        return data.replace(b'QEXACT4\n',b'QEXACT5\n',1).replace(b'QSAMPLE5\n',b'QSAMPLE6\n',1)
    v=variable(1,1,0)
    emit=assign([0],integer_bits(v))
    truth=from_bits(1,1,const(1,1))
    run(exact,computed([store(0,truth),emit]),{'1':1})
    # A computed predicate can retain measurement history after the record changes.
    run(exact,computed([gate('H',0),n(1,0,0),store(0,from_bits(1,1,read(0))),assign([0],const(1,0)),n(2,0),emit],q=1),{'0':Fraction(1,2),'1':Fraction(1,2)})
    byte=from_bits(0,8,n(2)+const(8,0))
    run(exact,computed([store(0,byte),assign([0],compare(2,variable(0,8,0),integer_constant(0,0,0)))],types=[(0,8)]),{'1':1})
    # Lazy false avoids an undefined read, but validation still sees bad types/references.
    undefined=compare(0,v,integer_constant(1,1,0))
    lazy=from_bits(1,1,n(7,0)+const(1,0)+undefined)
    run(exact,computed([store(0,lazy),emit]),{'0':1})
    run(exact,computed([store(0,from_bits(1,1,undefined)),emit]))
    for bad in [from_bits(1,8,const(1,1)),from_bits(1,1,read(1)),
                from_bits(1,1,n(7,0)+const(1,0)+compare(0,variable(0,1,0),integer_constant(0,1,0))),
                n(6,1,1),from_bits(1,1,n(9)),from_bits(2,1,const(1,0))]:
        run(exact,computed([store(0,bad)]))
    nested=const(1,0)
    for _ in range(15):nested=integer_bits(from_bits(1,1,nested))
    run(exact,computed([store(0,from_bits(1,1,nested)),emit]),{'0':1})
    run(exact,computed([store(0,from_bits(1,1,integer_bits(from_bits(1,1,nested))))]))
    broad=const(1,0)
    for _ in range(8):broad=binary(1,broad,broad)
    run(exact,computed([store(0,from_bits(1,1,broad)),emit]),{'0':1})
    run(exact,computed([store(0,from_bits(1,1,n(2)+broad))]))
    valid=computed([store(0,truth),emit])
    for end in range(len(valid)):run(exact,valid[:end])
    run(exact,valid+b'\n')
    run(exact,payload(exact,0,1,[0],[store(0,truth),emit],variables=[(1,1)]))
    run(exact,payload(exact,0,1,[0],[assign([0],integer_bits(truth))],typed=True))
print('PASS: '+str(checks)+' classical expression process checks.')
