"""Check tensor multiplication and adjoint identities on complex matrices."""
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
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),
                          capture_output=True,check=True,timeout=30,env=env)
    result = json.loads(proc.stdout)
    assert not result["approximate"]
    return result["copy_text"]

def bound(expression, families):
    for family in families:
        for index, matrix in enumerate(matrices[family]):
            expression = f'replace(({expression}),"{family}_{index}",{matrix})'
    return f"replace(({expression}),n,2)"

matrices = {"M": ("[0,i;1,0]","[1,0;2,3]"), "N": ("[0,1;0,0]","[1,1;0,1]")}
matrices["U"] = matrices["M"]
for lesson,number,families in (("041",344,"MN"),("042",242,"M"),("042",244,"U")):
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    sources[lesson] = inventory["source_sha256"]
    row = inventory["rows"][number-1]
    literal = row["literal"]
    copied = evaluate(literal)
    assert evaluate(copied) == copied
    cases[row["id"]] = literal,copied
    left,right = literal.strip("$ \r\n.").split("=")
    if number == 344:
        altered = right.replace("M_{n-1} N_{n-1}","N_{n-1} M_{n-1}").replace("M_0 N_0","N_0 M_0")
    else:
        altered = right.replace(r"^{\dagger}","")
    assert altered != right
    for name,expression,expected in (("identity",copied,"1"),("wrong-order-or-adjoint",evaluate("$$"+left+"="+altered+"$$"),"0")):
        concrete = bound(expression,families)
        assert evaluate(concrete) == expected, (number,name)
        cases[f"{number}-{name}"] = concrete,expected

inventory = json.loads(Path(__file__).with_name("ibm041-inventory.json").read_bytes())
for number,families,expected in [
    (346,"N","vector(matrix(2,2,[0,1,0,0]),matrix(2,2,[1,1,0,1]))"),
    (347,"MN","vector(matrix(2,2,[0,0,0,1]),matrix(2,2,[1,1,2,5]))"),
]:
    row = inventory["rows"][number-1]
    copied = evaluate(row["literal"])
    assert evaluate(copied)==copied
    cases[row["id"]] = row["literal"],copied
    concrete = bound(copied,families)
    assert evaluate(concrete)==expected
    cases[f"list-{number}"] = concrete,expected
reverse = bound(evaluate(r"$N_0 M_0,\ldots,N_{n-1} M_{n-1}$"),"MN")
expected = "vector(matrix(2,2,[1,0,0,0]),matrix(2,2,[3,3,2,3]))"
assert evaluate(reverse)==expected
cases["reverse-products"] = reverse,expected
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,14,
                 dict(source_sha256=sources),sessions_only=bool(args.session_report))
