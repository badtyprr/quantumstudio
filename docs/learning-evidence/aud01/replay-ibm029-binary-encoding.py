"""Check every decimal input and fixed-width binary output in the printed encoding."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--verify-clipboard", action="store_true")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
row = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][140]
assert row["id"].endswith("M141")
cases = {"M141": (row["literal"], 5, 20)}
for width, end in ((2, 3), (4, 11), (6, 32), (8, 63), (7, 127), (10, 1023)):
    lines = [rf"{i}\mapsto {i:0{width}b}" for i in (0, 1, 2)] if end > 3 else [r"0\mapsto 00", r"1\mapsto 01"]
    lines.extend([r"\vdots", rf"{end}\mapsto {end:0{width}b}"])
    cases[f"width-{width}"] = (r"\begin{gather}" + r"\\".join(lines) + r"\end{gather}", width, end)

def evaluate(expr):
    p = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(), env=env,
                       capture_output=True, check=True, timeout=30)
    return json.loads(p.stdout)

expected = {}
for key, (expr, width, end) in cases.items():
    entries = [f"qtuple(vector({x},qbitlabel({x},{width})))" for x in range(end+1)]
    expected[key] = ("qset(vector(" + ",".join(entries) + "))" if end < 64 else
                     f"qsetimage(qtuple(vector(j,qbitlabel(j,{width}))),qindexrange(0,{end}),j)")
    result = evaluate(expr)
    assert result["copy_text"] == evaluate(expected[key])["copy_text"] == expected[key], key
    pairs = re.findall(r"qtuple\(\[(\d+)\s+qbitlabel\((\d+), (\d+)\)\]\)", result["text"])
    assert pairs == [(str(x),str(x),str(width)) for x in range(end+1)], key
(args.directory/"inputs.json").write_text(json.dumps([[key, case[0], "0"] for key, case in cases.items()]), "utf8")
if args.verify_clipboard:
    records = json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(cases)
    for record in records:
        assert record["restored_same"] and record["copy"] == record["second_copy"] == expected[record["id"]]
    summary = json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    print(json.dumps(dict(source=row["id"], source_entries=21, checked_entries=sum(c[2]+1 for c in cases.values()),
                          clipboard_sessions=len(records), worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest()), indent=2))
