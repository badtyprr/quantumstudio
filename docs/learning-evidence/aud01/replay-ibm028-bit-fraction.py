"""Verify both rows of the phase-estimation lesson's one-bit fraction definition."""
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
row = next(row for row in inventory["rows"] if row["id"].endswith("-M039"))
gui = [[row["id"], row["literal"], "0"]]


def evaluate(expression):
    return subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                          capture_output=True, timeout=30)


def result(expression):
    process = evaluate(expression)
    assert process.returncode == 0, (expression, process.stderr)
    return json.loads(process.stdout)


source = row["literal"]
cases = [
    ("original", source, ["1", "1"]),
    ("changed-zero-row", source.replace("0 & a", "1 & a", 1), ["0", "1"]),
    ("changed-one-row", source.replace(r"\frac{1}{2}", r"\frac{1}{4}"), ["1", "0"]),
]
assert len({literal for _, literal, _ in cases}) == len(cases)
checks = []
for name, literal, truth in cases:
    record = result(literal)
    for form, text in [("source", literal.strip("$")), ("display", record["display_text"]),
                       ("copy", record["copy_text"])]:
        # The display spells division by two as multiplication by one half.
        # Check its meaning for every admissible bit below.
        if form != "display":
            assert result(text)["copy_text"] == record["copy_text"], (name, form)
        for bit, expected in enumerate(truth):
            probe = f"replace(({text}),a,{bit})"
            assert result(probe)["copy_text"] == expected, (name, form, bit)
            if form == "source":
                gui.append([f"M039-{name}-{bit}", probe, "0"])
        for invalid in ("-1", "1/2", "2"):
            failure = evaluate(f"replace(({text}),a,{invalid})")
            assert failure.returncode and b"Binary-string labels" in failure.stderr, (name, form, invalid)
    checks.append(dict(case=name, literal=literal, display=record["display_text"], copy=record["copy_text"],
                       at_zero=truth[0], at_one=truth[1]))

report = dict(source=inventory["source"], row=row["id"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              forms=["source", "display", "copy"], invalid_digits=["-1", "1/2", "2"], checks=checks)
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
