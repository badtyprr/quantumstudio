"""Check the four equalities in IBM-027's eigenvector derivation."""
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
source = next(row["literal"] for row in rows if row["id"].endswith("M023"))


def evaluate(body):
    p = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.stderr.decode())
    return json.loads(p.stdout)


def bind(body, assignments):
    for key, value in assignments:
        body = f"replace(({body}),{key},{value})"
    return body


inputs = [[r["id"], r["literal"]] for r in rows]
record = evaluate(source)
copied = record["copy_text"]
assert evaluate(copied)["copy_text"] == copied
basis = [("N", 2), ("λ_1", 1), ("λ_2", -1), ("ψ_1", "|+i>"), ("ψ_2", "|-i>")]
cases = [("first", "Y", "|+i>", 1, "1"), ("second", "Y", "|-i>", -1, "1"),
         ("wrong-eigenvalue", "Y", "|-i>", 1, "0"), ("wrong-operator", "X", "|+i>", 1, "0"),
         ("superposition", "Y", "|0>", 1, "0")]
for name, operator, state, weight, answer in cases:
    assignments = basis + [("M", operator), ("ψ_j", state), ("λ_j", weight)]
    for body in (source.strip("$"), record["display_text"], copied):
        for order in (assignments, assignments[::-1]):
            result = evaluate(bind(body, order))
            assert result["copy_text"] == answer, (name, body, result)
    inputs.append([f"{name}-{answer}", bind(copied, assignments)])
for index in (1, 2):
    indexed = source.strip("$").replace("_j", f"_{index}")
    assert evaluate(bind(indexed, basis + [("M", "Y")]))["copy_text"] == "1"

# An overlap expansion acts on an arbitrary column; orthogonality is optional.
action = r"\sum_{k=1}^{N} a_k \vert u_k\rangle\langle u_k\vert v_j\rangle"
samples = [
    ([("N", 0), ("v_j", "|1>")], "matrix(2,1,[0,0])"),
    ([("N", 1), ("a_1", 2), ("u_1", "|+i>"), ("v_j", "|0>")], "matrix(2,1,[1,i])"),
    ([("N", 2), ("a_1", 2), ("a_2", 3), ("u_1", "|0>"), ("u_2", "|+>"), ("v_j", "|1>")],
     "matrix(2,1,[3/2,3/2])"),
]
for assignments, expected in samples:
    assert evaluate(bind(action, assignments) + "=" + expected)["copy_text"] == "1"
dependent = action.replace("v_j", "v_k")
assert "qspectralaction" not in evaluate(dependent)["copy_text"]
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified eigenvector identities, complex overlaps and independent substitutions.")
