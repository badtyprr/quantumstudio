"""Verify the classical lesson's scalar constants independently with rational arithmetic."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm037-inventory.json").read_bytes())
checks = {}
rows = []
for row in inventory["rows"]:
    match = re.fullmatch(r"\$(\d+(?:/\d+)?)\$", row["literal"])
    if not match:
        continue
    literal = match.group(1)
    if literal not in checks:
        expected = Fraction(literal)
        copied = ""
        for expression in ["quantum:" + row["literal"], None]:
            result = subprocess.run([worker,"--json"],input=(expression or copied).encode(),
                                    env=env, capture_output=True, timeout=30, check=True)
            value = json.loads(result.stdout)
            assert not value["approximate"], literal
            copied = value["copy_text"]
            assert Fraction(copied.replace(" ", "").replace("∕", "/")) == expected
        checks[literal] = str(expected)
    rows.append(dict(id=row["id"], literal=literal, expected=checks[literal]))
assert len(rows) == 32
print(json.dumps(dict(source_sha256=inventory["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),rows=rows),indent=2))
