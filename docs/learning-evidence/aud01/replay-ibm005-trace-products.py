"""Check both partial-trace definitions in IBM-005 against explicit axis reductions."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source_root", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
manifest = json.loads(Path(__file__).with_name("deferred-named-trace.json").read_bytes())
lesson = next(entry for entry in manifest["lessons"] if entry["lesson"] == "IBM-005")
notebook = (args.source_root / lesson["source"]).read_bytes()
if hashlib.sha256(notebook).hexdigest() != lesson["source_sha256"]:
    raise ValueError("Use the pinned IBM-005 notebook at " + manifest["revision"])
cells = json.loads(notebook)["cells"]
worker = args.worker.resolve()
env = os.environ.copy()
if (worker.parent / "data").is_dir():
    env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

def copied(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         env=env, timeout=30, check=True, capture_output=True)
    return json.loads(run.stdout)["copy_text"]

def verify(expression, expected):
    actual = copied(expression)
    if actual != expected:
        raise ValueError((expression, expected, actual))

# Off-diagonal entries distinguish extracting blocks from summing the wrong rows.
# Density matrix of the normalized pure state (1, 2, 3, 4) / sqrt(30).
matrix = "([1,2,3,4;2,4,6,8;3,6,9,12;4,8,12,16]/30)"
for start, identity, domain, expected in [(12921, "I_A", "Γ", "matrix(2,2,[1 ∕ 6,11 ∕ 30,11 ∕ 30,5 ∕ 6])"),
                                          (13259, "I_B", "Σ", "matrix(2,2,[1 ∕ 3,7 ∕ 15,7 ∕ 15,2 ∕ 3])")]:
    row = next(item for item in lesson["occurrences"] if item["start"] == start)
    text = "".join(cells[row["cell"]]["source"])[start:row["end"]]
    if hashlib.sha256(text.encode()).hexdigest() != row["literal_sha256"]:
        raise ValueError(f"Source literal changed at {start}")
    left, right = text.strip().removeprefix("$$").removesuffix("$$").strip().removesuffix(".").split("=")
    mapped = f"subsystems({matrix},[A,B],[2,2])"
    verify(f"replace(({left}),ρ,{mapped})", expected)
    for product in (right, copied(right)):
        bound = f'replace(replace(replace(({product}),ρ,{matrix}),"{identity}",I),{domain},qset(vector(0,1)))'
        verify(bound, expected)
print("Both source definitions and copied products matched the independent reductions.")
