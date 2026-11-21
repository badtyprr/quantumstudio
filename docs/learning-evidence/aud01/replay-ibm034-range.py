"""Replay the Grover search range, including symbolic and invalid bounds."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
parser.add_argument("--package",type=Path)
parser.add_argument("--report",type=Path)
args = parser.parse_args()
directory = args.directory
inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
source = inventory["rows"][131]
assert source["id"].endswith("M132")
inputs = [[source["id"], source["literal"], "0"]]
expected = ["qindexrange(1,'T')"]
for value, result in [("0","qset(vector())"), ("1","qset(vector(1))"), ("4","qset(vector(1,2,3,4))"),
                      ("5/2",None), ("1025",None)]:
    inputs.append(["upper-"+value.replace("/","-"), f'replace(indexrange(1,T),"T",{value})',"0"])
    expected.append(result)
if not args.report:
    directory.mkdir(exist_ok=True,parents=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

suite = json.loads((directory/"result.json").read_bytes())
raw = (directory/"records.json").read_bytes()
records = json.loads(raw)
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(inputs)
assert json.loads((directory/"inputs.json").read_bytes()) == inputs
outcomes = []
for (key,expr,_), r, value in zip(inputs,records,expected):
    assert key == r["id"]
    if value is None:
        diagnostic = "integer endpoints" if key == "upper-5-2" else "1024 entries"
        assert r["label"] == "CHECK YOUR EXPRESSION" and diagnostic in r["display"]
    else:
        assert r["label"] == r["reentry_label"] == "EXACT RESULT" and r["restored_same"]
        assert r["copy"] == r["second_copy"] == value
        session = json.loads((directory/(key+".qsession")).read_text(encoding="utf-8-sig"))
        assert session["Expression"] == expr and session["Mode"] == 0
    outcomes.append(dict(id=key,expression=expr,display=r["display"],copy=r.get("copy")))
report = dict(source_sha256=inventory["source_sha256"],worker_sha256=sha256((args.package/"quantum-worker.exe").read_bytes()).hexdigest(),
              application_sha256=sha256((args.package/"QuantumStudio.exe").read_bytes()).hexdigest(),
              records_sha256=sha256(raw).hexdigest(),suite=suite,outcomes=outcomes)
args.report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
