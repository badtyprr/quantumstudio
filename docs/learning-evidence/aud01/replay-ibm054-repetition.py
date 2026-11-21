"""Verify repetition encoding, every majority input and all three phase-flip positions."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("inventory", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(args.inventory.read_bytes())["rows"]
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def evaluate(expr):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                         env=env, capture_output=True, check=True, timeout=30)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]


encoded = evaluate(rows[4]["literal"])
for bit in (0, 1):
    assert f"qtuple(vector(qbitlabel({bit},1),qbitlabel({7*bit},3)))" in encoded
decoder = evaluate(rows[5]["literal"])
for word in range(8):
    decoded = evaluate(f"qgraphapply({decoder},qbitlabel({word},3))")
    assert decoded == f"qbitlabel({int(word.bit_count() >= 2)},1)"
for n in (60, 61):
    assert evaluate(rows[n-1]["literal"]) == "1"
for wire, signs in enumerate(("--+", "-+-", "+--")):
    gates = ["I", "I", "I"]
    gates[2-wire] = "Z"
    product = "".join("{"+s+"}" for s in signs)
    assert evaluate(r"\vert "+product+r"\rangle = ("+"@".join(gates)+")*(|->@|->@|->)") == "1"
print("Verified both encodings, all eight decoder inputs and each single-qubit phase flip.")
