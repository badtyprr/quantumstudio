"""Verify arithmetic adaptations of the estimates in the pinned IBM-137 grant-writing lesson."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
raw = args.source.read_bytes()
if hashlib.sha256(raw).hexdigest() != "3459d0b4507cb6d3af2e33c5a168c8a336480eb1aa3b2f0efa7f4989815ab8c8":
    raise ValueError("Expected the pinned IBM-137 grant-writing page")
source = raw.decode()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

# The time-budget examples assume the entire illustrative allocation is spent
# on equal-duration runs. The prose allows for overhead and experimentation.
cases = [
    ("400 minutes", "400", "400"),
    ("400 minutes", "400/60", "20/3"),
    ("30-120 minutes", "30/60", "1/2"),
    ("30-120 minutes", "120/60", "2"),
    ("30-120 minutes", "floor(400/30)", "13"),
    ("30-120 minutes", "400-13*30", "10"),
    ("30-120 minutes", "floor(400/120)", "3"),
    ("30-120 minutes", "400-3*120", "40"),
    ("120 qubits", "120", "120"),
    ("two-qubit depths around 30", "30", "30"),
    ("~30% more complex", "100*(1+30/100)", "130"),
    ("~10× improved error rates", "(1/100)/10", "1/1000"),
]

for anchor, expression, expected in cases:
    if anchor not in source:
        raise ValueError(f"Could not locate {anchor!r} in the lesson")
    response = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                              capture_output=True, check=True, env=env, timeout=30)
    result = json.loads(response.stdout)
    if result["approximate"] or Fraction(result["copy_text"].replace(" ∕ ", "/")) != Fraction(expected):
        raise ValueError((expression, result["copy_text"], expected))
print(f"Passed all {len(cases)} source-value and adaptation checks.")
