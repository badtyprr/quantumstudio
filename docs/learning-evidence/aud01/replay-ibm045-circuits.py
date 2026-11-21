"""Replay the classical gate functions and both circuit wire-order conventions."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
rows = json.loads(Path(__file__).with_name("ibm045-inventory.json").read_bytes())["rows"]


def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         capture_output=True, check=True, timeout=30, env=env)
    result = json.loads(run.stdout)
    assert not result["approximate"]
    return result["copy_text"]


def literal(number):
    return rows[number - 1]["literal"]


def verify_gate(graph, outputs):
    width = 1 if len(outputs) == 2 else 2
    for index, bit in enumerate(outputs):
        assert evaluate(f"qgraphapply({graph},qbitlabel({index},{width}))") == bit


for number, outputs in [(3, "0001"), (4, "0111"), (5, "10"), (9, "0110"), (10, "0110"), (32, "0110")]:
    verify_gate(evaluate(literal(number)), outputs)
tables = evaluate(literal(6))
expected_tables = [evaluate(literal(number)) for number in (5, 3, 4)]
assert tables == "vector(" + ",".join(expected_tables) + ")"
verify_gate(evaluate(literal(10).replace("11 & 0", "11 & 1")), "0111")

for width in (1, 3):
    labels = [f'"q_{index}"' for index in range(width)]
    for number, ordered in [(37, list(reversed(labels))), (40, labels)]:
        expression = evaluate(literal(number))
        assert evaluate(f"replace(({expression}),n,{width})") == evaluate("qtuple(vector(" + ",".join(ordered) + "))")
    assert evaluate(f"replace(({evaluate(literal(39))}),n,{width})") == labels[-1]
assert evaluate(literal(38)) == '"q_0"'
print("Verified all gate inputs, the three side-by-side truth tables, a changed output, and both wire orders.")
