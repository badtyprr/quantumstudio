"""Replay IBM-038's numeric ket transitions and verify the Windows lesson sessions."""
import argparse
import hashlib
import json
from itertools import product
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
inventory = json.loads(Path(__file__).with_name("ibm038-inventory.json").read_bytes())
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(),
                            capture_output=True, timeout=30, check=True, env=env)
    value = json.loads(result.stdout)
    assert not value["approximate"], expression
    return value


cases = {}
for row in inventory["rows"]:
    literal = row["literal"]
    cases[row["id"]] = literal, evaluate(literal)["copy_text"]

action = inventory["rows"][154]
assert action["id"].endswith("-M155")
formula = cases[action["id"]][1]
assert evaluate(formula)["display_text"] == "A|0⟩ = |1⟩, A|1⟩ = |2⟩, A|2⟩ = |0⟩"
matrix = inventory["rows"][149]["literal"].split("=", 1)[1].strip("$ \n")
lesson_matrix = evaluate(matrix)["copy_text"]

def control(name, operator, expected):
    expression = f"replace(({formula}),'A',{operator})"
    assert evaluate(expression)["copy_text"] == expected, name
    cases[name] = expression, expected

control("lesson-matrix", lesson_matrix, "1")
control("larger-space", "matrix(4,4,[0,0,1,0,1,0,0,0,0,1,0,0,0,0,0,1])", "1")
control("extra-output-component", "matrix(4,3,[0,0,1,1,0,0,0,1,0,0,1,0])", "0")
for column in range(3):
    entries = [int(row == (col+1)%3) for row in range(3) for col in range(3)]
    entries[3*((column+1)%3)+column] = -1
    control(f"wrong-phase-{column}", "matrix(3,3,["+",".join(map(str,entries))+"])", "0")

# All 27 deterministic maps on three states, including noninvertible maps.
# Only the lesson's cyclic map satisfies all three equations.
maps_checked = 0
for image in product(range(3), repeat=3):
    entries = [str(int(image[col] == row)) for row in range(3) for col in range(3)]
    operator = "matrix(3,3,["+",".join(entries)+"])"
    expected = str(int(image == (1,2,0)))
    assert evaluate(f"replace(({formula}),'A',{operator})")["copy_text"] == expected, image
    maps_checked += 1

# The displayed definition singles out one square root of X. Its square
# alone also accepts the negative and adjoint roots.
roots = {
    "lesson": ("H*S*H", "1", "1"),
    "negative": ("-(H*S*H)", "0", "1"),
    "adjoint": ("H*dagger(S)*H", "0", "1"),
    "negative-adjoint": ("-(H*dagger(S)*H)", "0", "1"),
    "identity": ("identity(2)", "0", "0"),
    "pauli-x": ("X", "0", "0"),
}
for number in (146, 148):
    row = inventory["rows"][number-1]
    copied = cases[row["id"]][1]
    assert copied.startswith("qequalchain(") and evaluate(copied)["copy_text"] == copied
    for name, (operator, definition, square) in roots.items():
        expr = f"replace(({copied}),'R',({operator}))"
        truth = definition if number == 146 else square
        assert evaluate(expr)["copy_text"] == truth
        cases[f"root-{number}-{name}"] = expr, truth

# Change each concrete stage independently while supplying the correct R.
source = inventory["rows"][145]["literal"]
for name, old, new in [("composition", "H S H", "H T H"),
                       ("middle-factor", "0 & i", "0 & -i"),
                       ("last-matrix", "1+i", "1-i")]:
    altered = source.replace(old, new, 1)
    assert altered != source
    # Bind R before evaluation so an inconsistent concrete pair is always tested.
    expr = altered.replace("R =", "H S H =", 1)
    assert evaluate(expr)["copy_text"] == "0"
    cases["changed-"+name] = expr, "0"

clipboard_checks(worker, args.windows, args.report, cases, 182,
                 dict(source_sha256=inventory["source_sha256"], original_formulas=161,
                      transitions=formula, concrete_controls=6, deterministic_maps=maps_checked,
                      matrix_root_bindings=12, changed_definition_steps=3,
                      application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()))
