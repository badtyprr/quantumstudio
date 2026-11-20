"""Replay the four two-bit fractions whose radix point is outside the source math span."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
notebook = args.notebook.read_bytes()
assert hashlib.sha256(notebook).hexdigest() == inventory["source_sha256"]
body = "".join(json.loads(notebook)["cells"][0]["source"])
worker = args.worker.resolve()
gui, evidence = [], []


def evaluate(text, mode="fractionbits:"):
    return subprocess.run([worker, "--json"], input=("quantum:" + mode + text).encode(),
                          capture_output=True, timeout=30)


def checked(text, mode="fractionbits:"):
    response = evaluate(text, mode)
    assert response.returncode == 0, (text, response.stderr)
    return json.loads(response.stdout)


for value in range(4):
    row = inventory["rows"][110 + value]
    bits = format(value, "02b")
    literal = row["literal"]
    complete = body[row["start"] - 1:row["end"]]
    assert literal == f"${bits}$" and complete == "." + literal
    expected = checked(str(Fraction(value, 4)), "")["copy_text"]
    result = checked(literal)
    for form in [bits, literal, complete, "." + bits, result["copy_text"], result["display_text"]]:
        assert checked(form)["copy_text"] == expected, (form, expected)
    assert checked(result["copy_text"], "")["copy_text"] == expected
    assert checked(literal, "")["copy_text"] == str(int(bits))
    evidence.append(dict(id=row["id"], literal=literal, with_radix_point=complete, value=str(Fraction(value, 4)),
                         display=result["display_text"], copy=result["copy_text"]))
    gui.extend([[row["id"], literal, "4"], [row["id"] + "-with-point", complete, "4"]])

for bits in ["1", "001", "1000", "10101", "1" + "0" * 1023]:
    expected = checked(str(Fraction(int(bits, 2), 2 ** len(bits))), "")["copy_text"]
    assert checked(bits)["copy_text"] == expected
for invalid in ("12", ".2", "1" * 1025):
    error = evaluate(invalid)
    assert error.returncode and b"binar" in error.stderr.lower(), invalid

report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              mode="Binary fraction digits", rows=evidence)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
