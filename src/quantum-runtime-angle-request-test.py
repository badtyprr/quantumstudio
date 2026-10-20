"""Runtime angle wire format, feedback and malformed-input regression checks."""
import json, math, os, struct, subprocess, sys
from pathlib import Path
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve()
checks=0
def nums(*values):return ''.join(str(v)+'\n' for v in values).encode()
def constant(value):return nums(0,struct.unpack('>Q',struct.pack('>d',value))[0])
def rotation(angle,axis=1,wire=1):return nums(16,wire,axis)+angle
def request(steps,exact=True):
    header=b'QEXACT10\n'+nums(2,2) if exact else b'QSAMPLE11\n'+nums(2,10000,731,2)
    return header+nums(0,1000,2,0,1,len(steps))+b''.join(steps)
def run(payload,exact=True,success=True):
    global checks
    p=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30)
    assert (p.returncode==0)==success,(payload[:120],p.stderr)
    checks+=1
    if not success:
        assert not p.stdout and p.stderr
        return
    assert not p.stderr,p.stderr
    return json.loads(p.stdout)
def gate(text,wire=0):
    encoded=text.encode()
    return nums(0,1,wire,len(encoded))+encoded
# Real -> integer -> unsigned bit-register read; no initial-value substitution.
feedback=nums(1,1,1,1,0)
steps=[gate('H'),nums(1,0,0),rotation(feedback),nums(1,1,1)]
expected={'00':0.5,'10':math.cos(.5)**2/2,'11':math.sin(.5)**2/2}
for exact in (True,False):
    result=run(request(steps,exact),exact)
    if exact:
        values={}
        for k,v in result['probabilities'].items():
            p=subprocess.run([str(worker),'--json','--approx'],input=v.encode(),capture_output=True,timeout=30)
            assert p.returncode==0,p.stderr
            values[k]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
        assert all(abs(values.get(k,0)-v)<1e-10 for k,v in expected.items()),values
    else:
        values={k:v/10000 for k,v in result['counts'].items()}
        assert set(values)==set(expected) and all(abs(values[k]-v)<.02 for k,v in expected.items()),values
    for axis in range(3):run(request([rotation(constant(0),axis)],exact),exact)
    for angle in (constant(float('nan')),constant(float('inf')),nums(3),nums(2,4),nums(1,4,0,0,0)):
        run(request([rotation(angle)],exact),exact,False)
    run(request([rotation(constant(0),3)],exact),exact,False)
    run(request([rotation(constant(0),wire=2)],exact),exact,False)
    run(request([rotation(nums(2,3)+constant(1)+constant(0))],exact),exact,False)
    deep=constant(0)
    for _ in range(32):deep=nums(2,0)+constant(0)+deep
    run(request([rotation(deep)],exact),exact,False)
    valid=request([rotation(constant(0))],exact)
    for n in range(len(valid)):run(valid[:n],exact,False)
    run(valid+b'0\n',exact,False)
    old=valid.replace(b'QEXACT10\n',b'QEXACT9\n').replace(b'QSAMPLE11\n',b'QSAMPLE10\n')
    run(old,exact,False)
print(f'PASS: {checks} runtime angle protocol checks.')
