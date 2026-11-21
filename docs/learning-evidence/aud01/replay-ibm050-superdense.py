"""Check each source Bell-state identity and recover both classical message bits."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
rows = json.loads(Path(__file__).with_name("ibm050-inventory.json").read_bytes())["rows"]


def evaluate(expr):
    run = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(), capture_output=True, env=env, check=True)
    result = json.loads(run.stdout)
    assert not result["approximate"]
    return result["copy_text"]


assert evaluate(rows[31]["literal"]) == r"\begin{gathered}1\\1\\1\\1\end{gathered}"
for c, d, gate in [(0,0,"I"), (0,1,"Z"), (1,0,"X"), (1,1,"XZ")]:
    decoded = f"(I@H)*SWAP*CNOT*SWAP*(I@{gate})*|phi+>"
    phase = "-" if c and d else ""
    assert evaluate(f"({decoded})=={phase}|{c}{d}>") == "1"
    assert evaluate(f"probs({decoded})==probs(|{c}{d}>)") == "1"
assert evaluate("XZ==-ZX") == "1"
assert evaluate("XYZ==i*I") == "1"
print("Verified all four Bell-state equations and decoded all four messages with the source wire order.")
