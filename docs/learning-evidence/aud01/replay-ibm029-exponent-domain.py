"""Verify the exponent selection in Shor's classical circuit preparation (IBM-029 M357)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--verify-windows", action="store_true")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
def evaluate(expr):
    proc = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(), env=env,
                          capture_output=True, timeout=30, check=True)
    return json.loads(proc.stdout)["copy_text"]

row = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][356]
assert row["id"].endswith("M357")
raw = row["literal"]
copy = evaluate(raw)
assert evaluate(copy) == copy
checks = {}
for width in (1, 2, 3, 4, 6, 12, 32, 64):
    allowed = {2 ** j for j in range(1, width)}
    for exponent in sorted({-1, 0, 1, 2, 3, 4, 8, 15, 2**(width-1), 2**(width-1)+1, 2**width}):
        expr = f'replace(replace(({copy}),"m",{width}),"k",{exponent})'
        checks[f"m{width}-k{exponent}"] = (expr, str(int(exponent in allowed)))
def verify(item):
    expr, expected = item
    assert evaluate(expr) == expected, expr
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(verify, checks.values()))

gui = {"M357": (raw, copy)}
for key in ("m1-k2", "m2-k2", "m4-k3", "m4-k8", "m64-k9223372036854775808"):
    gui[key] = checks[key]
inputs = [[key, expr, "0"] for key, (expr, _) in gui.items()]
(args.directory / "inputs.json").write_text(json.dumps(inputs), encoding="utf8")
if args.verify_windows:
    records = json.loads((args.directory / "records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(gui)
    for record in records:
        assert record["restored_same"] and record["copy_text"] == record["reentry_text"] == gui[record["id"]][1]
    print(json.dumps(dict(source=row["id"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          widths=[1,2,3,4,6,12,32,64], exact_memberships=len(checks),
                          windows_sessions=len(records)), indent=2))
