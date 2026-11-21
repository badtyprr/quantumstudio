"""Verify Grover's OR phase operator and its Hadamard conjugate after Windows Copy."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
parser.add_argument("--package",type=Path)
parser.add_argument("--report",type=Path)
parser.add_argument("--worker-only",action="store_true")
args = parser.parse_args()
here = Path(__file__).parent
inputs, hashes = [], {}
for lesson, indices in [(32,(16,17)),(33,(55,))]:
    inventory = json.loads((here/f"ibm{lesson:03}-inventory.json").read_bytes())
    hashes[str(lesson)] = inventory["source_sha256"]
    for index in indices:
        row = inventory["rows"][index-1]
        inputs.append([row["id"],row["literal"],"0"])
directory = args.directory
if not args.report:
    directory.mkdir(exist_ok=True,parents=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

worker = args.package.resolve()/"quantum-worker.exe"
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def calculate(expr):
    r = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,check=True,timeout=30)
    v = json.loads(r.stdout)
    assert not v["approximate"]
    return v["copy_text"]

if args.worker_only:
    records = []
    for key,literal,_ in inputs:
        run = subprocess.run([worker,"--json"],input=("quantum:"+literal).encode(),env=env,capture_output=True,check=True,timeout=30)
        value = json.loads(run.stdout)
        assert not value["approximate"]
        records.append(dict(id=key,display=value["display_text"],copy=value["copy_text"],second_copy=calculate(value["copy_text"])))
    provenance = dict(mode="worker")
else:
    suite = json.loads((directory/"result.json").read_bytes())
    raw = (directory/"records.json").read_bytes()
    records = json.loads(raw)
    assert json.loads((directory/"inputs.json").read_bytes()) == inputs
    assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(inputs)
    provenance = dict(mode="Windows",application_sha256=sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest(),
                      suite=suite,records_sha256=sha256(raw).hexdigest())
results = []
for record,(key,source,_) in zip(records,inputs):
    assert record["id"] == key
    if not args.worker_only:
        assert record["restored_same"] and record["label"] == record["reentry_label"] == "EXACT RESULT"
        saved = json.loads((directory/(key+".qsession")).read_text(encoding="utf-8-sig"))
        assert saved["Expression"] == source and saved["Mode"] == 0
    checks = 0
    for field in ("display","copy","second_copy"):
        expr = record[field]
        for n in (1,2,3):
            size = 2**n
            oracle = "["+";".join(",".join(str((1 if i==0 else -1)*int(i==j)) for j in range(size)) for i in range(size))+"]"
            bound = f'replace(({expr}),"Z_OR",{oracle})'
            if key.endswith("M016"):
                for x in range(size):
                    action = f"replace(replace(replace(({bound}),qketstate(x),basis({x},{size})),x,bitstring({x},{n})),n,{n})"
                    assert calculate(action) == "1", (field,n,x)
                    inverted = action.replace('"Z_OR",'+oracle, '"Z_OR",(-'+oracle+')')
                    assert calculate(inverted) == "0", (field,n,x)
                    checks += 2
            elif key.endswith("M017"):
                assert calculate(bound) == calculate(oracle)
                checks += 1
            else:
                expected = "["+";".join(",".join(str(Fraction(2,size)-int(i==j)) for j in range(size)) for i in range(size))+"]"
                assert calculate(f"replace(({bound}),n,{n})") == calculate(expected), (field,n)
                checks += 1
    results.append(dict(source_id=key,substitutions=checks,copy=record["copy"]))
report = dict(source_sha256=hashes,worker_sha256=sha256(worker.read_bytes()).hexdigest(),
              results=results,**provenance)
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
