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
inventory = json.loads(Path(__file__).with_name("ibm041-inventory.json").read_bytes())
pair = inventory["rows"][154]
check(pair["id"],pair["literal"],"1")

def bind(expression):
    for name,value in (("a","[0;i]"),("b","[1;0]"),("c","[0;1;0]"),("d","[0;0;1]"),
                       ("M","[0,1;2,0]"),("N","[0,0,0;0,0,1+i;1,0,0]")):
        expression = f'replace(({expression}),"{name}",{value})'
    return expression

state = evaluate(r"$\vert(a,c)\rangle$")["copy_text"]
check("rectangular-basis",bind(state),"matrix(6,1,[0,0,0,0,i,0])")
row = inventory["rows"][326]
element = evaluate(row["literal"])["copy_text"]
check(row["id"],row["literal"],element)
joint = evaluate(r"$\langle (a,c) \vert M \otimes N \vert (b,d)\rangle$")["copy_text"]
assert element.startswith("qcompare("+joint+",")
check("matrix-element",bind(joint),"2 − 2i")
check("factorization",bind(element),"1")
wrong = row["literal"].replace(r"\langle a \vert M \vert b\rangle",r"\langle b \vert M \vert a\rangle")
assert wrong!=row["literal"]
check("reversed-first-element",bind(evaluate(wrong)["copy_text"]),"0")
def assign(expression,assignments):
    for name,value in assignments:
        key = "n" if name=="n" else f'"{name}"'
        expression = f"replace(({expression}),{key},{value})"
    return expression

domains = [("Σ_0","qset(vector(4,7))"),("Σ_1","qset(vector(2,3))")]
labels = [("a_0","7"),("a_1","2"),("b_0","4"),("b_1","3")]
for number in (171,343,328,329):
    row = inventory["rows"][number-1]
    declaration = evaluate(row["literal"])["copy_text"]
    check(row["id"],row["literal"],declaration)
    if number in (328,329):
        left,right,alphabet = ("a","b","Σ") if number==328 else ("c","d","Γ")
        given = [(left,"5"),(alphabet,"qset(vector(2,5))")]
        check(f"allowed-{number}",assign(declaration,given+[(right,"2")]),"1")
        check(f"excluded-{number}",assign(declaration,given+[(right,"3")]),"0")
    else:
        check(f"width-last-{number}",assign(declaration,domains+labels+[("n","2")]),"1")
        check(f"width-first-{number}",assign(declaration,[("n","2")]+labels+domains),"1")
        changed = [(key,"7" if key==("b_1" if number==343 else "a_1") else value) for key,value in labels]
        check(f"wrong-axis-{number}",assign(declaration,domains+changed+[("n","2")]),"0")
details = dict(source_sha256=sources,binary_labels_checked=1024)
if args.session_report:
    result = json.loads((args.windows/"result.json").read_text("utf-8-sig"))
    records = json.loads((args.windows/"records.json").read_text("utf-8-sig"))
    inputs = json.loads((args.windows/"inputs.json").read_bytes())
    assert inputs==[[key,expr,"0"] for key,(expr,_) in cases.items()]
    assert result["passed"] and result["sessionsOnly"] and result["calls"]==len(records)==len(cases)==28
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
    clipboard_checks(worker,args.windows,args.report,cases,28,details)
