"""Check the source probability formula for every on-grid output through three qubits."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
row = inventory["rows"][327]
assert row["id"].endswith("M328")


def evaluate(text):
    result = subprocess.run([worker, "--json"], input=("quantum:" + text).encode(),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, (text, result.stderr.decode())
    return json.loads(result.stdout)


original = evaluate(row["literal"])
second_copy = evaluate(original["copy_text"])["copy_text"]
forms = [original["display_text"], original["copy_text"], second_copy]
gui = [[row["id"], row["literal"], "0"]]
checks = []


def check(width, phase, outcome, probability, off_grid=False):
    for form in forms:
        for candidate, expected in [(probability, "1"), (f"({probability})+1/8", "0")]:
            bound = f"replace(({form}),p_y,({candidate}))"
            for name, value in [("m", width), ("θ", phase), ("y", outcome)]:
                bound = f"replace(({bound}),{name},({value}))"
            actual = evaluate(bound)["copy_text"]
            assert actual == expected, (forms.index(form), width, phase, outcome, candidate, actual, bound)
            if form == forms[0] and off_grid:
                gui.append([f"M328-{width}-{outcome}-{expected}", bound, "0"])
    checks.append(dict(qubits=width, phase=phase, outcome=outcome, probability=probability))


for width in (1, 2, 3):
    dimension = 2 ** width
    for phase_index in range(dimension):
        for outcome in range(dimension):
            check(width, f"{phase_index}/{dimension}", outcome, str(int(outcome == phase_index)))

# Halfway between grid points, the one-qubit outcomes are equiprobable.
# For two qubits, sin²(pi/8) and sin²(3*pi/8) give the two distinct weights.
for outcome in range(2):
    check(1, "1/4", outcome, "1/2", True)
for outcome in range(4):
    expected = "(2+sqrt(2))/8" if outcome in (0, 1) else "(2-sqrt(2))/8"
    check(2, "1/8", outcome, expected, True)

report = dict(source=inventory["source"], id=row["id"], literal=row["literal"],
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              display=original["display_text"], copy=original["copy_text"], second_copy=second_copy,
              forms=["display", "copy", "copy after re-entry"], rejected_probability_offset="1/8",
              cases=checks)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
