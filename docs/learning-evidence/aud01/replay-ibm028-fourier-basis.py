"""Replay the four-dimensional Fourier-basis construction in IBM-028."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
source = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
environment = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def literal(number):
    row = source["rows"][number - 1]
    assert row["id"].endswith(f"M{number:03d}")
    return row["literal"]


def evaluate(text):
    result = subprocess.run([worker, "--json"], input=("quantum:" + text).encode(),
                            capture_output=True, timeout=30, env=environment, check=True)
    record = json.loads(result.stdout)
    assert not record["approximate"], record
    return record["copy_text"]


def check(expression, value):
    assert evaluate(expression) == value, expression


def aligned(copy):
    start, end = r"\begin{gathered}", r"\end{gathered}"
    assert copy.startswith(start) and copy.endswith(end)
    rows = copy[len(start):-len(end)].split(r"\\")
    assert len(rows) == 4
    return rows


# The notebook explicitly specifies two qubits. Annotate the 16 numeric kets
# with that dimension, keeping every coefficient and named ket as printed.
annotated, count = re.subn(r"(\\vert\s*[0-3]\s*\\rangle)", r"\g<1>_{4}", literal(119))
assert count == 16
columns = evaluate(annotated)
check(columns, columns)
general = evaluate(literal(118))
matrix_definition = evaluate(literal(128))
qft = evaluate(literal(130))
check(literal(133), "1")
for transform, expected in [(qft, "1"), ("identity(4)", "0")]:
    check(f"replace(({matrix_definition}),V,({transform}))", expected)

# Bind the declared operator before evaluation, as an undeclared V is scalar.
context = 'matrixcontext("V",(4),(4),"unitary"):'
declared = evaluate(context + literal(123))
reentered = aligned(evaluate(declared))
action = aligned(declared)
gui = [["M119", annotated, "0"], ["M123", context + literal(123), "0"]]
witnesses = []
for index, (column, image) in enumerate(zip(aligned(columns), action)):
    operator = 'operatorparam(V,4,"unitary")'
    relations = [("M119", column), ("M123", f"replace(({image}),{operator},({qft}))"),
                 ("M123-copy", f"replace(({reentered[index]}),{operator},({qft}))")]
    for candidate in range(4):
        vector = f"fourier(4)*basis({candidate},4)"
        expected = str(int(index == candidate))
        for name, relation in relations:
            expression = f"replace(({relation}),φ_{index},({vector}))"
            check(expression, expected)
            if candidate in (index, (index + 1) % 4):
                gui.append([f"{name}-{index}-{expected}", expression, "0"])
        bound = f"replace((replace(({general}),φ_y,({vector}))),y,{index})"
        check(bound, expected)
        witnesses.append(dict(index=index, candidate=candidate, expected=int(expected)))

report = dict(source=source["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              m119_input=annotated, m119_copy=columns, m118_copy=general,
              m123_context=context, m123_copy=declared, m123_operator="QFT_4", m128_rejected_operator="identity(4)", cases=witnesses)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
