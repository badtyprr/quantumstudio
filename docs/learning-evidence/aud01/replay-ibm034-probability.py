"""Substitute probabilities into each printed inequality from the Grover lesson."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())


def evaluate(expression):
    p = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(), env=env,
                       capture_output=True, check=True, timeout=30)
    result = json.loads(p.stdout)
    assert not result["approximate"] and not result["cells"]
    return result


indices = {56, 60, 74, 97, 106}
reports = []
for index in sorted(indices):
    row = inventory["rows"][index-1]
    assert row["id"].endswith(f"M{index:03}") and row["status"] == "diagnostic"
    result = evaluate(row["literal"])
    assert evaluate(result["copy_text"])["copy_text"] == result["copy_text"], row["id"]
    parameter = "s" if index in (97,106) else "1"
    checks = 0
    for size, marked in [(8,1), (16,4), (32,16)]:
        fraction = Fraction(marked if parameter == "s" else 1, size)
        bound = fraction if index == 106 else Fraction(1,2) if index == 60 else 1-fraction
        for offset in [Fraction(-1,64), Fraction(0), Fraction(1,64)]:
            value = bound + offset
            for form in (result["copy_text"], result["display_text"]):
                predicate = f"replace(({form}),p(N,{parameter}),{value})"
                predicate = f"replace(replace(({predicate}),N,{size}),s,{marked})"
                observed = evaluate(predicate)["copy_text"]
                assert observed == str(int(value >= bound)), (index, predicate, observed)
                checks += 1
    reports.append(dict(id=row["id"], source=row["literal"], display=result["display_text"],
                        copy=result["copy_text"], substitutions_checked=checks))

print(json.dumps(dict(source_sha256=inventory["source_sha256"], worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      inequalities=reports), indent=2, ensure_ascii=False))
