"""Compare operator norms with independently prescribed singular values."""
import math, cmath, json, os, subprocess
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
checks=0
for rows,cols in [(2,3),(3,2),(4,4),(8,16),(16,8)]:
    rank=min(rows,cols)
    for deficient in (False,True):
        singular=[(0 if deficient and k>=rank//2 else (k+1)/rank) for k in range(rank)]
        u=[[cmath.exp(1j*(2*math.pi*r*k/rows+math.sin(r+1)))/math.sqrt(rows) for k in range(rank)] for r in range(rows)]
        v=[[cmath.exp(1j*(2*math.pi*c*k/cols+math.cos(c+1)))/math.sqrt(cols) for k in range(rank)] for c in range(cols)]
        matrix=[[sum(u[r][k]*singular[k]*v[c][k].conjugate() for k in range(rank)) for c in range(cols)] for r in range(rows)]
        literal='['+';'.join(','.join(f'({z.real:.15g}+({z.imag:.15g})*i)' for z in row) for row in matrix)+']'
        for p in (1,2,3,1.5,math.inf):
            order='infinity' if math.isinf(p) else str(p)
            expected=max(singular) if math.isinf(p) else sum(s**p for s in singular)**(1/p)
            expression='qschatten('+literal+','+order+')'
            result=subprocess.run([str(worker),'--json'],input=expression,encoding='utf-8',capture_output=True,env=env,timeout=30)
            assert result.returncode==0,result.stderr
            data=json.loads(result.stdout);actual=float(data['text'])
            assert data['approximate'] and abs(actual-expected)<2e-10,(rows,cols,p,actual,expected)
            checks+=1
for expression,expected in [('tracenorm(QFT(5))',32),('spectralnorm(QFT(5))',1),('frobeniusnorm(QFT(5))',math.sqrt(32)),('norm([3,0;0,4],1e10)',4)]:
    result=subprocess.run([str(worker),'--json'],input='quantum:'+expression,encoding='utf-8',capture_output=True,env=env,timeout=30)
    assert result.returncode==0,result.stderr
    actual=float(json.loads(result.stdout)['text']);assert abs(actual-expected)<2e-10,(expression,actual,expected);checks+=1
print(f'PASS: {checks} operator norm checks with complex rectangular matrices, prescribed singular values, rank deficiency, noninteger/large orders, and 1024 matrix entries.')

for expression,expected in [('tracenorm(1e200*[3,0;0,4])/1e200',7),('spectralnorm(1e-200*[3,0;0,4])/1e-200',4)]:
    result=subprocess.run([str(worker),'--json'],input='quantum:'+expression,encoding='utf-8',capture_output=True,env=env,timeout=30)
    assert result.returncode==0,result.stderr
    text=json.loads(result.stdout)['text']
    values=[float(v.strip()) for v in text[9:-1].split(',')] if text.startswith('interval(') else [float(text)]
    assert max(abs(v-expected) for v in values)<2e-10,(expression,text)
print('PASS: 2 additional checks for extreme input scales and interval endpoints.')
