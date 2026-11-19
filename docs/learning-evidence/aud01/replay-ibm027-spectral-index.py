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
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified selection of all three eigenpairs, assignment order, partial copies and range errors.")
