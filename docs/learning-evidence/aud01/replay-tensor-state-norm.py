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
parser.add_argument("--report", type=Path)
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

clipboard_checks(worker,args.windows,args.report,cases,19,dict(source_sha256=sources))
