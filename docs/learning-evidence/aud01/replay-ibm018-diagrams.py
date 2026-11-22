"""Check the five IBM query-model illustrations using a supplied local worker."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("figures", type=Path, help="Directory containing the five original SVGs")
parser.add_argument("worker", type=Path)
args = parser.parse_args()
evidence = json.loads(Path(__file__).with_name("ibm018-diagrams.json").read_bytes())
data = args.notebook.read_bytes()
if hashlib.sha256(data).hexdigest() != evidence["source_sha256"]:
    raise ValueError("IBM-018 notebook digest differs")
body = "".join(json.loads(data)["cells"][0]["source"])
refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
if refs != [figure["path"] for figure in evidence["figures"]]:
    raise ValueError("The illustrated source order differs")
for figure in evidence["figures"]:
    path = args.figures / Path(figure["path"]).name
    if hashlib.sha256(path.read_bytes()).hexdigest() != figure["sha256"]:
        raise ValueError(f"Wrong illustration: {path}")

worker = args.worker.resolve()
env = os.environ.copy()
if (worker.parent / "data").is_dir():
    env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=60, check=True, env=env)
    value = json.loads(result.stdout)
    if value["approximate"]:
        raise ValueError(f"Expected an exact value for {expression}")
    return value["copy_text"]

# Classical parity follows both branches from each f output. The two AND
# outputs are combined by OR. Test all four possible one-bit functions.
for f0, f1 in itertools.product(range(2), repeat=2):
    gates = f"({f0} and (not {f1})) or ((not {f0}) and {f1})"
    if evaluate(gates) != str(f0 ^ f1):
        raise ValueError((f0, f1))

# The source leaves f arbitrary. This fixture uses unequal register widths,
# repeated outputs and a leading-zero output, all allowed by the diagram.
table = [1, 4, 0, 1]
entries = [f"g({x:02b})&={y:03b}" for x, y in enumerate(table)]
graph = evaluate(r"\begin{aligned}" + r"\\".join(entries) + r"\end{aligned}")
failed_lookups = []
for x, y in enumerate(table):
    query = f"replace(g(bitstring({x},2)),g,{graph})"
    if evaluate(query) != f"qbitlabel({y},3)":
        failed_lookups.append(x)

size = len(table) * 8
matrix = evaluate("oracle([1,4,0,1],3)")
expected = [0] * (size * size)
for column in range(size):
    x, y = divmod(column, 8)
    row = 8*x + (y ^ table[x])
    expected[row*size + column] = 1
reference = f"matrix({size},{size},[" + ",".join(map(str, expected)) + "])"
if matrix != reference:
    raise ValueError("Unitary query differs from |x,y> -> |x,y XOR f(x)>")
print("Verified five source figures, four parity cases and all 1,024 oracle entries.")
if failed_lookups:
    raise ValueError(f"Classical lookups differ for inputs {failed_lookups}")
print("All four classical lookups passed.")
