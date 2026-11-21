"""Check the printed ring annotation on the entire equality in IBM-029 M037."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--verify-clipboard", action="store_true")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
row = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][36]
assert row["id"].endswith("M037")
def check(expr, expected):
    proc = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(), env=env,
                          capture_output=True, timeout=20, check=True)
    assert json.loads(proc.stdout)["copy_text"] == str(int(expected)), expr

cases = {"original": (row["literal"], True), "ordinary": (r"$5^2=1$",False)}
for n in (2,6,7,21):
    for base in (-3,0,2,5):
        for exponent in (0,2,5):
            value = pow(base,exponent,n)
            for delta in (0,1):
                target = value + delta
                expr = r"$$(" + str(base) + ")^{" + str(exponent) + "}=" + str(target+n) + r"\quad\text{(working within $\mathbb{Z}_{" + str(n) + "}$)}$$"
                # Exact integer power agrees with the stated representative modulo n.
                cases[f"{n}_{base}_{exponent}_{delta}"] = (expr, pow(base,exponent,n)==target%n)
for expr, expected in cases.values(): check(expr,expected)
keys = ["original","ordinary","2_-3_2_1","6_5_2_0","7_5_2_1","21_2_5_0"]
(args.directory/"inputs.json").write_text(json.dumps([[k,cases[k][0],"0"] for k in keys]),encoding="utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == keys
    for r in records:
        assert r["restored_same"] and r["copy"]==r["second_copy"]==str(int(cases[r["id"]][1]))
    gui=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert gui["passed"] and gui["clipboardRestored"] and not gui["sessionsOnly"]
    print(json.dumps(dict(source=row["id"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          exact_cases=len(cases),clipboard_cases=len(keys)),indent=2))
