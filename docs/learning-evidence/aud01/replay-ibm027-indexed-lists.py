"""Replay the eigenvalue lists and their one-based index domain in IBM-027."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
report = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())
rows = report["lessons"][1]["rows"]
by_id = {r["id"][-4:]: r["literal"] for r in rows}

def run(expression):
    return subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                          capture_output=True, timeout=30)

def evaluate(expression):
    p = run(expression)
    assert p.returncode == 0, (expression, p.stderr)
    return json.loads(p.stdout)

def forms(key):
    source = by_id[key]
    record = evaluate(source)
    cases = source.strip("$"), record["display_text"], record["copy_text"]
    assert all(evaluate(form)["copy_text"] == record["copy_text"] for form in cases)
    return cases

def tup(values):
    return "qtuple(vector(" + ",".join(values) + "))"

for key in ("M015", "M035", "M047"):
    for body in forms(key):
        for n in (0, 1, 3):
            expected = tup([f'"λ_{j}"' for j in range(1, n + 1)])
            assert evaluate(f"replace(({body}),N,{n})")["copy_text"] == expected
        # Repeated eigenvalues retain their two slots. Supply values before
        # and after binding the dimension, including via displayed history.
        partial = evaluate(f"replace(replace(({body}),λ_2,5),λ_1,5)")
        for saved in (partial["copy_text"], partial["display_text"]):
            assert evaluate(f"replace(replace(({saved}),N,3),λ_3,-1)")["copy_text"] == tup(["5","5","−1"])

for body in forms("M021"):
    for j in ("0", "1", "2", "3", "4", "3/2"):
        answer = j in ("1", "2", "3")
        assert evaluate(f"replace(replace(({body}),N,3),j,{j})")["copy_text"] == str(int(answer))
controls = [
    ("slice", "a_2,...,a_4", tup(['"a_2"','"a_3"','"a_4"'])),
    ("duplicates", "replace(replace((a_1,...,a_2),a_1,7),a_2,7)", tup(["7","7"])),
    ("empty", "a_2,...,a_1", tup([])),
    ("inside", "replace((j=1,...,3),j,3)", "1"),
    ("outside", "replace((j=1,...,3),j,0)", "0"),
    ("fractional-index", "replace((j=1,...,3),j,3/2)", "0"),
]
for name, expr, expected in controls:
    assert evaluate(expr)["copy_text"] == expected, name
for bad in ("a_1,...,b_N", "a_01,...,a_3", "replace((a_1,...,a_N),N,2.5)", "a_1,...,a_1025"):
    assert run(bad).returncode == 2, bad
if args.gui_inputs:
    inputs = [[r["id"], r["literal"]] for r in rows]
    inputs.extend([[key, expr] for key, expr, _ in controls])
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified three ordered eigenvalue lists, repeated values and integer index membership.")
