"""Compare the printed Shor arithmetic and basis tables with exact modular arithmetic."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
here=Path(__file__).parent
inventory=json.loads((here/"ibm029-inventory.json").read_bytes())
rows=inventory["rows"]
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
worker_hash=hashlib.sha256(worker.read_bytes()).hexdigest()
assert worker_hash==json.loads((here/"ibm029-windows-unit-copy.json").read_bytes())["worker_sha256"]
tables=re.findall(r"\\begin\{array\}\{c\|cccccc\}(.*?)\\end\{array\}",rows[21]["literal"],re.S)
assert len(tables)==2
cases={}
def add(key,expr,expected):
    cases[key]=(expr,expected)

for body,op,heading in zip(tables,("+","*"),("+",r"\cdot")):
    header,data=body.split(r"\hline")
    assert header.split("&")[0].strip()==heading
    assert list(map(int,re.findall(r"\d+",header)))==list(range(6))
    table=[list(map(int,re.findall(r"\d+",line))) for line in data.splitlines() if line.strip()]
    assert len(table)==6
    entries=[]
    for i,row in enumerate(table):
        assert row==[i]+[(i+j if op=="+" else i*j)%6 for j in range(6)]
        entries.extend(f"mod({i}{op}{j},6)" for j in range(6))
    add("M022-"+("sum" if op=="+" else "product"),"matrix(6,6,["+",".join(entries)+"])",
        "matrix(6,6,["+",".join(str(v) for row in table for v in row[1:])+"])")

orders={int(a):int(r) for a,r in re.findall(r"(\d+)\^\{(\d+)\}\s*=\s*1\b",rows[44]["literal"])}
assert sorted(orders)==[a for a in range(21) if math.gcd(a,21)==1]
for a,r in orders.items():
    residues=[pow(a,k,21) for k in range(1,r+1)]
    assert 1 not in residues[:-1] and residues[-1]==1
    expr="vector("+",".join(f"{a}^{k} pmod (21)" for k in range(1,r+1))+")"
    add(f"M045-orbit-{a}",expr,("vector("+",".join(map(str,residues))+")"))

    inverse=pow(a,-1,21)
    add(f"M076-order-identity-{a}",f"modmul({a},21)^{r}=identity(32)","1")
    add(f"M084-inverse-{a}",f"modmul({inverse},21)*modmul({a},21)=identity(32)","1")
add("M076-short-power","modmul(5,21)^5=identity(32)","0")
add("M084-wrong-inverse","modmul(16,21)*modmul(5,21)=identity(32)","0")

mapping={int(x):int(y) for x,y in re.findall(r"M_\{2\}\s*\\vert\s*(\d+)\s*\\rangle\s*=\s*\\vert\s*(\d+)\s*\\rangle",rows[67]["literal"])}
assert sorted(mapping)==list(range(15)) and all(y==2*x%15 for x,y in mapping.items())
dest=[mapping[x] for x in range(15)]+[15]
matrix="matrix(16,16,["+",".join(str(int(i==y)) for i in range(16) for y in dest)+"])"
add("M068-padded","modmul(2,15)",matrix)
for key,expr,expected in (("M015-original",rows[14]["literal"],1),("M019-original",rows[18]["literal"],0),
                          ("M018-M019-mod-seven","mod(3*5,7)=1",1),("M037-mod-six","5^2 pmod (6)=1",1),
                          ("M080-ordinary",r"replace(replace((a*b=1),a,5),b,17)",0),
                          ("M080-modular","mod(5*17,21)=1",1),("M082-ordinary","replace((a^(-1)),a,5)","1 ∕ 5")):
    add(key,expr,str(expected))
inputs=[[key,expr,"0"] for key,(expr,_) in cases.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
for (key,expr,_),rec in zip(inputs,records):
    assert rec["id"]==key and rec["restored_same"]
    assert rec["label"]==rec["reentry_label"]=="EXACT RESULT",key
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    for form in {expr,rec["copy"],rec["second_copy"]}:
        proc=subprocess.run([worker,"--json"],env=env,input=("quantum:"+form).encode(),capture_output=True,timeout=60,check=True)
        result=json.loads(proc.stdout)
        assert not result["approximate"] and result["copy_text"]==cases[key][1],(key,result["copy_text"])
report=dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],worker_sha256=worker_hash,
            windows_records_sha256=hashlib.sha256(records_path.read_bytes()).hexdigest(),orders=orders,
            printed_basis_map=mapping,cases={k:dict(input=expr,expected=expected) for k,(expr,expected) in cases.items()})
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
print(len(records),"Windows inputs;",len(orders),"minimal orders;",len(mapping),"printed basis transitions")
