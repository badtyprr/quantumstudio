"""Verify each original Grover probability table through Windows save, reopen and Copy."""
import argparse
from fractions import Fraction
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
source = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
reference = json.loads(Path(__file__).with_name("ibm034-tables.json").read_bytes())
assert source["source_sha256"] == reference["source_sha256"]
rows = {r["id"]:r for r in source["rows"]}
inputs = [[t["source_id"],rows[t["source_id"]]["literal"],"0"] for t in reference["tables"]]
directory = args.directory
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
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(inputs) == len(records) == 3
results = []
for table,r,(_,literal,_),heading in zip(reference["tables"],records,inputs,["p(N,1)","Success probability","p(N,4)"]):
    assert r["id"] == table["source_id"] and r["restored_same"] and r["label"] == r["reentry_label"] == "EXACT RESULT"
    session = json.loads((directory/(r["id"]+".qsession")).read_text(encoding="utf-8-sig"))
    assert session["Expression"] == literal and session["Mode"] == 0
    for expression in [literal,r["display"],r["copy"],r["second_copy"]]:
        p = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),env=env,
                           capture_output=True,check=True,timeout=30)
        matrix = json.loads(p.stdout)
        assert not matrix["approximate"] and matrix["rows"] == len(table["rows"])+1 and matrix["columns"] == 2
        assert matrix["cells"][0] == ["'N'",'"'+heading+'"']
        for actual,expected in zip(matrix["cells"][1:],table["rows"]):
            assert int(actual[0]) == expected["size"]
            assert Fraction(actual[1].replace(" ∕ ","/")) == Fraction(expected["printed"])
    results.append(dict(id=r["id"],columns=["N",heading],numeric_rows=len(table["rows"]),forms_checked=4))
report = dict(source_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
              application_sha256=sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest(),
              suite=suite,records_sha256=sha256(raw).hexdigest(),tables=results)
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
