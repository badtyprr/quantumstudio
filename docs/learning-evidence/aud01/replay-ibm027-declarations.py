"""Check every truth assignment in the simultaneous eigensystem equations of M034."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())
rows = inventory["lessons"][1]["rows"]
source = next(row["literal"] for row in rows if row["id"].endswith("M034"))


def evaluate(body):
    result = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, (body, result.stderr.decode())
    return json.loads(result.stdout)


def bind(body, assignments):
    for key, value in assignments:
        body = f"replace(({body}),{key},{value})"
    return body


assert evaluate("vector(1=1,2=3)")["copy_text"] == "vector(1,0)"
record = evaluate(source)
copied = record["copy_text"]
assert evaluate(copied)["copy_text"] == copied
inputs = [[row["id"], row["literal"]] for row in rows]
equations = [("λ_1", "1", "2"), ("λ_2", "1", "-1"),
             ("ψ_1", "|0>", "|1>"), ("ψ_2", "|1>", "|0>")]
original = source.strip("$").strip().rstrip(".")
for flags in itertools.product((False, True), repeat=len(equations)):
    expected = str(int(all(flags)))
    assignments = [(key, yes if flag else no)
                   for flag, (key, yes, no) in zip(flags, equations)]
    for body in (original, copied, record["display_text"]):
        for order in (assignments, assignments[::-1]):
            result = evaluate(bind(body, order))
            assert result["copy_text"] == expected, (flags, body, result)
    if sum(flags) >= 3:
        name = "".join(str(int(flag)) for flag in flags)
        inputs.append([f"declarations-{name}-{expected}", bind(copied, assignments)])
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified all 16 eigensystem assignments in both orders from source, display and Copy.")
