"""Check the Fourier family name, register widths and printed matrix identities."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
rows = {row["id"][-4:]: row for row in inventory["rows"]}
gui = []


def evaluate(expression):
    process = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, timeout=30)
    assert process.returncode == 0, (expression, process.stderr.decode())
    return json.loads(process.stdout)


def copied(expression):
    return evaluate(expression)["copy_text"]


name = rows["M132"]
record = evaluate(name["literal"])
assert record["copy_text"] == '"QFT"'
gui.append([name["id"], name["literal"], "0"])
for form in (name["literal"].strip("$"), record["display_text"], record["copy_text"]):
    assert copied(form) == '"QFT"'
    for dimension in (2, 3, 4):
        assert copied(f"replace(({form}),QFT,fourier({dimension}))") == copied(f"fourier({dimension})")

matrix = rows["M130"]
dimensioned = evaluate(matrix["literal"])
fourier = dimensioned["copy_text"]
assert fourier == copied("QFT(2)") == copied("fourier(4)")
assert fourier != copied("QFT(4)")
assert copied(dimensioned["display_text"]) == fourier
gui.append([matrix["id"], matrix["literal"], "0"])
gui.append([matrix["id"] + "-display", dimensioned["display_text"], "0"])
definition = evaluate(rows["M128"]["literal"])
for form in (definition["display_text"], definition["copy_text"]):
    assert copied(f"replace(({form}),V,QFT(2))") == "1"
    assert copied(f"replace(({form}),V,identity(4))") == "0"
for operator, answer in [("QFT(2)", "1"), ("identity(4)", "0")]:
    gui.append(["M128-display-" + answer, f"replace(({definition['display_text']}),V,{operator})", "0"])

checks = []
for number, dimension in [(133, 4), (187, 1), (188, 2), (189, 3), (190, 4), (191, 8)]:
    row = rows[f"M{number}"]
    expression = row["literal"]
    assert copied(expression) == "1"
    gui.append([row["id"], expression, "0"])
    start = expression.index(r"\begin{pmatrix}") + len(r"\begin{pmatrix}")
    end = expression.index(r"\end{pmatrix}", start)
    # Retain spacing commands, row breaks and the optional final terminator.
    # Every Fourier coefficient is nonzero, so deleting any one must break equality.
    bounds = [(start, start)]
    bounds.extend(m.span() for m in re.compile(r"&|\\\\(?:\[[^\]]*\])?").finditer(expression, start, end))
    bounds.append((end, end))
    cells = [(a[1], b[0]) for a, b in zip(bounds, bounds[1:]) if expression[a[1]:b[0]].strip()]
    assert len(cells) == dimension ** 2
    for index, (left, right) in enumerate(cells):
        changed = expression[:left] + " 0 " + expression[right:]
        assert copied(changed) == "0", (row["id"], index)
        if index == len(cells) - 1:
            gui.append([row["id"] + "-zero-last", changed, "0"])
    checks.append(dict(id=row["id"], dimension=dimension, exact_result="1",
                       individually_zeroed_coefficients=len(cells), changed_result="0"))

phase_checks = []
for number, gate in [(217, "P"), (219, "CP")]:
    row = rows[f"M{number}"]
    operator = evaluate(row["literal"])
    for form in (operator["display_text"], operator["copy_text"]):
        for angle in ("0", "pi/2", "pi", "-pi/2"):
            for offset, expected in [("", "1"), ("+pi", "0")]:
                expr = f"replace(replace(({form}),{gate}_α,{gate}({angle}{offset})),α,{angle})"
                assert copied(expr) == expected, (row["id"], expr)
    phase_checks.append(dict(id=row["id"], gate=gate, angles=["0", "pi/2", "pi", "-pi/2"],
                             forms=["display", "copy"], rejected_offset="pi"))
report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              name=dict(id=name["id"], literal=name["literal"], display=record["display_text"],
                        copy=record["copy_text"], substitution_dimensions=[2, 3, 4]),
              M128=dict(accepted="QFT(2)", rejected="identity(4)"),
              M130=dict(literal=matrix["literal"], dimension=4, qubits=2), matrices=checks,
              phase_gates=phase_checks)
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
