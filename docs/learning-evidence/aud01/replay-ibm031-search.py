"""Run the Search and Unique search specifications over every two-bit oracle."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm031-inventory.json").read_bytes())
assert [p["title"] for p in inventory["panels"]] == ["Search", "Unique search"]


def evaluate(expression):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),env=env,
                       capture_output=True,check=True,timeout=30)
    return json.loads(p.stdout)["copy_text"]


source = inventory["rows"][4]
assert source["literal"] == "$f(x) = 1$"
predicate = evaluate(source["literal"])
results = []
for mask in range(16):
    graph = "qset(vector("+",".join(f"tuple(bitstring({x},2),{(mask >> x)&1})" for x in range(4))+"))"
    matches = [x for x in range(4) if mask & (1 << x)]
    solution_set = evaluate(f"qpreimage({graph},qset(vector(1)))")
    expected_set = "qset(vector("+",".join(f"qbitlabel({x},2)" for x in matches)+"))"
    assert solution_set == expected_set, (mask,solution_set)
    for x in range(4):
        actual = evaluate(f"replace(replace(({predicate}),f,{graph}),x,bitstring({x},2))")
        assert actual == str(int(x in matches)), (mask,x,actual)
    results.append(dict(oracle_mask=mask,solutions=[format(x,"02b") for x in matches],
                        unique_promise=len(matches)==1))

print(json.dumps(dict(source_sha256=inventory["source_sha256"], worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      predicate_id=source["id"], cases=results),indent=2))
