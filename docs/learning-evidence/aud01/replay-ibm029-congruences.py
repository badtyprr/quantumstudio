"""Replay explicit Shor congruences against integer modular arithmetic."""
import argparse
from hashlib import sha256
from itertools import permutations
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
here=Path(__file__).parent
base=json.loads((here/"ibm029-inventory.json").read_bytes())
rows=base["rows"]
tests={
    "M018":(rows[17]["literal"],1),
    "M019":(rows[18]["literal"],0),
    "sum-difference":(r"$3+5\equiv5-4\pmod{7}$",1),
    "negative":(r"$-2\equiv5\;(\mathrm{mod}\;7)$",1),
    "negative-false":(r"$-2\equiv4\pmod{7}$",0),
    "grouped":(r"$(3\equiv1\pmod{2})+(4\equiv1\pmod{2})$",1),
    "both-sides":(r"$2^8\equiv3^4\pmod{7}$",1),
    "modulus-expression":(r"$19\equiv4\pmod{3+2}$",1),
    "M051-M052":("$"+rows[50]["literal"][1:-1]+" "+rows[51]["literal"][1:-1]+"$",None),
}
inputs=[[key,expr,"0"] for key,(expr,_) in tests.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
candidate=json.loads((directory/"ibm029-inventory.json").read_bytes())
assert candidate["source_sha256"]==base["source_sha256"] and candidate["worker_sha256"]==sha256(worker.read_bytes()).hexdigest()
assert len(candidate["rows"])==len(rows)==438
changes=[]
for old,new in zip(rows,candidate["rows"]):
    assert (old["id"],old["literal"])==(new["id"],new["literal"])
    if old["status"]!=new["status"]:
        changes.append(dict(id=old["id"],before=old["status"],after=new["status"],value=new.get("copy")))
assert changes==[dict(id=rows[17]["id"],before="diagnostic",after="exact",value="1")],changes

def check(expr,expected):
    proc=subprocess.run([worker,"--json"],env=env,input=("quantum:"+expr).encode(),capture_output=True,timeout=45,check=True)
    value=json.loads(proc.stdout)
    assert not value["approximate"] and value["copy_text"]==str(expected),(expr,expected,value["copy_text"])

records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
witnesses=[]
for (key,expr,_),gui in zip(inputs,records):
    assert gui["id"]==key and gui["restored_same"] and gui["label"]==gui["reentry_label"]=="EXACT RESULT"
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    forms={gui[field] for field in ("display","copy","second_copy")}
    if tests[key][1] is not None:
        for text in forms|{expr}:
            check(text,tests[key][1])
        continue
    for a,r,n in [(2,6,21),(2,5,21),(-2,3,9),(0,1,7),(7,0,5),(3,2,1),(3,100003,7)]:
        expected=int(pow(a,r,n)==1%n)
        for bindings in permutations((("a",a),("r",r),("N",n))):
            for text in forms:
                for name,val in bindings:
                    text=f'replace(({text}),"{name}",({val}))'
                check(text,expected)
        witnesses.append(dict(a=a,r=r,N=n,expected=expected))
report=dict(source=base["source"],notebook_sha256=base["source_sha256"],revision=candidate["revision"],
            worker_sha256=candidate["worker_sha256"],windows_records_sha256=sha256(records_path.read_bytes()).hexdigest(),
            inventory_summary=candidate["summary"],status_changes=changes,windows_inputs=inputs,joined_span_witnesses=witnesses,
            binding_orders=6)
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
print(candidate["summary"],len(records),"Windows inputs;",len(witnesses)*6,"symbolic binding cases")
