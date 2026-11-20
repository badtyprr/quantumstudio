"""Verify the open binary expansion and the one-place shift in IBM-028."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())


def run(text, mode=""):
    return subprocess.run([worker, "--json"], input=("quantum:" + mode + text).encode(),
                          env=env, capture_output=True, timeout=30)


def evaluate(text, mode=""):
    process = run(text, mode)
    assert process.returncode == 0, (text, process.stderr.decode())
    record = json.loads(process.stdout)
    assert not record["approximate"]
    return record


def bind(expression, replacements):
    for name, value in replacements:
        expression = f"replace(({expression}),{name},({value}))"
    return expression


rows, gui = [], []
tails = [Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(2, 3), Fraction(1)]
for number in (74, 76):
    row = inventory["rows"][number - 1]
    assert row["id"].endswith(f"M{number:03d}")
    result = evaluate(row["literal"], "fractionbits:")
    gui.append([row["id"], row["literal"], "4"])
    forms = [result["display_text"], result["copy_text"]]
    for form in forms:
        assert evaluate(form)["copy_text"] == result["copy_text"]
        for prefix in range(8):
            bits = [(f"a_{n}", (prefix >> (3-n)) & 1) for n in range(1, 4)]
            for tail in tails:
                # Both equations use the same unshifted theta, even when 2*theta exceeds 1.
                theta = (prefix + tail) / 8
                for candidate, expected in [(theta, "1"), (theta + Fraction(1, 16), "0")]:
                    expr = bind(form, bits + [('binarytail("a_",4)', tail), ("θ", candidate)])
                    assert evaluate(expr)["copy_text"] == expected, (number, prefix, tail, candidate)
                    if form == forms[0] and prefix == 5 and tail == Fraction(1, 3):
                        gui.append([f"M{number}-{expected}", expr, "0"])
        # Assigning a later digit first keeps the intervening digit free.
        for fourth in (0, 1):
            theta = Fraction(5, 8) + Fraction(fourth, 16) + Fraction(1, 32) + Fraction(1, 96)
            digits = [("a_1", 1), ("a_2", 0), ("a_3", 1), ("a_5", 1), ("a_4", fourth)]
            test = bind(form, digits + [('binarytail("a_",6)', "1/3"), ("θ", theta)])
            assert evaluate(test)["copy_text"] == "1"
    rows.append(dict(id=row["id"], literal=row["literal"], display=forms[0], copy=forms[1]))
for invalid in ("binaryfraction(vector(1,2,0),3,0)", "binaryfraction(vector(0,0,0),3,-1/10)",
                "binaryfraction(vector(0,0,0),3,11/10)", "binaryfraction(vector(0,0,0),3,i)"):
    assert run(invalid).returncode != 0, invalid
report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              mode="Binary fraction", rows=rows, prefixes=list(range(8)), tails=list(map(str, tails)),
              rejected_offset="1/16", additional_digit_order=[5, 4])
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
