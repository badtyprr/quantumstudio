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

def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         env=env, timeout=30, check=True, capture_output=True)
    return json.loads(run.stdout)["copy_text"]

# Off-diagonal entries distinguish extracting blocks from summing the wrong rows.
# Density matrix of the normalized pure state (1, 2, 3, 4) / sqrt(30).
matrix = "([1,2,3,4;2,4,6,8;3,6,9,12;4,8,12,16]/30)"
for start, identity, domain, expected in [(12921, "I_A", "Γ", "[5,11;11,25]/30"),
                                          (13259, "I_B", "Σ", "[10,14;14,20]/30")]:
    row = next(item for item in lesson["occurrences"] if item["start"] == start)
    text = "".join(cells[row["cell"]]["source"])[start:row["end"]]
    assert hashlib.sha256(text.encode()).hexdigest() == row["literal_sha256"]
    left, right = text.strip().removeprefix("$$").removesuffix("$$").strip().removesuffix(".").split("=")
    reference = evaluate(expected)
    mapped = f"subsystems({matrix},[A,B],[2,2])"
    assert evaluate(f"replace(({left}),ρ,{mapped})") == reference
    for product in (right, evaluate(right)):
        bound = f'replace(replace(replace(({product}),ρ,{matrix}),"{identity}",I),{domain},qset(vector(0,1)))'
        assert evaluate(bound) == reference
print("Both source definitions and copied products matched the independent reductions.")
