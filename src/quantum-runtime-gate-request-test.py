"""Parameterized gate protocol, phase interference and input rejection checks."""
import cmath,json,math,os,struct,subprocess,sys
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks=0
def nums(*values):return ''.join(str(v)+'\n' for v in values).encode()
def real(value):return nums(0,struct.unpack('>Q',struct.pack('>d',value))[0])
def integer(value):return nums(0,0,0,value&((1<<64)-1))
def parameter(kind,angles,wires,controls=0,state=0,power=1):
    return nums(17,len(wires),*wires,kind,controls,state,len(angles))+b''.join(angles)+integer(power)
def gate(text,wire):
    data=text.encode();return nums(0,1,wire,len(data))+data
def request(steps,exact):
    header=b'QEXACT11\n'+nums(2,2) if exact else b'QSAMPLE12\n'+nums(2,10000,731,2)
    return header+nums(0,1000,2,0,1,len(steps))+b''.join(steps)
def run(payload,exact,success=True):
    global checks
    p=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=45)
    assert (p.returncode==0)==success,(p.stderr,payload[:100]);checks+=1
    if not success:assert not p.stdout and p.stderr;return
    assert not p.stderr,p.stderr
    return json.loads(p.stdout)
def probabilities(result,exact):
    if not exact:return {k:v/10000 for k,v in result['counts'].items()}
    values={}
    for k,v in result['probabilities'].items():
        p=subprocess.run([str(worker),'--json','--approx'],input=v.encode(),capture_output=True,timeout=30)
        assert p.returncode==0,p.stderr
        values[k]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
    return values
for exact in (True,False):
    # A phase on a superposed control is observable. P and controlled gphase
    # agree; substituting controlled Rz would give a different distribution.
    for kind,angles,wires,controls in [(3,[1.0],[0],0),(4,[1.0],[0],1)]:
        steps=[gate('H',0),parameter(kind,[real(x) for x in angles],wires,controls,1 if controls else 0),gate('H',0),nums(1,0,0)]
        values=probabilities(run(request(steps,exact),exact),exact)
        expected={'00':math.cos(.5)**2,'10':math.sin(.5)**2}
        assert all(abs(values.get(k,0)-v)<(1e-10 if exact else .02) for k,v in expected.items()),values
    # U3(theta,0,0) is Ry(theta). Published U adds a relative control phase.
    for kind in (5,6):
        steps=[gate('H',0),parameter(kind,[real(1),real(0),real(0)],[0,1],1,1),gate('H',0),nums(1,0,0),nums(1,1,1)]
        factor=1 if kind==5 else cmath.exp(.5j)
        expected={'00':abs((1+factor*math.cos(.5))/2)**2,'10':abs((1-factor*math.cos(.5))/2)**2,'01':math.sin(.5)**2/4,'11':math.sin(.5)**2/4}
        values=probabilities(run(request(steps,exact),exact),exact)
        assert all(abs(values.get(k,0)-v)<(1e-10 if exact else .02) for k,v in expected.items()),(kind,values,expected)
    for kind in range(7):
        run(request([parameter(kind,[real(0)]*(3 if kind in (5,6) else 1),[] if kind==4 else [0])],exact),exact)
    for step in [parameter(7,[real(0)],[0]),parameter(5,[real(0)],[0]),parameter(3,[real(0)],[0,1],1,2),parameter(3,[real(0)],[0,0],1,1),parameter(3,[real(0)],[2]),parameter(3,[real(0)],[0],power=65),parameter(3,[real(float('nan'))],[0])]:
        run(request([step],exact),exact,False)
    valid=request([parameter(3,[real(1)],[0])],exact)
    for length in range(len(valid)):run(valid[:length],exact,False)
    run(valid+b'0\n',exact,False)
    run(valid.replace(b'QEXACT11\n',b'QEXACT10\n').replace(b'QSAMPLE12\n',b'QSAMPLE11\n'),exact,False)
print(f'PASS: {checks} runtime gate protocol checks.')
