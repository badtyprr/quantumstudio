"""Compare IBM-041's joint, marginal and conditional probabilities with exact counts."""
import argparse
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
parser.add_argument("--report", type=Path)
parser.add_argument("--session-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))

def evaluate(expr):
    result = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(),
                            timeout=30, capture_output=True, env=env, check=True)
    return json.loads(result.stdout)["copy_text"]

def bind(formula, bindings):
    for name, value in bindings:
        formula = f'replace(({formula}),"{name}",({value}))'
    return formula

inventory = json.loads(Path(__file__).with_name("ibm041-inventory.json").read_bytes())
copies = {}
cases = {}
for number in [60, 87, 116, 200, 217, 218, 219, 220, 221, 222, 275]:
    row = inventory["rows"][number-1]
    copies[number] = evaluate(row["literal"])
    cases[row["id"]] = row["literal"], copies[number]

def check(key, number, values, expected):
    expr = bind(copies[number], values)
    actual = evaluate(expr)
    assert Fraction(actual.replace(" ∕ ", "/")) == expected, (key, actual, expected)
    cases[key] = expr, actual

for number, register, outcome in [(219,"Y","b"), (220,"X","a"), (275,"X",None)]:
    for observed in [0,1]:
        bindings = [(register,observed)]
        if outcome:
            bindings.append((outcome,1))
        check(f"event-{number}-{observed}",number,bindings,observed==1)
        if outcome:
            check(f"event-reversed-bindings-{number}-{observed}",number,bindings[::-1],observed==1)

for label, table in [("independent", [[1,2,3],[2,4,6]]),
                     ("correlated", [[3,0,1],[1,4,1]])]:
    total = sum(map(sum, table))
    matrix = "matrix(2,3,["+",".join(f"{x}/{total}" for row in table for x in row)+"])"
    marginal = [sum(row) for row in table]
    column_counts = list(map(sum, zip(*table)))
    def vector(counts):
        return "["+";".join(f"{x}/{total}" for x in counts)+"]"
    distributions = [("X,Y",matrix), ("X",vector(marginal)), ("Y",vector(column_counts))]
    for a, row in enumerate(table):
        base = distributions + [("a",a)]
        check(f"{label}-marginal-{a}", 200, base+[("Γ","qset(vector(0,1,2))")], 1)
        check(f"{label}-wrong-marginal-{a}", 200, [("X,Y",matrix),("X","[1/2;1/2]"),("a",a),("Γ","qset(vector(0,1,2))")], 0)
        check(f"{label}-single-{a}", 221, base, Fraction(marginal[a],total))
        check(f"{label}-zero-{a}", 222, base, 0)
        for b, value in enumerate(row):
            bindings = base + [("b",b)]
            check(f"{label}-independence-{a}-{b}", 87, bindings, value*total == marginal[a]*column_counts[b])
            check(f"{label}-ratio-{a}-{b}", 217, bindings, 1)
            check(f"{label}-conditional-{a}-{b}", 218, bindings, Fraction(value,marginal[a]))
for joint, q, r, expected in [("[1/2,0;0,1/2]",0,1,1), ("[1/2,0;0,1/2]",1,1,0),
                              ("[0,1/2;1/2,0]",0,1,0)]:
    check(f"factor-{q}-{r}-{expected}-{len(cases)}",116,[("X,Y",joint),("q_0",q),("r_1",r)],expected)

lines = copies[60].removeprefix(r"\begin{gathered}").removesuffix(r"\end{gathered}").split(r"\\")
assert len(lines) == 4
for index, line in enumerate(lines):
    for name, joint, expected in [("diagonal","[1/2,0;0,1/2]","1"),("uniform","[1/4,1/4;1/4,1/4]","0")]:
        expr = bind(line, [("X,Y",joint)])
        assert evaluate(expr) == expected
        cases[f"aligned-{index}-{name}"] = expr, expected
clipboard_checks(worker, args.windows, args.report or args.session_report, cases, 84,
                 dict(source_sha256=inventory["source_sha256"], source_formulas=len(copies),
                      application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()),
                 sessions_only=bool(args.session_report))
