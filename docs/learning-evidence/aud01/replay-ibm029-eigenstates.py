"""Verify Shor's modular eigenstates, eigenphases and expansion of the unit basis state."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
source=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())


def verify(expr,answer):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,timeout=60)
    assert proc.returncode==0,(expr[:150],proc.stderr)
    value=json.loads(proc.stdout)
    assert not value["approximate"] and value["copy_text"]==str(answer),(expr[:150],value["copy_text"])


roots={1:"1",2:"-1",4:"i",6:"(1+i*sqrt(3))/2"}
examples=[]
for n,a in ((15,1),(15,4),(15,2),(15,14),(21,2),(21,5)):
    dimension=2**(n-1).bit_length()
    orbit=[1]
    x=a%n
    while x!=1:
        assert x not in orbit and x!=0
        orbit.append(x)
        x=x*a%n
    r=len(orbit)
    omega=roots[r]
    states=[]
    for j in range(r):
        terms=[f"(({omega})^{(-j*k)%r})*basis({label},{dimension})" for k,label in enumerate(orbit)]
        states.append("(("+"+".join(terms)+f")/sqrt({r}))")
    for j,state in enumerate(states):
        # The modular gate is a permutation on the full register, including padded states.
        verify(f"norm(modmul({a},{n})*{state}-(({omega})^{j})*{state})",0)
        for k,other in enumerate(states):
            verify(f"{state}~*{other}",int(j==k))
    verify(f"norm(("+"+".join(states)+f")/sqrt({r})-basis(1,{dimension}))",0)
    examples.append(dict(N=n,a=a,dimension=dimension,orbit=orbit,order=r,root_of_unity=omega,
                         eigenvalue_checks=r,inner_products=r*r,basis_reconstructions=1))

report=dict(source=source["source"],notebook_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
            source_ids=[92,98,107,108,113,115,116,117,120,123,125,331],examples=examples)
args.output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(sum(e["eigenvalue_checks"] for e in examples),"eigenstates,",sum(e["inner_products"] for e in examples),"inner products,",len(examples),"exact reconstructions")
