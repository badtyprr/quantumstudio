"""Check the zero-based eigenstate family in the pinned phase-estimation lesson."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
row = next(row for row in inventory["rows"] if row["id"].endswith("-M214"))


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=30, check=True)
    return json.loads(result.stdout)


record = evaluate(row["literal"])
checks = []
for origin, expression in [("source", row["literal"].strip("$")), ("display", record["display_text"]),
                           ("copy", record["copy_text"])]:
    assert evaluate(expression)["copy_text"] == record["copy_text"]
    for dimension in (1, 2, 4):
        family = f"replace(({expression}),N,{dimension})"
        expected = r"\{" + ",".join(f"|φ_{i}>" for i in range(dimension)) + r"\}"
        bound = expression
        for i in range(dimension):
            bound = f"replace(({bound}),φ_{i},basis({i},{dimension + 1}))"
        concrete = f"replace(({bound}),N,{dimension})"
        for probe, answer in [(f"({family})=({expected})", "1"),
                              (f"qmember(basis({dimension-1},{dimension+1}),{concrete})", "1"),
                              (f"qmember(basis({dimension},{dimension+1}),{concrete})", "0")]:
            assert evaluate(probe)["copy_text"] == answer, (origin, probe)
        checks.append(dict(origin=origin, dimension=dimension, expected_set=expected,
                           set_equality=True, first_outside_state_excluded=True))

report = dict(source=inventory["source"], row=row["id"], literal=row["literal"],
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              display=record["display_text"], copy=record["copy_text"], checks=checks)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
