"""Check shared Shor bounds at all pairs of five values through Windows output."""
import argparse
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
parser.add_argument("--package",type=Path)
parser.add_argument("--report",type=Path)
args = parser.parse_args()
directory = args.directory
previous = json.loads(Path(__file__).with_name("ibm029-shared-bounds.json").read_bytes())
inputs = [[row["id"],row["literal"],"0"] for row in previous["bounds"]]
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

worker = args.package.resolve()/"quantum-worker.exe"
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
suite = json.loads((directory/"result.json").read_bytes())
raw = (directory/"records.json").read_bytes()
records = json.loads(raw)
assert json.loads((directory/"inputs.json").read_bytes()) == inputs
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(inputs)
results = []
for row,r in zip(previous["bounds"],records):
    assert r["id"] == row["id"] and r["restored_same"] and r["label"] == r["reentry_label"] == "EXACT RESULT"
    variables = ("b","c") if row["id"].endswith("M362") else ("s","j")
    values = row["values_per_operand"]
    checks = 0
    for x,y in product(values,repeat=2):
        for form in ("display","copy","second_copy"):
            expr = f"""quantum:replace(replace(({r[form]}),"{variables[0]}",{x}),"{variables[1]}",{y})"""
            run = subprocess.run([worker,"--json"],input=expr.encode(),env=env,capture_output=True,check=True,timeout=30)
            assert json.loads(run.stdout)["copy_text"] == str(int(min(Fraction(x),Fraction(y))>=2)), (form,x,y)
            checks += 1
    results.append(dict(id=row["id"],display=r["display"],copy=r["copy"],second_copy=r["second_copy"],
                        operand_values=values,substitutions=checks))

report = dict(source_sha256=previous["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
              application_sha256=sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest(),
              records_sha256=sha256(raw).hexdigest(),suite=suite,bounds=results)
args.report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
