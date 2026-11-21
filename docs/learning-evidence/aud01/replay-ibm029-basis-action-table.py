"""Compare printed basis actions with independently constructed linear operators."""
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
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expr):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,
                            capture_output=True,timeout=30,check=True)
    return json.loads(result.stdout)["copy_text"]

row = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][67]
assert row["id"].endswith("M068")
def matrix(images):
    n = len(images)
    entries = [str(int(y==image)) for y in range(n) for image in images]
    return f"matrix({n},{n},[" + ",".join(entries) + "])"

cases = {"M068":(row["literal"],matrix([2*x%15 for x in range(15)]))}
for n in (2,3,4,5,8,12,16):
    for label,images in (("shift",[(i+1)%n for i in range(n)]),("collapse",[0]*n)):
        inputs = [rf"M_3\vert {i}\rangle=\vert {images[i]}\rangle" for i in reversed(range(n))]
        tex = r"\begin{array}{c}" + r"\\".join(inputs) + r"\end{array}"
        cases[f"{label}-{n}"] = (tex,matrix(images))
for expr,expected in cases.values():
    assert evaluate(expr)==evaluate(expected)==expected,expr
keys = ["M068","shift-3","collapse-3","shift-8","shift-16"]
(args.directory/"inputs.json").write_text(json.dumps([[k,cases[k][0],"0"] for k in keys]),encoding="utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == keys
    for r in records:
        assert r["restored_same"] and r["copy"]==r["second_copy"]==cases[r["id"]][1]
    summary=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    print(json.dumps(dict(source=row["id"],source_dimension=15,source_entries=225,matrices=len(cases),
                          clipboard_sessions=len(keys),worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest()),indent=2))
