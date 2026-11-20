"""Compare the full control/target amplitudes with the Shor eigenstate expansion."""
import argparse
import cmath
from fractions import Fraction
from hashlib import sha256
import json
from math import pi
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
here=Path(__file__).parent
source=json.loads((here/"ibm029-inventory.json").read_bytes())


def calculate(expr):
    proc=subprocess.run([worker,"--json","--approx"],env=env,input=("quantum:"+expr).encode(),
                        capture_output=True,timeout=120,check=True)
    result=json.loads(proc.stdout)
    assert result["columns"]==1 and result["rows"]==len(result["cells"])
    def number(text):
        text=text.replace("−","-").replace(" ∕ ","/").replace(" ","")
        return complex(text.replace("i","j")) if "i" in text else complex(Fraction(text))
    return [number(row[0]) for row in result["cells"]]


def phase(x):
    return cmath.exp(2j*pi*x)


examples=[]
for n,a,m in ((5,4,3),(7,2,4),(15,2,3),(21,2,2)):
    target_bits=(n-1).bit_length()
    d=2**target_bits
    size=2**m
    orbit=[1]
    while (x:=orbit[-1]*a%n)!=1:
        assert x not in orbit
        orbit.append(x)
    r=len(orbit)
    ops=[f"apply(H,s_0,[{j}])" for j in range(m)]
    targets=list(range(m,m+target_bits))
    for j in range(m):
        b=pow(a,2**(m-1-j),n)
        if b!=1:
            wires=",".join(map(str,[j]+targets))
            ops.append(f"apply(controlled(modmul({b},{n})),s_0,[{wires}])")
    controls=",".join(map(str,range(m)))
    ops.append(f"apply(fourier({size})~,s_0,[{controls}])")
    state=f"sequence([{','.join(ops)}],basis(1,{size*d}),s_0)"
    observed=calculate(state)
    assert len(observed)==size*d
    gamma=[[sum(phase(x*(k/r-y/size)) for x in range(size))/size for y in range(size)] for k in range(r)]
    predicted=[0j]*(d*size)
    for y in range(size):
        for h,label in enumerate(orbit):
            # The Windows circuit stores control wires first. The lesson writes
            # the same tensor product with the target factor first.
            predicted[y*d+label]=sum(phase(-k*h/r)*gamma[k][y] for k in range(r))/r
    amp_error=max(abs(z-w) for z,w in zip(observed,predicted))
    assert amp_error<1e-12
    probs=calculate(f"probs({state},[{controls}])")
    density_error=0
    for y in range(size):
        for z in range(size):
            reduced=sum(observed[y*d+j]*observed[z*d+j].conjugate() for j in range(d))
            mixture=sum(g[y]*g[z].conjugate() for g in gamma)/r
            density_error=max(density_error,abs(reduced-mixture))
            if z==y:
                assert abs(probs[y]-mixture)<1e-12
    assert density_error<1e-12 and abs(sum(probs)-1)<1e-12
    examples.append(dict(N=n,a=a,order=r,width=m,orbit=orbit,circuit=state,amplitudes=len(observed),
                         reduced_matrix_entries=size**2,max_amplitude_error=amp_error,max_density_error=density_error,
                         measurement_probabilities=[p.real for p in probs]))
report=dict(source=source["source"],notebook_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
            source_ids=[331,336,337,340,341,342,343,344],examples=examples)
args.output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(sum(x["amplitudes"] for x in examples),"amplitudes and",sum(x["reduced_matrix_entries"] for x in examples),"reduced-state entries passed")
