"""Exercise the no-cloning argument using a controlled NOT and an independent identity."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(source):
    run = subprocess.run([worker, "--json"], input=("quantum:" + source).encode(),
                         env=env, check=True, capture_output=True, timeout=30)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

def check(index, substitutions, expected):
    row = rows[index - 1]
    equation = evaluate(row["literal"])
    assert equation == row["copy"], row["id"]
    for name, value in substitutions:
        equation = f"replace(({equation}),{name},{value})"
    assert evaluate(equation) == expected, (row["id"], substitutions)

rows = json.loads(Path(__file__).with_name("ibm047-inventory.json").read_bytes())["rows"]
blank = ('qnamedket("φ")', "|0>")
for index in (42, 62, 67, 72):
    for state, truth in [("|0>", "1"), ("|1>", "1"), ("|+>", "0")]:
        check(index, [('"U"', "CNOT"), ('qnamedket("ψ")', state), blank], truth)

basis = [('qketstate("a")', "|0>"), ('qketstate("b")', "|1>"), blank]
for index in (65, 66):
    for gate, truth in [("CNOT", "1"), ("identity(4)", "0")]:
        check(index, [('"U"', gate), *basis], truth)

# The hypothetical cloning equation contradicts the linear action on the sum.
check(69, [('"U"', "CNOT"), *basis], "0")
print("Verified seven source formulas with 17 no-cloning checks")
