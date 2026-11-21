"""Verify the paired overlaps of the uniform state with both Grover subspaces."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())
source = inventory["rows"][68]
assert source["id"].endswith("M069") and source["status"] == "diagnostic"


def evaluate(s):
    p = subprocess.run([worker,"--json"],input=("quantum:"+s).encode(),env=env,
                       capture_output=True,check=True,timeout=30)
    return json.loads(p.stdout)


def normalized(size, support):
    entries = ";".join(str(int(i in support)) for i in range(size))
    return f"[{entries}]/sqrt({len(support)})"


result = evaluate(source["literal"])
checks = []
for size, marked in [(2,{1}), (4,{0}), (4,{0,2}), (8,{1,4,7})]:
    whole = set(range(size))
    unmarked = whole - marked
    for first_error, second_error in [(0,0), (1,0), (0,1), (1,1)]:
        substitutions = [
            ('qbars("A_0")', len(unmarked)+first_error),
            ('qbars("A_1")', len(marked)+second_error),
            ('N', size),
            ('qnamedket("A_0")', normalized(size,unmarked)),
            ('qnamedket("A_1")', normalized(size,marked)),
            ('qketstate("u")', normalized(size,whole)),
        ]
        for form in ("display_text","copy_text"):
            expr = result[form]
            for key, value in substitutions:
                expr = f"replace(({expr}),{key},{value})"
            observed = evaluate(expr)
            expected = str(int(not (first_error or second_error)))
            assert observed["copy_text"] == expected and not observed["approximate"], (form,expr,observed)
    checks.append(dict(size=size,marked=sorted(marked),input_pairs=4,forms=2))

print(json.dumps(dict(source_id=source["id"],source_sha256=inventory["source_sha256"],
                      worker_sha256=sha256(worker.read_bytes()).hexdigest(),literal=source["literal"],
                      display=result["display_text"],copy=result["copy_text"],partitions=checks),
                 ensure_ascii=False,indent=2))
