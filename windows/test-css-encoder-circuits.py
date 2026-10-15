"""Verify complete logical-column maps, coherent append, and noisy append."""
import json,re,subprocess,sys
from pathlib import Path
import numpy as np
from openqasm3 import parse,ast
records=json.loads(Path(sys.argv[1]+'.json').read_text(encoding='utf-8-sig'))
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
def rows(text):
    text=text.strip().strip('[]').strip()
    return [] if not text else [list(map(int,re.split(r'[,\s]+',r.strip()))) for r in re.split(r'[;\n]',text)]
def literal(a):return '['+';'.join(','.join(map(str,row)) for row in a)+']'
def mask(row):return int(''.join(map(str,row)),2)
def native(expr):
    p=subprocess.run([str(worker),'--json'],input='quantum:'+expr,encoding='utf-8',capture_output=True,timeout=60)
    assert p.returncode==0,(expr,p.stderr)
    assert json.loads(p.stdout)['text']=='0',(expr,p.stdout)
def simulate(steps,n,state):
    state=state.copy()
    for step in steps:
        name=step['Gate'];wires=step['Wires'];target=1<<(n-1-wires[-1])
        if name=='S':
            for i in range(2**n):
                if i&target:state[i]*=1j
            continue
        if name=='SWAP':
            a,b=[1<<(n-1-w) for w in wires]
            for i in range(2**n):
                if not(i&a) and i&b:
                    j=i^a^b;state[[i,j]]=state[[j,i]]
            continue
        assert name in ['H','CNOT'],name
        for i in range(2**n):
            if i&target:continue
            j=i|target
            if name=='H':
                a,b=state[i].copy(),state[j].copy();state[i]=(a+b)/np.sqrt(2);state[j]=(a-b)/np.sqrt(2)
            elif i&(1<<(n-1-wires[0])):state[[i,j]]=state[[j,i]]
    return state
valid=rejected=columns=0
for record in records:
    hx,hz=rows(record['Hx']),rows(record['Hz']);n=len((hx or hz)[0]);d=2**n
    compatible=all((mask(x)&mask(z)).bit_count()%2==0 for x in hx for z in hz)
    assert record['Rejected']==(not compatible),record
    if not compatible:rejected+=1;continue
    k=record['LogicalQubits'];m=2**k;circuit=json.loads(record['Circuit']);assert circuit['Qubits']==n
    assert len(circuit['Steps'])<=64
    # Independent code-space projector, followed by distinct normalized columns.
    projector=np.eye(d);indices=np.arange(d)
    for x in hx:projector=(projector+projector[indices^mask(x)])/2
    for z in hz:
        projector[[i for i in range(d) if (i&mask(z)).bit_count()%2],:]=0
    basis=[];seen=set()
    for u in range(d):
        support=tuple(np.flatnonzero(np.abs(projector[:,u])>1e-10))
        if not support or support in seen:continue
        seen.add(support);basis.append(projector[:,u]/np.linalg.norm(projector[:,u]))
    expected=np.stack(basis,axis=1);assert expected.shape==(d,m)
    v='css_encoder('+literal(hx)+','+literal(hz)+')'
    if record['Mixed']:
        assert record['Qasm'] is None
        native('norm(vec(('+record['Expression']+')-('+v+')('+record['Input']+')('+v+')†))')
    else:
        gates=[g for g in parse(record['Qasm']).statements if isinstance(g,ast.QuantumGate)]
        assert len(gates)==len(circuit['Steps'])
        for step,gate in zip(circuit['Steps'],gates):
            assert gate.name.name=={'H':'h','S':'s','CNOT':'cx','SWAP':'swap'}[step['Gate']]
            assert [q.indices[0][0].value for q in gate.qubits]==step['Wires']
        if record['Append']:
            initial=np.zeros((d,1),complex);initial[0]=1
            actual=simulate(circuit['Steps'],n,initial)
            logical=np.array([1j**i.bit_count()/np.sqrt(m) for i in range(m)],complex)[:,None]
            if k>1:logical=simulate([{'Gate':'CNOT','Wires':[0,1]}],k,logical)
            assert np.allclose(actual,expected@logical,atol=1e-12),record
            native('norm(('+record['Expression']+')-('+v+')('+record['Input']+'))')
        else:
            initial=np.zeros((d,m),complex);initial[np.arange(m)<<(n-k),np.arange(m)]=1
            actual=simulate(circuit['Steps'],n,initial)
            assert np.allclose(actual,expected,atol=1e-12),(record,actual,expected)
            columns+=m
            for logical in range(m) if n<=3 else sorted(set([0,m-1])):
                expr=record['Expression'].replace('|'+('0'*n)+'⟩','basis('+str(logical<<(n-k))+','+str(d)+')')
                reference=v if k==0 else '('+v+')basis('+str(logical)+','+str(m)+')'
                native('norm(('+expr+')-('+reference+'))')
    valid+=1
assert (valid,rejected)==(73,28),(valid,rejected)
print(f'PASS: {valid} encoder circuits; {columns} complete logical basis columns; coherent/noisy append; QASM exports; {rejected} incompatible check pairs rejected.')
