"""Full literal-angle QFT regression; stdlib numeric oracle over exact output.

Generated fixture from qBraid notebook revision86787e1ba372facc224f925189755e69c479828b,
qBraid-Algorithms/qft.ipynb. The request encoding matches the frozen importer's
binary64-to-17-digit gate expressions; both source and payload hashes are pinned.
This is worker coverage; frozen-importer/editor round trips remain release work.
"""
import cmath,hashlib,json,re,subprocess,sys,time
from pathlib import Path
def evaluate(text):
    # Iterative shunting-yard avoids Python AST construction recursion for the
    # thousands of exact terms in one amplitude. Never eval worker output.
    import re
    values=[];operators=[];expect_operand=True;position=0;count=0
    precedence={'+':1,'-':1,'*':2,'/':2,'u+':3,'u-':3,'^':4}
    def apply(op):
        if op in ('u+','u-'):
            value=values.pop();values.append(-value if op=='u-' else value);return
        if op in ('exp','sqrt','abs'):
            values.append({'exp':cmath.exp,'sqrt':cmath.sqrt,'abs':abs}[op](values.pop()));return
        right=values.pop();left=values.pop()
        values.append({'+':lambda:left+right,'-':lambda:left-right,'*':lambda:left*right,'/':lambda:left/right,'^':lambda:left**right}[op]())
    for match in re.finditer(r'\d+(?:\.\d+)?|exp|sqrt|abs|i|[+*/^()-]',text):
        assert not text[position:match.start()].strip();position=match.end();token=match.group();count+=1;assert count<1000000
        if token[0].isdigit() or token=='i':
            assert expect_operand;values.append(1j if token=='i' else float(token));expect_operand=False
        elif token in ('exp','sqrt','abs'):
            assert expect_operand;operators.append(token)
        elif token=='(':
            assert expect_operand;operators.append(token)
        elif token==')':
            assert not expect_operand
            while operators[-1]!='(':apply(operators.pop())
            operators.pop()
            if operators and operators[-1] in ('exp','sqrt','abs'):apply(operators.pop())
            expect_operand=False
        else:
            if expect_operand:
                assert token in ('+','-');operators.append('u'+token);continue
            while operators and operators[-1] in precedence and (precedence[operators[-1]]>precedence[token] or (precedence[operators[-1]]==precedence[token] and token!='^')):
                apply(operators.pop())
            operators.append(token);expect_operand=True
    assert not text[position:].strip() and not expect_operand
    while operators:apply(operators.pop())
    assert len(values)==1
    return values[0]

assert evaluate('-2^2')==-4 and evaluate('(-2)^2')==4
assert abs(evaluate('abs((1/2)*sqrt(2)*exp(i*(-1/7)))^2')-0.5)<1e-14
worker=Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if sys.platform=='win32' else '')).resolve()
source=Path(__file__).with_name('quantum-phase-iqft.qasm').read_text(encoding='utf-8')
assert hashlib.sha256(source.encode()).hexdigest()=='f92c9700786608fcf8a0f447736f9972402d1c5835dc23f7198ba86f34495568'
def numbers(*values):return ''.join(str(v)+'\n' for v in values).encode()
steps=[]
for line in source.splitlines()[4:]:
    measurement=re.fullmatch(r'b\[(\d+)\] = measure q\[(\d+)\];',line)
    if measurement:
        bit,wire=map(int,measurement.groups());steps.append(numbers(1,wire,bit));continue
    match=re.fullmatch(r'([a-z]+)(?:\(([-.0-9]+)\))? q\[(\d+)\](?:, q\[(\d+)\])?;',line)
    assert match,line
    name,angle,first,second=match.groups();wires=[int(first)]+([] if second is None else [int(second)])
    name={'h':'H','rx':'Rx','rz':'Rz','cx':'CNOT','swap':'SWAP'}[name]
    expression=(name+('('+format(float(angle),'.17g')+')' if angle is not None else '')).encode()
    steps.append(numbers(0,len(wires),*wires,len(expression))+expression)
assert len(steps)==58
payload=b'QEXACT2\n'+numbers(3,3,3,2,1,0,len(steps))+b''.join(steps)
assert hashlib.sha256(payload).hexdigest()=='ee756165a77d952032d0463c367e4381069e21cd43d0698798105200c2391801'
started=time.monotonic()
run=subprocess.run([str(worker),'--exact-circuit'],input=payload,capture_output=True,timeout=30)
assert run.returncode==0 and not run.stderr,run.stderr
assert len(run.stdout)<4001000
result=json.loads(run.stdout)
assert set(result)=={'qubits','classical_bits','bits','probabilities'}
assert (result['qubits'],result['classical_bits'],result['bits'])==(3,3,[2,1,0])
assert set(result['probabilities'])=={format(k,'03b') for k in range(8)}
# Independently calculated 60-digit dense-matrix values round to 1/8 at this
# stdlib tolerance. The local release investigation checks all literals at60digits.
probabilities={}
for label,text in result['probabilities'].items():
    assert isinstance(text,str) and 0<len(text)<=1000000
    value=evaluate(text);assert abs(value-0.125)<1e-12,(label,value)
    probabilities[label]=value
assert abs(sum(probabilities.values())-1)<1e-12
print('PASS: 55-gate literal inverse-QFT worker request; 8 probability checks; %.3fs'%(time.monotonic()-started))
