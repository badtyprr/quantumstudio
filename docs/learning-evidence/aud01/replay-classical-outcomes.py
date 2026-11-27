"""Verify classical outcome order, bit widths, and labelled probabilities."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report", type=Path)
reports.add_argument("--session-report", type=Path, help="Verify the Windows --reenter-text run")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
cases = {}
sources = {}

def evaluate(expression):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),
                            env=env,capture_output=True,timeout=30,check=True)
    value = json.loads(result.stdout)
    assert not value["approximate"]
    return value

def check(name,expression,expected):
    data = evaluate(expression)
    assert data["copy_text"]==expected and evaluate(expected)==data,name
    cases[name] = expression,expected
    return data

pairs = "qtuple(vector("+",".join(f"qtuple(vector({a},{b}))" for a in (1,2,3) for b in (0,1))+"))"
words = "qtuple(vector("+",".join(f"qbitlabel({i},2)" for i in range(4))+"))"
column = "matrix(4,1,[1 ∕ 2,0,0,1 ∕ 2])"
for lesson,numbers in (("041",((49,"qbitstrings(10)"),(74,pairs),(77,words),(82,column))),("042",((221,pairs),))):
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    sources[lesson] = inventory["source_sha256"]
    for number,expected in numbers:
        row = inventory["rows"][number-1]
        data = check(row["id"],row["literal"],expected)
        if number==49:
            labels = re.findall(r"qbitlabel\((\d+), (\d+)\)",data["text"])
            assert labels==[(str(i),"10") for i in range(1024)]
        elif number==82:
            swapped = row["literal"].replace("state 00","state TEMP").replace("state 01","state 00").replace("state TEMP","state 01")
            check("swapped-labels",swapped,"matrix(4,1,[0,1 ∕ 2,0,1 ∕ 2])")
            duplicate = swapped.replace("state 00","state 01")
            failure = subprocess.run([worker,"--json"],input=("quantum:"+duplicate).encode(),env=env,capture_output=True,timeout=30)
            assert failure.returncode and b"exactly once" in failure.stderr

check("repeated-words","$001, 111, 001$","qtuple(vector(qbitlabel(1,3),qbitlabel(7,3),qbitlabel(1,3)))")
check("reversed-pairs",r"$(3,1),\;(1,0),\;(3,1)$","qtuple(vector(qtuple(vector(3,1)),qtuple(vector(1,0)),qtuple(vector(3,1))))")
details = dict(source_sha256=sources,binary_labels_checked=1024)
if args.session_report:
    result = json.loads((args.windows/"result.json").read_text("utf-8-sig"))
    records = json.loads((args.windows/"records.json").read_text("utf-8-sig"))
    inputs = json.loads((args.windows/"inputs.json").read_bytes())
    assert inputs==[[key,expr,"0"] for key,(expr,_) in cases.items()]
    assert result["passed"] and result["sessionsOnly"] and result["calls"]==len(records)==len(cases)==8
    for (key,(expr,expected)),record in zip(cases.items(),records):
        session = json.loads((args.windows/(key+".qsession")).read_text("utf-8-sig"))
        assert session["Expression"]==expr and session["Mode"]==0
        assert record["id"]==key and record["restored_same"]
        assert record["label"]==record["reentry_label"]=="EXACT RESULT"
        assert record["copy_text"]==record["reentry_text"]==expected
    report = dict(details,worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                  windows_sessions=len(records),windows_checks=result["checks"],clipboard_verified=False)
    args.session_report.write_text(json.dumps(report,indent=2)+"\n","utf8")
else:
    clipboard_checks(worker,args.windows,args.report,cases,8,details)
