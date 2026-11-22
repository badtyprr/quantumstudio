"""Check named channels against IBM's original reset, dephasing and depolarizing equations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source_root", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
manifest = json.loads(Path(__file__).with_name("ibm007-008-matrix-unit-channels.json").read_bytes())

def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=30, env=env, check=True)
    return json.loads(result.stdout)["copy_text"]

for row in manifest["occurrences"]:
    notebook = (args.source_root / row["source"]).read_bytes()
    if hashlib.sha256(notebook).hexdigest() != row["source_sha256"]:
        raise ValueError(f"Use the source checkout at {manifest['revision']}")
    cell = json.loads(notebook)["cells"][row["cell"]]
    expression = "".join(cell["source"])[row["start"]:row["end"]]
    if hashlib.sha256(expression.encode()).hexdigest() != row["literal_sha256"]:
        raise ValueError(f"Source span changed in {row['source']}")
    copied = evaluate(expression)
    if evaluate(copied) != copied:
        raise ValueError(f"Unstable Copy in {row['lesson']} occurrence {row['occurrence']}")
    for kraus, expected in [(row["kraus"], "1"), ("vector(I)", "0")]:
        actual = evaluate(f'replace(({copied}),"{row["channel"]}",{kraus})')
        if actual != expected:
            raise ValueError((row["lesson"], row["occurrence"], kraus, expected, actual))
print(f'{len(manifest["occurrences"])} source equations passed with both channel assignments')
