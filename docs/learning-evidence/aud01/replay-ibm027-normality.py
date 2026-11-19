"""Validate the IBM-027 normality criterion with exact complex matrices."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
source = next(row["literal"] for row in rows if row["id"].endswith("M002"))


def evaluate(body):
    process = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                             capture_output=True, timeout=30)
    assert process.returncode == 0, (body, process.stderr.decode())
    return json.loads(process.stdout)


def bind(body, matrix):
    return f"replace(({body}),M,{matrix})"


# The Hermitian and symmetric examples give opposite answers if conjugation
# is accidentally dropped. Normality also includes non-Hermitian operators.
cases = [
    ("hermitian", "matrix(2,2,[1,i,-i,0])", "1"),
    ("symmetric-nonnormal", "matrix(2,2,[1,i,i,0])", "0"),
    ("jordan", "matrix(2,2,[1,1,0,1])", "0"),
    ("cyclic-unitary", "matrix(3,3,[0,1,0,0,0,1,1,0,0])", "1"),
    ("diagonal", "matrix(3,3,[2,0,0,0,i,0,0,0,-3])", "1"),
    ("rectangular", "matrix(3,2,[1,0,0,1,0,0])", "0"),
]
record = evaluate(source)
copy = record["copy_text"]
inputs = [[row["id"], row["literal"]] for row in rows]
assert evaluate(copy)["copy_text"] == copy
for body in (source.strip("$"), record["display_text"], copy):
    for name, matrix, expected in cases:
        assert evaluate(bind(body, matrix))["copy_text"] == expected, (name, body)
for name, matrix, expected in cases:
    inputs.append([f"{name}-{expected}", bind(copy, matrix)])
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified the normality criterion for six matrices from source, display and Copy.")
