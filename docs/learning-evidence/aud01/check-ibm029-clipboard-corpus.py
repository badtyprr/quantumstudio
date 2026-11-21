"""Check Shor lesson Clipboard batches against their source, worker output, and stored sessions."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
expected = json.loads((args.directory/"expected.json").read_bytes())
def evaluate(expr, mode="0"):
    prefix = {"0":"", "6":"scalars:", "7":"modpowers:"}[mode]
    p = subprocess.run([worker,"--json"],input=("quantum:"+prefix+expr).encode(),env=env,
                       capture_output=True,timeout=30)
    if p.returncode:
        assert p.returncode == 2 and p.stderr, p.stderr
        return None
    return json.loads(p.stdout)["copy_text"]

sessions = {}
modes = Counter()
for result in sorted(args.directory.glob("*/result.json")):
    d = result.parent
    summary = json.loads(result.read_text("utf-8-sig"))
    records = json.loads((d/"records.json").read_text("utf-8-sig"))
    inputs = json.loads((d/"inputs.json").read_bytes())
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    assert len(records) == summary["calls"] == len(inputs)
    for (key,expr,mode),record in zip(inputs,records):
        assert key == record["id"] and key not in sessions
        session = json.loads((d/(key+".qsession")).read_text("utf-8-sig"))
        assert session["Expression"] == expr and session["Mode"] == int(mode)
        assert record["restored_same"] and record["copy"] == record["second_copy"] == expected[key], key
        sessions[key] = (expr,mode)
        modes[mode] += 1
assert sessions.keys() == expected.keys()
diagnostics = []
for row in inventory["rows"]:
    key = row["id"]
    mode = "7" if key.endswith(("M176","M178")) else "6" if key.endswith(("M362","M363","M369","M374","M425")) else "0"
    value = evaluate(row["literal"],mode)
    if key in sessions:
        assert sessions[key] == (row["literal"],mode) and value == expected[key], key
    else:
        assert value is None, key
        diagnostics.append(key)
row = inventory["rows"][233]
assert row["id"].endswith("M234")
copy = expected[row["id"]]
finite = 0
for m in (1,2,3,6):
    for r in (1,2,3,5):
        for y in range(2**m//r-2,2**m//r+3):
            bound = f'replace(replace(replace(({copy}),"r",{r}),"m",{m}),y,{y})'
            truth = abs(Fraction(y,2**m)-Fraction(1,r)) < Fraction(1,2*r*(r+1))
            assert evaluate(bound) == str(int(truth)), (m,r,y)
            finite += 1
report = dict(source_sha256=inventory["source_sha256"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              source_spans=len(inventory["rows"]),clipboard_sessions=len(sessions),stable_copies=len(sessions),
              mode_counts=dict(modes),diagnostics=diagnostics,M234_exact_rational_checks=finite)
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
