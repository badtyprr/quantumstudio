"""Replay the complete pinned Shor lesson in the default Windows notation mode."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--package", type=Path)
parser.add_argument("--report", type=Path)
parser.add_argument("--inventory", type=Path, default=Path(__file__).with_name("ibm029-inventory.json"))
args = parser.parse_args()
inventory = json.loads(args.inventory.read_bytes())
rows = inventory["rows"]
# The shared Windows runner has a lesson-specific matrix declaration for
# IBM-028 M123. These keys identify the unmodified, context-free Shor inputs.
inputs = [[r["id"]+"-original",r["literal"],"0"] for r in rows]
directory = args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs,ensure_ascii=False).encode())
    raise SystemExit()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert args.package and digest(args.package/"quantum-worker.exe") == inventory["worker_sha256"]
suite = json.loads((directory/"result.json").read_bytes())
records = json.loads((directory/"records.json").read_bytes())
assert json.loads((directory/"inputs.json").read_bytes()) == inputs
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(rows) == 438
counts = Counter()
diagnostics,changes,failures = [],[],[]
for (key,expression,_),source,gui in zip(inputs,rows,records):
    assert gui["id"] == key
    number = source["id"]
    if source["status"] == "diagnostic":
        assert gui["label"] == "CHECK YOUR EXPRESSION", number
        diagnostics.append(dict(id=number,message=gui["display"]))
        counts["source_diagnostic"] += 1
        continue
    assert gui["label"] == "EXACT RESULT", number
    counts["source_exact"] += 1
    session = json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert session["Expression"] == expression and session["Mode"] == 0 and not session["Matrices"]
    if gui["restored_same"]:
        counts["restored_identically"] += 1
    else:
        failures.append(dict(id=number,stage="restore",first=gui["copy"],restored=gui["restored_copy"]))
    if gui["reentry_label"] != "EXACT RESULT":
        failures.append(dict(id=number,stage="reentry",copy=gui["copy"],message=gui.get("reentry_diagnostic")))
    else:
        counts["exact_after_reentry"] += 1
        if gui["copy"] == gui["second_copy"]:
            counts["stable_copy_text"] += 1
        else:
            changes.append(dict(id=number,first=gui["copy"],second=gui["second_copy"]))
report = dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],
              worker_sha256=inventory["worker_sha256"],application_sha256=digest(args.package/"QuantumStudio.exe"),
              records_sha256=digest(directory/"records.json"),suite=suite,counts=counts,
              diagnostics=diagnostics,changed_copy=changes,failures=failures)
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
print(dict(counts), len(changes),"changed Copy strings;",len(failures),"restore or re-entry failures")
if failures:
    raise SystemExit(1)
