"""Check the piecewise inner product of two Fourier basis states in IBM-028."""
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
source = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
row = source["rows"][214]
assert row["id"].endswith("M215")


def evaluate(text):
    result = subprocess.run([worker, "--json"], input=("quantum:" + text).encode(),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, (text, result.stderr.decode())
    return json.loads(result.stdout)


record = evaluate(row["literal"])
assert evaluate(record["copy_text"])["copy_text"] == record["copy_text"]
gui = [[row["id"], row["literal"], "0"]]
cases = []
for dimension in (2, 3, 4):
    for z in range(dimension):
        for y in range(dimension):
            # For the counterexample, duplicate a column for distinct labels
            # or choose an orthogonal column for equal labels.
            wrong = z if z != y else (y + 1) % dimension
            for form in ("display_text", "copy_text"):
                for column, expected in [(y, "1"), (wrong, "0")]:
                    expression = record[form]
                    for name, value in [("φ_z", f"fourier({dimension})*basis({z},{dimension})"),
                                        ("φ_y", f"fourier({dimension})*basis({column},{dimension})"),
                                        ("z", z), ("y", y)]:
                        expression = f"replace(({expression}),{name},({value}))"
                    assert evaluate(expression)["copy_text"] == expected, (dimension, z, y, form, column)
                    if dimension == 2 and form == "display_text":
                        gui.append([f"M215-{z}-{y}-{expected}", expression, "0"])
            cases.append(dict(dimension=dimension, z=z, y=y, rejected_column=wrong))
evidence = dict(source=source["source"], id=row["id"], literal=row["literal"],
                worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), forms=["display", "copy"],
                display=record["display_text"], copy=record["copy_text"], cases=cases)
args.output.write_bytes((json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
