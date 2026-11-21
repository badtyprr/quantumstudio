"""Exercise paired arithmetic table entry, operation headings and preservation of printed cells."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("--worker", type=Path)
parser.add_argument("--verify-windows", action="store_true")
args = parser.parse_args()
source = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][21]
assert source["id"].endswith("M022")
cases = {}
def table(labels, multiply, amend=False):
    op = r"\cdot" if multiply else "+"
    lines = [op + " & " + " & ".join(map(str, labels))]
    cells = [repr("·" if multiply else "+")] + [repr(str(i)) for i in labels]
    for x in labels:
        data = [(x*y if multiply else x+y) % len(labels) for y in labels]
        if amend and x == labels[-1]:
            data[-1] = 17
        row = list(map(str, [x] + data))
        lines.append(" & ".join(row))
        cells.extend(row)
    n = len(labels) + 1
    tex = (r"\begin{array}{c|" + "c"*len(labels) + "}\n" + lines[0] + r"\\\hline" +
           "\n" + (r"\\" + "\n").join(lines[1:]) + "\n" + r"\end{array}")
    return tex, f"matrix({n},{n},[" + ",".join(cells) + "])"

for key, labels in (("source", list(range(6))), ("binary", [0,1]), ("reordered", [2,0,1]), ("changed", [1,0])):
    left, left_copy = table(labels, False)
    right, right_copy = table(labels, True, amend=key=="changed")
    raw = source["literal"] if key=="source" else left + r"\qquad" + right
    cases[key] = (raw, f"vector({left_copy},{right_copy})")
inputs = [[key, raw, "0"] for key, (raw, expected) in cases.items()]
(args.directory / "inputs.json").write_text(json.dumps(inputs), encoding="utf8")
if args.worker:
    worker = args.worker.resolve()
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
    for raw, expected in cases.values():
        for entry in (raw, expected):
            p = subprocess.run([worker, "--json"], input=("quantum:" + entry).encode(), env=env,
                               capture_output=True, timeout=25, check=True)
            actual = json.loads(p.stdout)["copy_text"]
            assert actual == expected, (actual, expected)
if args.verify_windows:
    records = json.loads((args.directory / "records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(cases)
    for r in records:
        assert r["restored_same"] and r["copy_text"] == r["reentry_text"] == cases[r["id"]][1]
    assert args.worker
    print(json.dumps(dict(source=source["id"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          original_tables=2, original_data_cells=72, windows_sessions=len(records),
                          source_and_copy_worker_checks=len(cases)*2), indent=2))
