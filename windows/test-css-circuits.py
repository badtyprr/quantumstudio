"""Check CSS circuit amplitudes, QASM exports, and native coset-state equivalence."""
import json
import re
import subprocess
import sys
from pathlib import Path
import numpy as np
from openqasm3 import parse,ast
records=json.loads(Path(sys.argv[1]+'.json').read_text(encoding='utf-8-sig'))
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def rows(text):
    text=text.strip().strip('[]').strip()
    if not text:return []
    return [list(map(int,re.split(r'[,\s]+',r.strip()))) for r in re.split(r'[;\n]',text)]
def literal(matrix):
    return '['+';'.join(','.join(map(str,row)) for row in matrix)+']'
def mask(row):return int(''.join(map(str,row)),2)
valid=rejected=0
for record in records:
    hx,hz=rows(record['Hx']),rows(record['Hz']);n=len((hx or hz)[0]);u=int(record['Bits'],2)
    compatible=all(sum(a*b for a,b in zip(x,z))%2==0 for x in hx for z in hz)
    allowed=compatible and all((u&mask(z)).bit_count()%2==0 for z in hz)
    assert record['Rejected']==(not allowed),record
    if not allowed:
        rejected+=1;continue
    circuit=json.loads(record['Circuit']);assert circuit['Qubits']==n
    steps=circuit['Steps'];assert len(steps)<=64
    gates=[s for s in parse(record['Qasm']).statements if isinstance(s,ast.QuantumGate)]
    assert len(gates)==len(steps)
    state=np.zeros(2**n,dtype=complex);state[0]=1
    for step,gate in zip(steps,gates):
        name=step['Gate'];wires=step['Wires']
        assert gate.name.name=={'H':'h','X':'x','CNOT':'cx'}[name]
        assert [q.indices[0][0].value for q in gate.qubits]==wires
        target=1<<(n-1-wires[-1])
        for i in range(2**n):
            if i&target:continue
            j=i|target
            if name=='H':
                a,b=state[i],state[j];state[i]=(a+b)/np.sqrt(2);state[j]=(a-b)/np.sqrt(2)
            elif name=='X' or i&(1<<(n-1-wires[0])):
                state[i],state[j]=state[j],state[i]
    # Apply the commuting projectors to |u>, independently of RREF synthesis.
    expected=np.zeros(2**n,dtype=complex);expected[u]=1
    indices=np.arange(2**n)
    for x in hx:expected=(expected+expected[indices^mask(x)])/2
    expected/=np.linalg.norm(expected)
    assert np.allclose(state,expected,atol=1e-12),(record,state,expected)
    expr='norm(('+record['Expression']+')-css_state('+literal(hx)+','+literal(hz)+','+str(u)+'))'
    p=subprocess.run([str(worker),'--json'],input='quantum:'+expr,encoding='utf-8',capture_output=True,timeout=60)
    assert p.returncode==0,(record,p.stderr)
    assert json.loads(p.stdout)['text']=='0',(record,p.stdout)
    valid+=1
assert (valid,rejected)==(219,336),(valid,rejected)
print(f'PASS: {valid} circuits match independent projector amplitudes and native CSS states; QASM gates verified; {rejected} invalid combinations rejected.')
