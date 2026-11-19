"""Verify the printed phase domain, including its two different endpoints."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
baseline = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())
rows = baseline["lessons"][1]["rows"]
row = next(row for row in rows if row["id"].endswith("M082"))

def evaluate(expression):
    p = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (expression, p.stderr)
    return json.loads(p.stdout)

source = row["literal"].strip("$")
record = evaluate(row["literal"])
for form in (source, record["display_text"], record["copy_text"]):
    assert evaluate(form)["copy_text"] == record["copy_text"]
    for phase in map(Fraction, ("-1/1000", "0", "1/1000", "1/2", "999/1000", "1", "1001/1000")):
        result = evaluate(rf"replace(({form}),\theta,{phase})")
        assert result["copy_text"] == str(int(0 <= phase < 1)) and not result["approximate"]

controls = [
    ("zero", r"0\in[0,1)", 1), ("one", r"1\in[0,1)", 0),
    ("negative", r"-1/4\in[0,1)", 0), ("near-one", r"999/1000\in[0,1)", 1),
    ("irrational", r"sqrt(2)/2\in[0,1)", 1), ("right-closed", "1 ∈ (0,1]", 1), ("right-open", "1 ∉ [0,1)", 1),
    ("nested", r"2\in\left[(1+1), (2+1)\right)", 1),
    ("empty", r"0\in[0,0)", 0), ("complex", r"i\in[0,1)", 0),
]
for name, expr, expected in controls:
    assert evaluate(expr)["copy_text"] == str(expected), name
# A matched bracket pair keeps its existing collection interpretation.
assert evaluate(r"2\in[1,3]")["copy_text"] == "0"
assert evaluate(r"3\in[1,3]")["copy_text"] == "1"
for invalid in (r"$[0,1)$", r"$x\in[0,1,2)$", r"$x\in[0,(1+2]$"):
    p = subprocess.run([worker, "--json"], input=("quantum:" + invalid).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 2 and p.stderr.strip(), invalid
if args.gui_inputs:
    inputs = [[r["id"], r["literal"]] for r in rows]
    inputs.extend([[f"{name}-{expected}", expr] for name, expr, expected in controls])
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified 21 phase substitutions and ten interval controls.")
