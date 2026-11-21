"""Check the source Kraus sum with concrete operators in two binding orders."""
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
rows = json.loads(Path(__file__).with_name("ibm056-inventory.json").read_bytes())["rows"]


def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(),
                         capture_output=True, env=env, timeout=45)
    assert run.returncode == 0, (expression,run.stderr.decode())
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]


relation = evaluate(rows[41]["literal"])
for operators in (["X"], ["I/sqrt(2)", "S/sqrt(2)"]):
    family = "vector("+",".join(operators)+")"
    domain = "qset(vector("+",".join(map(str, range(len(operators))))+"))"
    for channel, expected in ((family,"1"), ("vector(Z)","0")):
        terms = [(f"A_{i}",op) for i,op in enumerate(operators)]
        for bindings in ([("indexset_j",domain), *terms, ("σ","[1,2i;-2i,4]/5"), ("Φ",channel)],
                         [("Φ",channel), ("σ","[1,2i;-2i,4]/5"), ("indexset_j",domain), *terms]):
            value = relation
            for name,replacement in bindings:
                value = evaluate(f'replace(({value}),"{name}",{replacement})')
            assert value == expected, (operators,channel,value)
print("Verified one- and two-operator channels in two binding orders, including wrong-channel rejection.")
