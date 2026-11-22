"""Replay the IBM-136 year-zero staffing tables on a packaged calculator."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
raw = args.source.read_bytes()
if hashlib.sha256(raw).hexdigest() != "b1e8609c0f576556d0213d1a869e34b9b3d65e3d5baf74fd945b3883d9255b7f":
    raise ValueError("Unexpected IBM-136 source")
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
tables = {
    "Academic institution, research organization, or QIC": (["Subject matter expert", "Project manager", "Program manager", "Administrator"], ("4.5", "5")),
    "Enterprise organization": (["Executive sponsor", "Project manager", "Subject matter expert", "Business SME"], ("4.25", "4.25")),
    "Startups": (["Project manager", "Subject matter expert", "Business SME"], ("4", "4")),
    "Global systems integrators": (["Executive sponsor", "Project manager", "Subject matter expert", "Business SME"], ("4.25", "4.25")),
}

def verify(expression, expected):
    response = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                              capture_output=True, env=env, check=True, timeout=30)
    value = json.loads(response.stdout)
    actual = value["copy_text"].replace(" ∕ ", "/")
    if value["approximate"] or Fraction(actual) != expected:
        raise ValueError((expression, actual, expected))

for section, (roles, totals) in tables.items():
    body = raw.decode().split("### " + section, 1)[1].split("\n#", 1)[0]
    entries = re.findall(r"^\|\s*([^|]+?)\s*\|\s*([\d.]+)(?:-([\d.]+))? FTE\s*\|", body, re.M)
    if [role for role, _, _ in entries] != roles:
        raise ValueError(f"Staffing table changed in {section}")
    bounds = [[], []]
    for role, lower, upper in entries:
        bounds[0].append(lower)
        bounds[1].append(upper or lower)
        for value in dict.fromkeys([lower, upper or lower]):
            verify(value, Fraction(value))
    for inputs, expected in zip(bounds, totals):
        verify("+".join(inputs), Fraction(expected))
print("Verified all 15 role entries, including the academic range, and all eight endpoint totals.")
