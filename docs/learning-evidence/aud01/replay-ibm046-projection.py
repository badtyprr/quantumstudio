"""Check the normalized projected state in IBM-046 with both computational projectors."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         capture_output=True, check=True, timeout=30, env=env)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

rows = json.loads(Path(__file__).with_name("ibm046-inventory.json").read_bytes())["rows"]
row = rows[135]
assert row["id"] == "IBM046-3c1262a5-M136"
expression = evaluate(row["literal"])
assert expression == row["copy"]
for projector, expected in [("[1,0;0,0]", "|0>"), ("[0,0;0,1]", "|1>")]:
    bound = f'replace(replace(({expression}),"Π_k",{projector}),qnamedket("ψ"),|+>)'
    assert evaluate(bound) == evaluate(expected)
print("Verified both normalized projections of the plus state from IBM-046 M136")
