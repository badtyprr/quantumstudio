"""Check the three source states and both normalized post-measurement states."""
import argparse
import hashlib
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
clipboard_checks(worker,args.windows,args.report,cases,17,dict(source_sha256=inventory["source_sha256"],
                 source_occurrences=3, ordered_states=len(vectors),
                 application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()))
