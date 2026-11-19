"""Compare the two printed forms of IBM-027's spectral decomposition."""
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
source = {row["id"][-4:]: row["literal"] for row in rows}

def evaluate(body):
    p = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.stderr)
    return json.loads(p.stdout)

def bind(body, entries):
    for name, term in entries:
        body = f"replace(({body}),{name},{term})"
    return body

def assignment(weights, states, operator):
    return [("N", len(weights)), ("M", operator),
            *[(f"λ_{i}", term) for i, term in enumerate(weights, 1)],
            *[(f"ψ_{i}", term) for i, term in enumerate(states, 1)]]

cases = [
    ("diagonal", assignment([1, -1], ["|0>", "|1>"], "Z"), "1"),
    ("wrong-operator", assignment([1, -1], ["|0>", "|1>"], "X"), "0"),
    ("degenerate", assignment([3, 3], ["|+>", "|->"], "3*identity(2)"), "1"),
    ("complex-states", assignment([1, -1], ["|+i>", "|-i>"], "Y"), "1"),
    ("wrong-phase", assignment([1, -1], ["|+i>", "|-i>"], "-Y"), "0"),
    ("complex-eigenvalues", assignment(["i", "-i"], ["|0>", "|1>"], "i*Z"), "1"),
    ("three-level", assignment([2, 3, 5], ["basis(2,3)", "basis(0,3)", "basis(1,3)"],
                               "matrix(3,3,[3,0,0,0,5,0,0,0,2])"), "1"),
]
inputs = [[r["id"], r["literal"]] for r in rows]
canonical = evaluate(source["M017"])["copy_text"]
for key in ("M016", "M017"):
    record = evaluate(source[key])
    assert record["copy_text"] == canonical
    original = source[key].strip("$").strip().rstrip(".").replace(r"\tag{1}", "")
    for body in (original, record["display_text"], canonical):
        assert evaluate(body)["copy_text"] == canonical
        for _, bindings, expected in cases:
            for ordered in (bindings, reversed(bindings)):
                assert evaluate(bind(body, ordered))["copy_text"] == expected
    # Reopen a partially bound expression before supplying the dimension.
    _, bindings, expected = cases[3]
    partial = evaluate(bind(canonical, bindings[2:]))["copy_text"]
    assert evaluate(bind(partial, bindings[:2]))["copy_text"] == expected
for name, bindings, expected in cases:
    inputs.append([f"{name}-{expected}", bind(canonical, bindings)])
# A single projector on a two-dimensional state is a valid partial sum.
partial = r"\sum_{j=1}^1 a_j \vert v_j\rangle\langle v_j\vert"
assert evaluate(bind(partial, [("a_1", 2), ("v_1", "|0>")])+"=matrix(2,2,[2,0,0,0])")["copy_text"] == "1"
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified both spectral forms against seven operator assignments in both binding orders.")
