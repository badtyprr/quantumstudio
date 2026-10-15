"""Check full reflection matrices against independent complex projectors."""
import math,cmath,json,subprocess,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
checks=0
for n in (2,3,4,8):
    state=[complex(math.sin(k+1),math.cos(2*k+1)) for k in range(n)]
    weight=sum(abs(z)**2 for z in state)
    literal='['+';'.join(f'({z.real:.16g}+({z.imag:.16g})*i)' for z in state)+']'
    for phase in (None,0,math.pi/3,-0.71,2.19):
        expression=('reflection('+literal+')' if phase is None else 'phase_reflection('+literal+','+str(phase)+')')
        p=subprocess.run([str(worker),'--json','--approx'],input='quantum:'+expression,encoding='utf-8',capture_output=True,env=env,timeout=30)
        assert p.returncode==0,p.stderr
        data=json.loads(p.stdout);assert data['rows']==n and data['columns']==n,data
        factor=-2 if phase is None else cmath.exp(1j*phase)-1
        expected=[[(1 if r==c else 0)+factor*state[r]*state[c].conjugate()/weight for c in range(n)] for r in range(n)]
        for r in range(n):
            for c in range(n):
                actual=complex(data['cells'][r][c].replace('−','-').replace(' ','').replace('i','j'))
                assert abs(actual-expected[r][c])<2e-12,(n,phase,r,c,actual,expected[r][c])
        checks+=1
print(f'PASS: {checks} full complex reflection matrices match independent projectors in qubit and qudit dimensions.')
