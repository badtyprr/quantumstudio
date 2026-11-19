"""Verify that binding a copied periodic phase relation preserves its truth value."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
source = next(row["literal"] for row in rows if row["id"].endswith("M072"))


def evaluate(body):
    p = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.stderr.decode())
    return json.loads(p.stdout)


def bind(body, key, value):
    return f"replace(({body}),{key},({value}))"


record = evaluate(source)
copied = record["copy_text"]
assert evaluate(copied)["copy_text"] == copied
inputs = [[row["id"], row["literal"]] for row in rows]
cases = [("origin", "0", "1", "1"), ("quarter", "1/4", "i", "1"),
         ("full-turn", "5/4", "i", "1"), ("negative", "-1/4", "-i", "1"),
         ("half", "1/2", "-1", "1"), ("wrong-phase", "1/4", "1", "0"),
         ("wrong-radius", "0", "2", "0"), ("zero-value", "0", "0", "0")]
for name, theta, eigenvalue, expected in cases:
    inputs.append([f"{name}-{expected}", bind(bind(copied, "λ", eigenvalue), "θ", theta)])
    for body in (source.strip("$").strip(), record["display_text"], copied):
        for first, last in [(("λ", eigenvalue), ("θ", theta)), (("θ", theta), ("λ", eigenvalue))]:
            partial = bind(body, *first)
            assert evaluate(bind(partial, *last))["copy_text"] == expected, (name, body)
            saved = evaluate(partial)["copy_text"]
            assert evaluate(bind(saved, *last))["copy_text"] == expected, (name, saved)
# Check the eigenvector and phase forms of the same equation. Save after
# binding the state but before choosing its eigenvalue or phase.
for row_id, parameter, correct, wrong in [("M052", "λ", "i", "-i"), ("M083", "θ", "1/4", "3/4")]:
    row = next(r for r in rows if r["id"].endswith(row_id))
    body = evaluate(row["literal"])["copy_text"]
    for state in ("|1>", "2|1>"):
        partial = bind(bind(body, "U", "S"), "ψ", state)
        saved = evaluate(partial)["copy_text"]
        for value, expected in [(correct, "1"), (wrong, "0")]:
            for expression in (partial, saved):
                assert evaluate(bind(expression, parameter, value))["copy_text"] == expected, (row_id, saved)
    inputs.append([f"{row_id}-eigenstate-1", bind(saved, parameter, correct)])
    inputs.append([f"{row_id}-mismatch-0", bind(saved, parameter, wrong)])
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified eight phases in both assignment orders, including partially bound copies.")
