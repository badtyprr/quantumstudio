"""Check descending system and outcome tuples against the two original lesson inventories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))

def evaluate(expr):
    result = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(),
                            timeout=30, capture_output=True, env=env, check=True)
    return json.loads(result.stdout)["copy_text"]

cases = {}
hashes = {}
for lesson, numbers in [("041", (39,41,165)), ("042", (41,87,240,251))]:
    inventory = json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())
    hashes[lesson] = inventory["source_sha256"]
    for number in numbers:
        row = inventory["rows"][number-1]
        prefix = "a_" if lesson == "041" and number == 41 else "X_"
        literal = row["literal"]
        copy = evaluate(literal)
        assert copy == f'qreverseindexedlist("{prefix}",0,qsub(n,1),vector())'
        cases[row["id"]] = literal, copy
        for count in (1, 4, 32):
            expr = f"replace(({copy}),n,{count})"
            expected = "qtuple(vector("+",".join(f'"{prefix}{i}"' for i in reversed(range(count)))+"))"
            assert evaluate(expr) == expected
            cases[f'{row["id"]}-count-{count}'] = expr, expected
        for early in (True, False):
            label = f'"{prefix}1"'
            bindings = [(label, 7), ("n", 3)]
            expr = copy
            for key, value in bindings if early else reversed(bindings):
                expr = f"replace(({expr}),{key},{value})"
            expected = f'qtuple(vector("{prefix}2",7,"{prefix}0"))'
            assert evaluate(expr) == expected
            cases[f'{row["id"]}-early-{int(early)}'] = expr, expected

    # These literal lists previously returned empty tuples.
    number, count = (47, 10) if lesson == "041" else (171, 5)
    row = inventory["rows"][number-1]
    expected = "qtuple(vector("+",".join(f'"X_{i}"' for i in reversed(range(count)))+"))"
    assert evaluate(row["literal"]) == expected
    cases[row["id"]] = row["literal"], expected

clipboard_checks(worker, args.windows, args.report, cases, 44,
                 dict(source_sha256=hashes, original_occurrences=9,
                      application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()))
