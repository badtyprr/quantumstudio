"""Replay the stabilizer and phase-gate meanings of S in the IBM-084 lesson."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--windows-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows = json.loads(Path(__file__).with_name("ibm084-inventory.json").read_bytes())["rows"]
context = 'matrixcontext("S",(4),(4),"hermitian"):'
error_context = 'matrixcontext("E",(4),(4),"general"):'
inputs = []
expected = {}
def evaluate(key, expr):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),
                            capture_output=True,env=env,check=True)
    copied = json.loads(result.stdout)["copy_text"]
    inputs.append([key,expr,"0"])
    expected[key] = copied
    return copied

symbol = """operatorparam('S',4,"hermitian")"""
for n in (4,5,6,149,151,153,156):
    identifier = rows[n-1]["id"]
    canonical = evaluate(identifier,context+(error_context if n==153 else "")+rows[n-1]["literal"])
    assert symbol in canonical
    if n in (5,149,153):
        errors = ("X","Z") if n==153 else ("I",)
        for state in ("00","01","11"):
            for error in errors:
                bound = canonical.replace(symbol,"qtensor(Z,Z)").replace("matrixparam('E',4,4)",f"qtensor({error},I)")
                bound = bound.replace("qnamedket('ψ')",f"|{state}>").replace("qketstate('ψ')",f"|{state}>")
                truth = state in ("00","11") and (n!=153 or error=="X")
                assert evaluate(f"{identifier}-{state}-{error}",bound)==str(int(truth))
# Later in this same notebook S and its adjoint denote actual phase gates.
for n,phase in ((360,"-i"),(362,"i")):
    expression = rows[n-1]["literal"]
    canonical = evaluate(rows[n-1]["id"],expression)
    assert evaluate(f"phase-{n}",f"qcompare({canonical},matrix(2,2,[1,0,0,{phase}]),4)")=="1"

args.directory.mkdir(parents=True,exist_ok=True)
if args.windows_report:
    records_file = args.directory/"records.json"
    records = json.loads(records_file.read_bytes())
    assert len(records)==len(inputs) and {r["id"] for r in records}==set(expected)
    for row in records:
        assert row["label"]==row["reentry_label"]=="EXACT RESULT" and row["restored_same"],row["id"]
        assert row["copy_text"]==row["reentry_text"]==expected[row["id"]],row["id"]
    report = dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                  records_sha256=hashlib.sha256(records_file.read_bytes()).hexdigest(),
                  declarations={"S":"four-dimensional Hermitian operator","E":"four-dimensional general matrix"},
                  verified=expected)
    args.windows_report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
else:
    (args.directory/"inputs.json").write_bytes(json.dumps(inputs,ensure_ascii=False).encode())
print(f"Verified {len(inputs)} declared stabilizer, substitution and phase-gate examples.")
