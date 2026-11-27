"""Verify classical outcome order, bit widths, and labelled probabilities."""
import argparse
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
# M080 uses a pair of decimal digits. The four rows below use binary registers.
for number, digits in [(50,"0000000110"),(104,"00"),(179,"00"),(185,"11")]:
    row = inventory["rows"][number-1]
    assert row["literal"] == "$"+digits+"$"
    word = check(row["id"], "bitword:"+row["literal"],
                 f"qbitlabel({int(digits,2)},{len(digits)})")["copy_text"]
    for wire, bit in enumerate(reversed(digits)):
        check(f"register-{number}-{wire}",f"mod(floor(qbitvalue({word})/2^{wire}),2)",bit)
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
row = inventory["rows"][35]
check(row["id"],row["literal"],"1")
mixed = evaluate(row["literal"].replace(r"\in\Sigma",r"\in\Gamma"))["copy_text"]
for last,answer in [(7,"1"),(8,"0")]:
    axes = [("Σ_1",3),("Σ_2",7),("Γ_1",3),("Γ_2",last)]
    given = [(key,f"qset(vector({value}))") for key,value in axes]
    check(f"independent-domains-{last}",assign(mixed,given+[("n","2")]),answer)
for number,indices in [(45,range(10)),(48,reversed(range(10)))]:
    row = inventory["rows"][number-1]
    names = ",".join(f'"Σ_{i}"' for i in indices)
    chain = f"qequalchain(vector({names},qset(vector(0,1))))"
    check(row["id"],row["literal"],chain)
    for middle,answer in [(1,"1"),(2,"0")]:
        given = [(f"Σ_{i}",f"qset(vector(0,{middle if i==4 else 1}))") for i in range(10)]
        check(f"middle-alphabet-{number}-{middle}",assign(chain,given),answer)
details = dict(source_sha256=sources,binary_labels_checked=1024)
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,57,details,
                 sessions_only=bool(args.session_report))
