"""Select an eigenpair by its free index in IBM-027's spectral identity."""
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


def request(body):
    return subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                          capture_output=True, timeout=30)


def copied(body):
    p = request(body)
    assert p.returncode == 0, (body, p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]


def bind(body, assignments):
    for key, value in assignments:
        body = f"replace(({body}),{key},({value}))"
    return body


original = source.strip("$")
canonical = copied(source)
inputs = [[row["id"], row["literal"], "2" if row["id"].endswith("M063") else "0"] for row in rows]
# Only the third eigenpair differs in the mismatching operator. This
# distinguishes a check of the selected eigenpair from a full matrix identity.
family = [("N", 3), ("λ_1", "i"), ("λ_2", 2), ("λ_3", -1),
          ("ψ_1", "basis(1,3)"), ("ψ_2", "basis(2,3)"), ("ψ_3", "basis(0,3)")]
for mismatch, first in [(False, -1), (True, 1)]:
    bindings = family + [("M", f"matrix(3,3,[{first},0,0,0,i,0,0,0,2])")]
    for index in (1, 2, 3):
        expected = "0" if mismatch and index == 3 else "1"
        selector = [("j", index)]
        for body in (original, canonical):
            for order in (selector + bindings, bindings + selector, bindings[::-1] + selector):
                assert copied(bind(body, order)) == expected, (index, order)
                cut = len(order)//2
                saved = copied(bind(body, order[:cut]))
                assert copied(bind(saved, order[cut:])) == expected, (index, saved)
        inputs.append([f"index-{index}-operator-{first}-{expected}", bind(canonical, bindings + selector), "0"])
# The bound of a saved selection is still enforced when N arrives later.
for index in (0, 4, "1/2"):
    rejected = request(bind(canonical, [("j", index), ("N", 3)]))
    assert rejected.returncode != 0 and b"index" in rejected.stderr.lower()
late = copied(bind(canonical, [("j", 4)]))
assert request(bind(late, [("N", 3)])).returncode != 0
# Individual eigenvector and eigenvalue expressions share the same free
# selector as the full derivation, even without a spectral sum in scope.
short = {r["id"][-4:]: r["literal"] for r in rows}
for name, key, value in [("M024", "λ_2", "3"), ("M026", "ψ_2", "basis(1,3)")]:
    for body in (short[name].strip("$"), copied(short[name])):
        assignments = [(key, value), ("j", 2)]
        for order in (assignments, assignments[::-1]):
            saved = copied(bind(body, order[:1]))
            assert copied(bind(saved, order[1:])) == copied(value), (name, order, saved)
        assert copied(bind(body, [("j", 2)])) == copied(short[name].replace("_j", "_2"))
for body in (short["M020"].strip("$").strip().rstrip("."), copied(short["M020"])):
    for weight, expected in [(2, "1"), (3, "0")]:
        data = [("M", "matrix(3,3,[1,0,0,0,2,0,0,0,-1])"),
                ("ψ_2", "basis(1,3)"), ("λ_2", weight)]
        for order in (data + [("j", 2)], [("j", 2)] + data):
            saved = copied(bind(body, order[:2]))
            assert copied(bind(saved, order[2:])) == expected, (order, saved)
same_ket = "replace(replace((|ψ_j> = j |ψ_j>),j,1),ψ_1,basis(0,2))"
assert copied(same_ket) == "1"
name, state = "ψ_j".encode(), b"|0>"
body = "quantum:replace((|ψ_j> = |0>),j,2)".encode()
packet = f"QSTATES1\n1\n{len(name)}\n{len(state)}\n".encode() + name + state + body
literal = subprocess.run([worker, "--json", "--states"], input=packet, capture_output=True, timeout=30)
assert literal.returncode == 0 and json.loads(literal.stdout)["copy_text"] == "1", literal.stderr
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified selection of all three eigenpairs, assignment order, partial copies and range errors.")
