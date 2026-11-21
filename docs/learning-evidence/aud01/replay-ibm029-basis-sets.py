"""Verify brace-delimited bases, register encoding and the Shor diagnostic inventory."""
import argparse
from hashlib import sha256
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
cases={f"M{i}":rows[i-1]["literal"] for i in (67,70)}
cases.update(binary_basis=r"$\{\vert 00\rangle,\ldots,\vert 11\rangle\}$",
             large_basis="basisset(128)",subset="qset(vector(basis(1,3),basis(0,3)))")
for x in range(21):
    cases[f"M141-{x}"]=f"|{x:05b}>"
inputs=[[k,v,"0"] for k,v in cases.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
current=json.loads((directory/"ibm029-inventory.json").read_bytes())
assert current["source_sha256"]==base["source_sha256"] and current["worker_sha256"]==sha256(worker.read_bytes()).hexdigest()
assert len(current["rows"])==len(rows)==438
old_diagnostics={r["id"] for r in rows if r["status"]=="diagnostic"}
# The explicit congruence was fixed after the historical full inventory.
prior=json.loads((here/"ibm029-congruences.json").read_bytes())
for change in prior["status_changes"]:
    assert change["before"]=="diagnostic" and change["after"]=="exact"
    old_diagnostics.remove(change["id"])
assert len(old_diagnostics)==26
remaining={r["id"] for r in current["rows"] if r["status"]=="diagnostic"}
assert old_diagnostics-remaining=={rows[i-1]["id"] for i in (67,70)} and not remaining-old_diagnostics
records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs


def check(expr,expected):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=60,check=True)
    result=json.loads(proc.stdout)
    assert not result["approximate"] and result["copy_text"]==str(expected),(expr[:140],result["copy_text"][:140])


for (key,expr,_),rec in zip(inputs,records):
    assert rec["id"]==key and rec["restored_same"] and rec["label"]==rec["reentry_label"]=="EXACT RESULT"
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    text=rec["copy"]
    assert text==rec["second_copy"],key
    if key.startswith("M141-"):
        x=int(key[5:])
        check(f"({text})=basis({x},32)",1)
    elif key=="M70":
        for n in (1,3,15,21,128):
            bound=f'replace(({text}),"N",{n})'
            check(f"cardinality({bound})",n)
            check(f"basis({n-1},{n}) ∈ {bound}",1)
            check(f"basis(0,{n+1}) ∈ {bound}",0)
    elif key=="subset":
        check(f"cardinality({text})",2)
        check(f"basis(2,3) ∈ {text}",0)
    else:
        n={"M67":15,"binary_basis":4,"large_basis":128}[key]
        assert text==f"basisset({n})",key
        check(f"cardinality({text})",n)
        for x in (range(n) if n<=15 else (0,n//2,n-1)):
            check(f"basis({x},{n}) ∈ {text}",1)
        check(f"(basis(0,{n})+basis(1,{n}))/sqrt(2) ∈ {text}",0)

# Each open diagnostic has an identified finite check. The approximation sign
# has no unique truth condition until a measurement or error bound is supplied.
coverage={
    "ibm029-tables.json":[22,37,45,68],
    "ibm029-congruences.json":[51,52],
    "ibm029-modular-registers.json":[61,144,152,153,157,162,424,427],
    "ibm029-eigenstates.json":[92,98,107],
    "ibm029-basis-sets.json":[141],
    "ibm029-controlled-powers.json":[180,357],
    "ibm029-denominators.json":[266],
    "ibm029-factor-proof.json":[362,374,425],
}
indexed=[rows[i-1]["id"] for numbers in coverage.values() for i in numbers]
assert set(indexed)==remaining and len(indexed)==len(remaining)
for file in coverage:
    if file!=args.report.name:
        assert json.loads((here/file).read_bytes())["notebook_sha256"]==base["source_sha256"]

report=dict(source=base["source"],notebook_sha256=base["source_sha256"],revision=current["revision"],
            worker_sha256=current["worker_sha256"],windows_records_sha256=sha256(records_path.read_bytes()).hexdigest(),
            status_counts=current["summary"],resolved=sorted(old_diagnostics-remaining),windows_inputs=inputs,
            remaining_diagnostics=[dict(id=rows[i-1]["id"],message=current["rows"][i-1]["message"],finite_example=file)
                                   for file,numbers in coverage.items() for i in numbers])
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
print(current["summary"],len(records),"Windows round trips;",len(remaining),"open diagnostics indexed")
