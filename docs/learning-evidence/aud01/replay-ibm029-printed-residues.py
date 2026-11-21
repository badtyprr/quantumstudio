"""Verify the two printed residues and the order equality in the Shor lesson."""
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
parser.add_argument("--verify-clipboard", action="store_true")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
def evaluate(expr):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,
                          capture_output=True,timeout=30,check=True)
    return json.loads(proc.stdout)["copy_text"]

# A register operator and a classical function graph have distinct Copy forms.
assert evaluate(rows[143]["literal"]) == "qregistermultiplier('a','N','n')"
for name in ("f_a(x)", "f_a ( x )", "(f_a(x))", "f_a((x))"):
    assert evaluate(rows[152]["literal"].replace("f_a(x)",name)) == "qregistermultipliergraph('a','N','n')"
checks = {}
gui = {}
for i in (424,427):
    row = rows[i-1]
    assert row["id"].endswith(f"M{i}")
    copied = evaluate(row["literal"])
    assert copied == evaluate(copied)
    gui[f"M{i}"] = (row["literal"],copied)
    for n in (5,6,15,21):
        for a in (2,5,7):
            for r in (2,4,6,16):
                bound = copied
                for symbol, value in (("r",r),("a",a),("N",n)):
                    bound = f'replace(({bound}),"{symbol}",{value})'
                half = pow(a,r//2,n)
                expected = f"vector({(half-1)%n},{(half+1)%n})" if i==424 else str(int(pow(a,r,n)==1))
                checks[bound] = expected
                if n==15 and a==2 and r in (2,4):
                    gui[f"M{i}-{r}"] = (bound,expected)
def verify(item):
    expr,expected = item
    assert evaluate(expr)==expected,expr
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(verify,checks.items()))
(args.directory/"inputs.json").write_text(json.dumps([[k,v[0],"0"] for k,v in gui.items()]),encoding="utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(gui)
    for r in records:
        assert r["restored_same"] and r["copy"] == r["second_copy"] == gui[r["id"]][1]
    summary=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    print(json.dumps(dict(sources=[rows[i-1]["id"] for i in (424,427)],exact_cases=len(checks),
                          windows_clipboard_cases=len(gui),worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest()),indent=2))
