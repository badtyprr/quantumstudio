"""Independent count-distribution checks for Hellinger measures."""
import json
import math
import random
import subprocess
from fractions import Fraction
from pathlib import Path

root=Path(__file__).resolve().parent.parent
worker=root/'dist/QuantumStudio/quantum-worker.exe'
checks=0
def run(source, approximate=True):
    return subprocess.run([str(worker),'--json']+(['--approx'] if approximate else []),
                          input='quantum:'+source,encoding='utf-8',capture_output=True,timeout=30)
def verify(source,expected):
    global checks
    result=run(source)
    assert result.returncode==0,(source,result.stderr)
    value=complex(json.loads(result.stdout)['text'].replace(' ','').replace('\u2212','-').replace('i','j'))
    assert abs(value-expected)<1e-12,(source,value,expected)
    checks+=1
def vector(xs,column=False):return '['+(';' if column else ',').join(map(str,xs))+']'

rng=random.Random(1729)
for n in (2,3,4,8,16):
    for trial in range(5):
        p=[rng.randrange(20) for _ in range(n)];q=[rng.randrange(20) for _ in range(n)]
        p[0]+=1;q[-1]+=1
        probability_p=[x/sum(p) for x in p];probability_q=[x/sum(q) for x in q]
        overlap=math.fsum(math.sqrt(x*y) for x,y in zip(probability_p,probability_q))
        distance=math.sqrt(math.fsum((math.sqrt(x)-math.sqrt(y))**2 for x,y in zip(probability_p,probability_q))/2)
        for name,expected in [('hellinger_fidelity',overlap**2),('hellinger_distance',distance)]:
            verify(f'{name}({vector(p)},{vector(q,True)})',expected)
            verify(f'{name}({vector([3*x for x in q])},{vector([7*x for x in p])})',expected)
verify('hellinger_fidelity([100,0,0,100],[90,10,10,90])',.9)
verify('hellinger_distance([1,0],[0,1])',1)
verify('hellinger_fidelity(probs(|+>),[25,25])',1)
verify('hellinger_fidelity([sqrt(2),sqrt(2)],[1,1])',1)
verify('hellinger_distance([1,2],[1,2])',0)
verify('hellinger_distance([1,2],[3,6])',0)
verify('hellinger_fidelity(probs(basis(0,1024)),probs(basis(0,1024)))',1)
verify('hellinger_distance([1,1],[1,1.00000001])',1e-8/(4*math.sqrt(2)))
verify('hellinger_fidelity(3,7)',1)
verify('hellinger_distance(3,7)',0)
for expression,expected in [('hellinger_fidelity([1,0],[1,1])','1/2'),('hellinger_distance([1,0],[0,1])','1')]:
    result=run(expression,False)
    assert result.returncode==0,(expression,result.stderr)
    data=json.loads(result.stdout)
    assert not data['approximate'] and Fraction(data['text'].replace(' ',''))==Fraction(expected),(expression,result.stdout)
invalid=['hellinger_fidelity([],[])','hellinger_distance([0,0],[1,1])',
         'hellinger_fidelity([-1,2],[1,1])','hellinger_distance([1,i],[1,1])',
         'hellinger_fidelity([1,2],[1,2,3])','hellinger_distance(I,I)',
         'hellinger_fidelity([infinity,1],[1,1])','hellinger_fidelity([interval(1,2),1],[1,1])',
         'hellinger_fidelity([1,2])','hellinger_distance([1,2],[1,2],3)']
invalid.append('hellinger_fidelity('+vector([1]*1025)+','+vector([1]*1025)+')')
for expression in invalid:
    result=run(expression)
    assert result.returncode!=0,(expression,result.stdout)
print(f'PASS: {checks} independent Hellinger numerical checks, two exact results and {len(invalid)} invalid inputs.')
