"""Verify that the four Hadamard identities on IBM-038 remain separate."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
row = json.loads(Path(__file__).with_name("ibm038-inventory.json").read_bytes())["rows"][122]
assert row["id"].endswith("M123")
source = row["literal"]
assert source.count("H ") == 4

def evaluate(expr):
    response = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                              env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")),
                              capture_output=True, timeout=30, check=True)
    value = json.loads(response.stdout)
    assert not value["approximate"]
    return value["copy_text"]

for changed in [None, 0, 1, 2, 3]:
    gates = ["H "] * 4
    expected = ["1"] * 4
    if changed is not None:
        gates[changed] = "Z "
        expected[changed] = "0"
    parts = source.split("H ")
    expression = parts[0] + "".join(gate + tail for gate,tail in zip(gates,parts[1:]))
    copied = evaluate(expression)
    assert copied == r"\begin{gathered}" + r"\\".join(expected) + r"\end{gathered}", changed
    assert evaluate(copied) == copied, changed
print("Verified all four Hadamard identities and four position-specific negative controls through Copy")
