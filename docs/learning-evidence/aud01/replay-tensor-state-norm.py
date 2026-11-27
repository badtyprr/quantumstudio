"""Verify descending state and operator factors in the multiple-system lessons."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report", type=Path)
reports.add_argument("--session-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
cases = {}
sources = {}

def evaluate(expression):
    proc = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(),
                          capture_output=True, check=True, timeout=30, env=env)
    result = json.loads(proc.stdout)
    assert not result["approximate"]
    return result["copy_text"]

def source(lesson, number):
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    sources[lesson] = inventory["source_sha256"]
    row = inventory["rows"][number-1]
    copied = evaluate(row["literal"])
    assert evaluate(copied) == copied
    cases[row["id"]] = row["literal"], copied
    return copied

def check(name, expression, expected):
    actual = evaluate(expression)
    assert actual == expected, (name, actual, expected)
    cases[name] = expression, expected

def bind(expression, *pairs):
    for name, value in pairs:
        symbol = name if name == "n" else f'"{name}"'
        expression = f'replace(({expression}),{symbol},{value})'
    return expression

series = source("042",40)
state = bind(series, ("ψ_0","[1;0]"), ("ψ_1","[0;i]"), ("n","2"))
check("descending-phase",state,"matrix(4,1,[0,0,i,0])")
check("one-state",bind(series, ("ψ_0","[1;2;3]"), ("n","1")),"matrix(3,1,[1,2,3])")

for number in (166,169):
    definition = source("041",number)
    factors = (("φ_0","[1;0]"), ("φ_1","[0;i]"), ("n","2"))
    check(f"true-{number}",bind(definition, *factors, ("ψ","[0;0;i;0]")),"1")
    check(f"reversed-{number}",bind(definition, *factors, ("ψ","[0;i;0;0]")),"0")

for lesson, number, family in (("041",341,"M"), ("042",241,"U"), ("042",253,"U")):
    operators = source(lesson,number)
    check(f"two-operators-{number}",bind(operators, (family+"_0","[0,1;1,0]"),
          (family+"_1","[1,0;0,-1]"), ("n","2")),
          "matrix(4,4,[0,1,0,0,1,0,0,0,0,0,0,−1,0,0,−1,0])")
norm = source("042",36)
for name, left, right, expected in (("unit","[0;i]","[1;0;0]","1"),
                                    ("scaled","[0;2*i]","[1;0;0]","0"),
                                    ("inverse-scales","[0;2*i]","[1/2;0;0]","1")):
    check(name,bind(norm, ("φ",left), ("ψ",right)),expected)

chain = source("042",42)
for name,high,low,expected in [("inverse","2*i","1/2","1"),("scaled","3*i","2","0"),("zero","0","2","0")]:
    assignments = [("ψ_1",f"[0;{high}]"),("ψ_0",f"[{low};0;0]")]
    check("norm-width-first-"+name,bind(chain,("n","2"),*assignments),expected)
    check("norm-width-last-"+name,bind(chain,*assignments,("n","2")),expected)

inventory = json.loads(Path(__file__).with_name("ibm041-inventory.json").read_bytes())
symbol = inventory["rows"][147]
assert symbol["literal"]==r"$\otimes$"
for number in (149,150,151):
    form = source("041",number)
    check(f"tensor-notation-{number}",bind(form,("φ","[1;i]"),("ψ","[2;3;5]")),
          "matrix(6,1,[2,3,5,2i,3i,5i])")

overlap = [("a_0","[1;0]"),("a_1","[0;i;0]"),("φ_0","[i;0]"),("φ_1","[0;1;0]"),
           ("ψ","[0;0;i;0;0;0]")]
elements = [("a_0","[0;i]"),("a_1","[0;1;0]"),("b_0","[0;1;0]"),("b_1","[1;0]"),
            ("M_0","[1,0,3;0,2+i,0]"),("M_1","[0,1;3,0;0,1]")]
for number,assignments,expected in [(170,overlap,"1"),(342,elements,"3 − 6i")]:
    identity = source("041",number)
    row = inventory["rows"][number-1]
    right = evaluate("$$"+row["literal"].split("=",1)[1])
    check(f"factor-product-{number}",bind(right,*assignments,("n","2")),expected)
    check(f"width-first-{number}",bind(identity,("n","2"),*assignments),"1")
    check(f"width-last-{number}",bind(identity,*assignments,("n","2")),"1")
check("independent-joint-state",bind(source("041",170),*overlap[:-1],("ψ","[0;0;-i;0;0;0]"),("n","2")),"0")
altered = inventory["rows"][341]["literal"].split("=")
changed = evaluate(altered[0]+"="+altered[1].replace("M_","N_"))
check("independent-operator-family",bind(changed,*elements,("N_0",elements[-2][1]),
      ("N_1","[0,1;-3,0;0,1]"),("n","2")),"0")
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,42,
                 dict(source_sha256=sources,operator_symbol_occurrence=symbol["id"]),
                 sessions_only=bool(args.session_report))
