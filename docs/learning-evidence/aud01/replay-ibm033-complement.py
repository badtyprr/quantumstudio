"""Check both Boolean inputs to the Grover complement identity after Windows Copy."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--package", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
source = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())
row = source["rows"][35]
assert row["id"].endswith("M036")
inputs = [[row["id"],row["literal"],"0"]]
directory = args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

suite = json.loads((directory/"result.json").read_bytes())
records_raw = (directory/"records.json").read_bytes()
record, = json.loads(records_raw)
assert suite["calls"] == 1 and suite["passed"] and suite["clipboardRestored"]
assert json.loads((directory/"inputs.json").read_bytes()) == inputs
assert record["id"] == row["id"] and record["label"] == record["reentry_label"] == "EXACT RESULT" and record["restored_same"]
session = json.loads((directory/(row["id"]+".qsession")).read_text(encoding="utf-8-sig"))
assert session["Expression"] == row["literal"] and session["Mode"] == 0
worker = args.package.resolve()/"quantum-worker.exe"
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
checks = []
for f in (0,1):
    for g in (0,1):
        for key in ("display","copy","second_copy"):
            expr = f"quantum:replace(replace(({record[key]}),f(x),{f}),g(x),{g})"
            p = subprocess.run([worker,"--json"],input=expr.encode(),env=env,capture_output=True,timeout=30,check=True)
            result = json.loads(p.stdout)
            assert result["copy_text"] == str(int(g == 1-f)) and not result["approximate"], (key,f,g,result)
        checks.append(dict(f=f,g=g,equality=int(g == 1-f)))
report = dict(id=row["id"],source_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
              application_sha256=sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest(),
              records_sha256=sha256(records_raw).hexdigest(),suite=suite,truth_table=checks,
              forms={key:record[key] for key in ("display","copy","second_copy")})
args.report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
