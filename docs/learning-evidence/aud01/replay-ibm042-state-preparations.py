"""Check the three source states and both normalized post-measurement states."""
import argparse
import hashlib
import itertools
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
inventory = json.loads(Path(__file__).with_name("ibm042-inventory.json").read_bytes())
cases = {}

def evaluate(expr):
    answer = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(),
                            capture_output=True, timeout=30, check=True, env=env)
    return json.loads(answer.stdout)["copy_text"]

def check(name, expr, expected):
    assert evaluate(expr) == expected, name
    cases[name] = expr, expected

states = inventory["rows"][7]
copied = evaluate(states["literal"])
assert copied.startswith(r"\begin{gathered}") and copied.endswith(r"\end{gathered}")
vectors = copied.removeprefix(r"\begin{gathered}").removesuffix(r"\end{gathered}").split(r"\\")
assert len(vectors) == 3 and evaluate(copied) == copied
cases[states["id"]] = states["literal"], copied
for i, (state, expected) in enumerate(zip(vectors, [
        "[1/sqrt(2);-1/sqrt(6);i/sqrt(6);1/sqrt(6)]", "[3/5;0;0;-4/5]", "[0;1;0;0]"])):
    check(f"vector-{i}",f"norm(({state})-({expected}))","0")
    check(f"norm-{i}",f"norm({state})","1")

# Project the original four amplitudes on each zero outcome. Checking the
# whole conditional vector detects an incorrect phase or register order.
for number, diagonal in [(148, (1,1,0,0)), (160, (1,0,1,0))]:
    row = inventory["rows"][number-1]
    check(row["id"], row["literal"], "1")
    left, right = row["literal"].strip("$ \r\n;").split("=")
    conditional = evaluate(right)
    entries = [str(diagonal[r] if r==c else 0) for r in range(4) for c in range(4)]
    projected = "matrix(4,4,["+",".join(entries)+"])*("+vectors[0]+")"
    check(f"probability-{number}",f"norm({projected})^2","2 ∕ 3")
    check(f"conditional-{number}",f"norm(({projected})/sqrt(2/3)-({conditional}))","0")
    check(f"wrong-phase-{number}","$$"+left+"= -("+right+");$$","0")
    check(f"wrong-normalization-{number}","$$"+left+"= 2*("+right+");$$","0")
classical = json.loads(Path(__file__).with_name("ibm041-inventory.json").read_bytes())
joint = "[1/2;0;1/12;1/12;1/6;1/6]"
for number in (252,258,264,268):
    row = classical["rows"][number-1]
    source = row["literal"]
    if number==258:
        # X is the first factor. Each parenthesized Y vector uses its own axis.
        assert source.count(r"\biggl(")==source.count(r"\biggr)")==2
        source = source.replace(r"\biggl(","basislabels([[1,2,3]],(").replace(r"\biggr)","))")
    axes = {252:"[0,1],[1,2,3]",258:"[0,1]",264:"[1,2,3]",268:"[1,2,3]"}[number]
    scoped = f"basislabels({axes}):"+source
    copied = evaluate(scoped)
    check(row["id"],scoped,copied)
    if number in (252,258):
        check(f"joint-{number}",f'replace(({copied}),"pi",{joint})',"1")
    else:
        assert copied=="1"

row = inventory["rows"][76]
qutrits = "basislabels([0,1,2],[0,1,2],[0,1,2]):"+row["literal"]
state = evaluate(qutrits)
cases[row["id"]] = qutrits,state
entries = [0]*27
for a,b,c in itertools.permutations(range(3)):
    entries[9*a+3*b+c] = (-1)**((a>b)+(a>c)+(b>c))
expected = "["+";".join(map(str,entries))+"]/sqrt(6)"
check("qutrit-permutation-signs",f"norm(({state})-({expected}))","0")

matrix_literal = next(r["literal"] for r in inventory["rows"][221:228] if r"\begin{pmatrix}" in r["literal"])
matrix = evaluate("$$"+matrix_literal.split("=",1)[1])
row = inventory["rows"][228]
scoped = 'matrixcontext("U",(6),(6),"general"):basislabels([1,2,3],[0,1]):'+row["literal"]
relation = evaluate(scoped)
cases[row["id"]] = scoped,relation
check("declared-unitary-column",f'replace(({relation}),"U",{matrix})',"1")
check("wrong-unitary-column",f'replace(({relation}),"U",qidentity(6))',"0")
shift = inventory["rows"][234]
inverse = inventory["rows"][236]
assert classical["rows"][299]["literal"] == shift["literal"]
def shift_matrix(size, step):
    cells = (str(int(row==(column+step)%size)) for row in range(size) for column in range(size))
    return f"matrix({size},{size},["+",".join(cells)+"])"

check(shift["id"],shift["literal"],shift_matrix(8,1))
check(inverse["id"],inverse["literal"],"1")
for size in (3,5,8):
    def resize(expr):
        return expr.replace("^{7}",f"^{{{size-1}}}").replace(r"\bmod 8",rf"\bmod {size}")
    for step in (-2,-1,1,2):
        expr = resize(shift["literal"]).replace("k+1",f"k{step:+d}")
        check(f"shift-{size}-{step}",expr,shift_matrix(size,step))
    wrong = resize(inverse["literal"]).replace("k-1","k+1")
    check(f"wrong-inverse-{size}",wrong,"0")
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,45,
                 dict(source_sha256=inventory["source_sha256"],classical_source_sha256=classical["source_sha256"],
                 scoped_formulas={"IBM-041":[252,258,264,268],"IBM-042":[77,229]},
                 qutrit_coordinates_checked=27,ordered_states=len(vectors),
                 application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()),
                 sessions_only=bool(args.session_report))
