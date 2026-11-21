"""Check the pinned circuit diagrams from the limitations-on-quantum-information lesson."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("figures", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm047-inventory.json").read_bytes())
hashes = {
    "cNOT-copy.svg": "64cbaadca4bd7890f41c59b9c86e2125cce4de60e735ac263a685448f7e4b66b",
    "discriminate.svg": "7918c79e74161b3fdd8b6fc21a40fea5c8e3145863c0a375d65a4f22e57c2d83",
}
sources = {}
for figure in inventory["figures"]:
    name = Path(figure["path"]).name
    digest = hashlib.sha256((args.figures / name).read_bytes()).hexdigest()
    assert digest == hashes[name]
    repository = inventory["source"].split("/learning/courses/")[0]
    sources[name] = dict(source=repository + "/public" + figure["path"], sha256=digest)
assert sources.keys() == hashes.keys()

def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         env=env, check=True, capture_output=True, timeout=30)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

checks = []
def check(name, expression, expected):
    result = evaluate(expression)
    assert result == evaluate(expected), expression
    checks.append(dict(figure=name, expression=expression, expected=expected, result=result))

# The diagram places the top wire at bit zero. Its bottom wire controls the top target.
for bit in (0, 1):
    check("cNOT-copy.svg", f"CNOT*(|{bit}>@|0>)", f"|{bit}{bit}>")
check("cNOT-copy.svg", "SWAP*CNOT*SWAP*|10>", "|10>")
# One instance of the unspecified discriminator U measures |+> and |-> in the X basis.
# The workspace occupies the high bit and begins at zero in both panels.
for state, expected in [("|+>", "[1;0;0;0]"), ("|->", "[0;1;0;0]")]:
    check("discriminate.svg", f"probs((I@H)*(|0>@{state}))", expected)
    check("discriminate.svg", f"probs(|0>@{state})", "[1/2;1/2;0;0]")
report = dict(figures=sources, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), checks=checks)
args.report.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
