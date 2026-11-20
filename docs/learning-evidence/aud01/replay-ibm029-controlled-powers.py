"""Verify Shor's repeated squaring, controlled powers and polynomial cost comparison."""
import argparse
from hashlib import sha256
import json
from math import gcd
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
here=Path(__file__).parent
source=json.loads((here/"ibm029-inventory.json").read_bytes())
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
worker_hash=sha256(worker.read_bytes()).hexdigest()
assert worker_hash==json.loads((here/"ibm029-congruences.json").read_bytes())["worker_sha256"]
cases={}
def add(key,expression,expected):
    cases[key]=(expression,str(expected))


def vector(values):
    if len(values)==1:
        return str(values[0])
    return "vector("+",".join(map(str,values))+")"


examples=[]
for n,a in ((6,5),(15,2),(21,5),(35,3)):
    for width in (1,2,5,12,64):
        exponents=[2**j for j in range(1,width)]
        residues=[pow(a,k,n) for k in exponents]
        assert all(gcd(b,n)==1 for b in residues)
        for tag,body,values in (("k","2^x",exponents),("residue",f"{a}^(2^x) pmod ({n})",residues)):
            expr=f"if({width}<2,[],genvector({body},1,{width}-1,1,x,1))"
            add(f"{tag}-{n}-{width}",expr,vector(values))
        examples.append(dict(N=n,a=a,m=width,squarings=len(residues),last_multiplier=residues[-1] if residues else a))
    for k in (2,4,8):
        b=pow(a,k,n)
        add(f"operator-{n}-{k}",f"modmul({a},{n})^{k}=modmul({b},{n})",1)
        add(f"controlled-{n}-{k}",f"controlled(modmul({a},{n}))^{k}=controlled(modmul({b},{n}))",1)

add("different-multiplier","controlled(modmul(5,21))^4=controlled(modmul(4,21))",0)
add("M349-original",source["rows"][348]["literal"],0)
add("linear-control-width","2*n+3=O(n)",1)
cost="(2*n+3)*n^2+(2*n+3)+(2*n+3)^2"
add("cubic-cost",cost+"=O(n^3)",1)
add("quadratic-negative-control",cost+"=O(n^2)",0)
for i in (176,178):
    add(f"M{i}-original",source["rows"][i-1]["literal"],"symbolic")
inputs=[[k,expr,"0"] for k,(expr,_) in cases.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


def exact(expr):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,timeout=90,check=True)
    result=json.loads(proc.stdout)
    assert not result["approximate"],expr
    return result["copy_text"]


records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
for (key,expr,_),record in zip(inputs,records):
    assert record["id"]==key and record["restored_same"]
    assert record["label"]==record["reentry_label"]=="EXACT RESULT",key
    session=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert session["Expression"]==expr and session["Mode"]==0 and not session["Matrices"]
    for text in {record["copy"],record["second_copy"]}:
        if key in ("M176-original","M178-original"):
            vals={"a":5,"k":2,"N":21}
            if key=="M176-original":
                vals["b"]=4
            for symbol,v in vals.items():
                text=f'replace(({text}),"{symbol}",{v})'
            assert exact(text)=="0", (key,text)
        else:
            assert exact(text)==cases[key][1],key
for n,a in ((6,5),(15,2),(21,5),(35,3)):
    value=a
    for j in range(1,64):
        value=int(exact(f"{value}^2 pmod ({n})"))
        assert value==pow(a,2**j,n)
for n in range(2,513):
    assert 2*n.bit_length()+1<=2*(n-1).bit_length()+3

report=dict(source=source["source"],notebook_sha256=source["source_sha256"],worker_sha256=worker_hash,
            windows_records_sha256=sha256(records_path.read_bytes()).hexdigest(),examples=examples,
            windows_cases=inputs,successive_squarings=252,control_width_checks=511)
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(len(records),"Windows inputs; 252 successive modular squarings; 511 register-width bounds")
