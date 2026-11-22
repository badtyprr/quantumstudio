"""Replay the spectral mixture and both IBM-015 purifications from their pinned notebooks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source_root", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
manifest = json.loads(Path(__file__).with_name("ibm015-purification-sources.json").read_bytes())
formula = {}
for lesson in manifest["lessons"]:
    raw = (args.source_root / lesson["source"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != lesson["source_sha256"]:
        raise ValueError("Use documentation revision " + manifest["source_revision"])
    cells = json.loads(raw)["cells"]
    for number, row in lesson["occurrences"].items():
        source = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        if hashlib.sha256(source.encode()).hexdigest() != row["literal_sha256"]:
            raise ValueError((lesson["lesson"], number))
        formula[lesson["lesson"], int(number)] = source

# The state definitions directly follow the two spectral decompositions.
family = ("ψ(θ)", "cos(θ)*|0>+sin(θ)*|1>")
wrong_family = ("ψ(θ)", "|0>")
matrix = "([3,1;1,1]/4)"
wrong_matrix = "(I/2)"

def evaluate(expression, definition=None):
    header = "QSTATES1\n0\n"
    if definition:
        name, body = definition
        header = f"QSTATES1\n1\n{len(name.encode())}\n{len(body.encode())}\n{name}{body}"
    response = subprocess.run([worker, "--states", "--json"], input=(header + "quantum:" + expression).encode(),
                              capture_output=True, check=True, timeout=30, env=env)
    result = json.loads(response.stdout)
    if result["approximate"]:
        raise ValueError("Unexpected approximate result for " + expression)
    return result["copy_text"]

def check(expression, expected, definition=None):
    actual = evaluate(expression, definition)
    if actual != expected:
        raise ValueError((expression, actual, expected))

def forms(lesson, number):
    source = formula[lesson, number]
    # Remove only display delimiters and final sentence punctuation for nesting.
    return (source.strip().strip("$").strip().rstrip(".,"), evaluate(source))

for key in [("IBM-003", 157), ("IBM-015", 82)]:
    check(formula[key], "1", family)
for definition, expected in [(family, r"\begin{gathered}1\\1\end{gathered}"),
                             (wrong_family, r"\begin{gathered}0\\0\end{gathered}")]:
    check(formula["IBM-003", 159], expected, definition)

for expression in forms("IBM-003", 156):
    check(expression, "1", family)
    check(expression, "0", wrong_family)

for number in (78, 81, 86):
    for expression in forms("IBM-015", number):
        for proposal, expected in [(matrix, "1"), (wrong_matrix, "0")]:
            check(f"replace(({expression}),ρ,{proposal})", expected, family)

for number, other_register in [
    (83, "[(2+sqrt(2))/4,0;0,(2-sqrt(2))/4]"),
    (91, "[1/2,1/(2*sqrt(2));1/(2*sqrt(2)),1/2]"),
]:
    for state in forms("IBM-015", number):
        density = f"density(({state}))"
        check(f"tr({density})", "1", family)
        for axis, reference in [(1, matrix), (0, other_register)]:
            check(f"qcompare(ptrace({density},[{axis}]),({reference}),4)", "1", family)
        check(f"qcompare(ptrace({density},[0]),{matrix},4)", "0", family)
print("Verified both decompositions, both purifications and the retained register in each reduction.")
