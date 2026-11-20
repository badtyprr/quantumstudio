"""Check denominator recovery and exact success probabilities under uniform phase samples."""
import argparse
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
from itertools import product
import json
from math import gcd, lcm, prod
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
here=Path(__file__).parent
inventory=json.loads((here/"ibm029-inventory.json").read_bytes())
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
worker_hash=sha256(worker.read_bytes()).hexdigest()
assert worker_hash==json.loads((here/"ibm029-congruences.json").read_bytes())["worker_sha256"]
examples=[]
cases={f"M{i}":inventory["rows"][i-1]["literal"] for i in (289,291,294,298,306,307)}
for n,a in ((15,1),(15,4),(7,2),(15,2),(21,2),(35,2),(17,3),(31,3)):
    r=next(h for h in range(1,n) if pow(a,h,n)==1)
    size=2**(2*n.bit_length()+1)
    samples=[]
    denominators=[]
    for k in range(r):
        phase=Fraction(k,r)
        y=int(size*phase+Fraction(1,2))
        assert abs(Fraction(y,size)-phase)<Fraction(1,2*n*n)
        # A zero phase contributes the neutral denominator 1 directly.
        recovered=f"qsumset(x,recoverphase({y}/{size},{n}),x)" if y else "0"
        samples.append(dict(k=k,y=y,u=phase.numerator,v=phase.denominator))
        denominators.append(f"denominator({recovered})")
    key=f"denominators-{n}-{a}"
    cases[key]="vector("+",".join(denominators)+")"
    examples.append(dict(N=n,a=a,order=r,phase_grid=size,key=key,samples=samples))

# Neither 1/3 nor 1/2 reveals order 6 alone.
cases["combine-proper-divisors"]="lcm(denominator(qsumset(x,recoverphase(341/1024,21),x)),denominator(qsumset(x,recoverphase(512/1024,21),x)))"
inputs=[[key,expr,"0"] for key,expr in cases.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


@lru_cache(maxsize=4096)
def copy(text):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+text).encode(),env=env,capture_output=True,timeout=60,check=True)
    value=json.loads(proc.stdout)
    assert not value["approximate"],text
    return value["copy_text"]


records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"]==len(records)==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
forms={}
for (key,expr,_),rec in zip(inputs,records):
    assert rec["id"]==key and rec["restored_same"] and rec["label"]==rec["reentry_label"]=="EXACT RESULT"
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    forms[key]={rec["copy"],rec["second_copy"]}
assert all(copy(s)=="6" for s in forms["combine-proper-divisors"])


def check(key,values,expected):
    for text in forms[key]:
        for k,v in values.items():
            name=k if k=="y" else f'"{k}"'
            text=f"replace(({text}),{name},({v}))"
        assert copy(f"({text})=({expected})")=="1",(key,values,expected)


for ex in examples:
    n,a,r=ex["N"],ex["a"],ex["order"]
    samples=ex["samples"]
    ds=[s["v"] for s in samples]
    expected="vector("+",".join(map(str,ds))+")"
    for text in forms[ex["key"]]:
        assert copy(text)==expected
    for s in samples:
        k,u,v,y=s["k"],s["u"],s["v"],s["y"]
        assert v==r//gcd(k,r)
        check("M289",dict(k=k,r=r),Fraction(u,v))
        check("M298",dict(k=k),int(k==0))
        check("M291",dict(y=y,m=ex["phase_grid"].bit_length()-1,α=Fraction(y,ex["phase_grid"])),1)
        for key in ("M294","M306"):
            for proposed in (u,u+1):
                check(key,dict(k=k,r=r,u=proposed,v=v),int(proposed==u))
    for k in (-1,0,r-1,r):
        check("M307",dict(k=k,r=r),int(0<=k<r))

    primes=[p for p in range(2,r+1) if r%p==0 and all(p%i for i in range(2,p))]
    distribution=Counter({1:1})
    probabilities=[]
    for t in range(1,7):
        following=Counter()
        for current,ways in distribution.items():
            for v,multiplicity in Counter(ds).items():
                combined=int(copy(f"lcm({current},{v})"))
                assert combined==lcm(current,v) and r%combined==0
                following[combined]+=ways*multiplicity
        assert sum(following.values())==r**t
        distribution=following
        probability=Fraction(distribution[r],r**t)
        assert probability==prod(1-Fraction(1,p**t) for p in primes)
        if t<=2:
            assert distribution==Counter(lcm(*vals) for vals in product(ds,repeat=t))
        probabilities.append(str(probability))
    ex["success_after_independent_samples"]=probabilities
report=dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],worker_sha256=worker_hash,
            windows_records_sha256=sha256(records_path.read_bytes()).hexdigest(),inputs=inputs,examples=examples)
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(len(cases),"Windows inputs;",sum(ex["order"] for ex in examples),"phases;",len(examples)*6,"exact success probabilities")
