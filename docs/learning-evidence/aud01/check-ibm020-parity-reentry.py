"""Check IBM-020 M047 before and after copying, with both bit-string and scalar bindings."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
def evaluate(expression):
    reply = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                           env=env, capture_output=True, check=True, timeout=30)
    return json.loads(reply.stdout)["copy_text"]

source = r"z\cdot x = 0"
copy = evaluate(source)
assert evaluate(copy) == copy
def check(case):
    formula, label_type, x, z = case
    value = lambda i: f"bitstring({i},4)" if label_type else str(i)
    bound = f"replace(replace({formula},x,{value(x)}),z,{value(z)})"
    expected = ((x & z).bit_count() % 2 == 0) if label_type else (x * z == 0)
    assert evaluate(bound) == str(int(expected)), bound

cases = [(formula, typed, x, z) for formula in (source, copy) for typed in (True, False)
         for x in range(16) for z in range(16)]
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(check, cases))
report = dict(source_id="R13-0-M047", source=source, copy=copy, stable=True,
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              typed_and_scalar_comparisons=len(cases))
args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
