"""Replay the matrix-size notation from the phase-estimation problem."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
source = rows[11]["literal"]
assert rows[11]["id"].endswith("M012")


def calculate(body, mode="dimensions:", valid=True):
    run = subprocess.run([args.worker.resolve(), "--json"], input=("quantum:" + mode + body).encode(),
                         capture_output=True, timeout=30)
    if valid:
        assert run.returncode == 0, (body, run.stderr.decode())
        return json.loads(run.stdout)
    assert run.returncode != 0 and b"dimension" in run.stderr.lower(), (body, run.stdout, run.stderr)


inputs = [[r["id"], r["literal"], "3" if r["id"].endswith("M012") else "2" if r["id"].endswith("M063") else "0"] for r in rows]
result = calculate(source)
canonical = result["copy_text"]
assert calculate(canonical, "")["copy_text"] == canonical
assert calculate(result["display_text"])["copy_text"] == canonical
for expression, expected in [
    ("3 × 4", "3 × 4"), (r"$4\times 3$", "4 × 3"),
    ("(2 × 3) × (2+2)", "6 × 4"),
    (f"replace(({canonical}),N,5)", "5 × 5"),
]:
    result = calculate(expression)
    assert result["display_text"] == expected, (expression, result)
    assert calculate(result["copy_text"], "")["copy_text"] == result["copy_text"]
    inputs.append([f"shape-{len(inputs)}", expression, "3"])

assert calculate("3 × 4", "")["copy_text"] == "12"
inputs.append(["arithmetic", "3 × 4", "0"])
for expression in ["0 × 2", "2 × (-1)", "(1/2) × 2", "2 × 3 × 4",
                   f"replace(({canonical}),N,0)"]:
    calculate(expression, valid=False)
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified ordered matrix dimensions, substitutions, invalid counts and arithmetic notation.")
