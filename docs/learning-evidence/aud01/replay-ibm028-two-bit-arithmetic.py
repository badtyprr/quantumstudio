"""Check the finite domains and bit weights in the two-bit phase-estimation example."""
import argparse
import hashlib
import itertools
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
gui, report = [], {}


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            check=True, capture_output=True, timeout=30)
    return json.loads(result.stdout)


def verify(number, assignments, expected):
    row = inventory["rows"][number - 1]
    if number not in report:
        assert row["id"].endswith(f"M{number:03}")
        record = evaluate(row["literal"])
        report[number] = dict(id=row["id"], literal=row["literal"], display=record["display_text"],
                              copy=record["copy_text"], substitutions=[])
        gui.extend([[row["id"], row["literal"], "0"], [row["id"] + "-display", record["display_text"], "0"]])
    case = report[number]
    for expression in (row["literal"].strip("$"), case["display"], case["copy"]):
        for name, value in assignments:
            expression = f"replace(({expression}),{name},({value}))"
        assert evaluate(expression)["copy_text"] == str(int(expected)), (number, expression, expected)
    case["substitutions"].append(dict(assignments=dict(assignments), expected=expected))


for i in range(-1, 5):
    for n, name in [(104, "x"), (109, "y"), (117, "y"), (136, "y"), (140, "y")]:
        verify(n, [(name, str(i))], 0 <= i < 4)
    for n in (110, 144):
        verify(n, [("θ", f"{i}/4")], 0 <= i < 4)
for n in (263, 273):
    for a, b in itertools.product((-1, 0, 1, 2), repeat=2):
        verify(n, [("a", str(a)), ("b", str(b))], a in (0, 1) and b in (0, 1))
for high, low in itertools.product(range(2), repeat=2):
    value = 2 * high + low
    for guess in (value, (value + 1) % 4):
        verify(105, [("a_1", str(high)), ("a_0", str(low)), ("x", str(guess))], value == guess)
        verify(108, [("θ", f"{value}/4"), ("y", str(guess))], value == guess)

evidence = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                forms=["source", "display", "copy"], rows=list(report.values()))
args.output.write_bytes((json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
