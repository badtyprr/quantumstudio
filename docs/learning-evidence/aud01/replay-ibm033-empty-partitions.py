"""Verify Grover search partition emptiness on all two-bit Boolean oracles."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report", type=Path)
reports.add_argument("--session-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            env=env, check=True, capture_output=True, timeout=30)
    value = json.loads(result.stdout)
    assert not value["approximate"]
    return value["copy_text"]


def words(indices):
    return "qset(vector(" + ",".join(f"qbitlabel({i},2)" for i in sorted(indices)) + "))"


cases = {}
copies = {}
for i in (5, 11, 12):
    literal = inventory["rows"][i - 1]["literal"]
    copy = evaluate(literal)
    assert evaluate(copy) == copy
    copies[i] = copy
    cases[f"M{i:03}"] = literal, copy

for mask in range(16):
    marked = {i for i in range(4) if mask & (1 << i)}
    unmarked = set(range(4)) - marked
    for i, truth in ((5, True), (11, not unmarked), (12, not marked)):
        expression = f'replace(({copies[i]}),vector("A_0","A_1"),vector({words(unmarked)},{words(marked)}))'
        expected = str(int(truth))
        assert evaluate(expression) == expected, (mask, i)
        if mask in (0, 5, 15):
            cases[f"M{i:03}-mask-{mask}"] = expression, expected
overlap = f'replace(({copies[5]}),vector("A_0","A_1"),vector({words({0, 1})},{words({1, 2})}))'
assert evaluate(overlap) == "0"
cases["overlapping-partition"] = overlap, "0"
clipboard_checks(worker, args.windows, args.report or args.session_report, cases, 13,
                 dict(source_sha256=inventory["source_sha256"], source_rows=[5, 11, 12],
                      boolean_oracles=16, bound_checks=49), sessions_only=bool(args.session_report))
